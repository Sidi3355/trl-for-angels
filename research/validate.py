"""Parse and validate Adaption founder records against MASTER_PLAN sections 5 and 10.

Usage:
    python research/validate.py data/raw/sample50.jsonl --profile sample50
    python research/validate.py data/raw/full.jsonl --profile full

Writes a Markdown report (default: results/data/validation_<file stem>.md) and a JSON
summary next to it, prints a short verdict, and exits 1 if any hard check fails.

Checks are of two kinds:
- FAIL: a hard rule is broken (format, counts, allowed values, banned words, names, dates).
- WARN: something to review by eye (heuristics such as consistency and leakage signals).
Some rules can't be checked by a script (realism, "surprising" records, whether a real
company's outcome is correct). The report lists them for the user's review.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Allowed values (section 10 template and labels)
# ---------------------------------------------------------------------------

OUTCOMES = ("shut down", "under $50m", "$50m-$500m", "$500m-$1b", "over $1b")
OUTCOME_LABELS = {  # normalised -> canonical
    "shut down": "shut down",
    "under $50m": "under $50M",
    "$50m-$500m": "$50M-$500M",
    "$500m-$1b": "$500M-$1B",
    "over $1b": "over $1B",
}
STRONG = {"$500M-$1B", "over $1B"}  # research label "yes"
YEARS = ("under 5", "5-8", "over 8")

INSTRUCTION = (
    "Based on this founder's profile at the time of founding, predict the company's "
    "outcome and how long it took."
)

COFOUNDERS = ("solo", "1", "2", "3+")
BACKGROUNDS = ("technical", "business", "mixed", "domain specialist")
EXPERIENCE = ("<5", "5-10", "10-15", "15+")
INDUSTRY_EXP = ("none", "some", "deep")
QS = ("top 50", "51-100", "101-300", "300+", "unranked")
SIZES = ("1-10", "11-50", "51-200", "201-1,000", "1,001-5,000", "5,000+")
DURATIONS = ("<1", "1-2", "2-3", "3-5", "5+")
UNKNOWN = "unknown"

# Bounds in years, for the "experience matches job durations" check.
EXPERIENCE_BOUNDS = {"<5": (0, 5), "5-10": (5, 10), "10-15": (10, 15), "15+": (15, 60)}
DURATION_BOUNDS = {"<1": (0, 1), "1-2": (1, 2), "2-3": (2, 3), "3-5": (3, 5), "5+": (5, 30)}
EXPERIENCE_SLACK = 2.0  # "roughly match": gaps, part-time work, rounding

PROFILES = {
    "sample50": {
        "rows": 50,
        "counts": {
            "shut down": 25,
            "under $50M": 8,
            "$50M-$500M": 7,
            "$500M-$1B": 5,
            "over $1B": 5,
        },
        "count_tolerance_pp": 0.0,  # exact counts
        "min_industries": 15,
        "unknown_records": (8, 8),  # exactly 8
    },
    "full": {
        "rows": 3000,
        "counts": {
            "shut down": 1500,
            "under $50M": 450,
            "$50M-$500M": 450,
            "$500M-$1B": 300,
            "over $1B": 300,
        },
        "count_tolerance_pp": 3.0,  # A5 "done when": within about 3 points
        "min_industries": 25,
        "unknown_records": (0.10, 0.20),  # "about 15%", as shares
        "max_drop_share": 0.02,  # A5: under 2% of rows dropped
        "batch": 50,
        "min_industries_per_batch": 15,
    },
}

# Banned evaluative words (10a, "AVOID STEREOTYPES" 4) and similar ones to review.
BANNED_WORDS = re.compile(
    r"\b(exceptional\w*|prestigious\w*|visionar\w*|strong\w*|struggl\w*|successful\w*)\b",
    re.IGNORECASE,
)
REVIEW_WORDS = re.compile(
    r"\b(renowned|elite|top-tier|world-class|brilliant|talented|impressive|outstanding|"
    r"distinguished|accomplished|notable|celebrated|star|rockstar|leading|top-performing|"
    r"failed|failure|unsuccessful|poor|weak|mediocre|award-winning|famous|iconic|"
    r"successfully|success)\b",
    re.IGNORECASE,
)

# Anonymisation (10a, "PROFILE RULES" 2): obvious names, places and dates.
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
MONTH_RE = re.compile(
    r"\b(January|February|March|April|June|July|August|September|October|November|"
    r"December)\b"
)
URL_RE = re.compile(r"(https?://|www\.|\.com\b|\.io\b|@)", re.IGNORECASE)
NAMED_ORG_RE = re.compile(
    r"\b(University of [A-Z]\w+|[A-Z]\w+ University|Institute of Technology|"
    r"[A-Z]\w+ (Inc|Ltd|LLC|GmbH|Corp)\b\.?)"
)
# A deliberately small list of names that commonly slip through generic descriptions.
NAMED_ENTITIES = (
    "Google", "Alphabet", "Amazon", "AWS", "Facebook", "Meta", "Microsoft", "Apple",
    "Netflix", "Uber", "Lyft", "Airbnb", "Stripe", "PayPal", "Tesla", "SpaceX", "IBM",
    "Oracle", "Intel", "Nvidia", "Salesforce", "LinkedIn", "Twitter", "Yahoo", "eBay",
    "Goldman Sachs", "Morgan Stanley", "JPMorgan", "J.P. Morgan", "McKinsey", "Bain",
    "BCG", "Boston Consulting", "Deloitte", "Accenture", "KPMG", "PwC", "Y Combinator",
    "Techstars", "Stanford", "Harvard", "MIT", "Berkeley", "Oxford", "Cambridge",
    "Princeton", "Yale", "Columbia", "Wharton", "INSEAD", "Caltech", "Carnegie Mellon",
    "IIT", "Tsinghua", "Peking University", "ETH",
    "Silicon Valley", "San Francisco", "New York", "London", "Berlin", "Paris",
    "Bangalore", "Bengaluru", "Singapore", "Tel Aviv", "Beijing", "Shanghai", "Tokyo",
    "Toronto", "Boston", "Seattle", "Los Angeles", "Chicago", "Austin", "Stockholm",
    "Amsterdam", "Dublin", "Sydney", "Lagos", "Nairobi", "São Paulo", "Mexico City",
    "United States", "USA", "U.S.", "America", "American", "Canada", "Canadian",
    "United Kingdom", "UK", "British", "Germany", "German", "France", "French", "India",
    "Indian", "China", "Chinese", "Israel", "Israeli", "Japan", "Japanese", "Brazil",
    "Nigeria", "Kenya", "Australia", "Europe", "European", "Asia", "Africa",
)
NAMED_ENTITY_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(n) for n in NAMED_ENTITIES) + r")(?![\w-])"
)
# Post-founding information (10a, "PROFILE RULES" 1) that may leak the label.
FUTURE_RE = re.compile(
    r"\b(this startup|the startup|current company|raised|funding round|series [a-e]\b|"
    r"valuation|unicorn|went public|acquired by|after founding|later)\b",
    re.IGNORECASE,
)

TECH_HINTS = re.compile(
    r"\b(engineer\w*|develop\w*|software|computer|comput\w*|data|scien\w*|research\w*|"
    r"physic\w*|math\w*|statistic\w*|electrical|mechanical|chemi\w*|bio\w*|"
    r"programm\w*|architect|technical|cto|machine learning|ml|ai|robotic\w*|devops|"
    r"security|firmware|hardware)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Parsed record
# ---------------------------------------------------------------------------


@dataclass
class Education:
    degree: str
    field: str
    qs: str


@dataclass
class Job:
    role: str
    company: str
    size: str
    industry: str
    duration: str


@dataclass
class Profile:
    industry: str
    cofounders: str
    background: str
    experience: str
    industry_experience: str
    education: list[Education] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    prior_startups: str = ""
    prior_startups_n: int | None = None  # None if unknown
    prior_exits: str = ""
    prior_exits_n: int | None = None
    unknown_fields: list[str] = field(default_factory=list)


@dataclass
class Record:
    row: int  # 1-based position in the file
    instruction: str
    input: str
    output: str
    outcome: str | None = None  # canonical band
    years: str | None = None
    profile: Profile | None = None
    errors: list[str] = field(default_factory=list)  # FAIL-level, per record
    warnings: list[str] = field(default_factory=list)  # WARN-level, per record

    @property
    def strong(self) -> bool:
        return self.outcome in STRONG


# ---------------------------------------------------------------------------
# Loading and normalising
# ---------------------------------------------------------------------------


def normalise(text: str) -> str:
    """Dashes to '-', whitespace collapsed, lowercased (section 5 matching rules)."""
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean_lines(text: str) -> list[str]:
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]


def load(path: Path) -> list[dict[str, str]]:
    """Rows as dicts from .jsonl, .json (a list, or {"data": [...]}) or .csv."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [data])
        return list(data)
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                rows.append({"__error__": f"line {i}: invalid JSON ({exc.msg})"})
    return rows


def _field(row: dict[str, str], name: str) -> str:
    """A field by name, case-insensitively; '' if missing."""
    for key, value in row.items():
        if key.strip().lower() == name:
            return "" if value is None else str(value)
    return ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

LINE1_RE = re.compile(
    r"^This founder leads a startup in the (?P<industry>.+?) industry, founded with "
    r"(?P<cofounders>\S+) co-founder\(s\)\.$"
)
LINE2_RE = re.compile(
    r"^Founder background: (?P<background>.+?), (?P<experience>\S+) years of work "
    r"experience, (?P<industry_exp>\S+) prior experience in this startup's industry\.$"
)
EDU_RE = re.compile(
    r"^- (?P<degree>.+?)(?: in (?P<field>.+?))?, university ranked QS (?P<qs>.+?)\.?$"
)
NO_DEGREE_RE = re.compile(r"^- no degree(?P<rest>.*)$", re.IGNORECASE)
SIZE_RE = re.compile(r"^(?P<size>.+?) employees$")
DURATION_RE = re.compile(r"^(?P<duration><1|1-2|2-3|3-5|5\+|unknown)(?: years?)?\.?$")
STARTUPS_RE = re.compile(r"^Prior startups: (?P<value>.+?)\.?$")
EXITS_RE = re.compile(r"^Prior exits: (?P<value>.+?)\.?$")
LEADING_INT_RE = re.compile(r"^(\d+)\b")
THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}\b)")


def parse_output(output: str) -> tuple[str | None, str | None, str | None]:
    """(outcome, years, error). Exactly two lines, 'outcome: ...' then 'years: ...'."""
    lines = [normalise(ln) for ln in output.strip().splitlines() if ln.strip()]
    if len(lines) != 2:
        return None, None, f"output has {len(lines)} non-empty lines, expected 2"
    m1 = re.fullmatch(r"outcome: (.+)", lines[0])
    m2 = re.fullmatch(r"years: (.+)", lines[1])
    if not m1 or not m2:
        return None, None, "output lines are not 'outcome: ...' then 'years: ...'"
    outcome, years = m1.group(1).rstrip("."), m2.group(1).rstrip(".")
    if outcome not in OUTCOME_LABELS:
        return None, None, f"unknown outcome {outcome!r}"
    if years not in YEARS:
        return None, None, f"unknown years {years!r}"
    return OUTCOME_LABELS[outcome], years, None


def _check_value(value: str, allowed: tuple[str, ...], name: str, rec: Record,
                 unknowns: list[str]) -> str:
    v = value.strip().lower()
    if v == UNKNOWN:
        unknowns.append(name)
        return UNKNOWN
    if v not in allowed:
        rec.errors.append(f"{name}: {value!r} is not one of {', '.join(allowed)}")
    return v


def _count(value: str, name: str, rec: Record) -> int | None:
    v = value.strip().lower()
    if v == UNKNOWN:
        return None
    if v == "none":
        return 0
    m = LEADING_INT_RE.match(v)
    if not m:
        rec.errors.append(f"{name}: {value!r} should be 'none', 'unknown' or start with N")
        return None
    return int(m.group(1))


def parse_input(text: str, rec: Record) -> Profile | None:
    """The founder profile, or None if the template's fixed lines are missing."""
    lines = _clean_lines(text)
    if len(lines) < 6:
        rec.errors.append(f"input has {len(lines)} lines; the template needs at least 6")
        return None
    unknowns: list[str] = []

    m1 = LINE1_RE.match(lines[0])
    m2 = LINE2_RE.match(lines[1])
    if not m1:
        rec.errors.append("line 1 doesn't match 'This founder leads a startup in the ...'")
    if not m2:
        rec.errors.append("line 2 doesn't match 'Founder background: ...'")
    if not (m1 and m2):
        return None

    profile = Profile(
        industry=m1["industry"].strip(),
        cofounders=_check_value(m1["cofounders"], COFOUNDERS, "co-founders", rec, unknowns),
        background=_check_value(m2["background"], BACKGROUNDS, "background", rec, unknowns),
        experience=_check_value(m2["experience"], EXPERIENCE, "experience", rec, unknowns),
        industry_experience=_check_value(
            m2["industry_exp"], INDUSTRY_EXP, "industry experience", rec, unknowns
        ),
    )
    if profile.industry.lower() == UNKNOWN:
        unknowns.append("industry")

    try:
        edu_at = next(i for i, ln in enumerate(lines) if ln == "Education:")
        jobs_at = next(i for i, ln in enumerate(lines) if ln == "Jobs (oldest first):")
        st_at = next(i for i, ln in enumerate(lines) if ln.startswith("Prior startups:"))
        ex_at = next(i for i, ln in enumerate(lines) if ln.startswith("Prior exits:"))
    except StopIteration:
        rec.errors.append(
            "missing one of 'Education:', 'Jobs (oldest first):', 'Prior startups:', "
            "'Prior exits:'"
        )
        return None
    if not (1 < edu_at < jobs_at < st_at < ex_at):
        rec.errors.append("template sections are out of order")
        return None
    if ex_at != len(lines) - 1:
        rec.errors.append(f"{len(lines) - 1 - ex_at} extra line(s) after 'Prior exits:'")
    if edu_at != 2:
        rec.errors.append("extra line(s) between line 2 and 'Education:'")

    for ln in lines[edu_at + 1 : jobs_at]:
        if (nd := NO_DEGREE_RE.match(ln)) and "university ranked" not in ln:
            profile.education.append(Education("no degree", nd["rest"].strip(" ,."), ""))
            continue
        m = EDU_RE.match(ln)
        if not m:
            rec.errors.append(f"education line doesn't match the template: {ln!r}")
            continue
        qs = _check_value(m["qs"], QS, "QS band", rec, unknowns)
        profile.education.append(Education(m["degree"].strip(), (m["field"] or "").strip(), qs))

    for ln in lines[jobs_at + 1 : st_at]:
        if not ln.startswith("- "):
            rec.errors.append(f"job line doesn't start with '- ': {ln!r}")
            continue
        # Sizes like "1,001-5,000" contain thousands commas: protect them, then split.
        protected = THOUSANDS_RE.sub("\x00", ln[2:])
        parts = [p.strip().replace("\x00", ",") for p in protected.split(",")]
        if len(parts) < 5:
            rec.errors.append(f"job line has fewer than 5 comma-separated parts: {ln!r}")
            continue
        duration_m = DURATION_RE.match(parts[-1])
        size_part = parts[-3]
        size_m = SIZE_RE.match(size_part)
        if not duration_m:
            rec.errors.append(f"job duration {parts[-1]!r} is not one of {', '.join(DURATIONS)}")
            duration = parts[-1]
        else:
            duration = duration_m["duration"]
            if duration == UNKNOWN:
                unknowns.append("job duration")
        if not size_m:
            rec.errors.append(f"job size {size_part!r} doesn't end in 'employees'")
            size = size_part
        else:
            size = _check_value(size_m["size"], SIZES, "employees", rec, unknowns)
        role, company = parts[0], ", ".join(parts[1:-3])
        profile.jobs.append(Job(role, company, size, parts[-2], duration))

    if not 1 <= len(profile.education) <= 3:
        rec.errors.append(f"{len(profile.education)} education entries, expected 1 to 3")
    if not 1 <= len(profile.jobs) <= 6:
        rec.errors.append(f"{len(profile.jobs)} jobs, expected 1 to 6")

    st = STARTUPS_RE.match(lines[st_at])
    ex = EXITS_RE.match(lines[ex_at])
    profile.prior_startups = st["value"] if st else lines[st_at]
    profile.prior_exits = ex["value"] if ex else lines[ex_at]
    profile.prior_startups_n = _count(profile.prior_startups, "prior startups", rec)
    profile.prior_exits_n = _count(profile.prior_exits, "prior exits", rec)
    if profile.prior_startups.lower() == UNKNOWN:
        unknowns.append("prior startups")
    if profile.prior_exits.lower() == UNKNOWN:
        unknowns.append("prior exits")

    profile.unknown_fields = unknowns
    return profile


def parse_record(row: dict[str, str], index: int) -> Record:
    rec = Record(
        row=index,
        instruction=_field(row, "instruction"),
        input=_field(row, "input"),
        output=_field(row, "output"),
    )
    if "__error__" in row:
        rec.errors.append(row["__error__"])
        return rec
    rec.outcome, rec.years, err = parse_output(rec.output)
    if err:
        rec.errors.append(f"output: {err}")
    if not rec.input.strip():
        rec.errors.append("input is empty")
    else:
        rec.profile = parse_input(rec.input, rec)
    return rec


# ---------------------------------------------------------------------------
# Per-record content checks
# ---------------------------------------------------------------------------


def _industry_tokens(text: str) -> set[str]:
    stop = {"and", "the", "a", "an", "of", "services", "tech", "technology", "industry"}
    return {t for t in re.findall(r"[a-z]+", text.lower()) if t not in stop and len(t) > 2}


def check_record(rec: Record) -> None:
    text = rec.input
    if normalise(rec.instruction) != normalise(INSTRUCTION):
        rec.warnings.append("instruction differs from the fixed instruction text")
    for m in BANNED_WORDS.finditer(text):
        rec.errors.append(f"evaluative word {m.group(0)!r}")
    for m in REVIEW_WORDS.finditer(text):
        rec.warnings.append(f"possibly evaluative word {m.group(0)!r}")
    for m in YEAR_RE.finditer(text):
        rec.errors.append(f"exact year {m.group(0)!r}")
    for m in MONTH_RE.finditer(text):
        rec.warnings.append(f"month name {m.group(0)!r} (exact date?)")
    for m in URL_RE.finditer(text):
        rec.errors.append(f"URL, domain or handle {m.group(0)!r}")
    for m in NAMED_ORG_RE.finditer(text):
        rec.errors.append(f"named organisation {m.group(0)!r}")
    for m in NAMED_ENTITY_RE.finditer(text):
        rec.errors.append(f"named person, place or organisation {m.group(0)!r}")
    # The template's own wording mentions "this startup"; only free text is checked.
    free_text = text.replace("prior experience in this startup's industry", "")
    for m in FUTURE_RE.finditer(free_text):
        rec.warnings.append(f"possible post-founding information {m.group(0)!r}")

    p = rec.profile
    if p is None:
        return
    if len(p.unknown_fields) > 2:
        rec.errors.append(f"{len(p.unknown_fields)} unknown fields; at most 2 allowed")

    for job in p.jobs:
        company = job.company.strip()
        if company and not re.match(r"^(a|an|the|unknown)\b", company, re.IGNORECASE):
            rec.warnings.append(f"employer {company!r} isn't a generic description ('a ...')")
        if re.search(r"\b(co-?founder|founder)\b", job.role, re.IGNORECASE) and \
                (p.prior_startups_n == 0):
            rec.warnings.append(
                f"job {job.role!r} looks like a founder role but prior startups is none"
            )

    # Consistency 1: experience ~ sum of job durations.
    if p.experience in EXPERIENCE_BOUNDS and p.jobs and all(
        j.duration in DURATION_BOUNDS for j in p.jobs
    ):
        lo = sum(DURATION_BOUNDS[j.duration][0] for j in p.jobs)
        hi = sum(DURATION_BOUNDS[j.duration][1] for j in p.jobs)
        e_lo, e_hi = EXPERIENCE_BOUNDS[p.experience]
        if lo > e_hi + EXPERIENCE_SLACK or hi < e_lo - EXPERIENCE_SLACK:
            rec.warnings.append(
                f"experience {p.experience} years vs jobs summing to {lo:g}-{hi:g} years"
            )

    # Consistency 2: prior exits vs prior startups.
    if p.prior_exits_n is not None and p.prior_startups_n is not None:
        if p.prior_exits_n > p.prior_startups_n:
            rec.errors.append(
                f"prior exits ({p.prior_exits_n}) exceed prior startups ({p.prior_startups_n})"
            )
        exited = len(re.findall(r"\b(acquired|acquisition|ipo)\b", p.prior_startups, re.I))
        if p.prior_exits_n > 0 and exited < p.prior_exits_n:
            rec.warnings.append(
                f"{p.prior_exits_n} prior exit(s) but prior startups list {exited} "
                "acquisition/IPO outcome(s)"
            )
        if p.prior_exits_n == 0 and exited > 0:
            rec.warnings.append("prior startups list an acquisition/IPO but prior exits is none")
        for band in re.findall(r"(under \$\d+[mb]|\$\d+[mb]-\$\d+[mb]|over \$\d+[mb])",
                               p.prior_exits.lower()):
            if band not in p.prior_startups.lower():
                rec.warnings.append(f"exit band {band!r} isn't among the prior startup outcomes")

    # Consistency 3: technical background should show a technical degree or role.
    if p.background == "technical":
        blob = " ".join([e.field + " " + e.degree for e in p.education] +
                        [j.role for j in p.jobs])
        if not TECH_HINTS.search(blob):
            rec.warnings.append("technical background but no technical degree or role found")

    # Consistency 4: job industries vs prior experience in the startup's industry.
    target = _industry_tokens(p.industry)
    overlap = sum(1 for j in p.jobs if target & _industry_tokens(j.industry + " " + j.company))
    if p.industry_experience == "none" and overlap:
        rec.warnings.append(
            f"industry experience 'none' but {overlap} job(s) look like {p.industry!r}"
        )
    if p.industry_experience == "deep" and not overlap:
        rec.warnings.append(f"industry experience 'deep' but no job looks like {p.industry!r}")


# ---------------------------------------------------------------------------
# Dataset-level checks
# ---------------------------------------------------------------------------


@dataclass
class Check:
    name: str
    status: str  # PASS, FAIL, WARN, INFO
    detail: str


def _shingles(text: str, k: int = 5) -> set[str]:
    toks = re.findall(r"\w+", text.lower())
    return {" ".join(toks[i : i + k]) for i in range(max(1, len(toks) - k + 1))}


def duplicates(records: list[Record], threshold: float = 0.8) -> tuple[list, list]:
    """Exact duplicates and near-duplicates (Jaccard of 5-word shingles >= threshold)."""
    exact: dict[str, list[int]] = defaultdict(list)
    for r in records:
        exact[normalise(r.input)].append(r.row)
    exact_groups = [rows for rows in exact.values() if len(rows) > 1]

    # Every pair, exactly: shared shingles from a sparse product. (Bucketing by a
    # few shingles misses near copies when every profile shares the template's
    # wording.) 3,000 profiles take about a second.
    import numpy as np
    from scipy import sparse

    near: list[tuple[int, int, float]] = []
    shingle_sets = [_shingles(r.input) for r in records]
    vocab: dict[str, int] = {}
    rows, cols = [], []
    for i, s in enumerate(shingle_sets):
        for g in s:
            rows.append(i)
            cols.append(vocab.setdefault(g, len(vocab)))
    if not rows:
        return exact_groups, near
    m = sparse.csr_matrix((np.ones(len(rows), dtype=np.int32), (rows, cols)),
                          shape=(len(records), len(vocab)))
    sizes = np.asarray(m.sum(axis=1)).ravel()
    shared = sparse.triu(m @ m.T, k=1).tocoo()
    union = sizes[shared.row] + sizes[shared.col] - shared.data
    jac = np.divide(shared.data, union, out=np.zeros(len(union)), where=union > 0)
    texts = [normalise(r.input) for r in records]
    for a, b, j in zip(shared.row, shared.col, jac):
        if j >= threshold and texts[a] != texts[b]:
            near.append((records[a].row, records[b].row, round(float(j), 2)))
    near.sort()
    return exact_groups, near


def career_path(p: Profile) -> tuple:
    return tuple((normalise(j.role), normalise(j.industry)) for j in p.jobs)


def single_field_signal(records: list[Record]) -> list[tuple[str, float, str]]:
    """Per field: cross-validated AUC of predicting 'strong' from that field alone.

    A high AUC means one field nearly gives the label away (a stereotype shortcut).
    """
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
        from sklearn.preprocessing import OneHotEncoder
    except ImportError:
        return []
    rows = [r for r in records if r.profile is not None and r.outcome is not None]
    y = np.array([r.strong for r in rows])
    if y.sum() < 5 or (~y).sum() < 5:
        return []

    def best_qs(p: Profile) -> str:
        order = {"top 50": 0, "51-100": 1, "101-300": 2, "300+": 3, "unranked": 4}
        ranks = [order[e.qs] for e in p.education if e.qs in order]
        return min(ranks, default=9).__str__()

    def max_size(p: Profile) -> str:
        ranks = [SIZES.index(j.size) for j in p.jobs if j.size in SIZES]
        return str(max(ranks, default=-1))

    features = {
        "co-founders": lambda p: p.cofounders,
        "background": lambda p: p.background,
        "experience": lambda p: p.experience,
        "industry experience": lambda p: p.industry_experience,
        "best university band": best_qs,
        "largest employer size": max_size,
        "number of jobs": lambda p: str(len(p.jobs)),
        "number of degrees": lambda p: str(len(p.education)),
        "has PhD": lambda p: str(any("phd" in e.degree.lower() for e in p.education)),
        "has MBA": lambda p: str(any("mba" in e.degree.lower() for e in p.education)),
        "no degree": lambda p: str(any(e.degree == "no degree" for e in p.education)),
        "prior startups": lambda p: str(min(p.prior_startups_n or 0, 3))
        if p.prior_startups_n is not None else "unknown",
        "prior exits": lambda p: str(min(p.prior_exits_n or 0, 2))
        if p.prior_exits_n is not None else "unknown",
        "has unknown field": lambda p: str(bool(p.unknown_fields)),
        "profile length (quartile)": None,  # filled below
        "industry": lambda p: p.industry.lower(),
    }
    lengths = np.array([len(r.input) for r in rows])
    quartiles = np.quantile(lengths, [0.25, 0.5, 0.75])
    n_splits = int(min(5, y.sum(), (~y).sum()))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    out = []
    for name, fn in features.items():
        if fn is None:
            vals = [[str(int(np.searchsorted(quartiles, length)))] for length in lengths]
        else:
            vals = [[fn(r.profile)] for r in rows]  # type: ignore[arg-type]
        x = OneHotEncoder(handle_unknown="ignore").fit_transform(vals)
        proba = cross_val_predict(
            LogisticRegression(max_iter=1000), x, y, cv=cv, method="predict_proba"
        )[:, 1]
        auc = roc_auc_score(y, proba)
        out.append((name, round(float(auc), 3), "out-of-fold"))
    return sorted(out, key=lambda t: -t[1])


def dataset_checks(records: list[Record], dropped: list[Record], cfg: dict,
                   total_rows: int) -> list[Check]:
    checks: list[Check] = []
    good = [r for r in records if r.outcome is not None]
    parsed = [r for r in good if r.profile is not None]

    # Rows and drops.
    if "max_drop_share" in cfg:
        share = len(dropped) / total_rows if total_rows else 0.0
        status = "PASS" if share < cfg["max_drop_share"] else "FAIL"
        checks.append(Check("Dropped rows", status,
                            f"{len(dropped)} of {total_rows} ({share:.1%}); limit "
                            f"{cfg['max_drop_share']:.0%}"))
    else:
        status = "PASS" if not dropped else "FAIL"
        checks.append(Check("Dropped rows", status,
                            f"{len(dropped)} of {total_rows} rows don't parse"))
    status = "PASS" if total_rows == cfg["rows"] else (
        "FAIL" if cfg["count_tolerance_pp"] == 0 else "WARN")
    checks.append(Check("Row count", status, f"{total_rows} rows, target {cfg['rows']}"))

    # Outcome counts.
    counts = Counter(r.outcome for r in good)
    lines, worst = [], 0.0
    for band, target in cfg["counts"].items():
        got = counts.get(band, 0)
        if cfg["count_tolerance_pp"] == 0:
            ok = got == target
            worst = max(worst, 0 if ok else 1)
            lines.append(f"{band}: {got} (target {target})")
        else:
            pp = 100 * (got / len(good) - target / cfg["rows"]) if good else 100.0
            worst = max(worst, abs(pp))
            lines.append(f"{band}: {got} ({got / len(good):.1%}, target "
                         f"{target / cfg['rows']:.0%}, {pp:+.1f} pp)")
    if cfg["count_tolerance_pp"] == 0:
        status = "PASS" if worst == 0 else "FAIL"
    else:
        status = "PASS" if worst <= cfg["count_tolerance_pp"] else "FAIL"
    checks.append(Check("Outcome counts", status, "; ".join(lines)))
    pos = sum(r.strong for r in good)
    checks.append(Check("Research label share", "INFO",
                        f"{pos} of {len(good)} 'yes' ($500M and above): "
                        f"{pos / len(good):.0%}" if good else "no rows"))

    # Shuffled: no long runs of one outcome.
    run, longest = 1, 1
    for a, b in zip(good, good[1:]):
        run = run + 1 if a.outcome == b.outcome else 1
        longest = max(longest, run)
    status = "PASS" if longest <= 6 else "WARN"
    checks.append(Check("Shuffled", status, f"longest run of one outcome: {longest}"))

    # Years by outcome (consistency 5).
    by = defaultdict(Counter)
    for r in good:
        by[r.outcome][r.years] += 1
    sd, big = by["shut down"], by["over $1B"]
    sd_over8 = sd["over 8"] / max(1, sum(sd.values()))
    big_u5 = big["under 5"] / max(1, sum(big.values()))
    status = "PASS" if sd_over8 <= 0.25 and big_u5 <= 0.2 else "WARN"
    checks.append(Check(
        "Timelines by outcome", status,
        f"shut down over 8 years: {sd_over8:.0%} (should be a minority); "
        f"over $1B under 5 years: {big_u5:.0%} (should be rare)"))

    # Stereotype rule 1: each trait appears in both strong and shut-down records.
    traits = {
        "top-50 university": lambda p: any(e.qs == "top 50" for e in p.education),
        "unranked or no degree": lambda p: any(
            e.qs == "unranked" or e.degree == "no degree" for e in p.education),
        "big-tech-sized employer (5,000+)": lambda p: any(j.size == "5,000+" for j in p.jobs),
        "solo founder": lambda p: p.cofounders == "solo",
        "first-time founder": lambda p: p.prior_startups_n == 0,
        "repeat founder": lambda p: (p.prior_startups_n or 0) >= 1,
        "prior exit": lambda p: (p.prior_exits_n or 0) >= 1,
    }
    missing, table = [], []
    for name, fn in traits.items():
        n_strong = sum(1 for r in parsed if r.strong and fn(r.profile))
        n_shut = sum(1 for r in parsed if r.outcome == "shut down" and fn(r.profile))
        n_all = sum(1 for r in parsed if fn(r.profile))
        table.append(f"{name}: {n_strong} strong / {n_shut} shut down / {n_all} total")
        if n_strong == 0 or n_shut == 0:
            missing.append(name)
    checks.append(Check("Traits in both strong and shut-down records",
                        "FAIL" if missing else "PASS",
                        ("missing from one side: " + ", ".join(missing) + ". " if missing else "")
                        + "; ".join(table)))

    # Stereotype rule 3: similar length and detail across bands.
    if parsed:
        def mean(xs):
            return sum(xs) / len(xs) if xs else 0.0
        rows_by_band = defaultdict(list)
        for r in parsed:
            rows_by_band[r.outcome].append(r)
        detail = []
        lens = {}
        for band in cfg["counts"]:
            rs = rows_by_band.get(band, [])
            lens[band] = mean([len(r.input) for r in rs])
            detail.append(f"{band}: {lens[band]:.0f} chars, "
                          f"{mean([len(r.profile.jobs) for r in rs]):.1f} jobs, "
                          f"{mean([len(r.profile.education) for r in rs]):.1f} degrees")
        strong_len = mean([len(r.input) for r in parsed if r.strong])
        shut_len = mean([len(r.input) for r in parsed if r.outcome == "shut down"])
        gap = (strong_len - shut_len) / shut_len if shut_len else 0.0
        status = "PASS" if abs(gap) <= 0.15 else "WARN"
        checks.append(Check("Similar length across bands", status,
                            f"strong vs shut down length gap {gap:+.0%}; " + "; ".join(detail)))

    # Variety 1: industries.
    inds = Counter(normalise(r.profile.industry) for r in parsed)
    status = "PASS" if len(inds) >= cfg["min_industries"] else "FAIL"
    checks.append(Check("Industries", status,
                        f"{len(inds)} distinct (need {cfg['min_industries']}): "
                        + ", ".join(f"{k} ({v})" for k, v in inds.most_common())))
    if "batch" in cfg:
        b, need = cfg["batch"], cfg["min_industries_per_batch"]
        short = []
        for i in range(0, len(parsed), b):
            n = len({normalise(r.profile.industry) for r in parsed[i : i + b]})
            if n < need and len(parsed[i : i + b]) == b:
                short.append(f"rows {i + 1}-{i + b}: {n}")
        checks.append(Check(f"Industries per {b} rows (file order)",
                            "WARN" if short else "PASS",
                            ", ".join(short) if short else f"every full block has >= {need}"))

    # Variety 2: mix of founder types.
    def dist(fn):
        return dict(Counter(fn(r.profile) for r in parsed).most_common())
    degrees = Counter()
    for r in parsed:
        for e in r.profile.education:
            d = e.degree.lower()
            key = next((k for k in ("phd", "mba", "msc", "ms", "ma", "bsc", "bs", "ba",
                                    "beng", "meng", "no degree") if re.search(rf"\b{k}\b", d)),
                       "other")
            degrees[key] += 1
    mix = {
        "co-founders": dist(lambda p: p.cofounders),
        "background": dist(lambda p: p.background),
        "experience": dist(lambda p: p.experience),
        "degrees": dict(degrees.most_common()),
    }
    missing_mix = [f"{k}={v}" for k, allowed in (("co-founders", COFOUNDERS),
                   ("background", BACKGROUNDS), ("experience", EXPERIENCE))
                   for v in allowed if v not in mix[k]]
    checks.append(Check("Mix of founder types", "WARN" if missing_mix else "PASS",
                        ("never used: " + ", ".join(missing_mix) + ". " if missing_mix else "")
                        + json.dumps(mix)))

    # Variety 3: duplicates and shared career paths.
    exact, near = duplicates(good)
    status = "FAIL" if exact else ("WARN" if near else "PASS")
    checks.append(Check("Duplicates (exact and near)", status,
                        f"exact groups: {exact or 'none'}; near pairs (rows, similarity): "
                        f"{near[:20] or 'none'}" + (" ..." if len(near) > 20 else "")))
    paths = defaultdict(list)
    for r in parsed:
        paths[career_path(r.profile)].append(r.row)
    shared = [rows for rows in paths.values() if len(rows) > 1]
    checks.append(Check("Same career path (roles + industries)",
                        "WARN" if shared else "PASS",
                        f"rows sharing a path: {shared[:20] or 'none'}"))

    # Variety 4: unknown fields.
    with_unknown = [r for r in parsed if r.profile.unknown_fields]
    lo, hi = cfg["unknown_records"]
    if isinstance(lo, float):
        share = len(with_unknown) / len(parsed) if parsed else 0.0
        status = "PASS" if lo <= share <= hi else "WARN"
        target = f"{lo:.0%}-{hi:.0%}"
        got = f"{len(with_unknown)} ({share:.0%})"
    else:
        status = "PASS" if lo <= len(with_unknown) <= hi else "FAIL"
        target, got = str(lo) if lo == hi else f"{lo}-{hi}", str(len(with_unknown))
    bands = Counter(r.outcome for r in with_unknown)
    checks.append(Check("Records with unknown fields", status,
                        f"{got}, target {target}; by outcome {dict(bands)}; fields "
                        f"{dict(Counter(f for r in with_unknown for f in r.profile.unknown_fields))}"))

    # Leakage signal: can one field alone predict the research label?
    signal = single_field_signal(parsed)
    if signal:
        high = [f"{n} ({a})" for n, a, _ in signal if a >= 0.75]
        status = "WARN" if high else "PASS"
        checks.append(Check(
            "Single-field predictiveness (AUC, out-of-fold)", status,
            ("fields at or above 0.75: " + ", ".join(high) + ". " if high else "")
            + "; ".join(f"{n}: {a}" for n, a, _ in signal)
            + (" (small sample: noisy)" if len(parsed) < 500 else "")))
    return checks


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

MANUAL_REVIEW = [
    "Grounding: records at $500M and above are based on real founders and the outcome and "
    "years are correct for that company (can't be checked by a script).",
    "No household-name companies or widely famous founders behind the records.",
    "About 15 records (sample) or 30% (full) are 'surprising': strong backgrounds that shut "
    "down and modest ones that reached large outcomes, spread across bands.",
    "Degrees, fields and roles fit together, beyond the technical-background heuristic.",
    "Profiles read as realistic and varied, with no shared template.",
]


def report(path: Path, records: list[Record], checks: list[Check], profile: str) -> str:
    good = [r for r in records if r.outcome is not None and r.profile is not None]
    fails = [c for c in checks if c.status == "FAIL"]
    rec_errors = [r for r in records if r.errors]
    rec_warns = [r for r in records if r.warnings]
    verdict = "PASS" if not fails and not rec_errors else "FAIL"
    out = [
        f"# Validation: `{path.name}`",
        "",
        f"**Verdict: {verdict}.** {len(records)} rows read, {len(good)} parsed, "
        f"{len(fails)} dataset check(s) failed, {len(rec_errors)} row(s) with errors, "
        f"{len(rec_warns)} row(s) with warnings to review. Profile: `{profile}`.",
        "",
        "FAIL means a rule from MASTER_PLAN section 10 is broken. WARN means a heuristic "
        "flagged something to look at by eye; it may be fine.",
        "",
        "## Dataset checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for c in checks:
        out.append(f"| {c.name} | {c.status} | {c.detail.replace('|', '/')} |")
    out += ["", "## Rows with errors", ""]
    if rec_errors:
        for r in rec_errors:
            out.append(f"- **Row {r.row}** ({r.outcome or 'no label'}): " + "; ".join(r.errors))
    else:
        out.append("None.")
    out += ["", "## Rows with warnings", ""]
    if rec_warns:
        for r in rec_warns:
            out.append(f"- Row {r.row} ({r.outcome or 'no label'}): " + "; ".join(r.warnings))
    else:
        out.append("None.")
    out += ["", "## For manual review (not checkable by script)", ""]
    out += [f"- [ ] {item}" for item in MANUAL_REVIEW]
    return "\n".join(out) + "\n"


def validate(path: Path, profile: str) -> tuple[list[Record], list[Check]]:
    cfg = PROFILES[profile]
    rows = load(path)
    records = [parse_record(row, i) for i, row in enumerate(rows, 1)]
    for r in records:
        check_record(r)
    dropped = [r for r in records if r.outcome is None or r.profile is None]
    checks = dataset_checks(records, dropped, cfg, len(rows))
    return records, checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--profile", choices=sorted(PROFILES), default="sample50")
    ap.add_argument("--out", type=Path, default=None, help="report path (.md)")
    args = ap.parse_args(argv)

    records, checks = validate(args.path, args.profile)
    root = Path(__file__).resolve().parents[1]
    out = args.out or root / "results" / "data" / f"validation_{args.path.stem}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = report(args.path, records, checks, args.profile)
    out.write_text(text, encoding="utf-8")
    summary = {
        "file": str(args.path),
        "profile": args.profile,
        "rows": len(records),
        "checks": [asdict(c) for c in checks],
        "rows_with_errors": {r.row: r.errors for r in records if r.errors},
        "rows_with_warnings": {r.row: r.warnings for r in records if r.warnings},
    }
    out.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    verdict_line = text.splitlines()[2]
    print(verdict_line)
    for c in checks:
        if c.status in ("FAIL", "WARN"):
            print(f"  {c.status}: {c.name}: {c.detail[:160]}")
    print(f"Report: {out}")
    return 1 if verdict_line.startswith("**Verdict: FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
