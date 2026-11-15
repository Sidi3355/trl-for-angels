"""D4: the risk-threshold table the app's controls read, built from the production model on val.

    python research/thresholds.py --stage d4

Reads data/predictions/prod_val.csv (D3: each val founder's calibrated outcome and years
distributions). For each target outcome and timeline (MASTER_PLAN section 8, investor
controls), the probability the app shows is

    P(outcome >= target)                              (the sum of the bands at or above it)
    x P(reaching it within the horizon)               (from the years question)

The product assumes the two are independent, so it is labelled an estimate. For every
threshold on a 0.01 grid the table gives, on val: how many founders would be advanced, the
share of those who reached the target in time (precision), and the share of all who did that
were advanced (recall). Three risk presets pick an advance threshold (advance at or above it)
with TRL's own best_threshold at three F-betas, which adapts to each target's base rate, and
a pass threshold (pass below it; escalate in between) that turns away at most a set share of
the founders who did reach the target:

    conservative   advance at the F0.5-best threshold (precision first); pass below the
                   point where at most 5% of the successes fall
    balanced       F1-best; at most 10% of the successes passed
    aggressive     F2-best (find more of the successes); at most 20% passed

Writes app/thresholds.json (the app loads only this) and a plain-English report in
results/experiments/04_production_model/<stage>/.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402
from common import OUTCOME_BANDS, ROOT, YEARS_BANDS  # noqa: E402

BANDS = list(OUTCOME_BANDS)  # ordered lowest to highest
YEARS = list(YEARS_BANDS)
TARGETS = {"$50M": "$50M-$500M", "$500M": "$500M-$1B", "$1B": "over $1B"}  # lowest band counted
TIMELINES = {"any": YEARS, "5 years": ["under 5"], "8 years": ["under 5", "5-8"]}
PRESETS = {"conservative": (0.5, 0.05), "balanced": (1.0, 0.10), "aggressive": (2.0, 0.20)}
"""Each preset: (the F-beta its advance threshold maximises, the most successes it may pass)."""
GRID = [round(x, 2) for x in np.arange(0.0, 1.0001, 0.01)]


def load(path: Path) -> dict[str, np.ndarray | list]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {
        "id": [r["id"] for r in rows],
        "outcome": [r["outcome"] for r in rows],
        "years": [r["years"] for r in rows],
        "p_outcome": np.array([[float(r[f"p_outcome_{b}"]) for b in BANDS] for r in rows]),
        "p_years": np.array([[float(r[f"p_years_{y}"]) for y in YEARS] for r in rows]),
    }


def scores_and_labels(d: dict, target: str, timeline: str) -> tuple[np.ndarray, np.ndarray]:
    lo = BANDS.index(TARGETS[target])
    in_time = [YEARS.index(y) for y in TIMELINES[timeline]]
    p = d["p_outcome"][:, lo:].sum(axis=1) * d["p_years"][:, in_time].sum(axis=1)
    y = np.array([BANDS.index(o) >= lo and yr in TIMELINES[timeline]
                  for o, yr in zip(d["outcome"], d["years"])])
    return p, y


def table(p: np.ndarray, y: np.ndarray) -> list[dict]:
    rows = []
    for t in GRID:
        adv = p >= t - 1e-9
        n_adv, tp = int(adv.sum()), int((adv & y).sum())
        rows.append({"threshold": t, "advanced": n_adv,
                     "advanced_share": n_adv / len(p),
                     "precision": tp / n_adv if n_adv else None,
                     "recall": tp / int(y.sum()) if y.sum() else None,
                     "missed_share": 1 - tp / int(y.sum()) if y.sum() else None})
    return rows


def preset(rows: list[dict], p: np.ndarray, y: np.ndarray, beta: float,
           missed_cap: float) -> dict:
    note = None
    if 0 < y.sum() < len(y):
        # TRL's F-beta-best cut, floored onto the grid the app's slider uses.
        adv = math.floor(100 * M.tune_threshold(p, y, beta) + 1e-9) / 100
    else:
        adv = 1.0
        note = "no founder (or every founder) reached this target on val; nothing advanced"
    ok = [r for r in rows if r["missed_share"] is not None and r["missed_share"] <= missed_cap
          and r["threshold"] <= adv]
    pas = max((r["threshold"] for r in ok), default=0.0)
    at = next(r for r in rows if r["threshold"] == adv)
    below = p < pas - 1e-9
    return {"advance_at": adv, "pass_below": pas,
            "expected_precision": at["precision"], "expected_recall": at["recall"],
            "advanced_share": at["advanced_share"], "passed_share": float(below.mean()),
            "missed_share_if_passed": float((below & y).sum() / y.sum()) if y.sum() else None,
            "note": note}


def build(d: dict) -> dict:
    out = {}
    for target in TARGETS:
        for timeline in TIMELINES:
            p, y = scores_and_labels(d, target, timeline)
            rows = table(p, y)
            out[f"{target}|{timeline}"] = {
                "target": target, "timeline": timeline, "n": len(p),
                "base_rate": float(y.mean()), "mean_predicted": float(p.mean()),
                "brier": M.brier(p, y), "ece": M.ece(p, y),
                "presets": {name: preset(rows, p, y, beta, cap)
                            for name, (beta, cap) in PRESETS.items()},
                "rows": rows,
            }
    return out


def band_check(d: dict) -> list[dict]:
    """D3's 'sensible distributions' check: mean predicted share per band vs the actual."""
    rows = []
    for j, band in enumerate(BANDS):
        rows.append({"question": "outcome", "band": band,
                     "mean_predicted": float(d["p_outcome"][:, j].mean()),
                     "actual_share": float(np.mean([o == band for o in d["outcome"]]))})
    for j, yr in enumerate(YEARS):
        rows.append({"question": "years", "band": yr,
                     "mean_predicted": float(d["p_years"][:, j].mean()),
                     "actual_share": float(np.mean([y == yr for y in d["years"]]))})
    return rows


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def report_md(tables: dict, bands: list[dict], n: int, stage: str) -> str:
    lines = [f"# Risk thresholds ({stage})", "",
             f"Built from the production model's predictions for the {n} val founders. The app "
             "reads these numbers from `app/thresholds.json`; nothing here uses test.", "",
             "**How to read a row:** with this preset, the app advances founders whose "
             "probability of reaching the target in time is at or above *advance at*, passes "
             "those below *pass below*, and escalates the rest. *Expected precision* is the "
             "share of advanced val founders who actually got there; *missed* is the share of "
             "those who got there that the pass rule would have turned away.", "",
             "Timelines combine the outcome and years questions as if they were independent, "
             "so those probabilities are estimates.", "",
             "| Target | Timeline | Base rate | Preset | Advance at | Pass below | Expected "
             "precision | Recall | Advanced | Missed | Note |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in tables.values():
        for name, ps in t["presets"].items():
            lines.append(
                f"| {t['target']} | {t['timeline']} | {pct(t['base_rate'])} | {name} | "
                f"{ps['advance_at']:.2f} | {ps['pass_below']:.2f} | "
                f"{pct(ps['expected_precision'])} | {pct(ps['expected_recall'])} | "
                f"{pct(ps['advanced_share'])} | {pct(ps['missed_share_if_passed'])} | "
                f"{ps['note'] or ''} |")
    lines += ["", "## Do the band distributions look sensible? (D3)", "",
              "The model's average predicted share of each band against the actual share "
              "on val. Close numbers mean the distributions are calibrated on average.", "",
              "| Question | Band | Mean predicted | Actual |", "|---|---|---|---|"]
    lines += [f"| {b['question']} | {b['band'].replace('$', chr(92) + '$')} | "
              f"{pct(b['mean_predicted'])} | {pct(b['actual_share'])} |" for b in bands]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True)
    ap.add_argument("--predictions", type=Path,
                    default=ROOT / "data" / "predictions" / "prod_val.csv")
    ap.add_argument("--app-out", type=Path, default=ROOT / "app" / "thresholds.json")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    args = ap.parse_args(argv)

    exp_dir = args.results / "experiments" / "04_production_model" / args.stage
    if exp_dir.exists():
        raise SystemExit(f"{exp_dir} exists: results are never overwritten")
    d = load(args.predictions)
    tables = build(d)
    bands = band_check(d)
    doc = {"source": "val", "n": len(d["id"]), "stage": args.stage,
           "probability": "P(outcome >= target) x P(within the timeline); the product assumes "
                          "independence, so label it an estimate",
           "targets": TARGETS, "timelines": TIMELINES, "presets": {
               k: {"advance": f"F{v[0]:g}-best threshold on val", "max_missed_share": v[1]}
               for k, v in PRESETS.items()},
           "outcome_bands": BANDS, "years_bands": YEARS, "tables": tables}
    args.app_out.parent.mkdir(parents=True, exist_ok=True)
    args.app_out.write_text(json.dumps(doc, indent=2))
    exp_dir.mkdir(parents=True)
    (exp_dir / "thresholds.json").write_text(json.dumps(doc, indent=2))
    (exp_dir / "thresholds.md").write_text(report_md(tables, bands, len(d["id"]), args.stage))
    (exp_dir / "band_check.json").write_text(json.dumps(bands, indent=2))
    print(f"wrote {args.app_out} and {exp_dir}: {len(tables)} target x timeline tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
