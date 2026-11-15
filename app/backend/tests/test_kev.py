"""The real answerer and decider (pipeline/kev.py), end to end through TRL against a fake Kev server.

The fake speaks kev_server's protocol: /answerer and /decider System One endpoints behind one address, a
bearer key, and /health. It records every request, so the tests can check what Kev is actually sent.
"""

import json
import math
import shutil
import socket
import threading
import time

import pytest
import uvicorn
from conftest import EXAMPLES, MOCKS, load, make_client, screen, wait_for
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from screener.pipeline import serialise
from screener.pipeline.context import NotConfigured
from screener.pipeline.kev import kev_urls, rounded, temper

KEY = "test-kev-key"
RULES = ["Has the founder founded a company before?", "Did the founder study at a top-50 university?",
         "Has the founder worked in this industry for 5+ years?", "Is the founder technical?"]
UNANSWERED = "r002"  # the fake answerer skips it, so it must read "unknown"
OUTCOMES = {"shut down": "the company closed", "under $50M": "exited, listed or raised, at a value under $50M",
            "$50M-$500M": "exit, IPO or funding value between $50M and $500M",
            "$500M-$1B": "exit, IPO or funding value between $500M and $1B",
            "over $1B": "exit, IPO or funding value over $1B"}
YEARS = {"under 5": "fewer than 5 years from founding", "5-8": "5 to 8 years from founding",
         "over 8": "more than 8 years from founding"}
TEMPS = {"outcome": 1.148698354997035, "years": 0.8705505632961241}


def raw_outcome(state: str) -> dict:
    """The fake decider's raw distribution: more 'yes' lines, better odds."""
    yes = sum(line.endswith(" yes") for line in state.splitlines())
    w = [4.0, 2.0, 2.0, 1.0 + yes, 0.5 + yes / 2]
    return {k: v / sum(w) for k, v in zip(OUTCOMES, w)}


RAW_YEARS = {"under 5": 0.5, "5-8": 0.3, "over 8": 0.2}


def fake_kev(calls: list) -> FastAPI:
    app = FastAPI()

    def authorised(request: Request) -> bool:
        return request.headers.get("authorization") == f"Bearer {KEY}"

    @app.get("/health")
    async def health(request: Request):
        return {"ready": True, "answerer": {"ready": True}, "decider": {"ready": True, "stand_in": False}}

    @app.get("/answerer/v1/models")
    async def models(request: Request):
        if not authorised(request):
            return JSONResponse({"detail": "missing or wrong bearer key"}, status_code=401)
        return {"models": [{"id": "kev-0.6b"}]}

    @app.post("/answerer/v1/systemone")
    async def answerer(request: Request):
        body = await request.json()
        calls.append(("answerer", authorised(request), body))
        if not authorised(request):
            return JSONResponse({"detail": "missing or wrong bearer key"}, status_code=401)
        answers = {qid: {"type": "noul", "noul": 0.8 if int(qid[1:]) % 2 else 0.3}
                   for qid in body["questions"] if qid != UNANSWERED}
        return {"model": "kev-0.6b", "answers": answers, "usage": {"input_tokens": 10, "output_tokens": 0}}

    @app.post("/decider/v1/systemone")
    async def decider(request: Request):
        body = await request.json()
        calls.append(("decider", authorised(request), body))
        if not authorised(request):
            return JSONResponse({"detail": "missing or wrong bearer key"}, status_code=401)
        dists = {"outcome": raw_outcome(body["state"]), "years": RAW_YEARS}
        return {"model": "kev-latest", "usage": {"input_tokens": 10, "output_tokens": 0},
                "answers": {q: {"type": "choice", "choice": max(d, key=d.get), "probabilities": d}
                            for q, d in dists.items()}}

    return app


@pytest.fixture(autouse=True)
def _fresh_trl_clients():
    """TRL keeps one HTTP client per endpoint for the process, bound to the event loop that first used it.
    Each test client runs its own loop, so drop them between tests (the server has one loop for its life)."""
    from think_reason_learn.llm._adapters._http import forget_clients
    forget_clients()
    yield
    forget_clients()


@pytest.fixture(scope="module")
def kev_server():
    calls: list = []
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(fake_kev(calls), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}", calls
    server.should_exit = True
    thread.join(5)


@pytest.fixture
def artifacts(tmp_path):
    """Real-shaped rules.json and model.json (as research exports them), with the mock thresholds."""
    real = tmp_path / "artifacts"
    shutil.copytree(MOCKS, real)
    rules = load(real / "rules.json")
    rules["mock"] = False
    rules["rules"] = [{"id": f"r{i + 1:03d}", "index": i, "question": q, "elastic_net_coef": None}
                      for i, q in enumerate(RULES)]
    (real / "rules.json").write_text(json.dumps(rules))
    model = load(real / "model.json")
    placeholder = "https://replace-with-tunnel.trycloudflare.com"
    model.update({
        "mock": False, "model_id": "kev-0.6b-prod-c3",
        "endpoint": {"base_url": f"{placeholder}/decider", "path": "/v1/systemone",
                     "auth": {"type": "bearer", "env_var": "KEV_API_KEY"}, "timeout_s": 60},
        "request": {"questions": {
            "outcome": {"type": "choice", "instructions": "What final outcome will this founder's company reach?",
                        "criteria": OUTCOMES},
            "years": {"type": "choice", "instructions": "How long after founding will the company reach that outcome?",
                      "criteria": YEARS}}, "response_format": "kev.serve"},
        "temperature": {"applied_by": "client", **TEMPS},
        "answerer": {"spec": f'LLM("kev-0.6b", base_url="{placeholder}/answerer/v1/systemone", kind="decision")',
                     "via": "trl"},
    })
    (real / "model.json").write_text(json.dumps(model))
    return real


def kev_client(artifacts, url, key=KEY):
    return make_client(artifacts_dir=str(artifacts), answerer="kev", decider="kev", kev_url=url, kev_api_key=key)


# ------------------------------------------------------------------------------------------- units

def test_kev_url_overrides_model_json_and_placeholder_needs_it(artifacts):
    from screener.pipeline.kev import configured, server_root
    model = load(artifacts / "model.json")
    assert kev_urls(model, "https://abc.trycloudflare.com/") == (
        "https://abc.trycloudflare.com/answerer/v1/systemone", "https://abc.trycloudflare.com/decider/v1/systemone")
    assert server_root("https://abc.trycloudflare.com/decider/v1/systemone") == "https://abc.trycloudflare.com"
    assert not any(configured(u) for u in kev_urls(model, None))  # placeholders: the backend starts, Kev calls refuse
    with pytest.raises(NotConfigured, match="https"):
        kev_urls(model, "abc.trycloudflare.com")


def test_temperature_is_logits_over_t():
    p = {"a": 0.6, "b": 0.3, "c": 0.1}
    t = 1.7
    logits = {k: math.log(v) / t for k, v in p.items()}
    z = sum(math.exp(v) for v in logits.values())
    want = {k: math.exp(v) / z for k, v in logits.items()}
    got = temper(p, t)
    assert all(abs(got[k] - want[k]) < 1e-12 for k in p)
    assert temper(p, None) == pytest.approx(p) and temper(p, 1.0) == pytest.approx(p)
    r = rounded({"a": 1 / 3, "b": 1 / 3, "c": 1 / 3})
    assert round(sum(r.values()), 10) == 1


def test_state_text_matches_trl_answers_text(artifacts):
    from think_reason_learn.rrf import answers_text
    rules, model = load(artifacts / "rules.json"), load(artifacts / "model.json")
    p_yes = [0.8, math.nan, 0.5, 0.49]
    labels = serialise.labels(p_yes, model)
    assert labels == ["yes", "unknown", "yes", "no"]
    assert serialise.state_text(rules, labels, model) == answers_text(RULES, p_yes)
    assert serialise.flip("unknown", model) is None and serialise.p_or_none(math.nan) is None


# ------------------------------------------------------------------------------------- end to end

def test_screening_through_kev(kev_server, artifacts, contract):
    url, calls = kev_server
    calls.clear()
    with kev_client(artifacts, url) as c:
        h = c.get("/health").json()
        assert h["errors"] == {} and h["components"]["answerer"] == h["components"]["decider"] == "kev"
        assert h["kev"] == {"configured": True, "host": url.split("//")[1], "reachable": True, "ready": True,
                            "decider_stand_in": False}
        calls.clear()
        _, first = screen(c, load(EXAMPLES / "investor_input_advance.json"))
        # The real decider is slow, so the memo comes back before its drivers, which fill in once it's opened.
        assert first["drivers_status"] == "pending" and first["drivers"] == [] and first["drivers_total"] == 3
        contract.check("memo", first)
        memo = wait_for(c, f"/v1/memos/{first['memo_id']}", key="drivers_status", done=("complete", "failed"))
    contract.check("memo", memo)
    assert memo["drivers_status"] == "complete"

    # Base Kev answered every rule once, through TRL, with the key; one rule unanswered reads "unknown".
    answerer = [b for role, ok, b in calls if role == "answerer"]
    assert len(answerer) == 1 and all(ok for _, ok, _ in calls)
    assert [q["instructions"] for q in answerer[0]["questions"].values()] == RULES
    assert answerer[0]["state"] == memo["rendered_profile"]
    got = {a["rule_id"]: (a["answer"], a["p_yes"]) for a in memo["answers"]}
    assert got == {"r001": ("yes", 0.8), "r002": ("unknown", None), "r003": ("yes", 0.8), "r004": ("no", 0.3)}

    # The decider got TRL's answers_text and model.json's questions word for word, descriptions included.
    deciders = [b for role, _, b in calls if role == "decider"]
    base_state = "\n".join(f"{q} {a}" for q, a in zip(RULES, ["yes", "unknown", "yes", "no"]))
    assert deciders[0]["state"] == base_state
    assert deciders[0]["questions"]["outcome"] == {
        "type": "choice", "instructions": "What final outcome will this founder's company reach?", "criteria": OUTCOMES}
    assert deciders[0]["questions"]["years"]["criteria"] == YEARS

    # Distributions are the raw ones with model.json's temperatures applied here.
    assert memo["distributions"] == {"outcome": rounded(temper(raw_outcome(base_state), TEMPS["outcome"])),
                                     "years": rounded(temper(RAW_YEARS, TEMPS["years"]))}

    # Drivers: every answered rule flipped once (not the unknown one).
    assert len(deciders) == 1 + 3
    assert sorted(d["id"] for d in memo["drivers"]) == ["r001", "r003", "r004"]
    flipped = {d["id"]: d["flipped"] for d in memo["drivers"]}
    assert flipped == {"r001": "no", "r003": "no", "r004": "yes"}


def test_what_if_answer_change_calls_only_the_decider(kev_server, artifacts, contract):
    url, calls = kev_server
    with kev_client(artifacts, url) as c:
        _, memo = screen(c, load(EXAMPLES / "investor_input_advance.json"))
        wait_for(c, f"/v1/memos/{memo['memo_id']}", key="drivers_status", done=("complete", "failed"))
        calls.clear()
        r = c.post(f"/v1/memos/{memo['memo_id']}/what-if",
                   json={"schema_version": "0.1.0", "changes": [{"kind": "answer", "rule_id": "r004", "value": "yes"}]})
    assert r.status_code == 200, r.text
    contract.check("what_if_response", r.json())
    assert [role for role, _, _ in calls] == ["decider"]
    assert calls[0][2]["state"].splitlines()[3].endswith(" yes")


def test_wrong_key_fails_the_screening_without_leaking_it(kev_server, artifacts):
    url, _ = kev_server
    from screener.pipeline import kev as kevmod
    kevmod._ready.clear()
    with kev_client(artifacts, url, key="not-the-key") as c:
        r = c.post("/v1/screenings", json={"schema_version": "0.1.0", "founder": {"name": "Someone Not In The Demo"},
                                           "fields": {"industry": "fintech", "background": "technical"}})
        job = wait_for(c, f"/v1/screenings/{r.json()['job_id']}")
    assert job["status"] == "failed"
    msg = job["error"]["message"]
    assert "KEV_API_KEY" in msg and "nothing was charged" in msg and "not-the-key" not in msg
    kevmod._ready.clear()


def test_without_kev_url_the_backend_runs_and_says_what_to_set(artifacts):
    """No KEV_URL: the backend still starts (the demo cache can answer), and a real founder is stopped before any
    research is paid for, with what to set."""
    with make_client(artifacts_dir=str(artifacts), answerer="kev", decider="kev", kev_api_key=KEY) as c:
        h = c.get("/health").json()
        r = c.post("/v1/screenings", json={"schema_version": "0.1.0", "founder": {"name": "Someone Real"}})
        job = wait_for(c, f"/v1/screenings/{r.json()['job_id']}")
        stages = [e["stage"] for e in c.get(job["events_url"], params={"format": "json"}).json()
                  if e["type"] == "stage"]
    assert h["status"] == "ok" and h["errors"] == {} and h["kev"] == {"configured": False, "reachable": False}
    assert job["status"] == "failed" and "KEV_URL" in job["error"]["message"]
    assert "nothing was charged" in job["error"]["message"] and "researching" not in stages


def test_kev_down_shows_on_health_and_stops_before_research(artifacts):
    with socket.socket() as s:  # a port nothing listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    with kev_client(artifacts, f"http://127.0.0.1:{port}") as c:
        h = c.get("/health").json()
        r = c.post("/v1/screenings", json={"schema_version": "0.1.0", "founder": {"name": "Someone Real"}})
        job = wait_for(c, f"/v1/screenings/{r.json()['job_id']}")
    assert h["kev"]["reachable"] is False and h["errors"] == {}
    assert job["status"] == "failed" and "isn't reachable" in job["error"]["message"]
    assert "nothing was charged" in job["error"]["message"]


def test_drivers_fill_in_a_few_at_a_time_most_important_first(kev_server, artifacts, monkeypatch):
    """With more flips than one chunk, the memo shows partial drivers between round trips."""
    from screener.pipeline import memo as memomod
    monkeypatch.setattr(memomod, "DRIVER_CHUNK", 1)
    rules = load(artifacts / "rules.json")
    for r, coef in zip(rules["rules"], [0.1, None, -0.9, 0.5]):  # r003 matters most, then r004, then r001
        r["elastic_net_coef"] = coef
    (artifacts / "rules.json").write_text(json.dumps(rules))
    url, calls = kev_server
    with kev_client(artifacts, url) as c:
        calls.clear()
        _, memo = screen(c, load(EXAMPLES / "investor_input_advance.json"))
        done = wait_for(c, f"/v1/memos/{memo['memo_id']}", key="drivers_status", done=("complete", "failed"))
    assert done["drivers_status"] == "complete" and len(done["drivers"]) == 3
    order = [b["state"].splitlines() for role, _, b in calls if role == "decider"][1:]  # after the verdict's own
    base = memo["answers"]
    changed = [next(i for i, line in enumerate(s) if not line.endswith(" " + base[i]["answer"])) for s in order]
    assert changed == [2, 3, 0]  # r003, r004, r001: by the size of the elastic-net weight


def test_drivers_failing_midway_keep_what_finished(kev_server, artifacts, monkeypatch):
    from screener.pipeline import memo as memomod
    from screener.pipeline.kev import KevDecider, KevUnavailable
    monkeypatch.setattr(memomod, "DRIVER_CHUNK", 1)
    real = KevDecider.decide_batch
    seen = {"n": 0}

    async def flaky(self, inputs, ctx):
        seen["n"] += 1
        if seen["n"] == 2:
            raise KevUnavailable("the tunnel went away")
        return await real(self, inputs, ctx)

    monkeypatch.setattr(KevDecider, "decide_batch", flaky)
    url, _ = kev_server
    with kev_client(artifacts, url) as c:
        _, memo = screen(c, load(EXAMPLES / "investor_input_advance.json"))
        done = wait_for(c, f"/v1/memos/{memo['memo_id']}", key="drivers_status", done=("complete", "failed"))
    assert done["drivers_status"] == "failed" and len(done["drivers"]) == 1


def test_demo_cache_answers_with_kev_off(kev_server, artifacts, tmp_path, monkeypatch):
    """Record the demo founders against Kev, then screen them again with Kev unreachable: same memo, no calls."""
    from screener.pipeline import kev as kevmod
    from tools.build_kev_demo_cache import main as build

    url, calls = kev_server
    cache_file = tmp_path / "kev_demo_cache.json"
    for k, v in {"ARTIFACTS_DIR": str(artifacts), "KEV_URL": url, "KEV_API_KEY": KEY}.items():
        monkeypatch.setenv(k, v)
    assert build(cache_file) == 0
    doc = load(cache_file)
    assert doc["fingerprint"]["model_id"] == "kev-0.6b-prod-c3" and len(doc["answers"]) == 3

    from screener.mocks.founders import DEMO_FOUNDERS
    monkeypatch.setattr(kevmod, "DEMO_CACHE", cache_file)
    import screener.main as mainmod
    monkeypatch.setattr(mainmod, "DEMO_CACHE", cache_file)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        dead = f"http://127.0.0.1:{s.getsockname()[1]}"
    with kev_client(artifacts, dead) as c:
        _, memo = screen(c, DEMO_FOUNDERS[0]["input"])
        done = wait_for(c, f"/v1/memos/{memo['memo_id']}", key="drivers_status", done=("complete", "failed"))
        assert done["drivers_status"] == "complete" and len(done["drivers"]) == done["drivers_total"]
        # A founder the cache doesn't know still needs Kev, and says so.
        r = c.post("/v1/screenings", json={"schema_version": "0.1.0", "founder": {"name": "Someone Not In The Demo"},
                                           "fields": {"industry": "fintech", "background": "technical"}})
        job = wait_for(c, f"/v1/screenings/{r.json()['job_id']}")
    assert job["status"] == "failed" and "Kev" in job["error"]["message"]

    # A cache built for another model is ignored.
    other = dict(doc, fingerprint={**doc["fingerprint"], "model_id": "something-else"})
    cache_file.write_text(json.dumps(other))
    from screener.pipeline.kev import KevCache
    assert len(KevCache(cache_file, model_id="kev-0.6b-prod-c3", rules=load(artifacts / "rules.json"))) == 0
