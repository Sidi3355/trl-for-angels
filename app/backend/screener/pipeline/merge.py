"""Merge investor fields with the agent's findings (MASTER_PLAN section 8, step 2).

- Investor values take precedence ('investor', or 'investor_voice' for fields from a voice note).
- An agent value that contradicts an investor value becomes a conflict, never a silent overwrite.
- An agent value that agrees is kept as corroboration (its sources are cited).
- Everything else the agent found is used with provenance 'agent'; the rest is 'unknown'.
- education and jobs merge as whole lists: entries can't be matched reliably between the two.
"""

from __future__ import annotations

from ..template import FIELD_KEYS, UNKNOWN
from .research import Findings


def merge(inp: dict, findings: Findings) -> tuple[dict, list[dict]]:
    """Returns (fields with provenance, conflicts)."""
    investor = {k: v for k, v in (inp.get("fields") or {}).items() if v != UNKNOWN}
    voice = set(inp.get("voice_fields") or [])
    fields, conflicts = {}, []
    for key in FIELD_KEYS:
        agent = findings.fields.get(key)
        agent_ok = agent is not None and agent[0] != UNKNOWN
        if key in investor:
            entry = {"value": investor[key], "provenance": "investor_voice" if key in voice else "investor",
                     "source_ids": [], "confidence": None}
            if agent_ok and agent[0] == investor[key]:
                entry["source_ids"] = list(agent[1])
                entry["note"] = "The agent found the same value."
            elif agent_ok:
                conflicts.append({
                    "field": key, "investor_value": investor[key], "agent_value": agent[0],
                    "agent_source_ids": list(agent[1]), "resolution": "investor_value_used",
                    "note": f"Agent confidence {agent[2]:.0%}.",
                })
            fields[key] = entry
        elif agent_ok:
            fields[key] = {"value": agent[0], "provenance": "agent", "source_ids": list(agent[1]), "confidence": agent[2]}
        else:
            fields[key] = {"value": UNKNOWN, "provenance": "unknown", "source_ids": [], "confidence": None}
            if findings.field_notes.get(key):
                fields[key]["note"] = findings.field_notes[key][:500]
    return fields, conflicts


def founding_date(inp: dict, findings: Findings, today: str) -> dict:
    """Investor date first, then the agent's, else today's date (assumed, with a warning)."""
    if inp.get("founding_date"):
        prov = "investor_voice" if "founding_date" in (inp.get("voice_fields") or []) else "investor"
        return {"value": inp["founding_date"], "provenance": prov, "source_ids": []}
    if findings.founding_date:
        return {"value": findings.founding_date[0], "provenance": "agent", "source_ids": list(findings.founding_date[1])}
    return {"value": today[:10], "provenance": "assumed", "source_ids": []}
