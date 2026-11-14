"""The real research agent: Claude with web search fills each template field (MASTER_PLAN 8, step 1).

For every field the agent returns {value, source_url, confidence, evidence}, using only information
true on the founding date. It finishes by calling the submit_profile tool, whose input is validated
here against the contract. Code, not the prompt, enforces the rules that matter:
- a field backed only by a post-founding source is dropped to unknown (founding-date cutoff);
- a value below AGENT_MIN_CONFIDENCE is dropped to unknown, with the guess kept in a note;
- a value outside the template's allowed values is dropped to unknown;
- spend is capped per founder and in total (pipeline/budget.py).
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

from ..contract import Contract
from ..template import FIELD_KEYS, FIELD_LABELS, UNKNOWN
from .budget import Budget
from .context import Emitter, NotConfigured, Pipeline
from .research import Findings

log = logging.getLogger("screener.agent")

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TURNS = 8  # API round trips per founder (pause_turn resumes and nudges included)

# ----------------------------------------------------------------------- tool schema

_ENUMS = {
    "cofounders": ["solo", "1", "2", "3+", UNKNOWN],
    "background": ["technical", "business", "mixed", "domain specialist", UNKNOWN],
    "work_experience": ["<5", "5-10", "10-15", "15+", UNKNOWN],
    "industry_experience": ["none", "some", "deep", UNKNOWN],
}
_BAND = {"enum": ["under $50M", "$50M-$500M", "$500M-$1B", "over $1B"]}
# Plain strings rather than nullable ones keep the schema small; the code treats "" as missing.
_URL = {"type": "string", "description": "URL, or an empty string if none"}
_DATE = {"type": "string", "description": "YYYY, YYYY-MM or YYYY-MM-DD, or an empty string if unknown"}


def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


_VALUE_SCHEMAS = {
    "industry": {"type": "string"},
    **{k: {"enum": v} for k, v in _ENUMS.items()},
    "education": {"anyOf": [{"const": UNKNOWN}, {"type": "array", "items": _obj({
        "degree": {"type": "string"}, "field": {"type": "string"},
        "qs_rank": {"enum": ["top 50", "51-100", "101-300", "300+", "unranked", UNKNOWN]}})}]},
    "jobs": {"anyOf": [{"const": UNKNOWN}, {"type": "array", "items": _obj({
        "role": {"type": "string"}, "company": {"type": "string"},
        "company_size": {"enum": ["1-10", "11-50", "51-200", "201-1,000", "1,001-5,000", "5,000+", UNKNOWN]},
        "industry": {"type": "string"},
        "duration": {"enum": ["<1", "1-2", "2-3", "3-5", "5+", UNKNOWN]}})}]},
    "prior_startups": {"anyOf": [{"enum": ["none", UNKNOWN]}, {"type": "array", "items": _obj({
        "outcome": {"enum": ["shut down", "acquired", "IPO", "still operating"]},
        "value_band": {"anyOf": [_BAND, {"type": "null"}]}})}]},
    "prior_exits": {"anyOf": [{"enum": ["none", UNKNOWN]}, {"type": "array", "items": _obj({
        "kind": {"enum": ["acquisition", "IPO"]}, "value_band": _BAND})}]},
}

SUBMIT_TOOL = {
    "name": "submit_profile",
    "description": "Submit the founder's profile as of the founding date. Call it exactly once, at the end.",
    # Not strict: the API refuses this schema in strict mode ("compiled grammar is too large"). Every
    # submission is validated against it in research() instead, and an invalid one is sent back with the errors.
    "eager_input_streaming": True,
    "input_schema": _obj({
        "founding_date": _obj({"value": {"type": "string", "description": "YYYY, YYYY-MM, YYYY-MM-DD or 'unknown'"},
                               "source_url": _URL, "evidence": {"type": "string"}}),
        "fields": _obj({k: _obj({"value": s, "source_url": _URL, "confidence": {"type": "number"},
                                 "evidence": {"type": "string"}}) for k, s in _VALUE_SCHEMAS.items()}),
        "sources": {"type": "array", "items": _obj({
            "url": {"type": "string"}, "title": {"type": "string"}, "published_date": _DATE,
            "before_founding": {"type": "boolean"}})},
        "post_founding_notes": {"type": "array", "items": _obj({"text": {"type": "string"}, "source_url": _URL})},
        "names_seen": {"type": "array", "items": {"type": "string"}},
        "research_notes": {"type": "string"},
    }),
}

SYSTEM_PROMPT = """You research startup founders for angel investors who screen deals without analysts.
Your job: find one founder's professional background exactly as it stood on the day their company was founded, using public web information, and submit it in a fixed template.

Work in this order:
1. Identify the right person. Use the name together with the company, website or LinkedIn given, and don't confuse namesakes.
2. Establish the company's founding date (unless it is given). If sources disagree, or the company was renamed or pivoted, use the date the venture itself started, and explain your choice in the evidence.
3. Research education, jobs, earlier startups and exits up to that date. Good sources: LinkedIn, company about pages, Crunchbase, Wikipedia, university or alumni pages, interviews, podcasts and press. LinkedIn pages often can't be fetched; search results about them still help.
4. Call submit_profile exactly once.

The founding-date cutoff is strict. Record only what was true on the founding date: no roles at this startup, no later jobs, funding, valuations, acquisitions, team size or traction. Put noteworthy later facts in post_founding_notes instead; they are shown to the investor but never used for scoring. A later article describing earlier events is fine as a source: set before_founding to true when the facts you took from it describe the time before founding. before_founding is about those facts, not the publication date: the founding date and the founding team describe the day of founding, so a recent page that gives them is before_founding true. If one page gives both early facts and later ones, list it once with before_founding true and cite it for the post-founding notes as well. Set it to false only for pages you use solely for post-founding notes.

Fill each field with the template's values exactly:
- industry: the startup's industry as a short lower-case label, preferably one of fintech, healthtech, biotech, B2B SaaS, developer tools, e-commerce, logistics, edtech, climate, cybersecurity, marketplaces, media, hardware, insurtech, agtech, gaming, proptech, HR tech, travel, food; otherwise a similar short label.
- cofounders: the number of co-founders besides this founder at founding: solo, 1, 2 or 3+.
- background: technical (engineering, computer science), business (sales, finance, consulting, marketing, operations), mixed (both), or domain specialist (deep expertise outside software, e.g. clinician, scientist, construction engineer).
- work_experience: total years worked before founding, excluding full-time study: <5, 5-10, 10-15 or 15+. It should roughly match the job durations.
- industry_experience: prior experience in the startup's own industry: none, some or deep. It must agree with the job industries.
- education: 1 to 3 entries. degree as an abbreviation (BSc, BA, BEng, MSc, MEng, MBA, PhD, MD) or "no degree" for study left unfinished; field of study; the university's QS World University Rankings band: top 50, 51-100, 101-300, 300+, or unranked if not ranked by QS. Use the current QS ranking: it describes the university, not the founder, so it doesn't break the cutoff. Give the page showing the degree itself as education's source_url, not the rankings page.
- jobs: 1 to 6 roles before founding, oldest first. role is a plain job title. company is a generic, neutral description and NEVER a name (for example "a large search and advertising company", "a payments startup", "a teaching hospital"), with no evaluative words such as fast-growing, leading or prestigious. company_size is the headcount band at the time. industry is the employer's industry in title case (e.g. "Fintech", "Professional Services"). duration is a band: <1, 1-2, 2-3, 3-5 or 5+ years. Count an earlier startup of the founder's own under prior_startups, not as a job.
- prior_startups: startups the founder founded or co-founded before this one, each with an outcome: shut down, acquired (with a value band), IPO (with a value band) or still operating. Use "none" if there were none.
- prior_exits: acquisitions or IPOs of those startups, as co-founder, with the same value bands. Use "none" if there were none.
Value bands: under $50M, $50M-$500M, $500M-$1B, over $1B. If a sale price was never disclosed and there is no credible estimate, set both prior_startups and prior_exits to "unknown" and explain in the evidence.

Accuracy matters more than completeness. For every field give the source_url you relied on most, a confidence from 0 to 1, and a short evidence note. Use "unknown" whenever you can't find or confirm something: a value with confidence below 0.5 is discarded anyway. Never guess a QS band, a headcount or a date you haven't seen evidence for.

Anonymise every value: no names of people, companies, products, universities or places. List every real name of a person, company, product or university you came across in names_seen, so the app can check the profile is anonymous.
List every page you relied on in sources. Use at most the searches you are allowed, and stop searching once the fields are settled."""


def _validator() -> Draft202012Validator:
    return Draft202012Validator(SUBMIT_TOOL["input_schema"])


# ------------------------------------------------------------------------- the agent

class ClaudeAgent:
    name = "claude"

    def __init__(self, *, api_key: str | None, model: str, base_url: str, max_searches: int, max_fetches: int,
                 effort: str, max_tokens: int, min_confidence: float, budget: Budget, contract: Contract,
                 client=None):
        if not api_key and client is None:
            raise NotConfigured("AGENT=claude needs SCREENER_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY on the host)")
        self.model, self.max_searches, self.max_fetches = model, max_searches, max_fetches
        self.effort, self.max_tokens, self.min_confidence = effort, max_tokens, min_confidence
        self.budget, self.contract = budget, contract
        if client is None:
            from anthropic import AsyncAnthropic  # imported here so mock mode doesn't need the SDK
            # base_url is explicit: never fall back to an ANTHROPIC_BASE_URL set in the environment
            client = AsyncAnthropic(api_key=api_key, base_url=base_url, max_retries=2, timeout=600)
        self.client = client
        self._validate = _validator()

    def tools(self) -> list[dict]:
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": self.max_searches}]
        # AGENT_MAX_FETCHES=0 leaves web fetch out entirely: the API refuses the tool from
        # restricted-network sandboxes (such as the Claude Code cloud environment), even with max_uses 0.
        if self.max_fetches > 0:
            tools.append({"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": self.max_fetches})
        return tools + [SUBMIT_TOOL]

    def user_message(self, inp: dict) -> str:
        f = inp["founder"]
        lines = ["Research this founder."]
        for key, label in (("name", "Name"), ("company_name", "Company"), ("linkedin_url", "LinkedIn"),
                           ("website_url", "Website")):
            if f.get(key):
                lines.append(f"{label}: {f[key]}")
        for url in f.get("other_urls") or []:
            lines.append(f"Other link: {url}")
        if inp.get("founding_date"):
            lines.append(f"The company was founded {inp['founding_date']}. Use only information true before then.")
        else:
            lines.append("The founding date isn't given: establish it first.")
        for key, label in (("linkedin_text", "LinkedIn text pasted by the investor"),
                           ("deck_text", "Pitch deck text pasted by the investor")):
            if f.get(key):
                lines.append(f"\n{label} (treat as a source; facts in it still follow the cutoff):\n{f[key][:8000]}")
        lines.append(f"\nYou may run up to {self.max_searches} web searches.")
        return "\n".join(lines)

    async def research(self, inp: dict, ctx: Pipeline, emit: Emitter) -> Findings:
        who = inp["founder"].get("name") or inp["founder"].get("website_url") or "the founder"
        cutoff = inp.get("founding_date")
        await emit("stage", f"Researching {who} (" + (f"information from before {cutoff} only)." if cutoff
                   else "finding the founding date first)."), stage="researching")
        if self.budget.exhausted:
            note = (f"The research budget (AGENT_BUDGET_USD ${self.budget.total_usd:.2f}) is used up, so no research "
                    "ran and only your fields were used.")
            await emit("warning", note, data={"code": "research_partial", "message": note})
            return Findings(ran=False, note=note)

        self.budget.runs += 1
        messages: list = [{"role": "user", "content": self.user_message(inp)}]
        run_usd, nudged = 0.0, False
        for turn in range(MAX_TURNS):
            msg = await self._call(messages, emit)
            # No names in logs or the spend record: hosting logs outlive the session.
            run_usd += self.budget.charge(msg.usage, msg.model, label="research")
            log.info("agent turn %d: %s, run $%.3f, total $%.3f", turn, msg.stop_reason, run_usd,
                     self.budget.spent_usd)
            if msg.stop_reason == "refusal":
                return await self._partial(emit, "The research model declined this request, so only your fields were used.")
            submit = next((b for b in msg.content if b.type == "tool_use" and b.name == "submit_profile"), None)
            if submit is not None:
                payload = submit.input if isinstance(submit.input, dict) else None
                errors = [] if payload is None else [e.message for e in self._validate.iter_errors(payload)]
                if payload is not None and not errors:
                    return await self._findings(payload, inp, ctx, emit, run_usd)
                if turn + 1 >= MAX_TURNS or run_usd >= self.budget.per_founder_usd:
                    break
                messages += [{"role": "assistant", "content": msg.content},
                             {"role": "user", "content": [{"type": "tool_result", "tool_use_id": submit.id, "is_error": True,
                                                           "content": "Invalid input: " + "; ".join((errors or ["not valid JSON"])[:5])
                                                           + ". Call submit_profile again with corrected input."}]}]
                continue
            if run_usd >= self.budget.per_founder_usd:
                break
            messages.append({"role": "assistant", "content": msg.content})
            if msg.stop_reason == "pause_turn":
                continue  # the server resumes its own tool loop; don't add a user message
            if nudged and msg.stop_reason == "end_turn":
                break
            near_cap = run_usd >= 0.7 * self.budget.per_founder_usd
            messages.append({"role": "user", "content": (
                "Stop searching now and call submit_profile with what you have; use unknown for anything unconfirmed."
                if near_cap else "Call submit_profile now with your findings.")})
            nudged = True
        return await self._partial(emit, f"Research stopped before finishing (spent ${run_usd:.2f} of the "
                                         f"${self.budget.per_founder_usd:.2f} per-founder cap), so only your fields were used.")

    async def _call(self, messages: list, emit: Emitter):
        kwargs = dict(
            model=self.model, max_tokens=self.max_tokens,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=messages, tools=self.tools(), output_config={"effort": self.effort},
            betas=[FALLBACK_BETA], fallbacks="default", cache_control={"type": "ephemeral"},
        )
        async with self.client.beta.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type != "content_block_stop":
                    continue
                block = event.content_block
                if block.type == "server_tool_use" and block.name == "web_search":
                    q = (block.input or {}).get("query", "")
                    await emit("search", f"Searching: {q}"[:300], data={"query": q})
                elif block.type == "server_tool_use" and block.name == "web_fetch":
                    url = (block.input or {}).get("url", "")
                    await emit("search", f"Reading {urlparse(url).netloc or url}"[:300], data={"query": url})
            return await stream.get_final_message()

    async def _partial(self, emit: Emitter, note: str) -> Findings:
        await emit("warning", note, data={"code": "research_partial", "message": note})
        return Findings(ran=False, note=note)

    async def _findings(self, payload: dict, inp: dict, ctx: Pipeline, emit: Emitter, run_usd: float) -> Findings:
        """Agent output -> Findings, enforcing the cutoff, the confidence floor and the allowed values."""
        sources: list[dict] = []
        by_url: dict[str, dict] = {}
        now = ctx.now()

        def source(url: str | None, *, title: str = "", published=None, before=None) -> dict | None:
            """The source for a URL, added if new. A URL the agent cited but didn't list is 'unverified' (None)."""
            if not url:
                return None
            key = url.rstrip("/")
            if key not in by_url:
                by_url[key] = {"id": f"s{len(sources) + 1}", "url": url,
                               "title": (title or urlparse(url).netloc or url)[:300],
                               "publisher": urlparse(url).netloc or None, "published_date": published,
                               "accessed_at": now, "before_founding": before, "used_for": []}
                sources.append(by_url[key])
            return by_url[key]

        for s in payload["sources"]:
            source(s["url"], title=s["title"], published=_date_or_none(s["published_date"]), before=s["before_founding"])

        fields, notes = {}, {}
        for key in FIELD_KEYS:
            f = payload["fields"][key]
            value, conf, label = f["value"], float(f["confidence"]), FIELD_LABELS[key]
            if value == UNKNOWN:
                if f["evidence"]:
                    notes[key] = f"Agent: {f['evidence'][:300]}"
                continue
            if conf < self.min_confidence:
                notes[key] = (f"Agent guessed {json.dumps(value)[:120]} at {conf:.0%} confidence, "
                              f"below the {self.min_confidence:.0%} floor.")
                continue
            src = source(f["source_url"])
            if src is None:
                notes[key] = "Agent gave no source, so the value wasn't used."
                continue
            if src["before_founding"] is False:
                notes[key] = "The only source describes the time after founding, so the value wasn't used."
                continue
            errs = self.contract.errors_for_def(key, value)
            if errs:
                notes[key] = f"Agent value didn't fit the template ({errs[0][:150]}), so it wasn't used."
                continue
            src["used_for"].append(key)
            fields[key] = (value, [src["id"]], round(min(max(conf, 0.0), 1.0), 2))
            await emit("field", f"{label}: " + (f"{len(value)} found." if isinstance(value, list) else f"{value}."),
                       data={"key": key, "value": value, "provenance": "agent", "source_ids": [src["id"]],
                             "confidence": fields[key][2]})

        founding = None
        fd = payload["founding_date"]
        if _date_or_none(fd["value"]):
            src = source(fd["source_url"])
            if src:
                src["used_for"].append("founding_date")
            founding = (fd["value"], [src["id"]] if src else [])
        post = []
        for n in payload["post_founding_notes"]:
            src = source(n["source_url"], before=False)
            if src:
                src["used_for"].append("notes")
            post.append({"text": n["text"][:1000], "source_ids": [src["id"]] if src else []})
        for s in sources:
            s["used_for"] = sorted(set(s["used_for"]))
        await emit("stage", f"Research done: {len(fields)} of 9 fields found from {len(sources)} sources "
                            f"(${run_usd:.2f}).", stage="researching")
        return Findings(fields=fields, sources=sources, post_founding=post, founding_date=founding,
                        field_notes=notes, names_seen=list(payload["names_seen"]), cost_usd=round(run_usd, 4),
                        research_notes=payload["research_notes"][:1000])


def _date_or_none(value) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?", value) else None
