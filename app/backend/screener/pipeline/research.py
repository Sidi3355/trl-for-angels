"""Research agent: fills template fields from public, pre-founding information.

AGENT=mock (default): serves canned findings for the three demo founders and finds nothing for anyone
else, while streaming realistic progress events. AGENT=claude: the Claude API with web search (pipeline/agent.py).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..mocks.founders import find_demo_founder
from ..template import FIELD_LABELS
from .context import Emitter, Pipeline


@dataclass
class Findings:
    """What the agent found. fields: key -> (value, source_ids, confidence)."""
    fields: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)
    post_founding: list = field(default_factory=list)
    founding_date: tuple | None = None  # (value, source_ids)
    ran: bool = True
    note: str | None = None
    field_notes: dict = field(default_factory=dict)  # key -> why a field stayed unknown
    names_seen: list = field(default_factory=list)  # real names to keep out of the profile
    cost_usd: float = 0.0
    research_notes: str | None = None


def _field_message(key: str, value) -> str:
    label = FIELD_LABELS[key]
    if isinstance(value, list):
        return f"{label}: {len(value)} found."
    if key == "work_experience":
        return f"{label}: {value} years."
    return f"{label}: {value}."


class MockAgent:
    name = "mock"

    async def research(self, inp: dict, ctx: Pipeline, emit: Emitter) -> Findings:
        who = inp["founder"].get("name") or inp["founder"].get("website_url") or inp["founder"].get("linkedin_url") or "the founder"
        spec = find_demo_founder(inp["founder"])
        cutoff = inp.get("founding_date") or (spec["findings"]["founding_date"][0] if spec else None)
        when = f"information from before {cutoff} only" if cutoff else "looking for the founding date first"
        await emit("stage", f"Researching {who} ({when}).", stage="researching")
        await ctx.sleep(0.4)
        if spec is None:
            note = "Mock mode: no live research runs, so only your fields were used."
            await emit("warning", note, data={"code": "research_partial", "message": note})
            return Findings(ran=False, note=note)

        f = copy.deepcopy(spec["findings"])
        sources = [{**s, "accessed_at": ctx.now()} for s in f["sources"]]
        searches = list(f["searches"])
        emitted = set()
        for src in sources:
            if searches:
                q = searches.pop(0)
                await emit("search", f"Searching: {q}", data={"query": q})
                await ctx.sleep(0.5)
            if src["before_founding"] is False:
                await emit("source", f"Found {src['title']}: from after founding, so memo notes only.", data={"source": src})
                await ctx.sleep(0.3)
                continue
            await emit("source", f"Found {src['title']}.", data={"source": src})
            await ctx.sleep(0.3)
            for key, (value, sids, conf) in f["fields"].items():
                if key not in emitted and sids and sids[0] == src["id"]:
                    emitted.add(key)
                    await emit("field", _field_message(key, value), data={
                        "key": key, "value": value, "provenance": "agent", "source_ids": sids, "confidence": conf})
                    await ctx.sleep(0.25)
        return Findings(fields=f["fields"], sources=sources, post_founding=f["post_founding"],
                        founding_date=tuple(f["founding_date"]) if f.get("founding_date") else None)
