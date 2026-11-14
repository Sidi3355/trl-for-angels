"""B3 control (CTRL): XGBoost on the train answer matrix, tuned on val.

    python research/baselines.py

CTRL separates "Kev helps" from "nonlinearity helps" (MASTER_PLAN section 3). It reads the same
answer matrices every answer-based condition uses (data/answers/{split}.csv, from B2: the 40
questions Kev reads), so its only difference from C1a-40 and C3 is the learner. A small grid is searched, each candidate trained on
train with early stopping on val log-loss; the candidate with the best val log-loss wins (a
proper scoring rule, so calibration counts too). Writes:
  data/predictions/ctrl_{val,test}.csv    same columns as TRL's predictions
  data/predictions/ctrl_importance.csv    gain importance per rule (for interp, F1)
  data/predictions/ctrl_config.json       the grid, every candidate's val log-loss, the winner
C1a, C1a-40 and C1b need nothing here: their predictions come from TRL's own predict_proba (B2).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import POSITIVE, ROOT  # noqa: E402

GRID = {"max_depth": (2, 3, 4), "learning_rate": (0.03, 0.1), "min_child_weight": (1, 5)}
FIXED = {"n_estimators": 2000, "subsample": 0.8, "colsample_bytree": 0.8,
         "eval_metric": "logloss", "early_stopping_rounds": 50, "random_state": 42,
         "n_jobs": 4, "tree_method": "hist"}


def read_matrix(answers_dir: Path, splits_dir: Path, split: str):
    """(ids, X with NaN for unanswered, y as bool, rule names) in the answer file's order."""
    with (answers_dir / f"{split}.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    ids = [r[0] for r in body]
    X = np.array([[float(v) if v != "" else np.nan for v in r[1:]] for r in body])
    labels = {}
    for line in (splits_dir / f"{split}.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            labels[rec["id"]] = rec["label"] == POSITIVE
    y = np.array([labels[i] for i in ids], bool)
    return ids, X, y, header[1:]


def fit_ctrl(Xtr, ytr, Xva, yva):
    from sklearn.metrics import log_loss
    from xgboost import XGBClassifier

    tried = []
    best = None
    for values in itertools.product(*GRID.values()):
        params = dict(zip(GRID, values))
        model = XGBClassifier(**params, **FIXED)
        model.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        loss = float(log_loss(yva, model.predict_proba(Xva)[:, 1], labels=[False, True]))
        tried.append({**params, "best_iteration": int(model.best_iteration),
                      "val_logloss": loss})
        if best is None or loss < best[0]:
            best = (loss, params, model)
    return best[2], best[1], tried


def write_predictions(path: Path, split: str, ids, y, p) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "split", "condition", "label", "p_success", "trl_decision"])
        for rid, label, prob in zip(ids, y, p):
            w.writerow([rid, split, "ctrl", POSITIVE if label else "failed", f"{prob:.6g}", ""])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--answers", type=Path, default=ROOT / "data" / "answers")
    ap.add_argument("--splits", type=Path, default=ROOT / "data" / "splits")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "predictions")
    args = ap.parse_args(argv)

    _, Xtr, ytr, rules = read_matrix(args.answers, args.splits, "train")
    va_ids, Xva, yva, rules_va = read_matrix(args.answers, args.splits, "val")
    if rules_va != rules:
        raise ValueError("train and val answer files have different rule columns")
    model, params, tried = fit_ctrl(Xtr, ytr, Xva, yva)
    args.out.mkdir(parents=True, exist_ok=True)
    write_predictions(args.out / "ctrl_val.csv", "val", va_ids, yva, model.predict_proba(Xva)[:, 1])
    if (args.answers / "test.csv").exists():
        te_ids, Xte, yte, _ = read_matrix(args.answers, args.splits, "test")
        write_predictions(args.out / "ctrl_test.csv", "test", te_ids, yte,
                          model.predict_proba(Xte)[:, 1])
    gain = model.get_booster().get_score(importance_type="gain")
    with (args.out / "ctrl_importance.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rule", "gain"])
        for j, rule in enumerate(rules):
            w.writerow([rule, f"{gain.get(f'f{j}', 0.0):.6g}"])
    (args.out / "ctrl_config.json").write_text(json.dumps(
        {"grid": GRID, "fixed": FIXED, "chosen": params, "candidates": tried,
         "selected_by": "lowest val log-loss"}, indent=2))
    print(f"CTRL: chose {params}, val log-loss "
          f"{min(c['val_logloss'] for c in tried):.4f} over {len(tried)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
