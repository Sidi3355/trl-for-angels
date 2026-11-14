"""C1-train and C2-temp: fine-tune Kev-0.6B for C3 or C4, choose the checkpoint on val, and fit
its temperature on val.

    <kev>/.venv/bin/python research/train_kev.py --condition c3 --kev-dir <kev> --out runs/c3

Runs in Kev's own environment (it uses kev's trainer and scorer). Reads data/kev/<condition>/
{train,val}.jsonl from research/serialise.py. Kev's recipe (MASTER_PLAN section 0):
architecture settings copied from the starting checkpoint's metadata, --max_state 4096,
learning rate 2e-5, fp32 on a T4.

Checkpoint choice on val: Kev writes snapshots only for full-weight training, so this trains
one epoch from the released checkpoint (ep1), then one more epoch from ep1 (ep2), and keeps
whichever of base, ep1 and ep2 has the lowest val log-loss (raw probabilities). The chosen
checkpoint's temperature is then fitted on val with Kev's own fit_temperature (min NLL, micro)
and written into it, so the served model returns calibrated probabilities. Writes
<out>/report.json and <out>/chosen (a copy of the chosen checkpoint).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "jaredpalmer/kev-0.6b"
LR = 2e-5
MAX_STATE = 4096


def recipe(model: str) -> dict:
    """The starting checkpoint's own architecture and training args (Kev's fine-tune recipe)."""
    from kev.checkpoint import Checkpoint

    meta = Checkpoint(model).meta
    args = meta.extra["args"]
    return {"base": meta.base, "base_revision": meta.base_revision, "lora": meta.lora,
            "head_dim": meta.head_dim, "lora_targets": args["lora_targets"],
            "option_isolation": int(meta.option_isolation),
            "special_embeddings": int(meta.special_embeddings),
            "weights_dtype": meta.weights_dtype, "p_none_pair": args["p_none_pair"]}


def train(kev_dir: Path, data: Path, init_from: str, out: Path, r: dict, batch: int,
          accum: int, checkpointing: int, dtype: str, device: str, max_steps: int | None,
          log: Path) -> dict:
    cmd = [sys.executable, "-m", "kev.train", "--data", str(data), "--init_from", init_from,
           "--out", str(out), "--device", device, "--dtype", dtype,
           "--base", r["base"], "--lora", r["lora"], "--head_dim", r["head_dim"],
           "--lora_targets", r["lora_targets"], "--option_isolation", r["option_isolation"],
           "--special_embeddings", r["special_embeddings"], "--weights_dtype",
           r["weights_dtype"], "--epochs", 1, "--lr", LR, "--batch", batch, "--accum", accum,
           "--checkpointing", checkpointing, "--seed", 42, "--p_none_pair", r["p_none_pair"],
           "--max_state", MAX_STATE]
    if r.get("base_revision"):
        cmd += ["--base_revision", r["base_revision"]]
    if max_steps:
        cmd += ["--max_steps", max_steps]
    t0 = time.time()
    with log.open("w") as fh:
        proc = subprocess.run([str(c) for c in cmd], cwd=kev_dir, stdout=fh,
                              stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"kev.train failed ({proc.returncode}); see {log}")
    metrics = json.loads((out / "training_metrics.json").read_text())
    if metrics.get("rejected_records"):
        raise RuntimeError(f"kev.train dropped {metrics['rejected_records']} records "
                           f"(over --max_state {MAX_STATE}); see {log}")
    return {"seconds": round(time.time() - t0, 1), "steps": metrics.get("optimizer_steps"),
            "records_seen": metrics.get("records_seen"),
            "peak_device_mib": round((metrics.get("peak_device_bytes") or 0) / 2**20)}


def score(run: str, records: list, out: Path, device: str, temperature: float = 1.0):
    """Kev's own scorer on val: (report, rows) at ``temperature`` (1.0 = raw)."""
    import gc

    import torch
    from kev.benchmark import evaluate_records
    from kev.checkpoint import LoadOptions
    from kev.predictors import LocalPredictor

    predictor = LocalPredictor(run, device, LoadOptions(temperature=1.0))
    try:
        return evaluate_records(records, predictor, out, temperature)
    finally:
        del predictor
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--condition", choices=("c3", "c4", "prod"), required=True,
                    help="prod: the production model (D3), two choice questions")
    ap.add_argument("--long-states", action="store_true",
                    help="prod with C3's input: turn on gradient checkpointing")
    ap.add_argument("--kev-dir", type=Path, required=True)
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "kev")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="fp32")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--accum", type=int, default=1)
    ap.add_argument("--checkpointing", type=int, default=None,
                    help="default: on for c3 (long states run out of T4 memory without it)")
    ap.add_argument("--max-steps", type=int, default=None, help="tests only")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(args.kev_dir))
    from kev.checkpoint import read_meta, write_meta
    from kev.data import load_records
    from kev.metrics import fit_temperature

    checkpointing = args.checkpointing if args.checkpointing is not None else int(
        args.condition == "c3" or args.long_states)
    data = args.data / args.condition
    args.out.mkdir(parents=True, exist_ok=True)
    val = load_records(data / "val.jsonl", source=args.condition)
    r = recipe(BASE)
    report: dict = {"condition": args.condition, "base": BASE, "recipe": r, "lr": LR,
                    "max_state": MAX_STATE, "batch": args.batch, "accum": args.accum,
                    "checkpointing": checkpointing, "dtype": args.dtype, "runs": {}}

    def save() -> None:
        (args.out / "report.json").write_text(json.dumps(report, indent=2, default=str))

    candidates = {"base": BASE}
    init = BASE
    for epoch in ("ep1", "ep2"):
        out = args.out / epoch
        report["runs"][epoch] = train(args.kev_dir, data / "train.jsonl", init, out, r,
                                      args.batch, args.accum, checkpointing, args.dtype,
                                      args.device, args.max_steps, args.out / f"{epoch}.log")
        candidates[epoch] = str(out)
        init = str(out)
        save()

    scores = {}
    for name, run in candidates.items():
        rep, _ = score(run, val, args.out / "val_scores" / name, args.device)
        scores[name] = rep["clean"]
        print(f"{name}: val nll {rep['clean']['nll']:.4f}, brier {rep['clean']['brier']:.4f}",
              flush=True)
    report["val_raw"] = scores
    chosen = min(scores, key=lambda k: scores[k]["nll"])
    report["chosen"] = chosen
    if chosen == "base":
        report["note"] = "fine-tuning didn't lower val log-loss; the base checkpoint is kept"
    _, rows = score(candidates[chosen], val, args.out / "val_scores" / f"{chosen}_for_T",
                    args.device)
    temperature = fit_temperature(rows, aggregation="micro")
    report["temperature"] = temperature
    # One temperature per question too (MASTER_PLAN section 7). Kev's checkpoint holds one,
    # so these go to temperatures.json; serve raw and apply them (common.apply_temperature).
    per_question = {}
    for qid in sorted({r["question"] for r in rows}):
        q_rows = [r for r in rows if r["question"] == qid]
        per_question[qid] = fit_temperature(q_rows, aggregation="micro")
    report["temperatures_per_question"] = per_question
    rep_cal, _ = score(candidates[chosen], val, args.out / "val_scores" / f"{chosen}_at_T",
                       args.device, temperature)
    # Kev's report keeps raw metrics under "clean" and calibrated ones under
    # "calibrated_clean".
    report["val_calibrated"] = rep_cal.get("calibrated_clean", rep_cal["clean"])
    if temperature in (0.25, 4.0):
        report["temperature_note"] = "at the edge of Kev's 0.25-4 grid: check val size"
    dest = args.out / "chosen"
    if chosen == "base":
        from huggingface_hub import snapshot_download

        shutil.copytree(snapshot_download(BASE), dest, dirs_exist_ok=True)
    else:
        shutil.copytree(candidates[chosen], dest, dirs_exist_ok=True)
    meta = read_meta(str(dest))
    meta.temperature = temperature
    (dest / "temperatures.json").write_text(json.dumps(
        {"global": temperature, "per_question": per_question,
         "fitted_on": "val", "method": "min NLL, micro, kev.metrics.fit_temperature",
         "apply": "serve raw (KEV_TEMPERATURE=1.0), then p^(1/T) renormalised per question"},
        indent=2))
    meta.extra["temperature_fit"] = {"rows": "val", "n": len(val),
                                     "method": "min NLL, micro, kev.metrics.fit_temperature",
                                     "value": temperature}
    write_meta(str(dest), meta)
    report["chosen_dir"] = str(dest)
    save()
    print(f"{args.condition}: chose {chosen}, temperature {temperature:.3f}; "
          f"val ECE raw {scores[chosen].get('ece'):.4f} -> calibrated "
          f"{report['val_calibrated'].get('ece'):.4f}", flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    sys.exit(main())
