"""The ceiling: how well the synthetic rows' own background score predicts success.

    python research/oracle.py --stage d1-final

The 2,950 synthetic founders' outcomes come from a known rule (research/generate_dataset.py):
a background score from the profile plus Gaussian noise, ranked within blocks of 50. The
noise-free background score is therefore close to the best any model could do from the profile.
This regenerates the dataset with --meta (it must match data/raw/full.jsonl byte for byte),
scores the synthetic val and test founders with it, and puts every condition beside it on the
same synthetic founders (the 50 real-grounded rows have no background score). The threshold for
F0.5 is tuned on val, as for every condition. A reference only: nothing is selected with it.
Writes results/summary/<stage>/oracle.{csv,md} (new files; nothing is overwritten).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402
from common import ROOT  # noqa: E402
from evaluate import CONDITIONS, read_predictions, write_csv  # noqa: E402


def background_scores() -> dict[str, float]:
    """Row id -> background score, for the synthetic rows."""
    with tempfile.TemporaryDirectory() as tmp:
        out, meta = Path(tmp) / "full.jsonl", Path(tmp) / "meta.jsonl"
        subprocess.run([sys.executable, str(ROOT / "research" / "generate_dataset.py"),
                        "--out", str(out), "--meta", str(meta)], check=True,
                        capture_output=True)
        if out.read_bytes() != (ROOT / "data" / "raw" / "full.jsonl").read_bytes():
            raise SystemExit("the regenerated dataset differs from data/raw/full.jsonl")
        rows = [json.loads(x) for x in meta.read_text().splitlines() if x.strip()]
    return {f"r{i:05d}": m["score"] for i, m in enumerate(rows, 1) if m["score"] is not None}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True)
    ap.add_argument("--predictions", type=Path, default=ROOT / "data" / "predictions")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    ap.add_argument("--bootstrap", type=int, default=M.BOOTSTRAP)
    args = ap.parse_args(argv)

    out_dir = args.results / "summary" / args.stage
    if (out_dir / "oracle.csv").exists():
        raise SystemExit(f"{out_dir / 'oracle.csv'} exists: results are never overwritten")
    score = background_scores()
    preds = read_predictions(args.predictions)
    ref = preds[("c1a", "test")]
    keep = {s: np.array([i in score for i in preds[("c1a", s)]["id"]]) for s in ("val", "test")}
    y = {s: preds[("c1a", s)]["y"][keep[s]] for s in ("val", "test")}
    # The background score isn't a probability; a logistic squash keeps its ranking (so PR-AUC
    # is unchanged) and puts it in [0, 1], where the threshold is tuned like any other score.
    oracle = {s: 1 / (1 + np.exp(-np.array([score[i] for i, k in
                                            zip(preds[("c1a", s)]["id"], keep[s]) if k])))
              for s in ("val", "test")}

    def row(name: str, label: str, pv: np.ndarray, pt: np.ndarray) -> dict:
        t = M.tune_threshold(pv, y["val"])
        m = M.metrics(pt, y["test"], t)
        rng = np.random.default_rng(M.SEED)
        pos, neg = np.flatnonzero(y["test"]), np.flatnonzero(~y["test"])
        draws = []
        for _ in range(args.bootstrap):
            i = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
            draws.append(M.metrics(pt[i], y["test"][i], t)["pr_auc"])
        lo, hi = np.percentile(draws, [2.5, 97.5])
        return {"condition": name, "name": label, "n_test": int(len(pt)),
                "positives": int(y["test"].sum()), "f05": m["f05"], "precision": m["precision"],
                "recall": m["recall"], "pr_auc": m["pr_auc"], "pr_auc_ci_low": float(lo),
                "pr_auc_ci_high": float(hi)}

    rows = [row("oracle", "the synthetic rule's own background score (no noise)",
                oracle["val"], oracle["test"])]
    for c, (short, label, _) in CONDITIONS.items():
        if (c, "val") in preds and (c, "test") in preds:
            if preds[(c, "test")]["id"] != ref["id"] or preds[(c, "val")]["id"] != preds[("c1a", "val")]["id"]:
                raise SystemExit(f"{c} covers different founders from c1a")
            rows.append(row(short, label, preds[(c, "val")]["p"][keep["val"]],
                            preds[(c, "test")]["p"][keep["test"]]))
    write_csv(out_dir / "oracle.csv", rows)
    lines = [f"# The ceiling: the synthetic rule's own score ({args.stage}, test)", "",
             f"Synthetic test founders only ({rows[0]['n_test']}, of whom "
             f"{rows[0]['positives']} succeeded); the real-grounded rows have no background "
             "score. *Oracle* ranks founders by the noise-free background score that, plus "
             "noise, decided their outcome, so it is close to the best any model could do from "
             "the profile. F0.5 uses a threshold tuned on val; PR-AUC has a stratified bootstrap "
             f"95% CI ({args.bootstrap} resamples). Written by `research/oracle.py`.", "",
             "| Condition | F0.5 | Precision | Recall | PR-AUC (95% CI) |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['condition']} | {r['f05']:.3f} | {r['precision']:.3f} | "
                     f"{r['recall']:.3f} | {r['pr_auc']:.3f} ({r['pr_auc_ci_low']:.3f}–"
                     f"{r['pr_auc_ci_high']:.3f}) |")
    (out_dir / "oracle.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-len(rows):]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
