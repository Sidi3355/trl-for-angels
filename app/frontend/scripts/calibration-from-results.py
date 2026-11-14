"""Write the calibration page's numbers (src/data/calibration.json) from the research results.

The page reads only that JSON, so swapping provisional numbers for final ones is: run this on the new
results folder, commit the JSON, redeploy. No code changes. Standard library only.

    python3 scripts/calibration-from-results.py \
        --metrics <results/summary/STAGE/metrics.csv> --reliability <results/summary/STAGE/plots/reliability_table.csv> \
        --condition c1a --split val --protocol "val-tuned F0.5" --status provisional \
        --model "TRL's standard model (RRF, elastic net)" \
        --source "results/summary/b3-provisional on the research branch" > src/data/calibration.json
"""

import argparse
import csv
import json
import sys
from datetime import date


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--reliability", required=True)
    ap.add_argument("--condition", required=True, help="e.g. c1a, c3, prod (matched case-insensitively)")
    ap.add_argument("--split", default="val")
    ap.add_argument("--protocol", default="val-tuned F0.5", help="the threshold_protocol row to read precision and recall from")
    ap.add_argument("--status", choices=["provisional", "final"], required=True)
    ap.add_argument("--model", required=True, help="plain-English name of the model these numbers describe")
    ap.add_argument("--model-note", default="")
    ap.add_argument("--target", default="$500M+", help="what 'success' means in these numbers")
    ap.add_argument("--source", required=True)
    a = ap.parse_args()

    cond = a.condition.lower()
    rows = [r for r in csv.DictReader(open(a.metrics)) if r["condition"].lower() == cond and r["split"] == a.split]
    row = next((r for r in rows if r["threshold_protocol"] == a.protocol), None)
    if row is None:
        sys.exit(f"no metrics row for {a.condition} / {a.split} / {a.protocol}")
    bins, seen = [], set()
    for r in csv.DictReader(open(a.reliability)):
        if r["condition"].lower() != cond or r["split"] != a.split or r["bin"] in seen:
            continue
        seen.add(r["bin"])
        bins.append({"low": float(r["low"]), "high": float(r["high"]), "count": int(r["count"]),
                     "predicted": round(float(r["mean_predicted"]), 4), "observed": round(float(r["share_successful"]), 4)})
    if not bins:
        sys.exit(f"no reliability rows for {a.condition} / {a.split}")
    bins.sort(key=lambda b: b["low"])
    n, pos = int(row["n"]), int(row["positives"])
    doc = {
        "status": a.status,
        "updated": date.today().isoformat(),
        "model": a.model,
        "model_note": a.model_note,
        "split": a.split,
        "founders": n,
        "successes": pos,
        "target": a.target,
        "base_rate": round(pos / n, 4),
        "ece": round(float(row["ece"]), 4),
        "brier": round(float(row["brier"]), 4),
        "precision": round(float(row["precision"]), 4),
        "recall": round(float(row["recall"]), 4),
        "flagged": int(row["predicted_positive"]),
        "bins": bins,
        "source": a.source,
    }
    json.dump(doc, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
