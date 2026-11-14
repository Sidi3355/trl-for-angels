"""Anonymise merged fields, then render the frozen template (MASTER_PLAN section 8, step 3).

The model is trained on fully anonymised profiles: no names of people, companies, products or
universities. The agent is told to write generic descriptions, but this step doesn't trust it:
every free-text value is checked against the names seen during research (plus the founder's and
company's names), and any match is removed before rendering. A final check refuses to return a
rendered profile that still contains one.
"""

from __future__ import annotations

import copy
import re

from ..template import UNKNOWN, render

MIN_NAME_LEN = 3
# Words that are names of things in the template itself, so never treated as leaks.
SAFE_WORDS = {"unknown", "none", "solo", "technical", "business", "mixed"}


class AnonymisationError(RuntimeError):
    pass


def names_to_redact(founder: dict, seen: list[str] | None) -> list[str]:
    """Founder and company names (and their parts), plus every name the agent reported seeing."""
    names = set()
    for raw in [founder.get("name"), founder.get("company_name"), *(seen or [])]:
        if not raw:
            continue
        raw = raw.strip()
        names.add(raw)
        if raw == founder.get("name"):  # 'Ada Moreno' -> also 'Moreno' (a first name alone is too common)
            parts = raw.split()
            if len(parts) > 1:
                names.add(parts[-1])
    return sorted((n for n in names if len(n) >= MIN_NAME_LEN and n.lower() not in SAFE_WORDS), key=len, reverse=True)


def _pattern(names: list[str]) -> re.Pattern | None:
    if not names:
        return None
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(n) for n in names) + r")(?![\w])", re.IGNORECASE)


def _scrub(text: str, pat: re.Pattern, generic: str) -> tuple[str, list[str]]:
    hits = [m.group(0) for m in pat.finditer(text)]
    if not hits:
        return text, []
    cleaned = pat.sub("", text)
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned)
    cleaned = re.sub(r"\s+([,.)])", r"\1", cleaned)
    cleaned = re.sub(r"\b(at|of|for|from)\s*$", "", cleaned.strip(), flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,-–")
    return (cleaned if len(cleaned) >= 3 else generic), hits


def anonymise(fields: dict, names: list[str]) -> tuple[dict, list[dict]]:
    """Remove names from free-text template values. Returns (fields, redactions)."""
    pat = _pattern(names)
    out = copy.deepcopy(fields)
    redactions: list[dict] = []
    if pat is None:
        return out, redactions

    def fix(path: str, text: str, generic: str) -> str:
        if text == UNKNOWN:
            return text
        new, hits = _scrub(text, pat, generic)
        if hits:
            redactions.append({"path": path, "removed": sorted(set(hits)), "now": new})
        return new

    if out["industry"]["value"] != UNKNOWN:
        out["industry"]["value"] = fix("industry", out["industry"]["value"], UNKNOWN)
    for key, generic in (("education", {"degree": UNKNOWN, "field": UNKNOWN}),
                         ("jobs", {"role": UNKNOWN, "company": "a company", "industry": UNKNOWN})):
        value = out[key]["value"]
        if isinstance(value, list):
            for i, entry in enumerate(value):
                for sub, fallback in generic.items():
                    entry[sub] = fix(f"{key}[{i}].{sub}", entry[sub], fallback)
    for r in redactions:
        top = r["path"].split("[")[0]
        note = out[top].get("note") or ""
        out[top]["note"] = (note + " " if note else "") + "A real name was removed to keep the profile anonymous."
    return out, redactions


def render_anonymous(values: dict, names: list[str]) -> str:
    """Render the template, refusing any output that still contains a name to redact."""
    text = render(values)
    pat = _pattern(names)
    if pat and (m := pat.search(text)):
        raise AnonymisationError(f"rendered profile still contains a name ({m.group(0)!r})")
    return text
