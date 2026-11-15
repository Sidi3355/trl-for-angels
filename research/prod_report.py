"""D3 report: how the production model's distributions look on val, and its P($500M+) against C3.

    python research/prod_report.py --stage d3-val

Reads data/predictions/prod_val.csv (the production model's calibrated outcome and years
distributions for the 400 val founders, asked with the options' descriptions, as trained),
data/predictions/prod_val_no_descriptions.csv (the same model asked without them: Kaggle's
first pass, kept for the record) and data/predictions/kev_c3_val.csv (C3). Writes
results/experiments/04_production_model/<stage>/: metrics.csv (the research target, P(outcome
at or above $500M), scored like every research condition), paired.csv (production − C3, the same
founders), band_shares.csv, predictions.csv, config.json, metrics_dictionary.md and plots/.
Val only: the production model is never scored on test (MASTER_PLAN section 7). Nothing is
overwritten.
"""

# ruff: noqa: E501  (DICTIONARY holds Markdown table rows, which cannot wrap)
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate as E  # noqa: E402
import metrics as M  # noqa: E402
from common import OUTCOME_BANDS, ROOT, YEARS_BANDS  # noqa: E402

BANDS, YEARS = list(OUTCOME_BANDS), list(YEARS_BANDS)
SUCCESS = ["$500M-$1B", "over $1B"]  # the research label (MASTER_PLAN section 3)
KEYS = ("f05", "precision", "recall", "brier", "ece", "pr_auc")
HF = "Sidi3355/trl-for-angels-kev-prod"
HF_COMMIT = "fc8409c7510dbd1fc360eee40fd1da2bfdce4f7b"


def load_prod(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {"rows": rows, "id": [r["id"] for r in rows],
            "P": np.array([[float(r[f"p_outcome_{b}"]) for b in BANDS] for r in rows]),
            "Q": np.array([[float(r[f"p_years_{b}"]) for b in YEARS] for r in rows]),
            "outcome": [r["outcome"] for r in rows], "years": [r["years"] for r in rows]}


def scored(p: np.ndarray, y: np.ndarray, boot: int) -> dict:
    """Every metric at the val-tuned F0.5 threshold, with stratified bootstrap 95% CIs."""
    t = M.tune_threshold(p, y)
    row = {"threshold": t, **M.metrics(p, y, t)}
    rng = np.random.default_rng(M.SEED)
    pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
    draws = {k: [] for k in KEYS}
    for _ in range(boot):
        i = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        m = M.metrics(p[i], y[i], t)
        for k in KEYS:
            draws[k].append(m[k])
    for k in KEYS:
        lo, hi = np.nanpercentile(np.asarray(draws[k], float), [2.5, 97.5])
        row[f"{k}_ci_low"], row[f"{k}_ci_high"] = float(lo), float(hi)
    return row


def paired(pa: np.ndarray, pb: np.ndarray, y: np.ndarray, boot: int) -> list[dict]:
    ta, tb = M.tune_threshold(pa, y), M.tune_threshold(pb, y)
    ma, mb = M.metrics(pa, y, ta), M.metrics(pb, y, tb)
    rng = np.random.default_rng(M.SEED)
    pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
    draws = {k: [] for k in ("f05", "brier", "ece", "pr_auc")}
    for _ in range(boot):
        i = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        ra, rb = M.metrics(pa[i], y[i], ta), M.metrics(pb[i], y[i], tb)
        for k in draws:
            draws[k].append(ra[k] - rb[k])
    out = []
    for k, v in draws.items():
        lo, hi = np.nanpercentile(np.asarray(v, float), [2.5, 97.5])
        out.append({"metric": k, "prod": ma[k], "c3": mb[k], "diff": ma[k] - mb[k],
                    "ci_low": float(lo), "ci_high": float(hi),
                    "ci_excludes_0": bool(lo > 0 or hi < 0)})
    return out


def plot_bands(shares: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    series = [("actual", "Actual share", E.TEXT_2),
              ("with_descriptions", "Predicted, asked as trained", "#2a78d6"),
              ("without_descriptions", "Predicted, options sent without descriptions",
               "#eb6834")]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), dpi=200,
                             gridspec_kw={"width_ratios": [5, 3]})
    fig.patch.set_facecolor(E.SURFACE)
    for ax, q, bands in ((axes[0], "outcome", BANDS), (axes[1], "years", YEARS)):
        ax.set_facecolor(E.SURFACE)
        rows = [s for s in shares if s["question"] == q]
        x = np.arange(len(bands))
        w = 0.26
        for j, (key, label, color) in enumerate(series):
            vals = [100 * r[key] for r in rows]
            bars = ax.bar(x + (j - 1) * w, vals, w * 0.92, color=color, label=label)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.0f}", ha="center",
                        fontsize=7, color=E.TEXT)
        ax.set_xticks(x, [b.replace("$", r"\$") for b in bands], fontsize=8, color=E.TEXT)
        ax.set_ylim(0, 62)
        ax.set_title(f"{q}: share of the 400 val founders (%)", color=E.TEXT, fontsize=10,
                     loc="left")
        ax.grid(axis="y", color=E.GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=E.TEXT_2, labelsize=8)
        for spine in ax.spines.values():
            spine.set_visible(False)
    axes[0].set_ylabel("Share of founders (%)", color=E.TEXT, fontsize=9)
    axes[0].legend(loc="upper right", fontsize=8, frameon=False, labelcolor=E.TEXT)
    fig.text(0.01, 0.01, "Predicted share: the production model's mean calibrated probability "
             "for each band. Val split, 400 founders.", color=E.TEXT_2, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=E.SURFACE)
    plt.close(fig)


DICTIONARY = """# Metrics dictionary (04_production_model, D3)

Terms are defined in plain English in [GLOSSARY.md](../../../GLOSSARY.md).

## metrics.csv (one row per model; val, 400 founders, 80 of whom reached $500M or more)

| Column | Meaning | Units | Better if |
|---|---|---|---|
| `model` | PROD (the production model: P(outcome is \\$500M-\\$1B or over \\$1B)) or C3 (P(success)) | – | – |
| `score` | the probability scored | – | – |
| `threshold` | flag a founder at or above it; tuned on these same val founders for F0.5 | probability | – |
| `n`, `positives`, `predicted_positive` | founders, founders who succeeded, founders flagged | count | – |
| `f05` | F0.5, the research metric (precision weighted above recall) | 0–1 | higher |
| `precision` | share of flagged founders who succeeded | 0–1 | higher |
| `recall` | share of successful founders who were flagged | 0–1 | higher |
| `brier` | mean squared error of the probability | 0–1 | lower |
| `ece` | expected calibration error, 10 equal-width bins | 0–1 | lower |
| `pr_auc` | area under the precision–recall curve (threshold-free ranking); random is 0.20 | 0–1 | higher |
| `*_ci_low`, `*_ci_high` | stratified bootstrap 95% CI (1,000 resamples, seed 42), threshold fixed | – | – |

## paired.csv (PROD − C3, the same 400 founders)

`metric`, each side's value (`prod`, `c3`), `diff`, its paired bootstrap 95% CI (`ci_low`,
`ci_high`) and whether that CI excludes zero. Positive F0.5 and PR-AUC differences favour PROD;
negative Brier and ECE differences do.

## band_shares.csv (one row per question and band)

`actual` is the share of val founders in the band; `with_descriptions` the production model's
mean calibrated probability for it, asked as trained; `without_descriptions` the same when the
options were sent without their descriptions (Kaggle's first pass, not used).

## predictions.csv (one row per val founder)

`id`, the true `outcome` and `years`, each band's calibrated probability (`p_outcome_<band>`,
`p_years_<band>`), and `p_500m_or_more`, the sum of the two top outcome bands.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True)
    ap.add_argument("--predictions", type=Path, default=ROOT / "data" / "predictions")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    ap.add_argument("--bootstrap", type=int, default=M.BOOTSTRAP)
    args = ap.parse_args(argv)

    out = args.results / "experiments" / "04_production_model" / args.stage
    if out.exists():
        raise SystemExit(f"{out} exists: results are never overwritten")
    prod = load_prod(args.predictions / "prod_val.csv")
    raw = load_prod(args.predictions / "prod_val_no_descriptions.csv")
    c3 = E.read_predictions(args.predictions)[("c3", "val")]
    if prod["id"] != c3["id"] or raw["id"] != prod["id"]:
        raise SystemExit("the production model and C3 cover different val founders")
    y = np.array([o in SUCCESS for o in prod["outcome"]])
    if not np.array_equal(y, c3["y"]):
        raise SystemExit("the production labels and C3's disagree")
    p_prod = prod["P"][:, [BANDS.index(b) for b in SUCCESS]].sum(1)

    rows = []
    for name, score, p in (("PROD", "P(outcome >= $500M)", p_prod), ("C3", "P(success)", c3["p"])):
        m = scored(p, y, args.bootstrap)
        rows.append({"model": name, "score": score, "split": "val", **m,
                     "plain_reading": E.plain_reading(m)})
    E.write_csv(out / "metrics.csv", rows)
    E.write_csv(out / "paired.csv", paired(p_prod, c3["p"], y, args.bootstrap))

    shares = []
    for q, bands, key in (("outcome", BANDS, "P"), ("years", YEARS, "Q")):
        for j, b in enumerate(bands):
            shares.append({"question": q, "band": b,
                           "actual": float(np.mean([v == b for v in prod[q]])),
                           "with_descriptions": float(prod[key][:, j].mean()),
                           "without_descriptions": float(raw[key][:, j].mean())})
    E.write_csv(out / "band_shares.csv", shares)

    preds = [{**{k: v for k, v in r.items() if k != "split"},
              "p_500m_or_more": f"{p:.6g}"} for r, p in zip(prod["rows"], p_prod)]
    E.write_csv(out / "predictions.csv", preds)

    E.CONDITIONS["prod"] = ("PROD", "the production model, P($500M or more)", "")
    E.STYLE["prod"] = ("#0e8a8a", "o")  # not a research condition: its own colour
    table = E.plot_reliability(
        ["prod", "c3"], "val",
        {("prod", "val"): {"p": p_prod, "y": y}, ("c3", "val"): c3},
        out / "plots" / "reliability_prod_vs_c3_val.png",
        "Production model's P($500M or more) against C3, val")
    E.write_csv(out / "reliability_table.csv", table)
    plot_bands(shares, out / "plots" / "band_shares_val.png")

    temps = json.loads((ROOT / "data" / "models" / "prod" / "temperatures.json").read_text())
    (out / "config.json").write_text(json.dumps({
        "stage": args.stage, "split": "val", "n": len(y),
        "model": f"{HF}@{HF_COMMIT}", "input": "c3 (TRL's 40 answers as text; D2)",
        "questions": "outcome (5 bands) and years (3 bands), with the options' descriptions "
                     "(research/common.py PROD_QUESTIONS)",
        "temperatures": temps["per_question"],
        "scored": "through TRL (fork d9d1380, ChoiceQuestion descriptions) against kev.serve "
                  "on CPU, fp32, raw; temperatures applied by research/kev_predict.py",
        "threshold_protocol": "tuned on these val founders for F0.5 (TRL's best_threshold)",
        "bootstrap": args.bootstrap, "seed": M.SEED, "ece_bins": M.ECE_BINS,
    }, indent=2) + "\n")
    (out / "metrics_dictionary.md").write_text(DICTIONARY)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
