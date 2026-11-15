"""The research metrics (MASTER_PLAN section 4b): F0.5, precision, recall, Brier, ECE, PR-AUC,
stratified bootstrap 95% CIs, and reliability tables.

One threshold protocol for every condition (4b.6): the threshold is tuned on val for F0.5 with
TRL's own best_threshold, then applied unchanged to test. Brier, ECE and PR-AUC need no
threshold.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score

BETA = 0.5
ECE_BINS = 10
BOOTSTRAP = 1000
SEED = 42


def tune_threshold(p: np.ndarray, y: np.ndarray, beta: float = BETA) -> float:
    """The F-beta-best threshold on these scores, by TRL's own rule (best_threshold)."""
    from think_reason_learn.core._combine import best_threshold

    return float(best_threshold(np.asarray(p, float), np.asarray(y, bool), beta))


def fbeta(precision: float, recall: float, beta: float = BETA) -> float:
    b2 = beta * beta
    denom = b2 * precision + recall
    return (1 + b2) * precision * recall / denom if denom > 0 else 0.0


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def ece(p: np.ndarray, y: np.ndarray, bins: int = ECE_BINS) -> float:
    """Expected calibration error: equal-width bins, weighted by how many fall in each."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        mask = idx == b
        if mask.any():
            total += mask.sum() * abs(p[mask].mean() - y[mask].mean())
    return float(total / len(p)) if len(p) else 0.0


def reliability(p: np.ndarray, y: np.ndarray, bins: int = ECE_BINS) -> list[dict]:
    """Per bin: the mean predicted probability, the share that succeeded, and the count."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    rows = []
    for b in range(bins):
        mask = idx == b
        rows.append({"bin": b, "low": b / bins, "high": (b + 1) / bins, "count": int(mask.sum()),
                     "mean_predicted": float(p[mask].mean()) if mask.any() else None,
                     "share_successful": float(y[mask].mean()) if mask.any() else None})
    return rows


def metrics(p: np.ndarray, y: np.ndarray, threshold: float | None = None,
            decisions: np.ndarray | None = None) -> dict:
    """Every metric for scores ``p`` against labels ``y`` (bool).

    Decisions come from ``threshold`` (positive at or above it), or are given directly
    (e.g. TRL's own predict()). Threshold-free metrics use ``p`` either way.
    """
    p, y = np.asarray(p, float), np.asarray(y, bool)
    if decisions is None:
        if threshold is None:
            raise ValueError("give a threshold or decisions")
        decisions = p >= threshold - 1e-9  # as TRL decides
    d = np.asarray(decisions, bool)
    tp, fp, fn = int((d & y).sum()), int((d & ~y).sum()), int((~d & y).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "n": len(y), "positives": int(y.sum()), "predicted_positive": int(d.sum()),
        "f05": fbeta(precision, recall), "precision": precision, "recall": recall,
        "brier": brier(p, y), "ece": ece(p, y),
        "pr_auc": float(average_precision_score(y, p)) if 0 < y.sum() < len(y) else float("nan"),
    }


METRIC_NAMES = ("f05", "precision", "recall", "brier", "ece", "pr_auc")


def bootstrap(p: np.ndarray, y: np.ndarray, threshold: float | None = None,
              decisions: np.ndarray | None = None, n: int = BOOTSTRAP,
              seed: int = SEED) -> dict[str, tuple[float, float]]:
    """95% percentile CIs, resampling positives and negatives separately (stratified).

    The threshold (or the decisions) stays fixed: it was chosen on val, not on this sample.
    """
    p, y = np.asarray(p, float), np.asarray(y, bool)
    d = None if decisions is None else np.asarray(decisions, bool)
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
    draws: dict[str, list[float]] = {m: [] for m in METRIC_NAMES}
    for _ in range(n):
        idx = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        m = metrics(p[idx], y[idx], threshold, None if d is None else d[idx])
        for k in METRIC_NAMES:
            draws[k].append(m[k])
    return {k: (float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5)))
            for k, v in draws.items()}
