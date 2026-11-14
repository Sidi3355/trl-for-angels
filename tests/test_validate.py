"""Tests for research/validate.py on hand-written records (test fixtures, not data)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import validate as v  # noqa: E402

GOOD_INPUT = """\
This founder leads a startup in the logistics industry, founded with 1 co-founder(s).
Founder background: business, 5-10 years of work experience, some prior experience in this startup's industry.
Education:
- BA in Economics, university ranked QS 101-300
Jobs (oldest first):
- Analyst, a management consulting firm, 1,001-5,000 employees, Professional Services, 2-3 years
- Operations Manager, a freight brokerage company, 201-1,000 employees, Logistics, 3-5 years
Prior startups: none.
Prior exits: none."""

GOOD_OUTPUT = "outcome: shut down\nyears: under 5"


def record(inp: str = GOOD_INPUT, out: str = GOOD_OUTPUT, instr: str = v.INSTRUCTION):
    rec = v.parse_record({"instruction": instr, "input": inp, "output": out}, 1)
    v.check_record(rec)
    return rec


def test_plan_example_parses_cleanly():
    rec = record()
    assert rec.errors == [], rec.errors
    assert rec.warnings == [], rec.warnings
    assert rec.outcome == "shut down" and rec.years == "under 5"
    p = rec.profile
    assert p.industry == "logistics" and p.cofounders == "1"
    assert p.background == "business" and p.experience == "5-10"
    assert [j.size for j in p.jobs] == ["1,001-5,000", "201-1,000"]
    assert [j.duration for j in p.jobs] == ["2-3", "3-5"]
    assert p.jobs[1].industry == "Logistics"
    assert p.prior_startups_n == 0 and p.prior_exits_n == 0
    assert p.unknown_fields == []


def test_output_normalises_dashes_case_and_spaces():
    rec = record(out="Outcome:  $500M–$1B\nYEARS: 5—8")
    assert rec.outcome == "$500M-$1B" and rec.years == "5-8"
    assert rec.strong


def test_bad_outputs_are_dropped():
    for out in ("outcome: shut down", "outcome: maybe\nyears: 5-8",
                "outcome: shut down\nyears: 3", "outcome: shut down\nyears: 5-8\nnote: x"):
        rec = record(out=out)
        assert rec.outcome is None, out
        assert any(e.startswith("output:") for e in rec.errors)


def test_banned_words_names_years_and_urls_fail():
    bad = GOOD_INPUT.replace("a freight brokerage company",
                             "a prestigious freight company in London") \
        .replace("Analyst,", "Analyst at Google in 2012,")
    rec = record(inp=bad)
    text = " ".join(rec.errors)
    for needle in ("prestigious", "London", "Google", "2012"):
        assert needle in text, needle


def test_unknown_fields_are_counted_and_capped():
    inp = GOOD_INPUT.replace("QS 101-300", "QS unknown").replace("Prior exits: none.",
                                                                 "Prior exits: unknown.")
    rec = record(inp=inp)
    assert sorted(rec.profile.unknown_fields) == ["QS band", "prior exits"]
    assert rec.errors == []
    inp3 = inp.replace("201-1,000 employees", "unknown employees")
    rec3 = record(inp=inp3)
    assert len(rec3.profile.unknown_fields) == 3
    assert any("at most 2" in e for e in rec3.errors)


def test_exits_cannot_exceed_startups():
    inp = GOOD_INPUT.replace("Prior startups: none.", "Prior startups: 1 founded before, "
                             "with outcomes 1 shut down.") \
        .replace("Prior exits: none.", "Prior exits: 2 acquisitions or IPOs as co-founder, "
                 "under $50M.")
    rec = record(inp=inp)
    assert any("exceed" in e for e in rec.errors)


def test_disallowed_template_values_fail():
    inp = GOOD_INPUT.replace("5-10 years", "7 years").replace("QS 101-300", "QS 150")
    rec = record(inp=inp)
    text = " ".join(rec.errors)
    assert "experience" in text and "QS band" in text


def test_experience_mismatch_warns():
    inp = GOOD_INPUT.replace("5-10 years of work", "15+ years of work")
    rec = record(inp=inp)
    assert any("experience 15+" in w for w in rec.warnings)


def _row(outcome: str, years: str, i: int) -> dict[str, str]:
    industries = ["fintech", "healthtech", "biotech", "B2B SaaS", "developer tools",
                  "e-commerce", "logistics", "edtech", "climate", "cybersecurity",
                  "marketplaces", "media", "hardware", "insurtech", "agtech", "gaming"]
    inp = GOOD_INPUT.replace("logistics industry", f"{industries[i % 16]} industry") \
        .replace("Operations Manager", f"Operations Manager {i}")
    return {"instruction": v.INSTRUCTION, "input": inp,
            "output": f"outcome: {outcome}\nyears: {years}"}


def test_dataset_counts_on_a_synthetic_file(tmp_path: Path):
    plan = [("shut down", 25), ("under $50M", 8), ("$50M-$500M", 7),
            ("$500M-$1B", 5), ("over $1B", 5)]
    rows, i = [], 0
    for band, n in plan:
        for _ in range(n):
            rows.append(_row(band, "5-8", i))
            i += 1
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    _, checks = v.validate(path, "sample50")
    by = {c.name: c for c in checks}
    assert by["Outcome counts"].status == "PASS"
    assert by["Row count"].status == "PASS"
    assert by["Industries"].status == "PASS"
    assert by["Shuffled"].status == "WARN"  # grouped by outcome on purpose
    # Every record is a first-time founder with no top-50 school: rule 1 must fail.
    assert by["Traits in both strong and shut-down records"].status == "FAIL"
    # Exactly 8 records with unknowns are required; there are none.
    assert by["Records with unknown fields"].status == "FAIL"

    rows[0]["output"] = "outcome: shut down"  # drop one row
    path.write_text("\n".join(json.dumps(r) for r in rows))
    _, checks = v.validate(path, "sample50")
    by = {c.name: c for c in checks}
    assert by["Dropped rows"].status == "FAIL"
    assert by["Outcome counts"].status == "FAIL"


def test_near_copies_are_found_among_many_templated_profiles():
    # Every profile shares the template's wording, and every pair is compared, so a
    # near copy is found however many profiles share that wording.
    rows = [_row("shut down", "5-8", i) for i in range(250)]
    copy = dict(rows[5])
    copy["input"] = copy["input"].replace("Analyst,", "Senior Analyst,")
    rows.append(copy)
    recs = [v.parse_record(r, i) for i, r in enumerate(rows, 1)]
    _, near = v.duplicates(recs)
    assert (6, 251) in [(a, b) for a, b, _ in near]
