"""Each mock-to-real swap is one setting, and a misconfiguration degrades clearly instead of crashing."""

import json
import shutil

from conftest import EXAMPLES, MOCKS, load, make_client, screen


def test_artifacts_dir_swap_with_real_style_rules(tmp_path, contract):
    """Point ARTIFACTS_DIR at 'real' artefacts (different rules, mock: false) while Jev and Kev are mocked."""
    real = tmp_path / "artifacts"
    shutil.copytree(MOCKS, real)
    rules = load(MOCKS / "rules.json")
    rules.pop("mock")
    rules["rules"] = [{"id": f"q{i:03d}", "index": i, "question": f"Real question {i}?"} for i in range(100)]
    (real / "rules.json").write_text(json.dumps(rules))
    with make_client(artifacts_dir=str(real)) as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["artifacts"]["rules"] == {"mock": False, "count": 100}
        _, memo = screen(c, load(EXAMPLES / "investor_input_advance.json"))
        contract.check("memo", memo)
        assert [a["rule_id"] for a in memo["answers"]] == [f"q{i:03d}" for i in range(100)]
        mock_note = next(w for w in memo["warnings"] if w["code"] == "mock_artifacts")["message"]
        assert "rules.json" not in mock_note and "answerer (base Kev)" in mock_note


def test_profile_mode_from_model_json(tmp_path, contract):
    """decider_input: profile (if C4 wins on val) switches drivers and what-ifs to fields, no code change."""
    real = tmp_path / "artifacts"
    shutil.copytree(MOCKS, real)
    model = load(MOCKS / "model.json")
    model["decider_input"] = "profile"
    model.pop("answer_serialisation")
    (real / "model.json").write_text(json.dumps(model))
    with make_client(artifacts_dir=str(real)) as c:
        _, memo = screen(c, load(EXAMPLES / "investor_input_escalate.json"))
        contract.check("memo", memo)
        assert memo["answers"] is None and {d["kind"] for d in memo["drivers"]} == {"field"}
        assert memo["what_if"] == {"answer_changes": "unsupported", "field_changes": "supported"}
        url = f"/v1/memos/{memo['memo_id']}/what-if"
        w = c.post(url, json={"schema_version": "0.1.0", "changes": [{"kind": "field", "key": "cofounders", "value": "1"}]})
        assert w.status_code == 200 and w.json()["used_answerer"] is False
        assert c.post(url, json=load(EXAMPLES / "what_if_request.json")).status_code == 422


def test_real_agent_without_key_degrades(contract):
    with make_client(agent="claude") as c:
        h = c.get("/health").json()
        assert h["status"] == "degraded" and "ANTHROPIC_API_KEY" in h["errors"]["agent"]
        r = c.post("/v1/screenings", json=load(EXAMPLES / "investor_input_advance.json"))
        assert r.status_code == 503 and r.json()["error"]["code"] == "not_configured"


def test_missing_artifacts_dir_degrades(tmp_path):
    with make_client(artifacts_dir=str(tmp_path / "nope")) as c:
        h = c.get("/health").json()
        assert h["status"] == "degraded" and "ARTIFACTS_DIR not found" in h["errors"]["artifacts"]


def test_access_token():
    with make_client(access_token="s3cret") as c:
        assert c.get("/health").status_code == 200  # health stays open
        assert c.get("/v1/demo/founders").status_code == 401
        assert c.get("/v1/demo/founders", headers={"X-Access-Token": "s3cret"}).status_code == 200
        assert c.get("/v1/demo/founders?access_token=s3cret").status_code == 200  # for EventSource


def test_env_file_example_parses():
    """Every variable in .env.example is a real setting (no typos), and empty values mean 'unset'."""
    from screener.config import BACKEND_DIR, Settings
    names = [line.split("=", 1)[0] for line in (BACKEND_DIR / ".env.example").read_text().splitlines()
             if line and not line.startswith("#")]
    fields = {f.upper() for f in Settings.model_fields} | {"SCREENER_ANTHROPIC_API_KEY"}
    assert set(names) <= fields, set(names) - fields
    s = Settings(_env_file=BACKEND_DIR / ".env.example")
    assert s.anthropic_api_key is None and s.access_token is None and s.agent == "mock"
