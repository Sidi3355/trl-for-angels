"""research/export_artifacts.py writes files that match the app's contract schemas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import export_artifacts as ex  # noqa: E402
import test_thresholds as tt  # noqa: E402

CONTRACT = Path(__file__).resolve().parent / "fixtures" / "app_contract"


@pytest.fixture
def research_outputs(tmp_path: Path) -> Path:
    """A tiny real C1a fit (TRL's fake models), rules.json, D3 and D4 outputs."""
    from think_reason_learn.rrf import RRF
    from think_reason_learn.testing import FakeLLM, fake_llms

    questions = ["Has the founder exited a company?", "Is the founder technical?"]
    writer = FakeLLM(generate=lambda r: {"questions": questions} if r.schema else "I.")
    judge = FakeLLM(answer=lambda s, q: 0.9 if ("exit" in s) == ("exit" in q.text) else 0.2,
                    kind="decision")
    X = [f"Founder {i} {'exited' if i % 2 else 'is new'}." for i in range(30)]
    y = ["successful" if i % 2 else "failed" for i in range(30)]
    with fake_llms(writer=writer, judge=judge):
        RRF("t", generator="fake:writer", answerer="fake:judge", n_prompts=1,
            questions_per_prompt=2).fit(X, y).save(tmp_path / "models" / "c1a")
    (tmp_path / "answers").mkdir()
    (tmp_path / "answers" / "rules.json").write_text(json.dumps(questions))
    prod = tmp_path / "models" / "prod"
    prod.mkdir()
    (prod / "temperatures.json").write_text(json.dumps(
        {"global": 1.3, "per_question": {"outcome": 1.4, "years": 1.1}}))
    tt.write_prod(tmp_path / "prod_val.csv", n=120)
    return tmp_path


@pytest.mark.parametrize("prod_input", ["c3", "c4"])
def test_export_matches_the_app_contract(research_outputs: Path, prod_input: str) -> None:
    r = research_outputs
    out = r / "artifacts"
    ex.main(["--prod-input", prod_input, "--endpoint", "https://kev.example/",
             "--answers", str(r / "answers"), "--models", str(r / "models"),
             "--prod-dir", str(r / "models" / "prod"), "--prod-val", str(r / "prod_val.csv"),
             "--contract", str(CONTRACT), "--out", str(out)])
    rules = json.loads((out / "rules.json").read_text())
    model = json.loads((out / "model.json").read_text())
    thresholds = json.loads((out / "thresholds.json").read_text())
    assert [x["question"] for x in rules["rules"]] == ["Has the founder exited a company?",
                                                       "Is the founder technical?"]
    assert model["decider_input"] == ("answers" if prod_input == "c3" else "profile")
    assert ("answer_serialisation" in model) == (prod_input == "c3")
    assert model["temperature"] == {"applied_by": "client", "outcome": 1.4, "years": 1.1}
    assert model["endpoint"]["base_url"] == "https://kev.example"
    assert len(thresholds["tables"]) == 9 and len(thresholds["tables"][0]["rows"]) == 100


def test_a_file_that_breaks_the_contract_is_refused(tmp_path: Path) -> None:
    doc = {"schema_version": "0.1.0", "source": {}, "task": "t", "rules": []}
    with pytest.raises(ValueError, match="rules.schema.json"):
        ex.validate(doc, CONTRACT / "rules.schema.json")
