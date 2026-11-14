"""Tests for research/metrics.py against hand-computed values."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import metrics as m  # noqa: E402


def test_counts_precision_recall_f05() -> None:
    p = np.array([0.9, 0.8, 0.3, 0.6, 0.1])
    y = np.array([1, 0, 1, 1, 0], bool)
    r = m.metrics(p, y, threshold=0.5)
    # Predicted positive: 0.9 (tp), 0.8 (fp), 0.6 (tp). Missed: 0.3 (fn).
    assert (r["predicted_positive"], r["precision"], r["recall"]) == (3, 2 / 3, 2 / 3)
    assert math.isclose(r["f05"], 2 / 3)
    assert math.isclose(m.fbeta(1.0, 0.5), 1.25 * 0.5 / (0.25 + 0.5))


def test_brier_and_ece() -> None:
    p = np.array([1.0, 0.0, 0.75, 0.75])
    y = np.array([1, 0, 1, 0], bool)
    assert math.isclose(m.brier(p, y), (0 + 0 + 0.0625 + 0.5625) / 4)
    # Bins: {0.0}: conf 0, acc 0; {0.75, 0.75}: conf .75, acc .5; {1.0}: conf 1, acc 1.
    assert math.isclose(m.ece(p, y), (2 * 0.25) / 4)
    rows = m.reliability(p, y)
    assert rows[7]["count"] == 2 and math.isclose(rows[7]["share_successful"], 0.5)
    assert rows[9]["count"] == 1 and rows[3]["count"] == 0


def test_given_decisions_override_the_threshold() -> None:
    p = np.array([0.9, 0.1])
    y = np.array([1, 1], bool)
    r = m.metrics(p, y, decisions=np.array([False, True]))
    assert (r["recall"], r["precision"]) == (0.5, 1.0)
    with pytest.raises(ValueError):
        m.metrics(p, y)


def test_tuned_threshold_is_trls_and_separates() -> None:
    p = np.array([0.1, 0.2, 0.7, 0.8])
    y = np.array([0, 0, 1, 1], bool)
    t = m.tune_threshold(p, y)
    assert 0.2 < t <= 0.7
    assert m.metrics(p, y, threshold=t)["f05"] == 1.0


def test_bootstrap_cis_bracket_the_estimate_and_are_reproducible() -> None:
    rng = np.random.default_rng(0)
    y = rng.random(400) < 0.2
    p = np.clip(0.2 + 0.4 * y + rng.normal(0, 0.15, 400), 0, 1)
    t = 0.5
    point = m.metrics(p, y, threshold=t)
    ci = m.bootstrap(p, y, threshold=t, n=200)
    for k in m.METRIC_NAMES:
        lo, hi = ci[k]
        assert lo <= point[k] <= hi, k
    assert ci == m.bootstrap(p, y, threshold=t, n=200)
