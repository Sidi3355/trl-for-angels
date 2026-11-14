"""Render and parse the frozen founder profile template (shared/profile_template.md).

`render(fields)` turns structured template fields (the contract's `profile_fields` shape) into the exact
template text. `parse(text)` does the reverse and raises TemplateError on any line that breaks the
template, so it doubles as the grammar check for the mocks and, later, for render.py's output.

Where the template is ambiguous, this module makes a provisional choice (listed in
app/contract/README.md, "Template ambiguities") until it can be checked against real rendered
profiles from the dataset:
  - a whole unknown section renders as "- unknown" under its heading;
  - an unknown job duration renders as "unknown years";
  - several prior startups render as e.g. "2 shut down, 1 acquired under $50M";
  - several prior exits render as e.g. "1 acquisition and 1 IPO as co-founder, under $50M, over $1B".
"""

from __future__ import annotations

import re

UNKNOWN = "unknown"

FIELD_KEYS = (
    "industry", "cofounders", "background", "work_experience", "industry_experience",
    "education", "jobs", "prior_startups", "prior_exits",
)
FIELD_LABELS = {
    "industry": "Industry", "cofounders": "Co-founders", "background": "Background",
    "work_experience": "Work experience", "industry_experience": "Industry experience", "education": "Education",
    "jobs": "Jobs", "prior_startups": "Prior startups", "prior_exits": "Prior exits",
}
COFOUNDERS = ("solo", "1", "2", "3+")
BACKGROUND = ("technical", "business", "mixed", "domain specialist")
WORK_EXPERIENCE = ("<5", "5-10", "10-15", "15+")
INDUSTRY_EXPERIENCE = ("none", "some", "deep")
QS_RANK = ("top 50", "51-100", "101-300", "300+", "unranked")
COMPANY_SIZE = ("1-10", "11-50", "51-200", "201-1,000", "1,001-5,000", "5,000+")
JOB_DURATION = ("<1", "1-2", "2-3", "3-5", "5+")
VALUE_BAND = ("under $50M", "$50M-$500M", "$500M-$1B", "over $1B")
STARTUP_OUTCOME = ("shut down", "acquired", "IPO", "still operating")
EXIT_KIND = ("acquisition", "IPO")


class TemplateError(ValueError):
    """A profile that doesn't follow the frozen template."""


def _alt(values: tuple[str, ...], unknown: bool = True) -> str:
    opts = list(values) + ([UNKNOWN] if unknown else [])
    return "(?:" + "|".join(re.escape(v) for v in opts) + ")"


# ---------------------------------------------------------------------------- render

def _plural(n: int, word: str) -> str:
    return word if n == 1 else word + "s"


def _render_prior_startups(value) -> str:
    if value in ("none", UNKNOWN):
        return value
    groups: dict[tuple[str, str | None], int] = {}
    for s in value:
        key = (s["outcome"], s.get("value_band"))
        groups[key] = groups.get(key, 0) + 1
    return ", ".join(f"{n} {o}" + (f" {b}" if b else "") for (o, b), n in groups.items())


def _render_prior_exits(value) -> str:
    if value in ("none", UNKNOWN):
        return value
    counts: dict[str, int] = {}
    bands: dict[str, list[str]] = {}
    for e in value:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        bands.setdefault(e["kind"], []).append(e["value_band"])
    kinds = " and ".join(f"{n} {_plural(n, k)}" for k, n in counts.items())
    band_list = ", ".join(b for k in counts for b in bands[k])
    return f"{kinds} as co-founder, {band_list}"


def render(fields: dict) -> str:
    """Render template fields to the exact template text. Missing fields render as 'unknown'."""
    f = {k: fields.get(k, UNKNOWN) for k in FIELD_KEYS}
    lines = [
        f"This founder leads a startup in the {f['industry']} industry, founded with {f['cofounders']} co-founder(s).",
        f"Founder background: {f['background']}, {f['work_experience']} years of work experience, "
        f"{f['industry_experience']} prior experience in this startup's industry.",
        "Education:",
    ]
    if f["education"] == UNKNOWN:
        lines.append("- unknown")
    else:
        for e in f["education"]:
            lines.append(f"- {e['degree']} in {e['field']}, university ranked QS {e['qs_rank']}")
    lines.append("Jobs (oldest first):")
    if f["jobs"] == UNKNOWN:
        lines.append("- unknown")
    else:
        for j in f["jobs"]:
            lines.append(
                f"- {j['role']}, {j['company']}, {j['company_size']} employees, {j['industry']}, {j['duration']} years"
            )
    lines.append(f"Prior startups: {_render_prior_startups(f['prior_startups'])}.")
    lines.append(f"Prior exits: {_render_prior_exits(f['prior_exits'])}.")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- parse

_L1 = re.compile(
    r"^This founder leads a startup in the (?P<industry>.+) industry, founded with "
    rf"(?P<cofounders>{_alt(COFOUNDERS)}) co-founder\(s\)\.$"
)
_L2 = re.compile(
    rf"^Founder background: (?P<background>{_alt(BACKGROUND)}), "
    rf"(?P<work_experience>{_alt(WORK_EXPERIENCE)}) years of work experience, "
    rf"(?P<industry_experience>{_alt(INDUSTRY_EXPERIENCE)}) prior experience in this startup's industry\.$"
)
_EDU = re.compile(rf"^- (?P<degree>.+?) in (?P<field>.+), university ranked QS (?P<qs_rank>{_alt(QS_RANK)})$")
_JOB = re.compile(
    r"^- (?P<role>[^,]+), (?P<company>.+), "
    rf"(?P<company_size>{_alt(COMPANY_SIZE)}) employees, (?P<industry>[^,]+), "
    rf"(?P<duration>{_alt(JOB_DURATION)}) years$"
)
_STARTUP_ITEM = re.compile(
    rf"^(?P<n>[1-9][0-9]*) (?P<outcome>{_alt(STARTUP_OUTCOME, unknown=False)})"
    rf"(?: (?P<band>{_alt(VALUE_BAND, unknown=False)}))?$"
)
_EXIT_KIND = re.compile(r"^(?P<n>[1-9][0-9]*) (?P<kind>acquisitions?|IPOs?)$")


def _parse_prior_startups(s: str, lineno: int):
    if s in ("none", UNKNOWN):
        return s
    out = []
    for part in s.split(", "):
        m = _STARTUP_ITEM.match(part)
        if not m:
            raise TemplateError(f"line {lineno}: bad prior startup item {part!r}")
        outcome, band = m["outcome"], m["band"]
        if outcome in ("acquired", "IPO") and not band:
            raise TemplateError(f"line {lineno}: {outcome!r} needs a value band")
        if outcome in ("shut down", "still operating") and band:
            raise TemplateError(f"line {lineno}: {outcome!r} takes no value band")
        out += [{"outcome": outcome, "value_band": band}] * int(m["n"])
    return out


def _parse_prior_exits(s: str, lineno: int):
    if s in ("none", UNKNOWN):
        return s
    m = re.match(r"^(?P<kinds>.+?) as co-founder, (?P<bands>.+)$", s)
    if not m:
        raise TemplateError(f"line {lineno}: bad prior exits {s!r}")
    kinds = []
    for part in m["kinds"].split(" and "):
        km = _EXIT_KIND.match(part)
        if not km:
            raise TemplateError(f"line {lineno}: bad exit count {part!r}")
        kind = "IPO" if km["kind"].startswith("IPO") else "acquisition"
        kinds += [kind] * int(km["n"])
    bands = m["bands"].split(", ")
    if len(bands) != len(kinds) or any(b not in VALUE_BAND for b in bands):
        raise TemplateError(f"line {lineno}: exit bands {bands} don't match {len(kinds)} exit(s)")
    return [{"kind": k, "value_band": b} for k, b in zip(kinds, bands)]


def parse(text: str) -> dict:
    """Parse template text back to fields. Raises TemplateError if any line breaks the template."""
    lines = text.split("\n")
    i = 0

    def take(pattern: re.Pattern | str, what: str):
        nonlocal i
        if i >= len(lines):
            raise TemplateError(f"line {i + 1}: expected {what}, got end of text")
        line = lines[i]
        if isinstance(pattern, str):
            if line != pattern:
                raise TemplateError(f"line {i + 1}: expected {pattern!r}, got {line!r}")
            i += 1
            return None
        m = pattern.match(line)
        if not m:
            raise TemplateError(f"line {i + 1}: expected {what}, got {line!r}")
        i += 1
        return m

    out: dict = {}
    m = take(_L1, "the industry / co-founders line")
    out["industry"], out["cofounders"] = m["industry"], m["cofounders"]
    m = take(_L2, "the founder background line")
    out.update(background=m["background"], work_experience=m["work_experience"],
               industry_experience=m["industry_experience"])

    take("Education:", "'Education:'")
    if i < len(lines) and lines[i] == "- unknown":
        out["education"] = UNKNOWN
        i += 1
    else:
        edu = []
        while i < len(lines) and lines[i].startswith("- "):
            m = take(_EDU, "an education line")
            edu.append({"degree": m["degree"], "field": m["field"], "qs_rank": m["qs_rank"]})
        if not 1 <= len(edu) <= 3:
            raise TemplateError(f"education must have 1 to 3 entries, got {len(edu)}")
        out["education"] = edu

    take("Jobs (oldest first):", "'Jobs (oldest first):'")
    if i < len(lines) and lines[i] == "- unknown":
        out["jobs"] = UNKNOWN
        i += 1
    else:
        jobs = []
        while i < len(lines) and lines[i].startswith("- "):
            m = take(_JOB, "a job line")
            jobs.append({k: m[k] for k in ("role", "company", "company_size", "industry", "duration")})
        if not 1 <= len(jobs) <= 6:
            raise TemplateError(f"jobs must have 1 to 6 entries, got {len(jobs)}")
        out["jobs"] = jobs

    m = take(re.compile(r"^Prior startups: (?P<v>.+)\.$"), "the prior startups line")
    out["prior_startups"] = _parse_prior_startups(m["v"], i)
    m = take(re.compile(r"^Prior exits: (?P<v>.+)\.$"), "the prior exits line")
    out["prior_exits"] = _parse_prior_exits(m["v"], i)
    if i != len(lines):
        raise TemplateError(f"line {i + 1}: unexpected text after 'Prior exits': {lines[i]!r}")
    return out


# ------------------------------------------------------------------ consistency checks

def unknown_paths(fields: dict) -> list[str]:
    """Field paths whose value is 'unknown' (whole fields, or sub-fields of education and jobs)."""
    paths = []
    for k in FIELD_KEYS:
        v = fields.get(k, UNKNOWN)
        if v == UNKNOWN:
            paths.append(k)
        elif k in ("education", "jobs"):
            for idx, entry in enumerate(v):
                paths += [f"{k}[{idx}].{sub}" for sub, sv in entry.items() if sv == UNKNOWN]
    return paths


_DURATION_MID = {"<1": 0.5, "1-2": 1.5, "2-3": 2.5, "3-5": 4, "5+": 6}
_EXPERIENCE_RANGE = {"<5": (0, 5), "5-10": (5, 10), "10-15": (10, 15), "15+": (15, 60)}


def consistency_issues(fields: dict) -> list[str]:
    """The template's internal-consistency rules that can be checked mechanically (plan 10a)."""
    issues = []
    startups, exits = fields.get("prior_startups"), fields.get("prior_exits")
    if isinstance(exits, list):
        if not isinstance(startups, list):
            issues.append("prior exits listed but prior startups are not")
        else:
            exited = [s["value_band"] for s in startups if s["outcome"] in ("acquired", "IPO")]
            if len(exits) > len(exited):
                issues.append("more prior exits than acquired or IPO'd prior startups")
            else:
                for e in exits:
                    if e["value_band"] in exited:
                        exited.remove(e["value_band"])
                    else:
                        issues.append(f"prior exit band {e['value_band']} matches no prior startup outcome")
    jobs, exp = fields.get("jobs"), fields.get("work_experience")
    if isinstance(jobs, list) and exp in _EXPERIENCE_RANGE and all(j["duration"] in _DURATION_MID for j in jobs):
        total = sum(_DURATION_MID[j["duration"]] for j in jobs)
        lo, hi = _EXPERIENCE_RANGE[exp]
        if not lo - 2.5 <= total <= hi + 2.5:
            issues.append(f"job durations sum to about {total:g} years, outside work experience band {exp}")
    return issues
