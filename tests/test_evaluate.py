"""Tests for research/evaluate.py on synthetic predictions (fixtures, not results)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import evaluate as ev  # noqa: E402


def write_preds(pred_dir: Path, splits=("val", "test")) -> None:
    rng = np.random.default_rng(0)
    pred_dir.mkdir(parents=True)
    for split in splits:
        n = 80
        y = rng.random(n) < 0.25
        with (pred_dir / f"trl_{split}.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "split", "condition", "label", "p_success", "trl_decision"])
            for cond in ("c1a", "c2"):
                p = np.clip(0.2 + 0.5 * y + rng.normal(0, 0.2, n), 0, 1)
                for i in range(n):
                    label = "successful" if y[i] else "failed"
                    native = "successful" if p[i] >= 0.5 else "failed"
                    w.writerow([f"r{i:05d}", split, cond, label, p[i], native])


def test_val_only_never_reads_test(tmp_path: Path) -> None:
    write_preds(tmp_path / "preds")
    ev.main(["--stage", "s1", "--predictions", str(tmp_path / "preds"),
             "--results", str(tmp_path / "results"), "--bootstrap", "20"])
    rows = list(csv.DictReader((tmp_path / "results/summary/s1/metrics.csv").open()))
    assert {r["split"] for r in rows} == {"val"}
    # C1a gets both threshold rules; C2 only the val-tuned one.
    assert sorted((r["condition"], r["threshold_protocol"]) for r in rows) == [
        ("C1a", "TRL native (train out-of-fold)"), ("C1a", "val-tuned F0.5"),
        ("C2", "val-tuned F0.5")]
    assert (tmp_path / "results/summary/s1/plots/reliability_c1a_vs_c2_val.png").exists()
    assert (tmp_path / "results/experiments/01_baselines/s1/predictions.csv").exists()


def test_the_metrics_dictionary_is_copied_next_to_each_table(tmp_path: Path) -> None:
    write_preds(tmp_path / "preds")
    (tmp_path / "results/summary").mkdir(parents=True)
    (tmp_path / "results/summary/metrics_dictionary.md").write_text("# columns")
    ev.main(["--stage", "s2", "--predictions", str(tmp_path / "preds"),
             "--results", str(tmp_path / "results"), "--bootstrap", "20"])
    for d in ("summary/s2", "experiments/01_baselines/s2", "experiments/02_kev_zero_shot/s2"):
        assert (tmp_path / "results" / d / "metrics_dictionary.md").read_text() == "# columns"


def test_test_metrics_carry_cis_and_results_are_never_overwritten(tmp_path: Path) -> None:
    write_preds(tmp_path / "preds")
    args = ["--stage", "final", "--include-test", "--predictions", str(tmp_path / "preds"),
            "--results", str(tmp_path / "results"), "--bootstrap", "50"]
    ev.main(args)
    rows = list(csv.DictReader((tmp_path / "results/summary/final/metrics.csv").open()))
    test = [r for r in rows if r["split"] == "test"]
    assert test and all(float(r["f05_ci_low"]) <= float(r["f05"]) <= float(r["f05_ci_high"])
                        for r in test)
    with pytest.raises(SystemExit, match="never overwritten"):
        ev.main(args)


def test_val_predictions_are_required(tmp_path: Path) -> None:
    write_preds(tmp_path / "preds", splits=("test",))
    with pytest.raises(SystemExit, match="thresholds are tuned on val"):
        ev.main(["--stage", "x", "--include-test", "--predictions", str(tmp_path / "preds"),
                 "--results", str(tmp_path / "results")])
