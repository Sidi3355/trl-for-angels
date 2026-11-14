"""Tests for research/thresholds.py on synthetic production predictions (fixtures, not data)."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import thresholds as th  # noqa: E402


def write_prod(path: Path, n: int = 300, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "split", "outcome", "years",
                    *[f"p_outcome_{b}" for b in th.BANDS], *[f"p_years_{y}" for y in th.YEARS]])
        for i in range(n):
            o = rng.choice(len(th.BANDS), p=[0.5, 0.15, 0.15, 0.1, 0.1])
            yr = rng.choice(3)
            s = rng.uniform(0, 0.5)  # informative on average, often wrong: overlapping
            po = rng.dirichlet(np.ones(5)) * (1 - s)
            po[o] += s
            py = rng.dirichlet(np.ones(3)) * 0.6
            py[yr] += 0.4
            w.writerow([f"r{i:05d}", "val", th.BANDS[o], th.YEARS[yr], *po, *py])


def test_probability_sums_bands_at_or_above_the_target(tmp_path: Path) -> None:
    write_prod(tmp_path / "p.csv")
    d = th.load(tmp_path / "p.csv")
    p, y = th.scores_and_labels(d, "$500M", "any")
    expected = d["p_outcome"][:, 3:].sum(axis=1)
    assert np.allclose(p, expected)
    assert all(yy == (o in ("$500M-$1B", "over $1B")) for yy, o in zip(y, d["outcome"]))
    p8, y8 = th.scores_and_labels(d, "$1B", "8 years")
    assert np.allclose(p8, d["p_outcome"][:, 4] * d["p_years"][:, :2].sum(axis=1))
    assert all(v == (o == "over $1B" and yr != "over 8")
               for v, o, yr in zip(y8, d["outcome"], d["years"]))


def test_presets_are_ordered_and_respect_their_caps(tmp_path: Path) -> None:
    write_prod(tmp_path / "p.csv")
    tables = th.build(th.load(tmp_path / "p.csv"))
    assert len(tables) == 9
    for t in tables.values():
        ps = t["presets"]
        for name, (_, cap) in th.PRESETS.items():
            assert ps[name]["pass_below"] <= ps[name]["advance_at"]
            assert ps[name]["missed_share_if_passed"] <= cap + 1e-9
        # More appetite for risk never advances fewer founders.
        assert (ps["aggressive"]["advanced_share"] >= ps["balanced"]["advanced_share"]
                >= ps["conservative"]["advanced_share"])
        precisions = [r["precision"] for r in t["rows"] if r["precision"] is not None]
        assert all(0 <= x <= 1 for x in precisions)


def test_cli_writes_the_app_file_and_never_overwrites(tmp_path: Path) -> None:
    write_prod(tmp_path / "p.csv")
    args = ["--stage", "d4", "--predictions", str(tmp_path / "p.csv"),
            "--app-out", str(tmp_path / "app/thresholds.json"),
            "--results", str(tmp_path / "results")]
    th.main(args)
    doc = json.loads((tmp_path / "app/thresholds.json").read_text())
    assert doc["source"] == "val" and set(doc["tables"]) == {
        f"{t}|{h}" for t in th.TARGETS for h in th.TIMELINES}
    bands = json.loads((tmp_path / "results/experiments/04_production_model/d4/"
                        "band_check.json").read_text())
    assert math.isclose(sum(b["actual_share"] for b in bands if b["question"] == "outcome"), 1)
    with pytest.raises(SystemExit, match="never overwritten"):
        th.main(args)
