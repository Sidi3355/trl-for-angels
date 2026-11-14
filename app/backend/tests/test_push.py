"""Push notifications: the key, watching a job, sending once it finishes, and the text of the message."""

import functools
import json

from conftest import EXAMPLES, load, screen, wait_for

SUB = load(EXAMPLES / "push_watch_request.json")["subscription"]


def body(policy=None, endpoint=None):
    sub = {**SUB, "endpoint": endpoint} if endpoint else SUB
    return {"schema_version": "0.1.0", "subscription": sub, **({"policy": policy} if policy else {})}


def fake_sender(client, status=201):
    sent = []

    def send(subscription, payload):
        sent.append((subscription["endpoint"], json.loads(payload)))
        return status

    client.app.state.service.pusher._sender = send
    return sent


def test_push_key(client, contract):
    r = client.get("/v1/push/key")
    assert r.status_code == 200
    contract.check("push_key", r.json())
    assert len(r.json()["public_key"]) == 87  # base64url of a 65-byte uncompressed P-256 point


def test_finished_screening_sends_now_with_the_verdict_at_the_investors_bar(client, contract):
    sent = fake_sender(client)
    job, memo = screen(client, load(EXAMPLES / "investor_input_advance.json"))
    r = client.post(f"/v1/screenings/{job['job_id']}/notify", json=body({"target": "$1B", "timeline_years": 8}))
    assert r.status_code == 202
    contract.check("push_watch_response", r.json())
    assert r.json()["status"] == "sent" and len(sent) == 1
    payload = sent[0][1]
    assert payload["url"] == f"/memos/{memo['memo_id']}"
    assert payload["title"].split(":")[0] in {"Meet", "Look closer", "Pass"}
    assert memo["founder"]["display_name"] in payload["title"]
    assert "$1B+ within 8 years" in payload["body"] and payload["body"].startswith("≈")


def test_running_screening_is_watched_then_notified_once(client):
    sent = fake_sender(client)
    svc = client.app.state.service
    inp = load(EXAMPLES / "investor_input_escalate.json")
    job = client.portal.call(functools.partial(svc.start_screening, inp, start=False))
    r = client.post(f"/v1/screenings/{job.id}/notify", json=body())
    assert r.json()["status"] == "watching" and sent == []
    # the same browser again replaces its subscription instead of adding a second one
    client.post(f"/v1/screenings/{job.id}/notify", json=body())
    assert len(svc.watchers[job.id]) == 1
    client.portal.call(svc.run_screening, job, inp)
    assert len(sent) == 1 and sent[0][1]["url"] == f"/memos/{job.memo_id}"
    assert job.id not in svc.watchers  # used once, then forgotten


def test_refused_push_reports_failed(client):
    fake_sender(client, status=410)
    job, _ = screen(client, load(EXAMPLES / "investor_input_pass.json"))
    assert client.post(f"/v1/screenings/{job['job_id']}/notify", json=body()).json()["status"] == "failed"


def test_batch_notification_counts_by_verdict(client):
    sent = fake_sender(client)
    r = client.post("/v1/batches", json=load(EXAMPLES / "batch_request.json"))
    b = wait_for(client, f"/v1/batches/{r.json()['batch_id']}")
    assert client.post(f"/v1/batches/{b['batch_id']}/notify", json=body()).json()["status"] == "sent"
    payload = sent[0][1]
    assert payload["title"] == "Your list is screened (3 founders)"
    assert payload["body"] == "1 to meet, 1 to look closer at, 1 to pass."
    assert payload["url"] == f"/batch?id={b['batch_id']}"


def test_bad_requests(client):
    fake_sender(client)
    job, _ = screen(client, load(EXAMPLES / "investor_input_advance.json"))
    assert client.post(f"/v1/screenings/{job['job_id']}/notify", json={"schema_version": "0.1.0"}).status_code == 422
    http = body(endpoint="http://insecure.example.com/x")
    assert client.post(f"/v1/screenings/{job['job_id']}/notify", json=http).status_code == 422
    assert client.post("/v1/screenings/job_nope/notify", json=body()).status_code == 404
    assert client.post(f"/v1/batches/{job['job_id']}/notify", json=body()).status_code == 404  # a screening isn't a batch
