"""Score every condition (B3 provisional, D1 final): metrics, CIs and reliability plots.

    python research/evaluate.py --stage b3-provisional            # val only
    python research/evaluate.py --stage d1-final --include-test   # the one test read

Reads every predictions file in data/predictions/ (TRL's trl_{split}.csv for C1a, C1a-40, C1b, C2;
ctrl_{split}.csv; later the Kev conditions), all with the columns
id, split, condition, label, p_success, trl_decision.

One threshold protocol for every condition (MASTER_PLAN 4b.6): tuned on val for F0.5 with
TRL's best_threshold, then applied unchanged to test. For C1a, C1a-40 and C1b, TRL's own as-shipped
decisions (predict(), threshold tuned out-of-fold on train) are reported too. Test metrics
get stratified bootstrap 95% CIs.

Results are never overwritten (section 9c): everything goes to a folder named after --stage,
results/summary/<stage>/ and results/experiments/<experiment>/<stage>/, and the script stops
if that folder exists. Test is read only with --include-test.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402
from common import POSITIVE, ROOT  # noqa: E402

# Names used everywhere (section 9c), and the experiment folder each belongs to.
CONDITIONS = {
    "c1a": ("C1a", "RRF, elastic net (TRL default)", "01_baselines"),
    "c1a40": ("C1a-40", "RRF, elastic net on the 40 questions Kev reads", "01_baselines"),
    "c1b": ("C1b", "RRF, vote (the paper's)", "01_baselines"),
    "ctrl": ("CTRL", "XGBoost on TRL's answers", "01_baselines"),
    "c2": ("C2", "base Kev on TRL's answers", "02_kev_zero_shot"),
    "extra": ("EXTRA", "base Kev on the founder text", "02_kev_zero_shot"),
    "c3": ("C3", "fine-tuned Kev on TRL's answers", "03_kev_finetuned"),
    "c4": ("C4", "fine-tuned Kev on the founder text", "03_kev_finetuned"),
}
NATIVE = ("c1a", "c1a40", "c1b")  # conditions with TRL's own as-shipped decisions

# Fixed colour per condition (reference categorical palette, light mode, validated), so a
# condition looks the same in every plot; marker shapes carry identity without colour.
STYLE = {
    "c1a": ("#2a78d6", "o"), "c1b": ("#eb6834", "s"), "ctrl": ("#1baf7a", "^"),
    "c2": ("#eda100", "D"), "c3": ("#e87ba4", "v"), "c4": ("#008300", "P"),
    "extra": ("#6250d6", "X"), "c1a40": ("#e34948", "h"),
}
SURFACE, TEXT, TEXT_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
DEFAULT_PLOTS = ("c1a,c1b,ctrl", "c1a,c2,c3,c4", "c3,c1a", "c1a40,ctrl,c2,c3")


def read_predictions(pred_dir: Path) -> dict[tuple[str, str], dict]:
    """(condition, split) -> {"id", "y", "p", "trl"} arrays."""
    rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(pred_dir.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if not {"id", "split", "condition", "label", "p_success"} <= set(
                    reader.fieldnames or []):
                continue  # e.g. ctrl_importance.csv
            for r in reader:
                rows[(r["condition"], r["split"])].append(r)
    out = {}
    for key, rs in rows.items():
        out[key] = {"id": [r["id"] for r in rs],
                    "y": np.array([r["label"] == POSITIVE for r in rs]),
                    "p": np.array([float(r["p_success"]) for r in rs]),
                    "trl": [r.get("trl_decision", "") for r in rs]}
    return out


def plain_reading(m: dict) -> str:
    if not m["predicted_positive"]:
        return "flags no founders"
    per10 = round(10 * m["precision"])
    return (f"flags {m['predicted_positive']} of {m['n']}; of every 10 it flags, about "
            f"{per10} succeed; finds {round(100 * m['recall'])}% of the successes")


def plot_reliability(conds: list[str], split: str, preds: dict, path: Path,
                     title: str) -> list[dict]:
    """A reliability diagram for up to four conditions; returns the plotted table."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.plot([0, 1], [0, 1], color=TEXT_2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(0.97, 0.91, "perfectly calibrated", color=TEXT_2, fontsize=8, ha="right",
            rotation=40, rotation_mode="anchor")
    table = []
    for c in conds:
        if (c, split) not in preds:
            continue
        d = preds[(c, split)]
        bins = [b for b in M.reliability(d["p"], d["y"]) if b["count"]]
        xs = [b["mean_predicted"] for b in bins]
        ys = [b["share_successful"] for b in bins]
        color, marker = STYLE[c]
        name = CONDITIONS[c][0]
        ax.plot(xs, ys, color=color, lw=2, zorder=3, label=f"{name}: {CONDITIONS[c][1]}")
        for x, yv, b in zip(xs, ys, bins):
            ax.plot([x], [yv], marker=marker, ms=7, zorder=4, mew=1.5,
                    color=color if b["count"] >= 5 else SURFACE,
                    markeredgecolor=SURFACE if b["count"] >= 5 else color)
        if xs:
            ax.annotate(name, (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                        color=TEXT, fontsize=9, va="center")
        table += [{"condition": c, "split": split, **b} for b in bins]
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_xlabel("Predicted probability of success (bin average)", color=TEXT, fontsize=10)
    ax.set_ylabel("Share of founders who succeeded", color=TEXT, fontsize=10)
    ax.set_title(title, color=TEXT, fontsize=11, loc="left")
    ax.grid(color=GRID, lw=0.8)
    ax.tick_params(colors=TEXT_2, labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=TEXT)
    fig.text(0.01, 0.01, "Hollow markers: bins with fewer than 5 founders. "
             f"Split: {split}. 10 equal-width bins.", color=TEXT_2, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return table


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True, help="e.g. b3-provisional, d1-final")
    ap.add_argument("--include-test", action="store_true", help="read test (D1, or B3/B4)")
    ap.add_argument("--conditions", default="", help="comma list; default: all found")
    ap.add_argument("--plots", default=";".join(DEFAULT_PLOTS),
                    help="semicolon-separated comma lists of conditions, max 4 each")
    ap.add_argument("--predictions", type=Path, default=ROOT / "data" / "predictions")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    ap.add_argument("--bootstrap", type=int, default=M.BOOTSTRAP)
    args = ap.parse_args(argv)

    summary_dir = args.results / "summary" / args.stage
    if summary_dir.exists():
        raise SystemExit(f"{summary_dir} exists: results are never overwritten; "
                         "use a new --stage and record why in DECISIONS.md")
    preds = read_predictions(args.predictions)
    found = sorted({c for c, _ in preds}, key=list(CONDITIONS).index)
    conds = [c for c in (args.conditions.split(",") if args.conditions else found) if c]
    missing_val = [c for c in conds if (c, "val") not in preds]
    if missing_val:
        raise SystemExit(f"no val predictions for {missing_val}: thresholds are tuned on val")
    splits = ["val", "test"] if args.include_test else ["val"]

    rows, per_exp = [], defaultdict(list)
    for c in conds:
        val = preds[(c, "val")]
        t = M.tune_threshold(val["p"], val["y"])
        protocols = [("val-tuned F0.5", t, None)]
        if c in NATIVE and any(val["trl"]):
            protocols.append(("TRL native (train out-of-fold)", None, "trl"))
        for split in splits:
            if (c, split) not in preds:
                continue
            d = preds[(c, split)]
            for protocol, thr, source in protocols:
                dec = np.array([x == POSITIVE for x in d["trl"]]) if source else None
                m = M.metrics(d["p"], d["y"], thr, dec)
                row = {"condition": CONDITIONS[c][0], "name": CONDITIONS[c][1],
                       "split": split, "threshold_protocol": protocol,
                       "threshold": "" if thr is None else round(thr, 4), **m}
                if split == "test":
                    ci = M.bootstrap(d["p"], d["y"], thr, dec, n=args.bootstrap)
                    for k, (lo, hi) in ci.items():
                        row[f"{k}_ci_low"], row[f"{k}_ci_high"] = lo, hi
                row["plain_reading"] = plain_reading(m)
                rows.append(row)
                per_exp[CONDITIONS[c][2]].append(row)

    write_csv(summary_dir / "metrics.csv", rows)
    dictionary = args.results / "summary" / "metrics_dictionary.md"
    if dictionary.exists():  # the column guide sits next to every metrics.csv
        (summary_dir / "metrics_dictionary.md").write_text(dictionary.read_text())
    lines = [f"# Metrics ({args.stage})", "",
             "One row per condition, split and threshold rule. F0.5 (the main metric) "
             "weighs precision twice as much as recall; Brier and ECE are calibration "
             "errors (lower is better). Terms: [GLOSSARY](../../GLOSSARY.md).", "",
             "| Condition | Split | Threshold | F0.5 | Precision | Recall | Brier | ECE | "
             "PR-AUC | What this means |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        def cell(k, r=r):
            v = f"{r[k]:.3f}"
            return f"{v} ({r[k + '_ci_low']:.3f}–{r[k + '_ci_high']:.3f})" \
                if f"{k}_ci_low" in r else v
        lines.append(f"| {r['condition']} ({r['name']}) | {r['split']} | "
                     f"{r['threshold_protocol']} | {cell('f05')} | {cell('precision')} | "
                     f"{cell('recall')} | {cell('brier')} | {cell('ece')} | {cell('pr_auc')} | "
                     f"{r['plain_reading']} |")
    if not args.include_test:
        lines += ["", "Validation only: test has not been read."]
    else:
        lines += ["", "Test values carry stratified bootstrap 95% CIs "
                      f"({args.bootstrap} resamples), with the threshold fixed from val."]
    (summary_dir / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    plot_split = "test" if args.include_test else "val"
    plotted = []
    for spec in args.plots.split(";"):
        group = [c for c in spec.split(",") if c in conds][:4]
        if len(group) < 1:
            continue
        name = "reliability_" + "_vs_".join(group) + f"_{plot_split}.png"
        title = "Calibration: " + " vs ".join(CONDITIONS[c][0] for c in group)
        plotted += plot_reliability(group, plot_split, preds,
                                    summary_dir / "plots" / name, title)
    write_csv(summary_dir / "plots" / "reliability_table.csv", plotted)

    for exp, exp_rows in per_exp.items():
        exp_dir = args.results / "experiments" / exp / args.stage
        write_csv(exp_dir / "metrics.csv", exp_rows)
        if dictionary.exists():
            (exp_dir / "metrics_dictionary.md").write_text(dictionary.read_text())
        pred_rows = []
        for c in conds:
            if CONDITIONS[c][2] != exp or (c, plot_split) not in preds:
                continue
            d = preds[(c, plot_split)]
            t = M.tune_threshold(preds[(c, "val")]["p"], preds[(c, "val")]["y"])
            pred_rows += [{"id": i, "condition": CONDITIONS[c][0], "split": plot_split,
                           "label": POSITIVE if yy else "failed", "p_success": float(pp),
                           "decision": POSITIVE if pp >= t - 1e-9 else "failed"}
                          for i, yy, pp in zip(d["id"], d["y"], d["p"])]
        write_csv(exp_dir / "predictions.csv", pred_rows)
        (exp_dir / "config.json").write_text(json.dumps(
            {"stage": args.stage, "include_test": args.include_test,
             "threshold_protocol": "tuned on val for F0.5 with TRL's best_threshold",
             "bootstrap": args.bootstrap, "seed": M.SEED, "ece_bins": M.ECE_BINS},
            indent=2))
    print(f"wrote {summary_dir} and {len(per_exp)} experiment folder(s); "
          f"{len(rows)} metric rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
