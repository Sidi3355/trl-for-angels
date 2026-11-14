"""A4 on Kaggle: TRL's RRF smoke test, Claude as the generator and Kev-0.6B as the answerer.

Runs under the TRL venv's Python, next to a3_check.py (server helpers) and validate.py
(record parsing). Steps:
  1. start Kev (fp32 on the GPU) and check one Claude call through TRL works
  2. estimate_cost for this run and for the full B1 fit on 2,000 founders
  3. fit RRF on the sample rows with a small n_prompts, through TRL's real fit()
  4. answers() returns a matrix with no gaps, and predict_proba() runs
  5. report the cost and time per founder, and save the rules, answers and TRL cache

Needs ANTHROPIC_API_KEY in the environment (a Kaggle Secret). Never prints it.

    python a4_check.py --data a4_rows.jsonl --out /kaggle/working/a4
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "research")]  # repo layout or one flat folder

from a3_check import environment, start_server  # noqa: E402
from validate import STRONG, load as load_rows, parse_record  # noqa: E402

TASK = ("Predict whether this startup founder's company will succeed (exit, IPO or funding "
        "over $500M).")
B1_ROWS = 2000


def pick_rows(path: Path, n: int = 20, n_strong: int = 6, seed: int = 42) -> list[dict]:
    """n sample rows (n_strong successful, the rest not), chosen reproducibly."""
    import random

    parsed = [(row, parse_record(row, i)) for i, row in enumerate(load_rows(path), 1)]
    good = [(row, rec) for row, rec in parsed if rec.outcome is not None]
    strong = [row for row, rec in good if rec.outcome in STRONG]
    other = [row for row, rec in good if rec.outcome not in STRONG]
    rng = random.Random(seed)
    picked = rng.sample(strong, min(n_strong, len(strong)))
    picked += rng.sample(other, min(n - len(picked), len(other)))
    rng.shuffle(picked)
    return picked


def load(path: Path) -> tuple[list[str], list[str]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    X, y = [], []
    for i, row in enumerate(rows, 1):
        rec = parse_record(row, i)
        if rec.outcome is None:
            raise ValueError(f"row {i} has no parseable outcome: {rec.errors}")
        X.append(rec.input)
        y.append("successful" if rec.outcome in STRONG else "failed")
    return X, y


def usage_table(usage) -> list[dict]:
    return json.loads(usage.by("role", "model").to_json(orient="records"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kev-dir", type=Path, default=Path("/tmp/work/kev"))
    ap.add_argument("--model", default="jaredpalmer/kev-0.6b")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="fp32")
    ap.add_argument("--port", type=int, default=8009)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--data", type=Path, help="exactly the rows to fit on (JSONL)")
    src.add_argument("--sample", type=Path,
                     help="a sample file to pick 20 rows from (6 successful, seed 42)")
    ap.add_argument("--generator", default="anthropic:claude-opus-5-5")
    ap.add_argument("--max-output-tokens", type=int, default=16000,
                    help="Claude thinks before writing; TRL's default 4096 can cut it off")
    ap.add_argument("--n-prompts", type=int, default=2)
    ap.add_argument("--questions-per-prompt", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path("a4"))
    ap.add_argument("--fake-generator", action="store_true",
                    help="offline test: TRL's scripted fake writer instead of Claude")
    args = ap.parse_args()

    from think_reason_learn.llm import LLM, LLMSession, set_config
    from think_reason_learn.llm._loop import run_sync
    from think_reason_learn.llm._spec import resolve
    from think_reason_learn.rrf import RRF

    args.out.mkdir(parents=True, exist_ok=True)
    set_config(cache_dir=args.out / "trl_cache")  # keep paid replies with the outputs
    report: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "args": {k: str(v) for k, v in vars(args).items()}}

    def save():
        (args.out / "a4_report.json").write_text(json.dumps(report, indent=2, default=str))

    if not args.fake_generator and not os.environ.get("ANTHROPIC_API_KEY"):
        report["verdict"] = "FAIL"
        report["error"] = "ANTHROPIC_API_KEY is not set: attach the Kaggle Secret and rerun"
        save()
        print(report["error"])
        return 1

    if args.sample:
        args.data = args.out / "a4_rows.jsonl"
        args.data.write_text("".join(json.dumps(r) + "\n" for r in pick_rows(args.sample)))
    X, y = load(args.data)
    report["data"] = {"rows": len(X), "successful": y.count("successful"),
                      "file": str(args.data)}
    fake = contextlib.nullcontext()
    if args.fake_generator:  # offline test of this script: scripted writer, real Kev
        from think_reason_learn.testing import FakeLLM, fake_llms

        def write(request):
            if request.schema is None:
                return "OK"
            return {"questions": ["Has the founder founded a startup before?",
                                  "Does the founder have a technical background?",
                                  "Did the founder attend a top-50 university?",
                                  "Has the founder worked at a company with 5,000+ employees?",
                                  "Does the founder have a prior exit?"]}

        fake = fake_llms(writer=FakeLLM(generate=write))
        args.generator = "fake:writer"
    fake.__enter__()
    generator = LLM(args.generator, max_output_tokens=args.max_output_tokens)
    kev = LLM("kev-0.6b", base_url=f"http://127.0.0.1:{args.port}/v1/systemone",
              kind="decision", api_key="local")

    def make_rrf(n_prompts: int, questions_per_prompt: int) -> RRF:
        return RRF(TASK, generator=generator, answerer=kev, n_prompts=n_prompts,
                   questions_per_prompt=questions_per_prompt, beta=0.5, random_state=42)

    kev_py = str(args.kev_dir / ".venv" / "bin" / "python")
    report["environment"] = environment(kev_py)
    proc = None
    try:
        proc, report["server"] = start_server(args.kev_dir, kev_py, args.model, args.port,
                                              args.device, args.dtype,
                                              args.out / "kev_serve.log", 1800)
        print("server:", report["server"], flush=True)

        # 1. One Claude call through TRL.
        t0 = time.time()
        session = LLMSession()
        reply = run_sync(session.generate([resolve(generator)],
                                          "Reply with the single word OK.", role="check"))
        report["generator_check"] = {"reply": reply[:50], "seconds": round(time.time() - t0, 1),
                                     "usage": usage_table(session.usage)}
        print("generator check:", report["generator_check"], flush=True)
        save()

        # 2. Cost estimates (no calls).
        small = make_rrf(args.n_prompts, args.questions_per_prompt).estimate_cost(X, y)
        reps = -(-B1_ROWS // len(X))
        big_X, big_y = (X * reps)[:B1_ROWS], (y * reps)[:B1_ROWS]
        full = make_rrf(10, 10).estimate_cost(big_X, big_y)  # B1: library defaults
        report["estimate"] = {
            "this_run_usd": round(small.cost_usd, 4), "this_run": usage_table(small),
            "b1_fit_2000_rows_usd": round(full.cost_usd, 4), "b1_fit": usage_table(full),
            "note": "B1 estimate repeats these rows to 2,000; TRL counts calls from settings "
                    "and tokens from text lengths, without calling any model",
        }
        print("estimate:", {k: v for k, v in report["estimate"].items()
                            if k.endswith("usd")}, flush=True)
        save()

        # 3-4. The real fit, then answers and predict_proba.
        rrf = make_rrf(args.n_prompts, args.questions_per_prompt)
        t0 = time.time()
        rrf.fit(X, y)
        fit_secs = time.time() - t0
        answers = rrf.answers(X)
        proba = rrf.predict_proba(X)
        answers.to_csv(args.out / "answers.csv", index=False)
        (args.out / "rules.json").write_text(json.dumps(list(rrf.rules_), indent=2))
        rrf.questions_.to_csv(args.out / "questions.csv", index=False)
        cost = rrf.usage_.cost_usd
        report["fit"] = {
            "seconds": round(fit_secs, 1),
            "rules": len(rrf.rules_),
            "rules_list": list(rrf.rules_),
            "questions_generated": len(rrf.questions_),
            "answers_shape": list(answers.shape),
            "answers_missing": int(answers.isna().sum().sum()),
            "proba_shape": list(proba.shape),
            "proba_first_rows": [[round(float(p), 3) for p in row] for row in proba[:5]],
            "classes": [str(c) for c in rrf.classes_],
            "usage": usage_table(rrf.usage_),
            "cost_usd": round(cost, 4),
            "cost_per_founder_usd": round(cost / len(X), 5),
            "seconds_per_founder": round(fit_secs / len(X), 2),
        }
        ok = (report["fit"]["answers_missing"] == 0 and answers.shape[0] == len(X)
              and answers.shape[1] == len(rrf.rules_) > 0)
        report["verdict"] = "PASS" if ok else "FAIL"
    except Exception as exc:
        report["verdict"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        log = args.out / "kev_serve.log"
        if log.exists():
            report["server_log_tail"] = log.read_text()[-1500:]
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=60)
        report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save()
    print(json.dumps({k: report.get(k) for k in ("verdict", "error", "estimate", "fit")},
                     indent=2, default=str)[:4000])
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
