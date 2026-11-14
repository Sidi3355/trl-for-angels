"""The real research agent's control flow, with a scripted fake Claude client (no API key, no cost)."""

import asyncio
import copy
from types import SimpleNamespace as NS

import pytest

from conftest import CONTRACT_DIR
from screener.artifacts import load_artifacts
from screener.contract import get_contract
from screener.pipeline.agent import ClaudeAgent, SUBMIT_TOOL
from screener.pipeline.budget import Budget, cost_of
from screener.pipeline.context import Pipeline, no_emit
from screener.pipeline.models import MockAnswerer, MockDecider
from screener.pipeline.screening import screen


def usage(inp=1000, out=500, searches=0):
    return NS(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=0, cache_read_input_tokens=0,
              server_tool_use=NS(web_search_requests=searches, web_fetch_requests=0))


def msg(stop, blocks, u=None, model="claude-opus-5-5"):
    return NS(stop_reason=stop, content=blocks, usage=u or usage(), model=model)


def search_block(q):
    return NS(type="server_tool_use", name="web_search", input={"query": q}, id="srv1")


def submit_block(payload, id="toolu_1"):
    return NS(type="tool_use", name="submit_profile", input=payload, id=id)


class FakeStream:
    def __init__(self, message):
        self.message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        async def gen():
            for b in self.message.content:
                yield NS(type="content_block_stop", content_block=b)
        return gen()

    async def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        return FakeStream(self.script.pop(0))


def field(value, url="https://example.com/profile", conf=0.9, ev="seen"):
    return {"value": value, "source_url": url, "confidence": conf, "evidence": ev}


def payload(**overrides):
    p = {
        "founding_date": {"value": "2013", "source_url": "https://example.com/about", "evidence": "about page"},
        "fields": {
            "industry": field("B2B SaaS", "https://example.com/about"),
            "cofounders": field("solo"),
            "background": field("business"),
            "work_experience": field("10-15"),
            "industry_experience": field("some"),
            "education": field([{"degree": "BA", "field": "Business", "qs_rank": "300+"}]),
            "jobs": field([{"role": "Sales Manager", "company": "a large IT company (Acme Corp)",
                            "company_size": "5,000+", "industry": "Technology", "duration": "5+"},
                           {"role": "Account Executive", "company": "a data storage company",
                            "company_size": "5,000+", "industry": "Technology", "duration": "3-5"}]),
            "prior_startups": field([{"outcome": "shut down", "value_band": None}] * 3),
            "prior_exits": field("none"),
        },
        "sources": [
            {"url": "https://example.com/profile", "title": "Profile", "published_date": "2021", "before_founding": True},
            {"url": "https://example.com/about", "title": "About", "published_date": "", "before_founding": True},
            {"url": "https://example.com/news-2021", "title": "Valuation news", "published_date": "2021-01",
             "before_founding": False},
        ],
        "post_founding_notes": [{"text": "Valued at $3B in 2021.", "source_url": "https://example.com/news-2021"}],
        "names_seen": ["Acme Corp", "Pat Example"],
        "research_notes": "Founding year from the about page.",
    }
    for k, v in overrides.items():
        p["fields"][k] = v
    return p


def make(script, budget=None, **kw):
    client = FakeClient(script)
    agent = ClaudeAgent(api_key=None, model="claude-opus-5-5", base_url="https://api.anthropic.com", max_searches=10,
                        max_fetches=5, effort="medium", max_tokens=16000, min_confidence=0.5,
                        budget=budget or Budget(total_usd=5, per_founder_usd=1), contract=get_contract(CONTRACT_DIR),
                        client=client, **kw)
    arts = load_artifacts(CONTRACT_DIR / "mocks", get_contract(CONTRACT_DIR))
    ctx = Pipeline(artifacts=arts, agent=agent, answerer=MockAnswerer(), decider=MockDecider(), pace=0)
    return agent, client, ctx


INP = {"schema_version": "0.1.0", "founder": {"name": "Pat Example", "company_name": "Examplely"}}


def run(coro):
    return asyncio.run(coro)


def test_pause_turn_then_submit_maps_fields_and_enforces_rules():
    p = payload(
        background=field("business", "https://example.com/news-2021"),     # only a post-founding source
        industry_experience=field("deep", conf=0.3),                        # below the confidence floor
    )
    agent, client, ctx = make([
        msg("pause_turn", [search_block("Pat Example founder background")], usage(searches=4)),
        msg("tool_use", [submit_block(p)], usage(searches=2)),
    ])
    events = []

    async def emit(type, message, *, stage=None, data=None):
        events.append((type, message))

    f = run(agent.research(INP, ctx, emit))
    assert f.ran and set(f.fields) == {"industry", "cofounders", "work_experience", "education", "jobs",
                                       "prior_startups", "prior_exits"}
    assert "after founding" in f.field_notes["background"] and "40%" not in f.field_notes["industry_experience"]
    assert "30% confidence" in f.field_notes["industry_experience"]
    assert f.founding_date == ("2013", ["s2"]) and f.post_founding[0]["source_ids"] == ["s3"]
    assert {s["id"]: s["before_founding"] for s in f.sources} == {"s1": True, "s2": True, "s3": False}
    assert ("search", "Searching: Pat Example founder background") in events
    # after pause_turn the history ends with the assistant turn: no extra user message
    assert [m["role"] for m in client.calls[1]["messages"]] == ["user", "assistant"]
    expected = cost_of(usage(searches=4), "claude-opus-5-5") + cost_of(usage(searches=2), "claude-opus-5-5")
    assert f.cost_usd == round(expected, 4) and agent.budget.searches == 6


def test_request_shape():
    agent, client, ctx = make([msg("tool_use", [submit_block(payload())])])
    run(agent.research(INP, ctx, no_emit))
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["output_config"] == {"effort": "medium"}
    assert call["betas"] == ["server-side-fallback-2026-07-01"] and call["fallbacks"] == "default"
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    tools = {t["name"]: t for t in call["tools"]}
    assert tools["web_search"]["max_uses"] == 10 and tools["web_fetch"]["max_uses"] == 5
    assert tools["submit_profile"] == SUBMIT_TOOL and "strict" not in SUBMIT_TOOL  # too large for strict mode
    assert "founding date isn't given" in call["messages"][0]["content"]


def test_zero_fetches_leaves_web_fetch_out():
    agent, client, ctx = make([msg("tool_use", [submit_block(payload())])])
    agent.max_fetches = 0
    run(agent.research(INP, ctx, no_emit))
    assert [t["name"] for t in client.calls[0]["tools"]] == ["web_search", "submit_profile"]


def test_nudges_when_no_submit_then_accepts():
    agent, client, ctx = make([msg("end_turn", [NS(type="text", text="Here is what I found...")]),
                               msg("tool_use", [submit_block(payload())])])
    f = run(agent.research(INP, ctx, no_emit))
    assert f.ran and client.calls[1]["messages"][-1]["content"].startswith("Call submit_profile now")


def test_invalid_submit_gets_an_error_result_and_a_retry():
    bad = payload()
    del bad["fields"]["jobs"]
    agent, client, ctx = make([msg("tool_use", [submit_block(bad)]), msg("tool_use", [submit_block(payload(), "toolu_2")])])
    f = run(agent.research(INP, ctx, no_emit))
    assert f.ran
    retry = client.calls[1]["messages"][-1]["content"][0]
    assert retry["type"] == "tool_result" and retry["is_error"] and "jobs" in retry["content"]


def test_per_founder_cap_stops_research():
    pricey = usage(inp=300_000, out=10_000, searches=10)  # about $1.50 at Opus 5.5 prices
    agent, client, ctx = make([msg("pause_turn", [search_block("q")], pricey)])
    f = run(agent.research(INP, ctx, no_emit))
    assert not f.ran and "per-founder cap" in f.note and len(client.calls) == 1


def test_total_budget_exhausted_skips_the_call():
    budget = Budget(total_usd=1, per_founder_usd=1, spent_usd=1.01)
    agent, client, ctx = make([], budget=budget)
    f = run(agent.research(INP, ctx, no_emit))
    assert not f.ran and "budget" in f.note and client.calls == []


def test_refusal_returns_partial():
    agent, _, ctx = make([msg("refusal", [])])
    f = run(agent.research(INP, ctx, no_emit))
    assert not f.ran and "declined" in f.note


def test_end_to_end_memo_redacts_leaked_names(contract):
    agent, _, ctx = make([msg("tool_use", [submit_block(payload())])])
    memo = run(screen(INP, ctx, memo_id="memo_t", job_id=None))
    contract.check("memo", memo)
    assert "Acme" not in memo["rendered_profile"] and "Pat Example" not in memo["rendered_profile"]
    jobs = memo["fields"]["jobs"]
    assert jobs["value"][0]["company"] == "a large IT company" and "removed" in jobs["note"]
    assert "redacted" in {w["code"] for w in memo["warnings"]}
    assert memo["notes"]["post_founding"][0]["text"].startswith("Valued at")
    assert memo["founder"]["founding_date"] == {"value": "2013", "provenance": "agent", "source_ids": ["s2"]}
    assert memo["rendered_profile"].splitlines()[-2] == "Prior startups: 3 shut down."


def test_missing_key_is_not_configured():
    from screener.pipeline.context import NotConfigured
    with pytest.raises(NotConfigured, match="SCREENER_ANTHROPIC_API_KEY"):
        ClaudeAgent(api_key=None, model="m", base_url="https://api.anthropic.com", max_searches=1, max_fetches=1,
                    effort="low", max_tokens=1000, min_confidence=0.5, budget=Budget(1, 1),
                    contract=get_contract(CONTRACT_DIR))
