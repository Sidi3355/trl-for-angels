"""End-to-end tests of the API on mocks. Every response is also checked against the contract."""

import pytest

from conftest import EXAMPLES, MOCKS, load, parse_sse, screen, wait_for

DEMO = ["advance", "escalate", "pass"]


def test_health(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["errors"] == {}
    assert h["components"] == {"agent": "mock", "answerer": "mock", "decider": "mock",
                               "transcriber": "mock", "note_sorter": "off"}
    assert h["artifacts"]["dir"] == "app/contract/mocks" and h["artifacts"]["rules"]["count"] == 20
    assert h["mock"] is True
    assert set(h["keys"].values()) == {False}  # key status only, never values


@pytest.mark.parametrize("key", DEMO)
def test_screening_matches_committed_mock_memo(client, contract, key):
    """The service produces the same memos as app/contract/mocks/mock_memo.json (ids and times aside)."""
    job, memo = screen(client, load(EXAMPLES / f"investor_input_{key}.json"))
    contract.check("screening_job", job)
    contract.check("memo", memo)
    committed = next(m for m in load(MOCKS / "mock_memo.json") if m["client_ref"] == memo["client_ref"])
    assert memo["verdict"]["decision"] == key
    for part in ("verdict", "distributions", "fields", "rendered_profile", "answers", "conflicts", "unknowns",
                 "facets", "notes", "warnings", "disclaimer", "what_if"):
        assert memo[part] == committed[part], part
    assert [d["id"] for d in memo["drivers"]] == [d["id"] for d in committed["drivers"]]


def test_unknown_founder_uses_only_investor_fields(client, contract):
    body = {"schema_version": "0.1.0", "founder": {"name": "Someone Not In The Demo"},
            "fields": {"industry": "fintech", "background": "technical"}}
    _, memo = screen(client, body)
    contract.check("memo", memo)
    provs = {k: v["provenance"] for k, v in memo["fields"].items()}
    assert provs["industry"] == provs["background"] == "investor"
    assert {p for k, p in provs.items() if k not in ("industry", "background")} == {"unknown"}
    codes = {w["code"] for w in memo["warnings"]}
    assert {"research_partial", "founding_date_assumed", "many_unknowns", "mock_artifacts"} <= codes
    assert memo["founder"]["founding_date"]["provenance"] == "assumed"
    assert memo["sources"] == []


def test_progress_events_sse_and_resume(client, contract):
    r = client.post("/v1/screenings", json=load(EXAMPLES / "investor_input_advance.json"))
    job = wait_for(client, f"/v1/screenings/{r.json()['job_id']}")
    stream = client.get(job["events_url"])
    assert stream.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(stream.text)
    for ev in events:
        contract.check("progress_event", ev)
    assert [e["seq"] for e in events] == list(range(len(events)))
    stages = [e["stage"] for e in events if e["type"] == "stage"]
    assert stages == ["queued", "researching", "merging", "rendering", "answering", "deciding", "writing_memo", "done"]
    assert any(e["type"] == "source" and e["data"]["source"]["before_founding"] is False for e in events)
    # Resume: Last-Event-ID and ?after= both return only later events; ?format=json for polling clients
    resumed = parse_sse(client.get(job["events_url"], headers={"Last-Event-ID": "10"}).text)
    assert [e["seq"] for e in resumed] == list(range(11, len(events)))
    assert [e["seq"] for e in client.get(job["events_url"] + "?after=20&format=json").json()] == list(range(21, len(events)))


def test_invalid_input_is_422_with_details(client):
    r = client.post("/v1/screenings", json={"schema_version": "0.1.0", "founder": {"name": "X"},
                                            "fields": {"cofounders": "two"}})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"
    assert any("cofounders" in d for d in r.json()["details"])
    assert client.post("/v1/screenings", json={"schema_version": "0.1.0", "founder": {}}).status_code == 422
    assert client.post("/v1/screenings", content="not json", headers={"Content-Type": "application/json"}).status_code == 400


def test_not_found(client):
    for url in ("/v1/memos/nope", "/v1/screenings/nope", "/v1/batches/nope"):
        r = client.get(url)
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_what_if_answer_and_field_changes(client, contract):
    _, memo = screen(client, load(EXAMPLES / "investor_input_escalate.json"))
    url = f"/v1/memos/{memo['memo_id']}/what-if"
    r = client.post(url, json=load(EXAMPLES / "what_if_request.json"))
    assert r.status_code == 200, r.text
    w = r.json()
    contract.check("what_if_response", w)
    assert w["used_answerer"] is False and w["answers_changed"] == ["r12"] and w["rendered_profile"] is None
    assert w["verdict"]["decision"] == "advance" and w["baseline"] == memo["distributions"]
    assert w == {**load(EXAMPLES / "what_if_response.json"), "memo_id": memo["memo_id"]}

    f = client.post(url, json={"schema_version": "0.1.0",
                               "changes": [{"kind": "field", "key": "cofounders", "value": "1"}]}).json()
    contract.check("what_if_response", f)
    assert f["used_answerer"] is True and "r12" in f["answers_changed"]
    assert "founded with 1 co-founder(s)." in f["rendered_profile"]

    bad = client.post(url, json={"schema_version": "0.1.0", "changes": [
        {"kind": "field", "key": "prior_exits", "value": [{"kind": "acquisition", "value_band": "over $1B"}]}]})
    assert bad.status_code == 422 and "consistency" in bad.json()["error"]["message"]
    policy = client.post(url, json={**load(EXAMPLES / "what_if_request.json"),
                                    "policy": {"target": "$1B", "risk": "cautious"}}).json()
    assert policy["verdict"]["policy"]["target"] == "$1B"


def _finish_batch(client, r):
    assert r.status_code == 202, r.text
    return wait_for(client, f"/v1/batches/{r.json()['batch_id']}")


def test_batch_json(client, contract):
    b = _finish_batch(client, client.post("/v1/batches", json=load(EXAMPLES / "batch_request.json")))
    contract.check("batch_response", b)
    assert b["status"] == "complete" and b["counts"] == {"advance": 1, "escalate": 1, "pass": 1, "filtered_out": 0}
    assert [i["decision"] for i in b["items"]] == DEMO
    for item in b["items"]:
        assert client.get(item["memo_url"]).json()["verdict"]["decision"] == item["decision"]
    events = parse_sse(client.get(b["events_url"]).text)
    assert sum(e["type"] == "batch_item" for e in events) == 3 and events[-1]["stage"] == "done"


def test_batch_csv_with_policy_and_filters(client, contract):
    csv = (EXAMPLES / "batch.csv").read_text()
    b = _finish_batch(client, client.post("/v1/batches?risk=bold", content=csv, headers={"Content-Type": "text/csv"}))
    contract.check("batch_response", b)
    assert b["policy"]["risk"] == "bold" and b["counts"]["advance"] == 2

    req = {**load(EXAMPLES / "batch_request.json"), "policy": {"filters": {"technical": True}}}
    f = _finish_batch(client, client.post("/v1/batches", json=req))
    assert f["counts"]["filtered_out"] == 2 and [i["filtered_out"] for i in f["items"]] == [False, True, True]


def test_batch_csv_errors_name_the_row(client):
    r = client.post("/v1/batches", content="name,cofounders\nAda,2\nBea,lots\n", headers={"Content-Type": "text/csv"})
    assert r.status_code == 422 and r.json()["details"] == ["row 2, cofounders: 'lots' is not one of "
                                                            "['solo', '1', '2', '3+', 'unknown']"]
    r = client.post("/v1/batches", content="stage,score\nseed,9\n", headers={"Content-Type": "text/csv"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_csv"
    r = client.post("/v1/batches", content="name,notes\n,just a note\n", headers={"Content-Type": "text/csv"})
    assert r.status_code == 422 and r.json()["details"] == ["row 1: needs a name, linkedin_url or website_url"]


def test_artifacts_and_demo_founders(client, contract):
    for name in ("rules", "thresholds", "model"):
        doc = client.get(f"/v1/artifacts/{name}").json()
        contract.check(name, doc)
        assert doc == load(MOCKS / f"{name}.json")
    assert client.get("/v1/artifacts/secrets").status_code == 422
    demo = client.get("/v1/demo/founders").json()
    assert [d["founder"]["name"] for d in demo] == ["Ada Moreno", "Samir Haddad", "Jordan Pike"]


def test_research_switched_off(client):
    body = {**load(EXAMPLES / "investor_input_advance.json"), "options": {"research": False}}
    _, memo = screen(client, body)
    assert memo["sources"] == [] and "research_partial" in {w["code"] for w in memo["warnings"]}
