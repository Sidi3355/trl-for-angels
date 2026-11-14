"""Voice notes: transcription and sorting notes into form fields. Fake clients only: no keys, no credits."""

import asyncio
import json
from types import SimpleNamespace as NS

import pytest

from conftest import CONTRACT_DIR, load, EXAMPLES, make_client
from screener.contract import get_contract
from screener.pipeline.budget import Budget
from screener.pipeline.notes import ClaudeSorter, ElevenLabsTranscriber, MockSorter, NoteError, empty_raw, finish

NOTE = load(EXAMPLES / "note_sort_request.json")["text"]
AUDIO = b"\x1aE\xdf\xa3" + b"\0" * 4000  # bytes standing in for a webm recording


def test_transcribe_mock_when_no_key(contract):
    with make_client() as c:
        assert c.get("/health").json()["components"]["transcriber"] == "mock"
        r = c.post("/v1/notes/transcribe", content=AUDIO, headers={"Content-Type": "audio/webm;codecs=opus"})
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["example"] is True and "Example note" in doc["text"]
        assert contract.errors("note_transcript", doc) == []


def test_transcribe_rejects_bad_uploads():
    with make_client(note_max_audio_mb=0.001) as c:
        assert c.post("/v1/notes/transcribe", content=AUDIO, headers={"Content-Type": "text/plain"}).status_code == 400
        assert c.post("/v1/notes/transcribe", content=b"x" * 50, headers={"Content-Type": "audio/mp4"}).json()["error"]["code"] == "empty_recording"
        r = c.post("/v1/notes/transcribe", content=b"x" * 5000, headers={"Content-Type": "audio/mp4"})
        assert r.status_code == 413 and r.json()["error"]["code"] == "too_large"


def test_elevenlabs_transcriber_calls_scribe_and_maps_errors():
    from elevenlabs.core.api_error import ApiError
    t = ElevenLabsTranscriber("placeholder")
    calls = []

    async def convert(**kw):
        calls.append(kw)
        return NS(text="  Met the founder.  ", language_code="eng")

    t.client = NS(speech_to_text=NS(convert=convert))
    doc = asyncio.run(t.transcribe(AUDIO, "audio/mp4"))
    assert doc == {"text": "Met the founder.", "language_code": "eng", "example": False}
    kw = calls[0]
    assert kw["model_id"] == "scribe_v3" and kw["no_verbatim"] is True and kw["file"][0] == "note.m4a"

    for status, body, code, http in [(401, {"detail": "invalid"}, "transcription_unavailable", 503),
                                     (401, {"detail": {"status": "quota_exceeded"}}, "transcription_unavailable", 503),
                                     (422, {}, "transcription_failed", 422), (500, {}, "transcription_failed", 502)]:
        async def boom(**kw):
            raise ApiError(status_code=status, body=body)
        t.client = NS(speech_to_text=NS(convert=boom))
        with pytest.raises(NoteError) as e:
            asyncio.run(t.transcribe(AUDIO, "audio/webm"))
        assert (e.value.code, e.value.status) == (code, http)
        if "quota" in json.dumps(body):
            assert "credits" in str(e.value)


def test_sort_off_without_claude_key():
    with make_client() as c:
        assert c.get("/health").json()["components"]["note_sorter"] == "off"
        r = c.post("/v1/notes/sort", json={"schema_version": "0.1.0", "text": NOTE})
        assert r.status_code == 503 and r.json()["error"]["code"] == "not_configured"
        assert "ANTHROPIC_API_KEY" in r.json()["error"]["message"]


def test_sort_with_mock_sorter(contract):
    with make_client(note_sorter="mock") as c:
        assert c.post("/v1/notes/sort", json={"schema_version": "0.1.0", "text": ""}).status_code == 422
        r = c.post("/v1/notes/sort", json={"schema_version": "0.1.0", "text": NOTE})
        assert r.status_code == 200, r.text
        doc = r.json()
    assert contract.errors("note_sort_response", doc) == []
    assert doc["fields"] == {"cofounders": "1", "background": "technical", "prior_startups": "none", "prior_exits": "none"}
    assert {e["field"] for e in doc["evidence"]} == set(doc["fields"])
    assert any("seed" in k for k in doc["kept_out"]) and any("design partners" in k for k in doc["kept_out"])
    assert doc["sorter"] == "mock"


def test_finish_keeps_only_supported_template_values(contract):
    raw = empty_raw() | {
        "founder_name": "Ada Moreno", "company_name": "Tallyframe", "founding_date": "2024-03",
        "industry": "Tallyframe tools",                     # contains the company name: dropped
        "cofounders": "2",                                  # no quote: dropped
        "background": "technical",
        "work_experience": "5-10",
        "prior_startups": {"status": "listed", "startups": [{"outcome": "acquired", "value_band": ""}]},  # band missing: dropped
        "prior_exits": {"status": "listed", "exits": [{"kind": "acquisition", "value_band": "$50M-$500M"}]},
        "evidence": [{"field": f, "quote": "q"} for f in ("name", "company_name", "industry", "background",
                                                         "work_experience", "prior_startups", "prior_exits")],
        "kept_out": ["raised a seed round (after founding)", "  "],
    }
    doc = finish(raw, contract, "claude")
    assert contract.errors("note_sort_response", doc) == []
    assert doc["fields"] == {"background": "technical", "work_experience": "5-10",
                             "prior_exits": [{"kind": "acquisition", "value_band": "$50M-$500M"}]}
    assert doc["founder"] == {"name": "Ada Moreno", "company_name": "Tallyframe"}
    assert doc["founding_date"] is None                     # given but not quoted
    assert doc["kept_out"] == ["raised a seed round (after founding)"]
    # contradiction: an exit but "no prior startups" -> both dropped
    raw2 = empty_raw() | {"prior_startups": {"status": "none", "startups": []},
                          "prior_exits": {"status": "listed", "exits": [{"kind": "IPO", "value_band": "over $1B"}]},
                          "evidence": [{"field": "prior_startups", "quote": "q"}, {"field": "prior_exits", "quote": "q"}]}
    assert finish(raw2, contract, "claude")["fields"] == {}


class FakeAnthropic:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.beta = NS(messages=NS(create=self._create))

    async def _create(self, **kw):
        self.calls.append(kw)
        return self.replies.pop(0)


def reply(payload, stop="end_turn"):
    return NS(stop_reason=stop, model="claude-opus-5-5", content=[NS(type="text", text=json.dumps(payload))],
              usage=NS(input_tokens=1500, output_tokens=400, cache_creation_input_tokens=0, cache_read_input_tokens=0,
                       server_tool_use=None))


def test_claude_sorter_request_cost_and_refusal(contract):
    payload = empty_raw() | {"cofounders": "1", "industry": "Developer Tools",
                             "evidence": [{"field": "cofounders", "quote": "one co-founder"},
                                          {"field": "industry", "quote": "dev tools"}],
                             "kept_out": ["raised a seed round (after founding)"]}
    fake = FakeAnthropic([reply(payload), reply({}, stop="refusal")])
    budget = Budget(total_usd=1.0, per_founder_usd=1.0)
    sorter = ClaudeSorter(api_key=None, model="claude-opus-5-5", base_url="https://api.anthropic.com", effort="low",
                          budget=budget, contract=contract, client=fake)
    doc = asyncio.run(sorter.sort(NOTE, "2024-03"))
    assert doc["fields"] == {"industry": "developer tools", "cofounders": "1"} and doc["sorter"] == "claude"
    kw = fake.calls[0]
    assert kw["model"] == "claude-opus-5-5" and kw["output_config"]["effort"] == "low"
    assert kw["output_config"]["format"]["type"] == "json_schema" and kw["fallbacks"] == "default"
    assert "Founding date: 2024-03" in kw["messages"][0]["content"] and NOTE in kw["messages"][0]["content"]
    assert budget.spent_usd == pytest.approx((1500 * 4 + 400 * 20) / 1e6)
    with pytest.raises(NoteError) as e:
        asyncio.run(sorter.sort(NOTE))
    assert e.value.status == 422
    budget.spent_usd = 5.0
    with pytest.raises(NoteError) as e:
        asyncio.run(sorter.sort(NOTE))
    assert e.value.code == "sorting_unavailable"


def test_mock_sorter_is_conservative(contract):
    doc = asyncio.run(MockSorter(contract).sort("Non-technical founder, gut feel is good. Solo founder in fintech, "
                                                "12 years of experience."))
    assert doc["fields"] == {"industry": "fintech", "cofounders": "solo", "work_experience": "10-15"}
    assert doc["kept_out"] == []
