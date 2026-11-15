"""Paired test comparisons (D1): how much one condition beats another, with a 95% CI.

    python research/paired.py --stage d1-final

Two separate CIs that overlap don't show two conditions are equal, and two that don't overlap
overstate the gap less often than people think; the right test is the difference itself, on
the same founders. Each resample draws the same founders for both conditions (stratified:
positives and negatives separately, 1,000 resamples, seed 42), with each condition's threshold
fixed from val, exactly as evaluate.py scores them. Reads data/predictions/; writes
results/summary/<stage>/paired.{csv,md} beside evaluate.py's tables (a new file; nothing is
overwritten). The comparisons are fixed below from the research question, not picked from
the results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402
from common import ROOT  # noqa: E402
from evaluate import CONDITIONS, read_predictions, write_csv  # noqa: E402

# (A, B, what A − B answers). Positive F0.5 / PR-AUC differences favour A; negative Brier /
# ECE differences favour A.
COMPARISONS = [
    ("c1b", "c1a", "the paper's vote against TRL's default"),
    ("ctrl", "c1a", "XGBoost against TRL's default"),
    ("c2", "c1a", "base Kev as the learn stage against TRL's default"),
    ("c3", "c1a", "fine-tuned Kev as the learn stage against TRL's default"),
    ("c4", "c1a", "fine-tuned Kev on the profile (no think or reason steps) against TRL's default"),
    ("c3", "c1a40", "fine-tuned Kev against the elastic net on the same 40 questions"),
    ("c3", "ctrl", "fine-tuned Kev against XGBoost on the same 40 questions (nonlinearity)"),
    ("c3", "c2", "what fine-tuning does for Kev reading TRL's answers"),
    ("c4", "extra", "what fine-tuning does for Kev reading the profile"),
    ("c3", "c4", "TRL's answers against the profile, as fine-tuned Kev's input"),
    ("c1a40", "c1a", "40 questions against all of them, for the elastic net"),
]
KEYS = ("f05", "brier", "ece", "pr_auc")
HIGHER_BETTER = {"f05": True, "pr_auc": True, "brier": False, "ece": False}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--predictions", type=Path, default=ROOT / "data" / "predictions")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    ap.add_argument("--bootstrap", type=int, default=M.BOOTSTRAP)
    args = ap.parse_args(argv)

    out_dir = args.results / "summary" / args.stage
    if (out_dir / "paired.csv").exists():
        raise SystemExit(f"{out_dir / 'paired.csv'} exists: results are never overwritten")
    preds = read_predictions(args.predictions)
    rows = []
    for a, b, question in COMPARISONS:
        if not all((c, s) in preds for c in (a, b) for s in ("val", args.split)):
            print(f"skip {a} vs {b}: predictions missing", file=sys.stderr)
            continue
        A, B = preds[(a, args.split)], preds[(b, args.split)]
        if A["id"] != B["id"]:  # same founders, same order, or the pairing is meaningless
            order = {i: k for k, i in enumerate(B["id"])}
            if sorted(order) != sorted(A["id"]):
                raise SystemExit(f"{a} and {b} cover different founders")
            ix = [order[i] for i in A["id"]]
            B = {"id": A["id"], "y": B["y"][ix], "p": B["p"][ix]}
        if not np.array_equal(A["y"], B["y"]):
            raise SystemExit(f"{a} and {b} disagree on labels")
        y = A["y"]
        ta = M.tune_threshold(preds[(a, "val")]["p"], preds[(a, "val")]["y"])
        tb = M.tune_threshold(preds[(b, "val")]["p"], preds[(b, "val")]["y"])
        ma, mb = M.metrics(A["p"], y, ta), M.metrics(B["p"], y, tb)
        rng = np.random.default_rng(M.SEED)
        pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
        draws = {k: [] for k in KEYS}
        for _ in range(args.bootstrap):
            idx = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
            ra, rb = M.metrics(A["p"][idx], y[idx], ta), M.metrics(B["p"][idx], y[idx], tb)
            for k in KEYS:
                draws[k].append(ra[k] - rb[k])
        row = {"a": CONDITIONS[a][0], "b": CONDITIONS[b][0], "question": question,
               "split": args.split, "n": len(y)}
        for k in KEYS:
            v = np.asarray(draws[k], float)
            lo, hi = float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))
            better = v > 0 if HIGHER_BETTER[k] else v < 0
            row |= {f"{k}_a": ma[k], f"{k}_b": mb[k], f"{k}_diff": ma[k] - mb[k],
                    f"{k}_ci_low": lo, f"{k}_ci_high": hi,
                    f"{k}_share_a_better": float(np.mean(better)),
                    f"{k}_ci_excludes_0": bool(lo > 0 or hi < 0)}
        rows.append(row)

    write_csv(out_dir / "paired.csv", rows)
    lines = [
        f"# Paired comparisons ({args.stage}, {args.split})", "",
        "**How to read this:** each row is condition A minus condition B, scored on the same "
        f"{rows[0]['n'] if rows else ''} {args.split} founders, with a paired, stratified "
        f"bootstrap 95% CI ({args.bootstrap} resamples) and thresholds fixed from val. For "
        "F0.5 and PR-AUC a positive difference favours A; for Brier and ECE (errors) a "
        "negative one does. **Bold:** the CI excludes zero, so the gap is unlikely to be "
        "chance on this test set. Terms: [GLOSSARY](../../GLOSSARY.md).", "",
        "| A − B | What it answers | F0.5 | Brier | ECE | PR-AUC |", "|---|---|---|---|---|---|"]
    for r in rows:
        def cell(k, r=r):
            s = f"{r[f'{k}_diff']:+.3f} ({r[f'{k}_ci_low']:+.3f} to {r[f'{k}_ci_high']:+.3f})"
            return f"**{s}**" if r[f"{k}_ci_excludes_0"] else s
        lines.append(f"| {r['a']} − {r['b']} | {r['question']} | {cell('f05')} | "
                     f"{cell('brier')} | {cell('ece')} | {cell('pr_auc')} |")
    lines += ["", "Generated by `research/paired.py` from `data/predictions/`; the full table, "
              "with each side's value and the share of resamples favouring A, is `paired.csv`."]
    (out_dir / "paired.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_dir / 'paired.md'} ({len(rows)} comparisons)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
