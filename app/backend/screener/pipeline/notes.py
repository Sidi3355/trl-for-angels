"""Voice notes and typed notes -> form fields the investor checks (MASTER_PLAN 8b, voice notes).

Two steps, each one swappable component:
- transcribe: audio -> text. ElevenLabs Scribe (`scribe_v3`, batch), or a mock that returns an example.
- sort: text -> template fields. Claude with a JSON schema, or a keyword-matching mock for tests and demos.

The sorter only suggests: the investor sees every value in the form before screening. Code, not the
prompt, enforces what matters (see `finish`): a value must fit the template (checked against the
contract), be backed by a quote from the notes, and never carry a name. Education and jobs are never
filled from a note: the merge replaces the agent's whole list with the investor's, so one job mentioned
in passing would wipe the agent's fuller history. Facts from after founding are listed in `kept_out` and
stay in the notes, which never reach the model. Nothing is stored: audio and text live for the request.
"""

from __future__ import annotations

import json
import logging
import re

from ..contract import Contract
from ..template import (BACKGROUND, COFOUNDERS, EXIT_KIND, INDUSTRY_EXPERIENCE, STARTUP_OUTCOME, VALUE_BAND,
                        WORK_EXPERIENCE)
from .budget import Budget
from .context import NotConfigured

log = logging.getLogger("screener.notes")

VERSION = "0.1.0"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TEXT = 20000

# Content types the recorder may send (Chrome and Android: webm/opus; iPhone Safari: mp4/aac).
AUDIO_EXTENSIONS = {
    "audio/webm": "webm", "video/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/x-m4a": "m4a",
    "audio/m4a": "m4a", "video/mp4": "mp4", "audio/aac": "aac", "audio/mpeg": "mp3", "audio/mp3": "mp3",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav", "audio/flac": "flac",
}

SORT_FIELDS = ("industry", "cofounders", "background", "work_experience", "industry_experience",
               "prior_startups", "prior_exits")
EVIDENCE_FIELDS = ("name", "company_name", "founding_date", *SORT_FIELDS)
INDUSTRIES = ("fintech", "healthtech", "biotech", "b2b saas", "developer tools", "e-commerce", "logistics", "edtech",
              "climate", "cybersecurity", "marketplaces", "media", "hardware", "insurtech", "agtech", "gaming",
              "proptech", "hr tech", "travel", "food")
DATE_RE = re.compile(r"^[0-9]{4}(-(0[1-9]|1[0-2]))?$")

EXAMPLE_TRANSCRIPT = (
    "Example note, because speech-to-text isn't set up on this server: met the founder today. Technical "
    "background, one co-founder, about eight years as an engineer at a payments company. First-time founder. "
    "They already have forty design partners.")


class NoteError(Exception):
    """A transcription or sorting failure the caller can act on (mapped to an HTTP error in main.py)."""

    def __init__(self, message: str, *, status: int = 502, code: str = "note_failed", retryable: bool = True):
        super().__init__(message)
        self.status, self.code, self.retryable = status, code, retryable


def audio_extension(content_type: str) -> str | None:
    return AUDIO_EXTENSIONS.get(content_type.split(";")[0].strip().lower())


# ------------------------------------------------------------------------- transcribe

class MockTranscriber:
    """No speech-to-text service: returns a fixed example, flagged as such, whatever was recorded."""
    name = "mock"

    async def transcribe(self, audio: bytes, content_type: str) -> dict:
        return {"text": EXAMPLE_TRANSCRIPT, "language_code": "eng", "example": True}


class ElevenLabsTranscriber:
    """ElevenLabs Scribe, batch: the whole recording in one request (a voice note is about a minute)."""
    name = "elevenlabs"

    def __init__(self, api_key: str | None, model: str = "scribe_v3"):
        if not api_key:
            raise NotConfigured("speech-to-text needs ELEVENLABS_API_KEY")
        from elevenlabs import AsyncElevenLabs  # imported here so mock mode doesn't need the SDK
        self.client = AsyncElevenLabs(api_key=api_key, timeout=90)
        self.model = model

    async def transcribe(self, audio: bytes, content_type: str) -> dict:
        from elevenlabs.core.api_error import ApiError
        ctype = content_type.split(";")[0].strip().lower()
        try:
            result = await self.client.speech_to_text.convert(
                model_id=self.model, file=(f"note.{audio_extension(ctype) or 'webm'}", audio, ctype),
                no_verbatim=True, tag_audio_events=False, timestamps_granularity="none", numbers_format="digits")
        except ApiError as e:
            raise _elevenlabs_error(e.status_code, e.body) from None
        except Exception as e:  # network failures and the like
            log.warning("transcription failed: %r", e)
            raise NoteError("couldn't reach the speech-to-text service; try again", code="transcription_failed") from None
        text = (getattr(result, "text", None) or "").strip()
        return {"text": text[:MAX_TEXT], "language_code": getattr(result, "language_code", None) or None, "example": False}


def _elevenlabs_error(status: int | None, body) -> NoteError:
    detail = json.dumps(body)[:300] if body is not None else ""
    log.warning("ElevenLabs error %s: %s", status, detail)
    if "quota" in detail.lower():
        return NoteError("the ElevenLabs account has no credits left this month", status=503,
                         code="transcription_unavailable", retryable=False)
    if status in (401, 403):
        return NoteError("ElevenLabs refused the key: check ELEVENLABS_API_KEY and that it allows Speech to Text",
                         status=503, code="transcription_unavailable", retryable=False)
    if status == 429:
        return NoteError("the speech-to-text service is busy; try again in a minute", status=503,
                         code="transcription_unavailable")
    if status in (400, 413, 415, 422):
        return NoteError("the speech-to-text service couldn't read this recording", status=422,
                         code="transcription_failed", retryable=False)
    return NoteError(f"the speech-to-text service failed ({status}); try again", code="transcription_failed")


# ------------------------------------------------------------------------- sort: shared checks

def empty_raw() -> dict:
    """The sorter output shape (see SORT_SCHEMA): an empty string means 'the notes don't say'."""
    return {"founder_name": "", "company_name": "", "founding_date": "", "industry": "", "cofounders": "",
            "background": "", "work_experience": "", "industry_experience": "",
            "prior_startups": {"status": "", "startups": []}, "prior_exits": {"status": "", "exits": []},
            "evidence": [], "kept_out": []}


def _industry(value: str) -> str:
    v = re.sub(r"\s+", " ", (value or "").strip().lower())
    v = re.sub(r"^(the|a|an) ", "", v)
    v = re.sub(r" (industry|space|sector)$", "", v)
    if not v or len(v) > 40 or len(v.split()) > 4 or not re.fullmatch(r"[a-z0-9&/ -]+", v):
        return ""
    return "B2B SaaS" if v == "b2b saas" else v


def _startups(raw: dict):
    status = raw.get("status", "")
    if status == "none":
        return "none"
    if status != "listed" or not raw.get("startups"):
        return None
    out = []
    for s in raw["startups"][:10]:
        band = s.get("value_band") or None
        out.append({"outcome": s.get("outcome"), "value_band": band if s.get("outcome") in ("acquired", "IPO") else None})
    return out


def _exits(raw: dict):
    status = raw.get("status", "")
    if status == "none":
        return "none"
    if status != "listed" or not raw.get("exits"):
        return None
    return [{"kind": e.get("kind"), "value_band": e.get("value_band")} for e in raw["exits"][:10]]


def _mentions_name(value: str, names: list[str]) -> bool:
    """Whole-word match of any part of a name given in the notes (only industry is free text)."""
    words = set(re.findall(r"[a-z0-9]+", value.lower()))
    return any(tok in words for n in names for tok in re.findall(r"[a-z0-9]{3,}", n.lower()))


def finish(raw: dict, contract: Contract, sorter: str) -> dict:
    """Turn sorter output into a note_sort_response, keeping only values the template and the notes support."""
    quotes: dict[str, str] = {}
    for ev in raw.get("evidence") or []:
        field, quote = ev.get("field"), (ev.get("quote") or "").strip()
        if field in EVIDENCE_FIELDS and quote and field not in quotes:
            quotes[field] = quote[:300]
    kept_out = [s.strip()[:200] for s in (raw.get("kept_out") or []) if isinstance(s, str) and s.strip()][:20]

    founder = {}
    for key, raw_key in (("name", "founder_name"), ("company_name", "company_name")):
        v = re.sub(r"\s+", " ", (raw.get(raw_key) or "").strip())
        if v and len(v) <= 120 and key in quotes:
            founder[key] = v
    names = list(founder.values())

    candidates = {
        "industry": _industry(raw.get("industry", "")),
        **{k: raw.get(k) or "" for k in ("cofounders", "background", "work_experience", "industry_experience")},
        "prior_startups": _startups(raw.get("prior_startups") or {}),
        "prior_exits": _exits(raw.get("prior_exits") or {}),
    }
    fields = {}
    for key, value in candidates.items():
        if value in ("", None):
            continue
        if key not in quotes:
            log.info("note sorter: %s=%r had no quote, left blank", key, value)
            continue
        if key == "industry" and _mentions_name(value, names):
            log.info("note sorter: %s=%r contains a name, left blank", key, value)
            continue
        errs = contract.errors_for_def(key, value)
        if errs:
            log.info("note sorter: %s=%r doesn't fit the template (%s), left blank", key, value, errs[0])
            continue
        fields[key] = value
    # A prior exit needs a prior startup: drop both when the note contradicts itself.
    if isinstance(fields.get("prior_exits"), list) and fields.get("prior_startups") == "none":
        fields.pop("prior_exits"), fields.pop("prior_startups")

    date = (raw.get("founding_date") or "").strip()
    founding_date = date if DATE_RE.match(date) and "founding_date" in quotes else None
    used = set(fields) | set(founder) | ({"founding_date"} if founding_date else set())
    return {
        "schema_version": VERSION, "fields": fields, "founder": founder, "founding_date": founding_date,
        "evidence": [{"field": f, "quote": q} for f, q in quotes.items() if f in used],
        "kept_out": kept_out, "sorter": sorter,
    }


# ------------------------------------------------------------------------- sort: mock

class MockSorter:
    """Keyword matching, for tests and demos without a Claude key. Catches simple phrasings only."""
    name = "mock"

    def __init__(self, contract: Contract):
        self.contract = contract

    async def sort(self, text: str, founding_date: str | None = None) -> dict:
        raw, low = empty_raw(), text.lower()

        def hit(field: str, pattern: str, value) -> None:
            m = re.search(pattern, low)
            if m and not raw[field]:
                raw[field] = value
                raw["evidence"].append({"field": field, "quote": text[m.start():m.end()]})

        hit("cofounders", r"\bsolo founder\b|\bno co-?founders?\b", "solo")
        hit("cofounders", r"\b(?:one|1|a) co-?founder\b", "1")
        hit("cofounders", r"\b(?:two|2) co-?founders\b", "2")
        hit("cofounders", r"\b(?:three|four|five|3|4|5)\+? co-?founders\b", "3+")
        hit("background", r"(?<!non-)(?<!non )\btechnical\b", "technical")
        hit("background", r"\bbusiness background\b", "business")
        hit("background", r"\bdomain (?:expert|specialist)\b", "domain specialist")
        m = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)\+? "
                      r"years?\b(?: of)?(?: work)? (?:experience|as an?\b)", low)
        if m:
            words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                     "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20}
            n = int(m[1]) if m[1].isdigit() else words[m[1]]
            raw["work_experience"] = "<5" if n < 5 else "5-10" if n < 10 else "10-15" if n < 15 else "15+"
            raw["evidence"].append({"field": "work_experience", "quote": text[m.start():m.end()]})
        m = re.search(r"\bfirst[- ]time founder\b", low)
        if m:
            raw["prior_startups"]["status"] = raw["prior_exits"]["status"] = "none"
            raw["evidence"] += [{"field": f, "quote": text[m.start():m.end()]} for f in ("prior_startups", "prior_exits")]
        for name in INDUSTRIES:
            m = re.search(rf"\b{re.escape(name)}\b", low)
            if m:
                raw["industry"] = name
                raw["evidence"].append({"field": "industry", "quote": text[m.start():m.end()]})
                break
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if re.search(r"\b(raised|revenue|arr|customers|design partners|traction|users|pilots?|hired|signed)\b",
                         sentence.lower()):
                raw["kept_out"].append(sentence.strip().rstrip(".")[:160] + " (after founding)")
        return finish(raw, self.contract, self.name)


# ------------------------------------------------------------------------- sort: Claude

def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


def _choice(values) -> dict:
    return {"type": "string", "enum": ["", *values]}


SORT_SCHEMA = _obj({
    "founder_name": {"type": "string", "description": "As written in the notes, or empty"},
    "company_name": {"type": "string", "description": "As written in the notes, or empty"},
    "founding_date": {"type": "string", "description": "YYYY or YYYY-MM, or empty"},
    "industry": {"type": "string", "description": "The startup's industry in a few lowercase words, or empty"},
    "cofounders": _choice(COFOUNDERS),
    "background": _choice(BACKGROUND),
    "work_experience": _choice(WORK_EXPERIENCE),
    "industry_experience": _choice(INDUSTRY_EXPERIENCE),
    "prior_startups": _obj({
        "status": {"type": "string", "enum": ["", "none", "listed"]},
        "startups": {"type": "array", "items": _obj({
            "outcome": {"type": "string", "enum": list(STARTUP_OUTCOME)}, "value_band": _choice(VALUE_BAND)})},
    }),
    "prior_exits": _obj({
        "status": {"type": "string", "enum": ["", "none", "listed"]},
        "exits": {"type": "array", "items": _obj({
            "kind": {"type": "string", "enum": list(EXIT_KIND)}, "value_band": {"type": "string", "enum": list(VALUE_BAND)}})},
    }),
    "evidence": {"type": "array", "items": _obj({
        "field": {"type": "string", "enum": list(EVIDENCE_FIELDS)}, "quote": {"type": "string"}})},
    "kept_out": {"type": "array", "items": {"type": "string"}},
})

SYSTEM = """You turn an angel investor's notes about a startup founder into fields of a fixed founder-profile template. The investor checks your fields before they are used, and a model trained on this template scores the profile, so accuracy matters more than coverage: fill a field only when the notes state it or make it unambiguous, and otherwise leave it as an empty string.

The profile describes the founder as they were on the day the company was founded. Anything about the startup after founding (customers, traction, revenue, funding raised, hires, partnerships, product progress) must not go into a field: list each such fact briefly in kept_out instead, for example "raised a seed round (after founding)". Opinions and gut feel are neither fields nor kept_out; they stay in the investor's notes.

Fields:
- industry: the startup's industry in a few lowercase words, e.g. fintech, healthtech, developer tools, b2b saas, climate.
- cofounders: how many co-founders besides this founder: solo, 1, 2 or 3+.
- background: technical (engineering or science roles or degrees), business, mixed, or domain specialist (deep expertise in the startup's own field, e.g. a doctor building healthtech).
- work_experience: total years of work before founding: <5, 5-10, 10-15 or 15+. You may add up job durations the notes give.
- industry_experience: experience in the startup's industry before founding: none, some or deep.
- prior_startups: companies the founder founded before this one. "none" for a first-time founder; "listed" with each one's outcome (shut down, acquired, IPO, still operating) and, for acquired or IPO, its value band; empty if the notes don't say.
- prior_exits: acquisitions or IPOs of companies they co-founded, each with its value band. "none" if they have none (a first-time founder has none); empty if the notes don't say.
- Value bands: under $50M, $50M-$500M, $500M-$1B, over $1B.
- founder_name, company_name: as written in the notes; they are used only to look the founder up. Never put a name of a person, company, university or product into any other field.
- founding_date: YYYY or YYYY-MM, only if the notes say when the company was founded.

Education and job history are filled from other sources, so leave them out. For every field you fill, including founder_name, company_name and founding_date, add an evidence item with the shortest exact quote from the notes that supports it."""


class ClaudeSorter:
    """Claude with a JSON schema (structured outputs): one call per note, charged to the shared spend caps."""
    name = "claude"

    def __init__(self, *, api_key: str | None, model: str, base_url: str, effort: str, budget: Budget,
                 contract: Contract, client=None):
        if client is None:
            if not api_key:
                raise NotConfigured("sorting notes into the form needs the Claude key (ANTHROPIC_API_KEY)")
            from anthropic import AsyncAnthropic  # imported here so mock mode doesn't need the SDK
            # base_url is explicit: never fall back to an ANTHROPIC_BASE_URL set in the environment
            client = AsyncAnthropic(api_key=api_key, base_url=base_url, max_retries=2, timeout=90)
        self.client, self.model, self.effort, self.budget, self.contract = client, model, effort, budget, contract

    async def sort(self, text: str, founding_date: str | None = None) -> dict:
        import anthropic
        if self.budget.exhausted:
            raise NoteError(f"the Claude spend cap for this server (${self.budget.total_usd:.2f}) is used up, so notes "
                            "can't be sorted; they're still kept as notes", status=503, code="sorting_unavailable",
                            retryable=False)
        prompt = f"Founding date: {founding_date or 'not given'}\n\n<notes>\n{text[:MAX_TEXT]}\n</notes>"
        try:
            msg = await self.client.beta.messages.create(
                model=self.model, max_tokens=8000, system=SYSTEM, messages=[{"role": "user", "content": prompt}],
                output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": SORT_SCHEMA}},
                betas=[FALLBACK_BETA], fallbacks="default")
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            raise NoteError("Claude refused the key, so notes can't be sorted", status=503,
                            code="sorting_unavailable", retryable=False) from None
        except anthropic.RateLimitError:
            raise NoteError("Claude is busy; try again in a minute", status=503, code="sorting_unavailable") from None
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            log.warning("note sorting failed: %r", e)
            raise NoteError("sorting the notes failed; try again", code="sorting_failed") from None
        self.budget.charge(msg.usage, getattr(msg, "model", self.model), label="notes")
        if msg.stop_reason == "refusal":
            raise NoteError("Claude declined to sort these notes", status=422, code="sorting_failed", retryable=False)
        if msg.stop_reason == "max_tokens":
            raise NoteError("the notes were too long to sort", status=422, code="sorting_failed", retryable=False)
        body = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
        try:
            raw = json.loads(body)
        except json.JSONDecodeError:
            log.warning("note sorter returned non-JSON: %.200s", body)
            raise NoteError("sorting the notes failed; try again", code="sorting_failed") from None
        return finish({**empty_raw(), **raw}, self.contract, self.name)


# ------------------------------------------------------------------------- wiring

class NoteTools:
    """The configured transcriber and sorter, or why each isn't available."""

    def __init__(self, transcriber=None, sorter=None, transcriber_error: str = "", sorter_error: str = ""):
        self.transcriber, self.sorter = transcriber, sorter
        self.transcriber_error, self.sorter_error = transcriber_error, sorter_error

    def summary(self) -> dict:
        return {"transcriber": self.transcriber.name if self.transcriber else "off",
                "note_sorter": self.sorter.name if self.sorter else "off"}
