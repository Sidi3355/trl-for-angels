"""Tests for research/serialise.py on hand-written splits and answers (fixtures, not data)."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import serialise as s  # noqa: E402
from think_reason_learn.rrf import answers_text  # noqa: E402

RULES = ["Has the founder founded a startup before?", "Does the founder have a prior exit?"]


def setup_dirs(tmp_path: Path, answers: dict[str, list[float]] | None = None,
               header: list[str] | None = None) -> tuple[Path, Path]:
    splits, ans = tmp_path / "splits", tmp_path / "answers"
    splits.mkdir()
    ans.mkdir()
    founders = [
        {"id": "r00001", "input": "Founder one.\nPrior exits: none.", "label": "failed"},
        {"id": "r00002", "input": "Founder two.\nPrior exits: 1.", "label": "successful"},
    ]
    for split in s.SPLITS:
        (splits / f"{split}.jsonl").write_text("".join(json.dumps(f) + "\n" for f in founders))
    (ans / "rules.json").write_text(json.dumps(RULES))
    answers = answers or {"r00001": [0.2, 0.1], "r00002": [0.9, math.nan]}
    for split in s.SPLITS:
        with (ans / f"{split}.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header or ["id", *RULES])
            for rid, vals in answers.items():
                w.writerow([rid, *vals])
    return splits, ans


def test_c3_and_c4_records(tmp_path: Path) -> None:
    splits, ans = setup_dirs(tmp_path)
    counts = s.serialise(splits, ans, tmp_path / "kev")
    assert counts == {"c3": {k: 2 for k in s.SPLITS}, "c4": {k: 2 for k in s.SPLITS}}
    c3 = [json.loads(x) for x in (tmp_path / "kev/c3/train.jsonl").read_text().splitlines()]
    c4 = [json.loads(x) for x in (tmp_path / "kev/c4/val.jsonl").read_text().splitlines()]
    # C3's state is exactly TRL's answers_text, in rules.json order; NaN reads "unknown".
    assert c3[1]["state"] == answers_text(RULES, [0.9, math.nan])
    assert c3[1]["state"].splitlines() == [f"{RULES[0]} yes", f"{RULES[1]} unknown"]
    # C4's state is the founder text as TRL renders it (unchanged for plain texts).
    assert c4[0]["state"] == "Founder one.\nPrior exits: none."
    for rec, label in ((c3[0], False), (c3[1], True), (c4[1], True)):
        q = rec["questions"][s.QUESTION_ID]
        assert q == {"type": "noul", "instructions": s.QUESTION, "label": label}
    assert c3[0]["_meta"] == {"row_id": "r00001"}


def test_columns_must_match_the_rules(tmp_path: Path) -> None:
    splits, ans = setup_dirs(tmp_path, header=["id", RULES[1], RULES[0]])
    with pytest.raises(ValueError, match="rules.json order"):
        s.serialise(splits, ans, tmp_path / "kev")


def test_every_founder_needs_answers(tmp_path: Path) -> None:
    splits, ans = setup_dirs(tmp_path, answers={"r00001": [0.2, 0.1]})
    with pytest.raises(ValueError, match="1 founders have no answers"):
        s.serialise(splits, ans, tmp_path / "kev")


def test_c4_alone_before_any_answers(tmp_path: Path) -> None:
    splits, _ = setup_dirs(tmp_path)
    counts = s.serialise(splits, tmp_path / "no-answers-yet", tmp_path / "kev")
    assert counts["c3"] == {} and counts["c4"]["test"] == 2
    assert not (tmp_path / "kev/c3").exists()


def test_kev_reads_the_records(tmp_path: Path) -> None:
    """Kev's own loader accepts the files (skipped where Kev isn't installed)."""
    kev = Path("/home/user/kev")
    if not (kev / "kev" / "data.py").exists():
        pytest.skip("Kev checkout not available")
    splits, ans = setup_dirs(tmp_path)
    s.serialise(splits, ans, tmp_path / "kev")
    import subprocess

    code = ("import sys; from kev.data import load_records; "
            "r = load_records(sys.argv[1]); print(len(r), r[0]['_meta']['row_id'])")
    out = subprocess.run([str(kev / ".venv/bin/python"), "-c", code,
                          str(tmp_path / "kev/c3/train.jsonl")],
                         capture_output=True, text=True, cwd=kev, check=True)
    assert out.stdout.split() == ["2", "r00001"]


@pytest.mark.parametrize("input_kind", ["c3", "c4"])
def test_production_files_ask_both_choice_questions(tmp_path: Path, input_kind: str) -> None:
    splits, ans = setup_dirs(tmp_path)
    for split in s.SPLITS:  # production labels need each founder's outcome and years
        path = splits / f"{split}.jsonl"
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        rows[0].update(outcome="shut down", years="under 5")
        rows[1].update(outcome="over $1B", years="5-8")
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    counts = s.production(splits, ans, tmp_path / "kev", input_kind)
    assert counts == {k: 2 for k in s.SPLITS}
    recs = [json.loads(x) for x in (tmp_path / "kev/prod/train.jsonl").read_text().splitlines()]
    q = recs[1]["questions"]
    assert list(q) == ["outcome", "years"]
    assert q["outcome"]["type"] == q["years"]["type"] == "choice"
    assert (q["outcome"]["label"], q["years"]["label"]) == ("over $1B", "5-8")
    assert list(q["outcome"]["criteria"]) == ["shut down", "under $50M", "$50M-$500M",
                                              "$500M-$1B", "over $1B"]
    expected = (answers_text(RULES, [0.9, math.nan]) if input_kind == "c3"
                else "Founder two.\nPrior exits: 1.")
    assert recs[1]["state"] == expected
