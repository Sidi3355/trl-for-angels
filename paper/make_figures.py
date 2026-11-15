"""Figures for the preprint (paper/figures/*.pdf), from the committed results.

    python paper/make_figures.py

Reads data/predictions/ and results/summary/d1-final/{paired,oracle}.csv and
results/experiments/04_production_model/d3-val/band_shares.csv. Colours and markers follow
research/evaluate.py, so a condition looks the same as in every results plot (the six used here
pass the dataviz palette validator; identity is also carried by axis labels, never colour alone).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import evaluate as E  # noqa: E402
import metrics as M  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Liberation Serif (Times metrics, TrueType so it embeds cleanly) matches the body font.

OUT = ROOT / "paper" / "figures"
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
NAMES = {k: v[0] for k, v in E.CONDITIONS.items()}
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7, "axes.edgecolor": INK_2,
    "axes.labelcolor": INK, "xtick.color": INK_2, "ytick.color": INK_2, "pdf.fonttype": 42,
})


def style(ax, grid_axis="x"):
    ax.grid(axis=grid_axis, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fig_paired():
    rows = {(r["a"], r["b"]): r for r in read_csv(ROOT / "results/summary/d1-final/paired.csv")}
    pairs = [("C1b", "C1a"), ("CTRL", "C1a"), ("C2", "C1a"), ("C3", "C1a"), ("C4", "C1a"),
             ("C3", "C1a-40"), ("C3", "CTRL"), ("C3", "C4"), ("C3", "C2"), ("C4", "EXTRA")]
    metrics = [("f05", "F0.5 (higher is better)"), ("pr_auc", "PR-AUC (higher is better)"),
               ("ece", "ECE (lower is better)")]
    fig, axes = plt.subplots(1, 3, figsize=(5.5, 2.75), sharey=True)
    y = np.arange(len(pairs))[::-1]
    for ax, (k, title) in zip(axes, metrics):
        for yi, pr in zip(y, pairs):
            r = rows[pr]
            d, lo, hi = float(r[f"{k}_diff"]), float(r[f"{k}_ci_low"]), float(r[f"{k}_ci_high"])
            sig = r[f"{k}_ci_excludes_0"] == "True"
            ax.plot([lo, hi], [yi, yi], color=INK, lw=1.2, solid_capstyle="round")
            ax.plot([d], [yi], "o", ms=4.5, mew=1.1, color=INK if sig else "white",
                    markeredgecolor=INK, zorder=3)
        ax.axvline(0, color=INK_2, lw=0.8, ls=(0, (3, 2)))
        ax.set_title(title, loc="left")
        style(ax)
    axes[0].set_yticks(y, [f"{a} − {b}" for a, b in pairs])
    axes[1].set_xlabel("Paired difference on the 600 test founders (A − B), 95% CI")
    fig.text(0.01, 0.005, "Filled: the CI excludes zero. Thresholds fixed from val; "
             "paired stratified bootstrap, 1,000 resamples.", color=INK_2, fontsize=6.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "paired_differences.pdf")
    plt.close(fig)


def fig_scores():
    preds = E.read_predictions(ROOT / "data" / "predictions")
    conds = ["c1a", "ctrl", "c1b", "c2", "extra", "c3", "c4"]
    fig, ax = plt.subplots(figsize=(2.7, 2.6))
    rng = np.random.default_rng(0)
    for i, c in enumerate(conds[::-1]):
        d = preds[(c, "test")]
        color = E.STYLE[c][0] if c != "c1b" else E.STYLE["c1b"][0]
        jitter = rng.uniform(-0.28, 0.28, len(d["p"]))
        ax.scatter(d["p"][~d["y"]], i + jitter[~d["y"]], s=3, color=color, alpha=0.25, lw=0)
        ax.scatter(d["p"][d["y"]], i + jitter[d["y"]], s=5, color=INK, alpha=0.7, lw=0,
                   marker="o")
        lo, hi = np.percentile(d["p"], [5, 95])
        ax.plot([lo, hi], [i + 0.38, i + 0.38], color=color, lw=1.6, solid_capstyle="round")
    ax.set_yticks(range(len(conds)), [NAMES[c] for c in conds[::-1]])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Predicted P(success), test founders")
    ax.axvline(0.2, color=INK_2, lw=0.7, ls=(0, (3, 2)))
    ax.text(0.21, -0.75, "base rate (0.20)", fontsize=6.5, color=INK_2, va="center")
    ax.set_ylim(-1.1, len(conds) - 0.4)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "score_ranges.pdf")
    plt.close(fig)


def fig_oracle():
    rows = read_csv(ROOT / "results/summary/d1-final/oracle.csv")
    order = ["oracle", "C1a", "CTRL", "C1a-40", "C3", "C4", "C2", "EXTRA", "C1b"]
    by = {r["condition"]: r for r in rows}
    fig, ax = plt.subplots(figsize=(2.7, 2.6))
    y = np.arange(len(order))[::-1]
    pos = int(rows[0]["positives"]) / int(rows[0]["n_test"])
    for yi, c in zip(y, order):
        r = by[c]
        v, lo, hi = float(r["pr_auc"]), float(r["pr_auc_ci_low"]), float(r["pr_auc_ci_high"])
        ax.plot([lo, hi], [yi, yi], color=INK, lw=1.1, solid_capstyle="round")
        ax.plot([v], [yi], "D" if c == "oracle" else "o", ms=4.5, color=INK, zorder=3)
        ax.text(hi + 0.006, yi, f"{v:.3f}", va="center", fontsize=6.5, color=INK)
    ax.axvline(pos, color=INK_2, lw=0.7, ls=(0, (3, 2)))
    ax.text(pos + 0.003, y[-1] - 0.75, f"random ({pos:.2f})", fontsize=6.5, color=INK_2)
    ax.set_yticks(y, ["Oracle (true score)" if c == "oracle" else c for c in order])
    ax.set_xlim(0.15, 0.43)
    ax.set_ylim(-1.2, len(order) - 0.4)
    ax.set_xlabel("PR-AUC (95% CI)")
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "ceiling.pdf")
    plt.close(fig)


def fig_reliability():
    preds = E.read_predictions(ROOT / "data" / "predictions")
    fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.75), sharey=True)
    panels = [("Reading TRL's answers", ["c1a", "c2", "c3"]),
              ("Reading the founder profile", ["extra", "c4"])]
    for ax, (title, conds) in zip(axes, panels):
        ax.plot([0, 1], [0, 1], color=INK_2, lw=0.8, ls=(0, (3, 2)))
        for c in conds:
            d = preds[(c, "test")]
            bins = [b for b in M.reliability(d["p"], d["y"]) if b["count"]]
            xs = [b["mean_predicted"] for b in bins]
            ys = [b["share_successful"] for b in bins]
            color, marker = E.STYLE[c]
            ax.plot(xs, ys, color=color, lw=1.6, label=f"{NAMES[c]}: {E.CONDITIONS[c][1]}")
            for x, yv, b in zip(xs, ys, bins):
                ax.plot([x], [yv], marker=marker, ms=4.5, mew=1,
                        color=color if b["count"] >= 5 else "white", markeredgecolor=color)
            dx, dy = {"c3": (4, -7), "c4": (5, 4)}.get(c, (4, 0))
            ax.annotate(NAMES[c], (xs[-1], ys[-1]), xytext=(dx, dy), textcoords="offset points",
                        fontsize=7, color=INK, va="center")
        ax.set(xlim=(0, 1), ylim=(0, 1), title=title)
        ax.set_xlabel("Predicted probability (bin mean)")
        ax.legend(loc="upper left", frameon=False)
        style(ax, "both")
    axes[0].set_ylabel("Share of founders who succeeded")
    fig.text(0.01, 0.005, "Test, 600 founders, 10 equal-width bins; hollow markers: bins with "
             "fewer than 5 founders.", color=INK_2, fontsize=6.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "reliability.pdf")
    plt.close(fig)


def fig_bands():
    rows = read_csv(ROOT / "results/experiments/04_production_model/d3-val/band_shares.csv")
    fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.2), gridspec_kw={"width_ratios": [5, 3]})
    series = [("actual", "Actual share", INK_2), ("with_descriptions", "Asked as trained",
              "#2a78d6"), ("without_descriptions", "Options sent without descriptions",
              "#eb6834")]
    for ax, q in zip(axes, ("outcome", "years")):
        rs = [r for r in rows if r["question"] == q]
        x = np.arange(len(rs))
        w = 0.26
        for j, (k, label, color) in enumerate(series):
            vals = [100 * float(r[k]) for r in rs]
            ax.bar(x + (j - 1) * w, vals, w * 0.9, color=color, label=label)
            for xi, v in zip(x + (j - 1) * w, vals):
                ax.text(xi, v + 0.8, f"{v:.0f}", ha="center", fontsize=5.5, color=INK)
        ax.set_xticks(x, [r["band"].replace("$", r"\$") for r in rs])
        ax.set_ylim(0, 60)
        ax.set_title(f"{q} (% of the 400 val founders)", loc="left")
        style(ax, "y")
    axes[0].legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "band_shares.pdf")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig_paired()
    fig_scores()
    fig_oracle()
    fig_reliability()
    fig_bands()
    print(f"wrote {sorted(p.name for p in OUT.glob('*.pdf'))}")
