"""Tests for research/splits.py on synthetic records (test fixtures, not data).

Every output goes to pytest's tmp_path; nothing here writes to data/ or results/.
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import splits as sp  # noqa: E402
import validate as v  # noqa: E402

PLAN_3000 = {"shut down": 1500, "under $50M": 450, "$50M-$500M": 450,
             "$500M-$1B": 300, "over $1B": 300}

INDUSTRIES = ["fintech", "healthtech", "biotech", "B2B SaaS", "developer tools", "e-commerce",
              "logistics", "edtech", "climate", "cybersecurity", "marketplaces", "media",
              "hardware", "insurtech", "agtech", "gaming", "proptech", "HR tech", "travel",
              "food", "robotics", "legal tech", "energy storage", "pet care", "sports tech"]
DEGREES = ["BSc", "BA", "MSc", "MBA", "PhD", "BEng", "MA"]
SUBJECTS = ["Computer Science", "Economics", "Biology", "Mechanical Engineering", "History",
            "Mathematics", "Physics", "Finance", "Chemistry", "Industrial Design", "Law",
            "Electrical Engineering"]
ROLES = ["Analyst", "Software Engineer", "Product Manager", "Sales Director",
         "Research Scientist", "Operations Manager", "Designer", "Data Scientist", "Consultant",
         "Account Executive", "Engineering Manager", "Marketing Associate", "Nurse",
         "Teacher", "Buyer", "Trader"]
EMPLOYERS = [("a payments company", "Financial Services"), ("a hospital network", "Healthcare"),
             ("a freight brokerage company", "Logistics"), ("a game studio", "Gaming"),
             ("a search and advertising company", "Internet"),
             ("an insurance carrier", "Insurance"), ("a chip maker", "Semiconductors"),
             ("a school district", "Education"), ("a retail chain", "Retail"),
             ("a telecom operator", "Telecommunications"), ("a law firm", "Legal Services"),
             ("a utility company", "Energy"), ("a hotel group", "Hospitality"),
             ("a car maker", "Automotive")]
PRIORS = [("none", "none"), ("1 founded before, with outcomes 1 shut down", "none"),
          ("1 founded before, with outcomes 1 acquired under $50M",
           "1 acquisition as co-founder, under $50M"),
          ("2 founded before, with outcomes 1 shut down, 1 acquired $50M-$500M",
           "1 acquisition as co-founder, $50M-$500M")]


def _profile(rng: random.Random) -> str:
    """A varied founder profile in the section 10 template."""
    lines = [
        f"This founder leads a startup in the {rng.choice(INDUSTRIES)} industry, founded with "
        f"{rng.choice(v.COFOUNDERS)} co-founder(s).",
        f"Founder background: {rng.choice(v.BACKGROUNDS)}, {rng.choice(v.EXPERIENCE)} years of "
        f"work experience, {rng.choice(v.INDUSTRY_EXP)} prior experience in this startup's "
        "industry.",
        "Education:",
    ]
    for _ in range(rng.randint(1, 2)):
        qs = "unknown" if rng.random() < 0.05 else rng.choice(v.QS)
        lines.append(f"- {rng.choice(DEGREES)} in {rng.choice(SUBJECTS)}, university ranked "
                     f"QS {qs}")
    lines.append("Jobs (oldest first):")
    for _ in range(rng.randint(1, 4)):
        company, industry = rng.choice(EMPLOYERS)
        lines.append(f"- {rng.choice(ROLES)}, {company}, {rng.choice(v.SIZES)} employees, "
                     f"{industry}, {rng.choice(v.DURATIONS)} years")
    startups, exits = rng.choice(PRIORS)
    if rng.random() < 0.08:
        exits = "unknown"
    lines += [f"Prior startups: {startups}.", f"Prior exits: {exits}."]
    return "\n".join(lines)


def _row(outcome: str, years: str, inp: str) -> dict[str, str]:
    return {"instruction": v.INSTRUCTION, "input": inp,
            "output": f"outcome: {outcome}\nyears: {years}"}


def _dataset(counts: dict[str, int], seed: int = 0) -> list[dict[str, str]]:
    """Rows with exactly these band counts, in a shuffled order."""
    rng = random.Random(seed)
    rows = [_row(band, rng.choice(v.YEARS), _profile(rng))
            for band, n in counts.items() for _ in range(n)]
    rng.shuffle(rows)
    return rows


def _write(path: Path, rows: list[dict] | list[str]) -> Path:
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def _run(tmp: Path, rows: list, seed: int = 42, name: str = "out") -> tuple[sp.SplitResult, Path]:
    """Write rows, run the split into tmp/name, and return the result and that folder."""
    tmp.mkdir(parents=True, exist_ok=True)
    src = tmp / "full.jsonl"
    if not src.exists():
        _write(src, rows)
    out = tmp / name
    run_info = out / "run_info.json"
    out.mkdir()
    run_info.write_text(json.dumps({"updated": "x", "splits": {"planned": sp.PLANNED,
                                                               "actual": None}}, indent=2))
    res = sp.make_splits(src, out / "splits", out / "stats.md", run_info, seed=seed)
    return res, out


def _read_split(out: Path, split: str) -> list[dict]:
    text = (out / "splits" / f"{split}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


@pytest.fixture(scope="module")
def full(tmp_path_factory) -> tuple[sp.SplitResult, Path, list[dict]]:
    """One run on 3,000 rows with the plan's band counts, shared by several tests."""
    rows = _dataset(PLAN_3000)
    res, out = _run(tmp_path_factory.mktemp("full"), rows)
    return res, out, rows


# ---------------------------------------------------------------------------


def test_sizes_for_3000_rows(full):
    res, out, _ = full
    assert res.sizes == {"train": 2000, "val": 400, "test": 600}
    assert not res.scaled
    for s, n in res.sizes.items():
        assert len(_read_split(out, s)) == n
    actual = json.loads((out / "run_info.json").read_text())["splits"]["actual"]
    assert {k: actual[k] for k in sp.SPLITS} == res.sizes
    assert actual["seed"] == 42 and actual["input_file"] == "full.jsonl"
    assert actual["rows_read"] == actual["rows_kept"] == 3000


def test_run_info_keeps_other_keys(full):
    _, out, _ = full
    info = json.loads((out / "run_info.json").read_text())
    assert info["updated"] == "x"
    assert info["splits"]["planned"] == sp.PLANNED
    assert info["splits"]["actual"]["duplicate_groups"] == 0


@pytest.mark.parametrize("n", [3000, 1500, 757, 101, 7])
def test_split_sizes_keep_the_ratio(n):
    sizes = sp.split_sizes(n)
    assert sum(sizes.values()) == n
    for s, planned in sp.PLANNED.items():
        assert abs(sizes[s] - Fraction(n * planned, 3000)) < 1


def test_other_totals_are_scaled_and_reported(tmp_path):
    counts = {"shut down": 380, "under $50M": 113, "$50M-$500M": 112,
              "$500M-$1B": 77, "over $1B": 75}  # 757 rows
    res, out = _run(tmp_path, _dataset(counts, seed=1))
    assert res.scaled
    assert res.sizes == sp.split_sizes(757) == {"train": 505, "val": 101, "test": 151}
    assert "scaled" in (out / "stats.md").read_text()
    assert json.loads((out / "run_info.json").read_text())["splits"]["actual"][
        "scaled_from_planned"] is True


def _assert_stratified(res: sp.SplitResult) -> None:
    n = len(res.kept)
    totals = Counter(r.outcome for r in res.kept)
    for s, recs in res.by_split.items():
        got = Counter(r.outcome for r in recs)
        for band, total in totals.items():
            exact = Fraction(total * len(recs), n)
            assert abs(got[band] - exact) <= 1, (s, band, got[band], float(exact))


def test_stratified_on_outcome_band(full, tmp_path):
    _assert_stratified(full[0])
    counts = {"shut down": 400, "under $50M": 97, "$50M-$500M": 151,
              "$500M-$1B": 33, "over $1B": 16}  # uneven bands, 697 rows
    res, _ = _run(tmp_path, _dataset(counts, seed=2))
    _assert_stratified(res)
    assert [c[1] for c in res.checks] == ["PASS"] * len(res.checks)


def test_band_quotas_add_up_exactly():
    counts = {"shut down": 401, "under $50M": 97, "$50M-$500M": 151, "$500M-$1B": 33,
              "over $1B": 17}
    sizes = sp.split_sizes(sum(counts.values()))
    q = sp.band_quotas(counts, sizes)
    for b, c in counts.items():
        assert sum(q[b].values()) == c
    for s, size in sizes.items():
        assert sum(q[b][s] for b in counts) == size
        for b, c in counts.items():
            assert abs(q[b][s] - Fraction(c * size, sum(counts.values()))) < 1


def test_same_input_and_seed_give_identical_files(tmp_path):
    rows = _dataset({"shut down": 150, "under $50M": 45, "$50M-$500M": 45, "$500M-$1B": 30,
                     "over $1B": 30}, seed=3)
    _, a = _run(tmp_path, rows, name="a")
    _, b = _run(tmp_path, rows, name="b")
    for rel in ["splits/train.jsonl", "splits/val.jsonl", "splits/test.jsonl", "stats.md",
                "run_info.json"]:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel
    _, c = _run(tmp_path, rows, seed=7, name="c")
    assert (a / "splits/test.jsonl").read_bytes() != (c / "splits/test.jsonl").read_bytes()


def test_duplicate_groups_never_span_splits(tmp_path):
    rng = random.Random(4)
    rows = _dataset({"shut down": 300, "under $50M": 90, "$50M-$500M": 90, "$500M-$1B": 60,
                     "over $1B": 60}, seed=4)
    long_rows = [i for i, r in enumerate(rows) if r["input"].count("\n- ") >= 4]
    picks = rng.sample(long_rows, 26)
    expected: list[set[int]] = []  # groups as 1-based positions in the file
    for i in picks[:10]:  # exact copies
        rows.append(dict(rows[i]))
        expected.append({i + 1, len(rows)})
    i = picks[25]  # the same profile with a different outcome
    other = "over $1B" if "shut down" in rows[i]["output"] else "shut down"
    rows.append(dict(rows[i], output=f"outcome: {other}\nyears: 5-8"))
    expected.append({i + 1, len(rows)})
    for i in picks[10:20]:  # near copies: one word changed in a long profile
        near = dict(rows[i])
        near["input"] = re.sub(r"founded with (\S+) co-founder",
                               lambda m: "founded with "
                               + ("2" if m.group(1) != "2" else "1") + " co-founder",
                               near["input"])
        rows.append(near)
        expected.append({i + 1, len(rows)})
    for i in picks[20:25]:  # groups of three: an exact copy plus a near copy
        rows.append(dict(rows[i]))
        near = dict(rows[i])
        near["input"] = re.sub(r"Founder background: ([^,]+),",
                               lambda m: "Founder background: "
                               + ("mixed" if m.group(1) != "mixed" else "business") + ",",
                               near["input"])
        rows.append(near)
        expected.append({i + 1, len(rows) - 1, len(rows)})
    # Shuffle the file, then translate the expected groups to the new positions.
    order = list(range(len(rows)))
    rng.shuffle(order)
    new_pos = {old: new + 1 for new, old in enumerate(order)}
    rows = [rows[old] for old in order]
    expected = [{new_pos[p - 1] for p in g} for g in expected]

    res, out = _run(tmp_path, rows)
    found = [{r.row for r in g.rows} for g in res.groups]
    for g in expected:
        assert any(g <= f for f in found), f"group {sorted(g)} not detected"
    by_id = {}
    for s in sp.SPLITS:
        for rec in _read_split(out, s):
            by_id[rec["id"]] = s
    for g in res.groups:
        assert len({by_id[res.ids[r.row]] for r in g.rows}) == 1
    # Groups are spread over the splits, not all parked in train.
    assert len({by_id[res.ids[g.rows[0].row]] for g in res.groups}) > 1
    assert json.loads((out / "run_info.json").read_text())["splits"]["actual"][
        "duplicate_groups"] == len(res.groups)
    report = (out / "stats.md").read_text()
    assert "1 group(s) have copies with different outcome bands" in report
    _assert_stratified(res)


def test_group_bigger_than_its_band_share_stays_together(tmp_path):
    # 150 rows: 100 / 20 / 30. Thirty copies of one over-$1B profile, out of 40 over-$1B
    # rows, exceed that band's train share (26.7); quota swaps keep the sizes exact.
    rows = _dataset({"shut down": 60, "under $50M": 20, "$50M-$500M": 20, "$500M-$1B": 10,
                     "over $1B": 11}, seed=8)
    big = next(r for r in rows if "over $1B" in r["output"])
    rows += [dict(big) for _ in range(29)]
    res, out = _run(tmp_path, rows)
    assert res.sizes == res.target_sizes == {"train": 100, "val": 20, "test": 30}
    assert len(res.groups) == 1 and len(res.groups[0].rows) == 30
    assert len({res.split_of[res.ids[r.row]] for r in res.groups[0].rows}) == 1
    assert res.swaps == 3
    assert res.checks[-1][1] == "WARN"  # the band can't be within one row of its share
    assert "quota swap" in (out / "stats.md").read_text()


def test_unparseable_rows_are_dropped_and_counted(tmp_path):
    rows: list = _dataset({"shut down": 50, "under $50M": 15, "$50M-$500M": 15,
                           "$500M-$1B": 10, "over $1B": 10}, seed=5)
    bad_output = dict(rows[0], output="outcome: shut down")
    bad_input = dict(rows[1], input="A founder with a background in sales.")
    bad_both = dict(rows[2], input="", output="outcome: maybe\nyears: 5-8")
    rows[2:2] = ["{not json", bad_output, bad_input, bad_both]  # positions 3 to 6
    res, out = _run(tmp_path, rows)
    assert res.rows_read == 104 and len(res.kept) == 100
    assert {k: v_ for k, v_ in res.dropped.items() if v_} == {
        "json": [3], "output": [4], "input": [5], "both": [6]}
    ids = [r["id"] for s in sp.SPLITS for r in _read_split(out, s)]
    assert len(ids) == 100
    assert not {"r00003", "r00004", "r00005", "r00006"} & set(ids)
    assert {"r00001", "r00002", "r00007", "r00104"} <= set(ids)
    actual = json.loads((out / "run_info.json").read_text())["splits"]["actual"]
    assert (actual["rows_read"], actual["rows_kept"], actual["rows_dropped"]) == (104, 100, 4)
    report = (out / "stats.md").read_text()
    for reason in sp.DROP_REASONS.values():
        assert reason in report


def test_output_records_carry_id_outcome_years_label(full):
    res, out, rows = full
    seen = set()
    for s in sp.SPLITS:
        for rec in _read_split(out, s):
            assert tuple(rec) == sp.FIELDS
            assert re.fullmatch(r"r\d{5}", rec["id"]) and rec["id"] not in seen
            seen.add(rec["id"])
            raw = rows[int(rec["id"][1:]) - 1]
            assert (rec["instruction"], rec["input"], rec["output"]) == (
                raw["instruction"], raw["input"], raw["output"])
            assert rec["outcome"] in sp.BANDS and rec["years"] in v.YEARS
            assert raw["output"] == f"outcome: {rec['outcome']}\nyears: {rec['years']}"
            assert rec["label"] == ("successful" if rec["outcome"] in {"$500M-$1B", "over $1B"}
                                    else "failed")
    assert len(seen) == 3000
    labels = Counter(r["label"] for s in sp.SPLITS for r in _read_split(out, s))
    assert labels == {"successful": 600, "failed": 2400}


def test_report_is_plain_and_complete(full):
    _, out, _ = full
    text = (out / "stats.md").read_text()
    assert text.startswith("# Data splits\n\n**In short:**")
    for heading in ("What the words mean", "Rows read, kept and dropped", "Split sizes",
                    "Outcome bands per split", "Years to outcome per split",
                    "Research label per split", "Profiles with an unknown field",
                    "Duplicate groups", "Leakage checks"):
        assert f"## {heading}" in text
    assert "2,000 train / 400 val / 600 test" in text
    assert str(out) not in text  # no machine-specific paths


def test_cli_with_explicit_paths(tmp_path, capsys):
    src = _write(tmp_path / "x.jsonl", _dataset({"shut down": 20, "under $50M": 6,
                                                 "$50M-$500M": 6, "$500M-$1B": 4,
                                                 "over $1B": 4}, seed=6))
    rc = sp.main([str(src), "--out-dir", str(tmp_path / "splits"), "--report",
                  str(tmp_path / "stats.md"), "--run-info", str(tmp_path / "run_info.json")])
    assert rc == 0
    assert "40 rows read" in capsys.readouterr().out
    assert json.loads((tmp_path / "run_info.json").read_text())["splits"]["actual"][
        "input_file"] == "x.jsonl"
