"""B2: Kev's answer matrices for every split, and TRL's own predictions for C1a, C1a-40, C1b, C2.

    python research/answers.py --kev-dir ../kev --out-root OUT --cache-dir OUT/trl_cache

Run after fit_rrf.py, with the same cache, so train answers come from the cache. Loads the
saved models (data/models/*), serves base Kev on the port they were fitted with, and writes:
  data/answers/{split}.csv           an `id` column, then P(yes) per rule in rules.json order
                                     (C2's rules_: the 40 questions Kev reads). From
                                     c2.answers().
  data/predictions/trl_{split}.csv   per founder and condition (c1a, c1a40, c1b, c2): the
                                     true label,
                                     P(success) from TRL's predict_proba, and TRL's own
                                     decision from predict() (its threshold tuned on train)
  data/answers/answers_report.json   shapes, missing answers, timings, usage
Test predictions are written now, with the answers, but are not looked at until the final
evaluation (D1); everything is chosen on val.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import POSITIVE, ROOT, SPLITS, kev_server, load_split, usage_rows  # noqa: E402

CONDITIONS = ("c1a", "c1a40", "c1b", "c2")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--splits", type=Path, default=ROOT / "data" / "splits")
    ap.add_argument("--out-root", type=Path, default=ROOT)
    ap.add_argument("--cache-dir", type=Path, required=True)
    ap.add_argument("--kev-dir", type=Path, default=ROOT.parent / "kev")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--predict-splits", default="val,test")
    args = ap.parse_args(argv)

    from think_reason_learn.llm import set_config
    from think_reason_learn.rrf import RRF

    set_config(cache_dir=args.cache_dir)
    answers_dir = args.out_root / "data" / "answers"
    preds_dir = args.out_root / "data" / "predictions"
    preds_dir.mkdir(parents=True, exist_ok=True)
    models = {n: RRF.load(args.out_root / "data" / "models" / n) for n in CONDITIONS}
    rules = json.loads((answers_dir / "rules.json").read_text())
    c2 = models["c2"]
    if list(c2.rules_) != rules:
        raise ValueError("rules.json doesn't match the saved C2 model's rules_")
    # Serve Kev where the models were fitted, so TRL's cache keys match.
    port = urlparse(c2.answerer.base_url).port or 8009
    report: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "rules": len(rules),
                    "splits": {}, "predictions": {}}

    with kev_server(args.kev_dir, port=port, device=args.device,
                    log=args.out_root / "logs" / "kev_answerer_b2.log"):
        for split in SPLITS:
            ids, X, _ = load_split(args.splits, split)
            t0 = time.time()
            matrix = c2.answers(X)
            missing = int(matrix.isna().sum().sum())
            with (answers_dir / f"{split}.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["id", *rules])
                for rid, row in zip(ids, matrix.to_numpy()):
                    w.writerow([rid, *("" if math.isnan(p) else f"{p:.6g}" for p in row)])
            report["splits"][split] = {"rows": len(ids), "shape": list(matrix.shape),
                                       "missing_answers": missing,
                                       "seconds": round(time.time() - t0, 1)}
            print(f"{split}: {matrix.shape} answers, {missing} missing", flush=True)

        for split in args.predict_splits.split(","):
            ids, X, y = load_split(args.splits, split)
            path = preds_dir / f"trl_{split}.csv"
            with path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["id", "split", "condition", "label", "p_success", "trl_decision"])
                for name, model in models.items():
                    t0 = time.time()
                    pos = list(model.classes_).index(POSITIVE)
                    proba = model.predict_proba(X)[:, pos]
                    decided = model.predict(X)
                    for rid, label, p, d in zip(ids, y, proba, decided):
                        w.writerow([rid, split, name, label, f"{p:.6g}", d])
                    report["predictions"][f"{name}_{split}"] = {
                        "rows": len(ids), "seconds": round(time.time() - t0, 1)}
            print(f"predictions: {path.name}", flush=True)

    report["usage"] = {n: usage_rows(m.usage_) for n, m in models.items()}
    report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (answers_dir / "answers_report.json").write_text(json.dumps(report, indent=2, default=str))
    bad = {s: r["missing_answers"] for s, r in report["splits"].items() if r["missing_answers"]}
    if bad:
        print(f"WARNING: missing answers {bad}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
