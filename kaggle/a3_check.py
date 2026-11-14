"""A3 on Kaggle: serve Kev on the GPU, call it through TRL, time answering and fine-tuning.

Runs under the TRL venv's Python. Starts `kev.serve` from the Kev checkout's own venv,
then:
  1. environment: GPU, driver, torch build, bf16 support
  2. endpoint: one call through TRL's LLMSession (the A3 "done when")
  3. answering speed through TRL, projected to the full run (~300k answers)
  4. fine-tuning on this GPU with Kev's own recipe (copied from the checkpoint's metadata),
     on short (C4-like) and long (C3-like) states, projected to C3 and C4
and writes everything to one JSON report.

All profiles and labels here are synthetic and exist only for timing. Nothing here is
research data.

    python a3_check.py --kev-dir /tmp/work/kev --out /kaggle/working/a3_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

FULL_ANSWERS = 3000 * 100  # founders x RRF's default ~100 questions (10 prompts x 10)
TRAIN_RECORDS = 2000  # train split
TRAIN_EPOCHS = 2

INDUSTRIES = ["fintech", "healthtech", "logistics", "edtech", "climate", "B2B SaaS",
              "cybersecurity", "e-commerce", "biotech", "gaming", "insurtech", "agtech"]
FACTS = [
    "the founder has a technical background", "the founder has a business background",
    "the founder has founded a startup before", "the founder has a prior exit",
    "the founder attended a top-50 university", "the founder has a PhD",
    "the founder has an MBA", "the founder has no degree",
    "the founder has more than 10 years of work experience",
    "the founder has deep experience in the startup's industry",
    "the founder worked at a company with more than 5,000 employees",
    "the founder worked at a startup with fewer than 50 employees",
    "the founder is a solo founder", "the startup has three or more co-founders",
    "the founder held a management role", "the founder held an engineering role",
    "the founder worked in consulting", "the founder worked in finance",
    "the founder changed industries during their career",
    "the founder stayed at one employer for more than 5 years",
    "the founder's prior startup shut down", "the founder studied a STEM field",
    "the founder worked in sales or business development",
    "the founder has research experience", "the founder worked abroad",
]
PHRASINGS = ["Does the profile show that {}?", "Is it true that {}?",
             "Based on the profile, {}?", "Would you say {}?"]


def questions() -> dict[str, str]:
    texts = [p.format(f) for p in PHRASINGS for f in FACTS]
    return {f"q{i:03d}": t[0].upper() + t[1:] for i, t in enumerate(texts)}


def profile(rng: random.Random) -> str:
    return (
        f"This founder leads a startup in the {rng.choice(INDUSTRIES)} industry, founded with "
        f"{rng.choice(['solo', '1', '2', '3+'])} co-founder(s).\n"
        f"Founder background: {rng.choice(['technical', 'business', 'mixed'])}, "
        f"{rng.choice(['<5', '5-10', '10-15', '15+'])} years of work experience, "
        f"{rng.choice(['none', 'some', 'deep'])} prior experience in this startup's industry.\n"
        "Education:\n"
        f"- {rng.choice(['BSc', 'BA', 'MSc', 'MBA', 'PhD'])} in "
        f"{rng.choice(['Economics', 'Computer Science', 'Biology', 'History'])}, "
        f"university ranked QS {rng.choice(['top 50', '51-100', '101-300', '300+'])}\n"
        "Jobs (oldest first):\n"
        f"- Analyst, a management consulting firm, 1,001-5,000 employees, Professional Services, "
        f"{rng.choice(['1-2', '2-3', '3-5'])} years\n"
        f"- {rng.choice(['Product Manager', 'Software Engineer', 'Operations Manager'])}, a "
        f"{rng.choice(['payments', 'freight', 'software'])} company, 201-1,000 employees, "
        f"{rng.choice(['Financial Services', 'Logistics', 'Software'])}, 3-5 years\n"
        f"Prior startups: {rng.choice(['none', '1 founded before, with outcomes 1 shut down'])}.\n"
        "Prior exits: none."
    )


def serialised_answers(rng: random.Random) -> str:
    """A C3-like state: one line per rule, '<question> yes|no'."""
    return "\n".join(f"{q} {rng.choice(['yes', 'no'])}" for q in questions().values())


# ---------------------------------------------------------------------------


def sh(cmd: list[str], **kw) -> str:
    """A command's stdout, or '' if the program isn't installed (e.g. nvidia-smi on CPU)."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()
    except FileNotFoundError:
        return ""


def environment(kev_py: str) -> dict:
    info: dict = {"nvidia_smi": sh(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                    "--format=csv,noheader"]) or "none"}
    probe = (
        "import json, torch\n"
        "d = {'torch': torch.__version__, 'cuda_build': torch.version.cuda,\n"
        "     'cuda_available': torch.cuda.is_available()}\n"
        "if torch.cuda.is_available():\n"
        "    d.update(device=torch.cuda.get_device_name(0),\n"
        "             capability='.'.join(map(str, torch.cuda.get_device_capability(0))),\n"
        "             arch_list=torch.cuda.get_arch_list(),\n"
        "             bf16_native=torch.cuda.get_device_capability(0)[0] >= 8)\n"
        "print(json.dumps(d))\n"
    )
    out = sh([kev_py, "-c", probe])
    try:
        info.update(json.loads(out.splitlines()[-1]))
    except (json.JSONDecodeError, IndexError):
        info["torch_probe_error"] = out[-500:]
    return info


def start_server(kev_dir: Path, kev_py: str, model: str, port: int, device: str, dtype: str,
                 log: Path, timeout: float) -> tuple[subprocess.Popen, dict]:
    env = {**os.environ, "KEV_DTYPE": dtype}
    proc = subprocess.Popen(
        [kev_py, "-m", "kev.serve", "--run", model, "--port", str(port), "--device", device],
        cwd=kev_dir, env=env, stdout=log.open("w"), stderr=subprocess.STDOUT,
    )
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"kev.serve exited ({proc.returncode}); see {log}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5) as r:
                models = json.load(r)["models"][0]
            keep = ("run", "base", "lora", "device", "backend", "dtype", "temperature")
            return proc, {"load_seconds": round(time.time() - t0, 1),
                          **{k: models.get(k) for k in keep}}
        except OSError:
            time.sleep(3)
    proc.kill()
    raise TimeoutError(f"kev.serve not up after {timeout:.0f}s; see {log}")


def trl_answers(url: str, samples: list[str], qs: dict[str, str]) -> tuple[list, float]:
    """Answers through TRL's LLMSession, on TRL's own event loop (as RRF runs them)."""
    from think_reason_learn.llm import LLM, LLMSession, YesNoQuestion, set_config
    from think_reason_learn.llm._loop import run_sync
    from think_reason_learn.llm._spec import resolve

    set_config(cache=False)
    endpoint = resolve(LLM("kev", base_url=f"{url}/v1/systemone", kind="decision",
                           api_key="local"))
    questions_ = {k: YesNoQuestion(v) for k, v in qs.items()}

    async def run():
        return await LLMSession().answer([endpoint], samples, questions_, role="answerer")

    t0 = time.time()
    out = run_sync(run())
    return out, time.time() - t0


def endpoint_check(url: str) -> dict:
    sample = ("This founder leads a startup in the logistics industry, founded with 1 "
              "co-founder(s).\nPrior startups: none.\nPrior exits: none.")
    qs = {"exit": "Does the founder have a prior exit?",
          "logistics": "Is the startup in the logistics industry?"}
    out, secs = trl_answers(url, [sample], qs)
    return {"ok": all(a is not None for a in out[0].values()), "seconds": round(secs, 2),
            "answers": {k: a.probabilities if a else None for k, a in out[0].items()}}


def speed_check(url: str, n_samples: int, n_questions: int) -> dict:
    rng = random.Random(42)
    qs = dict(list(questions().items())[:n_questions])
    samples = [profile(rng) for _ in range(n_samples)]
    trl_answers(url, samples[:1], dict(list(qs.items())[:2]))  # warm-up
    out, secs = trl_answers(url, samples, qs)
    answered = sum(a is not None for row in out for a in row.values())
    rate = answered / secs if secs else 0.0
    return {"samples": n_samples, "questions": n_questions, "answers": answered,
            "seconds": round(secs, 1), "answers_per_second": round(rate, 1),
            "projected_full_run_hours": round(FULL_ANSWERS / rate / 3600, 2) if rate else None,
            "note": "through TRL's LLMSession, default concurrency, cache off"}


class GpuMemory(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.peak_mib, self.stop = 0, threading.Event()

    def run(self):
        while not self.stop.is_set():
            out = sh(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"])
            if out:
                self.peak_mib = max(self.peak_mib, max(int(x) for x in out.split()))
            time.sleep(1)


def recipe(kev_py: str, model: str) -> dict:
    """The checkpoint's own architecture and training args (Kev's fine-tune recipe)."""
    code = (
        "import json\nfrom kev.checkpoint import Checkpoint\n"
        f"m = Checkpoint({model!r}).meta; a = m.extra['args']\n"
        "print(json.dumps({'base': m.base, 'base_revision': m.base_revision, 'lora': m.lora,"
        " 'head_dim': m.head_dim, 'lora_targets': a['lora_targets'],"
        " 'option_isolation': int(m.option_isolation),"
        " 'special_embeddings': int(m.special_embeddings), 'weights_dtype': m.weights_dtype,"
        " 'batch': a['batch'], 'accum': a['accum'], 'checkpointing': a['checkpointing'],"
        " 'p_none_pair': a['p_none_pair'], 'lr': a['lr']}))\n"
    )
    return json.loads(sh([kev_py, "-c", code]).splitlines()[-1])


def state_tokens(kev_py: str, base: str, texts: list[str]) -> list[int]:
    code = (
        "import json, sys\nfrom transformers import AutoTokenizer\n"
        f"tok = AutoTokenizer.from_pretrained({base!r})\n"
        "print(json.dumps([len(tok(t)['input_ids']) for t in json.load(sys.stdin)]))\n"
    )
    out = subprocess.run([kev_py, "-c", code], input=json.dumps(texts), capture_output=True,
                         text=True).stdout.strip().splitlines()
    return json.loads(out[-1]) if out else []


def train_check(kev_dir: Path, kev_py: str, model: str, device: str, dtype: str, kind: str,
                n_records: int, batch: int, max_state: int, work: Path,
                timeout: float) -> dict:
    rng = random.Random(7)
    data = work / f"train_{kind}.jsonl"
    states = [serialised_answers(rng) if kind == "long" else profile(rng)
              for _ in range(n_records)]
    with data.open("w") as fh:
        for i, state in enumerate(states):
            fh.write(json.dumps({"state": state, "questions": {"success": {
                "type": "noul",
                "instructions": "Will this founder's company succeed (exit, IPO or funding "
                                "over $500M)?",
                "label": bool(i % 5 == 0)}}}) + "\n")
    r = recipe(kev_py, model)
    lengths = state_tokens(kev_py, r["base"], states)
    attempts = [{"batch": batch, "accum": 1, "checkpointing": r["checkpointing"]},
                {"batch": batch, "accum": 1, "checkpointing": 1},
                {"batch": max(1, batch // 2), "accum": 2, "checkpointing": 1}]
    tried = []
    for cfg in attempts:
        out = work / f"run_{kind}_{len(tried)}"
        cmd = [kev_py, "-m", "kev.train", "--data", str(data), "--init_from", model,
               "--out", str(out), "--device", device, "--dtype", dtype,
               "--base", r["base"], "--lora", r["lora"], "--head_dim", r["head_dim"],
               "--lora_targets", r["lora_targets"], "--option_isolation", r["option_isolation"],
               "--special_embeddings", r["special_embeddings"],
               "--weights_dtype", r["weights_dtype"], "--epochs", 1, "--lr", 2e-5,
               "--batch", cfg["batch"], "--accum", cfg["accum"],
               "--checkpointing", cfg["checkpointing"], "--seed", 42,
               "--p_none_pair", r["p_none_pair"], "--max_state", max_state]
        if r.get("base_revision"):
            cmd += ["--base_revision", r["base_revision"]]
        cmd = [str(c) for c in cmd]
        mem = GpuMemory()
        mem.start()
        t0 = time.time()
        try:
            proc = subprocess.run(cmd, cwd=kev_dir, capture_output=True, text=True,
                                  timeout=timeout)
            log, code = proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            raw = exc.stdout or ""
            log = raw.decode() if isinstance(raw, bytes) else raw
            code = "timeout"
        mem.stop.set()
        secs = time.time() - t0
        (work / f"train_{kind}_{len(tried)}.log").write_text(log)
        metrics_path = out / "training_metrics.json"
        m = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
        steps = m.get("step_seconds") or []
        # The first step includes warm-up; time the rest when there are any.
        timed = steps[1:] or steps
        per_step = sorted(timed)[len(timed) // 2] if timed else None
        # CUDA OOM prints "out of memory"; a host-RAM OOM kills the process (-9).
        oom = "out of memory" in log.lower() or code == -9
        result = {**cfg, "returncode": code, "seconds": round(secs, 1),
                  "optimizer_steps": m.get("optimizer_steps"),
                  "median_step_seconds": per_step,
                  "records_seen": m.get("records_seen"),
                  "rejected_records": m.get("rejected_records"),
                  "truncated_records": m.get("truncated_records"),
                  "peak_device_mib": round(m["peak_device_bytes"] / 2**20)
                  if m.get("peak_device_bytes") else None,
                  "peak_gpu_mib_nvidia_smi": mem.peak_mib or None,
                  "oom": oom,
                  "log_tail": log[-1500:] if code != 0 else log[-400:]}
        tried.append(result)
        if code == 0:
            break
        if not result["oom"]:
            break  # a different failure: retrying with less memory won't help
    ok = tried[-1]
    per_step = ok.get("median_step_seconds")
    steps_full = TRAIN_RECORDS * TRAIN_EPOCHS / (ok["batch"] * ok["accum"])
    dropped = ok.get("rejected_records") or 0
    return {"kind": kind, "records": n_records, "max_state": max_state,
            "state_tokens": {"min": min(lengths), "max": max(lengths),
                             "mean": round(sum(lengths) / len(lengths))} if lengths else None,
            "recipe": r, "attempts": tried,
            "works": ok["returncode"] == 0 and not dropped,
            "projected_hours_2000x2epochs": round(per_step * steps_full / 3600, 2)
            if per_step else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kev-dir", type=Path, default=Path("/tmp/work/kev"))
    ap.add_argument("--model", default="jaredpalmer/kev-0.6b")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="fp32", help="KEV_DTYPE for serving; --dtype for training")
    ap.add_argument("--port", type=int, default=8009)
    ap.add_argument("--speed-samples", type=int, default=40)
    ap.add_argument("--questions", type=int, default=100)
    ap.add_argument("--train-records", type=int, default=48)
    ap.add_argument("--train-batch", type=int, default=8)
    ap.add_argument("--max-state", type=int, default=4096,
                    help="kev.train --max_state; Kev's default 384 drops C3-length states")
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--out", type=Path, default=Path("a3_report.json"))
    ap.add_argument("--work", type=Path, default=None,
                    help="where logs and test runs go (default: a temp folder)")
    args = ap.parse_args()

    kev_py = str(args.kev_dir / ".venv" / "bin" / "python")
    if args.work:
        args.work.mkdir(parents=True, exist_ok=True)
    work = args.work or Path(tempfile.mkdtemp(prefix="a3_"))
    report: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "args": {
        k: str(v) for k, v in vars(args).items()}, "kev_commit": sh(
        ["git", "-C", str(args.kev_dir), "rev-parse", "--short", "HEAD"])}

    def save():
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2))

    def step(name, fn):
        print(f"--- {name}", flush=True)
        t0 = time.time()
        try:
            report[name] = fn()
        except Exception as exc:  # record and carry on, so one failure doesn't hide the rest
            report[name] = {"error": f"{type(exc).__name__}: {exc}"}
        report[name + "_seconds"] = round(time.time() - t0, 1)
        print(json.dumps(report[name], indent=2)[:3000], flush=True)
        save()

    step("environment", lambda: environment(kev_py))
    server_log = work / "kev_serve.log"
    url = f"http://127.0.0.1:{args.port}"
    proc = None
    try:
        print("--- server (first run downloads the model)", flush=True)
        proc, report["server"] = start_server(args.kev_dir, kev_py, args.model, args.port,
                                              args.device, args.dtype, server_log, 1800)
        print(report["server"], flush=True)
        save()
        step("endpoint", lambda: endpoint_check(url))
        step("speed", lambda: speed_check(url, args.speed_samples, args.questions))
    except Exception as exc:
        report["server"] = {"error": f"{type(exc).__name__}: {exc}",
                            "log_tail": server_log.read_text()[-2000:]
                            if server_log.exists() else ""}
        save()
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=60)

    if not args.skip_train:
        for kind in ("short", "long"):
            step(f"train_{kind}", lambda kind=kind: train_check(
                args.kev_dir, kev_py, args.model, args.device, args.dtype, kind,
                args.train_records, args.train_batch, args.max_state, work, 3600))

    ok = (report.get("endpoint", {}).get("ok") and
          (args.skip_train or all(report.get(f"train_{k}", {}).get("works")
                                  for k in ("short", "long"))))
    report["verdict"] = "PASS" if ok else "FAIL"
    report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save()
    print(f"\nVERDICT: {report['verdict']}. Report: {args.out}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
