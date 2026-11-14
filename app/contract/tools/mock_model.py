"""MOCK answerer and decider. Not the real model, and not a claim about what predicts success.

It exists so the mocks hang together (answers follow from the profile, distributions follow from the
answers, drivers and what-ifs follow from flipping answers), and so the task 2 backend can serve
plausible what-if results before Jev and the production Kev are wired in.

- mock_answer(fields)  stands in for Jev answering rules.json through TRL: P(yes) per rule.
- mock_decide(answers) stands in for the production Kev: outcome and years distributions from the
  binary answers (ordinal logistic on a weighted sum; years as a mixture given the outcome).
"""

from __future__ import annotations

import math
import re

U = "unknown"


def _lst(v):
    return v if isinstance(v, list) else []


def _match(pattern: str, jobs) -> bool:
    return any(re.search(pattern, j["role"], re.I) for j in _lst(jobs))


def _r01(f):  # prior startup acquired or IPO
    ps = f["prior_startups"]
    if ps == U:
        return 0.3
    return 0.95 if any(s["outcome"] in ("acquired", "IPO") for s in _lst(ps)) else 0.04


def _r02(f):  # exit of $50M or more
    pe = f["prior_exits"]
    if pe == U:
        return 0.25
    if not isinstance(pe, list):
        return 0.03
    return 0.94 if any(e["value_band"] != "under $50M" for e in pe) else 0.1


def _r03(f):  # first startup
    ps = f["prior_startups"]
    return {"none": 0.96, U: 0.6}.get(ps, 0.03) if not isinstance(ps, list) else 0.03


def _r04(f):
    return {"technical": 0.95, "mixed": 0.6, U: 0.5}.get(f["background"], 0.08)


def _r05(f):
    edu = f["education"]
    if edu == U:
        return 0.4
    if any(e["qs_rank"] in ("top 50", "51-100") for e in edu):
        return 0.92
    return 0.4 if any(e["qs_rank"] == U for e in edu) else 0.06


def _r06(f):
    edu = f["education"]
    if edu == U:
        return 0.5
    grad = {"MSc", "MS", "MA", "MBA", "PhD", "MD", "MEng", "MPhil", "JD"}
    return 0.93 if any(e["degree"] in grad for e in edu) else 0.07


def _r07(f):
    return {"10-15": 0.95, "15+": 0.97, "5-10": 0.12, "<5": 0.02}.get(f["work_experience"], 0.5)


def _r08(f):
    return {"deep": 0.93, "some": 0.3, "none": 0.04}.get(f["industry_experience"], 0.45)


def _r09(f):
    jobs = f["jobs"]
    if jobs == U:
        return 0.5
    if any(j["company_size"] in ("1,001-5,000", "5,000+") for j in jobs):
        return 0.95
    return 0.45 if any(j["company_size"] == U for j in jobs) else 0.06


def _r10(f):
    if f["jobs"] == U:
        return 0.4
    pat = r"staff|principal|engineering manager|cto|head of engineering|vp,? engineering|tech lead|architect"
    return 0.9 if _match(pat, f["jobs"]) else 0.08


def _r11(f):
    if f["jobs"] == U:
        return 0.45
    return 0.9 if _match(r"manager|director|lead|head|vp|chief|partner|attending", f["jobs"]) else 0.12


def _r12(f):
    return {"solo": 0.03, U: 0.45}.get(f["cofounders"], 0.97)


def _r13(f):
    return {"2": 0.95, "3+": 0.97, U: 0.3}.get(f["cofounders"], 0.04)


def _r14(f):
    if f["jobs"] == U:
        return 0.4
    return 0.92 if any(j["duration"] == "5+" for j in f["jobs"]) else 0.1


def _r15(f):
    small = ("1-10", "11-50", "51-200", "201-1,000")
    tech = r"engineer|developer|product|data|scientist|designer"
    return 0.85 if any(j["company_size"] in small and re.search(tech, j["role"], re.I) for j in _lst(f["jobs"])) else 0.1


def _r16(f):
    if f["jobs"] == U or f["industry"] == U:
        return 0.45
    return 0.9 if any(j["industry"].lower() == f["industry"].lower() for j in f["jobs"]) else 0.15


def _r17(f):
    jobs = _lst(f["jobs"])
    if not jobs:
        return 0.3
    return 0.9 if sum(j["company_size"] == "5,000+" for j in jobs) / len(jobs) >= 0.5 else 0.1


def _r18(f):
    return {"<5": 0.96, U: 0.3}.get(f["work_experience"], 0.02)


def _r19(f):
    return {"domain specialist": 0.95, U: 0.3}.get(f["background"], 0.05)


def _r20(f):
    jobs = _lst(f["jobs"])
    changes = sum(a["industry"] != b["industry"] for a, b in zip(jobs, jobs[1:]))
    return 0.85 if changes > 2 else 0.1


# (id, question, answer function, weight on 'yes', population P(yes) for the val simulation)
RULES = [
    ("r01", "Has the founder previously founded a company that was acquired or went public?", _r01, 0.9, 0.12),
    ("r02", "Has the founder had an exit worth $50M or more as a co-founder?", _r02, 0.8, 0.08),
    ("r03", "Is this the founder's first startup?", _r03, -0.35, 0.65),
    ("r04", "Does the founder have a technical background, such as engineering or computer science?", _r04, 0.35, 0.45),
    ("r05", "Does the founder hold a degree from a university ranked in the QS top 100?", _r05, 0.3, 0.3),
    ("r06", "Does the founder hold a graduate degree (master's, MBA, PhD or equivalent)?", _r06, 0.1, 0.4),
    ("r07", "Does the founder have more than 10 years of work experience?", _r07, 0.25, 0.4),
    ("r08", "Does the founder have deep prior experience in the startup's industry?", _r08, 0.5, 0.3),
    ("r09", "Has the founder worked at a company with more than 1,000 employees?", _r09, 0.15, 0.55),
    ("r10", "Has the founder held a senior engineering or technical leadership role?", _r10, 0.45, 0.2),
    ("r11", "Has the founder held a management or leadership role?", _r11, 0.2, 0.5),
    ("r12", "Did the founder start the company with at least one co-founder?", _r12, 0.35, 0.75),
    ("r13", "Does the founding team have three or more people?", _r13, 0.15, 0.35),
    ("r14", "Has the founder spent five or more years with a single employer?", _r14, 0.05, 0.25),
    ("r15", "Has the founder worked in a technical or product role at a company with 1,000 or fewer employees?", _r15, 0.3, 0.3),
    ("r16", "Has the founder worked in the same industry as the startup?", _r16, 0.3, 0.5),
    ("r17", "Has the founder spent most of their career at organisations with more than 5,000 employees?", _r17, -0.2, 0.2),
    ("r18", "Does the founder have less than five years of work experience?", _r18, -0.4, 0.2),
    ("r19", "Is the founder a domain specialist, such as a clinician or scientist?", _r19, 0.1, 0.12),
    ("r20", "Has the founder changed industries more than twice?", _r20, -0.15, 0.15),
]
RULE_IDS = [r[0] for r in RULES]

SCALE = 0.45
CORR = 1.0  # how strongly a simulated founder's latent quality pushes all answers the same way
CUTS = (0.0, 0.85, 1.45, 2.2)  # ordinal cutpoints between the five outcome bands


def _yes_prob(q: float, w: float, z: float) -> float:
    """P(yes) for a simulated founder with latent quality z: strong founders tick many boxes at once."""
    return 1 / (1 + math.exp(-(math.log(q / (1 - q)) + CORR * (1 if w > 0 else -1) * z)))


def _population_mean_score() -> float:
    """E[sum of w * x] over the simulated population (deterministic quadrature over z ~ N(0, 1))."""
    zs = [i / 20 for i in range(-120, 121)]
    pdf = [math.exp(-z * z / 2) for z in zs]
    norm = sum(pdf)
    return sum(w * sum(p * _yes_prob(q, w, z) for z, p in zip(zs, pdf)) / norm for _, _, _, w, q in RULES)


BIAS = -SCALE * _population_mean_score()  # centres the average simulated founder at the mix's base rates


def simulate_answers(rng) -> list[int]:
    """Binary answers for one simulated val founder (used to build the mock thresholds.json)."""
    z = rng.gauss(0, 1)
    return [1 if rng.random() < _yes_prob(q, w, z) else 0 for _, _, _, w, q in RULES]
OUTCOME_BANDS = ("shut down", "under $50M", "$50M-$500M", "$500M-$1B", "over $1B")
YEARS_BANDS = ("under 5", "5-8", "over 8")
YEARS_GIVEN_OUTCOME = {  # shut-downs are mostly fast; big outcomes mostly take longer
    "shut down": (0.6, 0.33, 0.07),
    "under $50M": (0.35, 0.45, 0.2),
    "$50M-$500M": (0.2, 0.5, 0.3),
    "$500M-$1B": (0.12, 0.5, 0.38),
    "over $1B": (0.06, 0.44, 0.5),
}


def mock_answer(fields: dict) -> list[float]:
    """Mock Jev: P(yes) for each rule, in rule order, from merged template field values."""
    f = {k: fields.get(k, U) for k in (
        "industry", "cofounders", "background", "work_experience", "industry_experience",
        "education", "jobs", "prior_startups", "prior_exits")}
    return [round(fn(f), 2) for _, _, fn, _, _ in RULES]


def binary(p_yes: list[float], threshold: float = 0.5) -> list[int]:
    return [1 if p >= threshold else 0 for p in p_yes]


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def mock_decide(x: list[int]) -> dict:
    """Mock production Kev: outcome and years distributions from binary answers (rule order)."""
    s = BIAS + SCALE * sum(w * xi for (_, _, _, w, _), xi in zip(RULES, x))
    above = [_sigmoid(s - c) for c in CUTS]
    probs = [1 - above[0], above[0] - above[1], above[1] - above[2], above[2] - above[3], above[3]]
    outcome = {b: round(p, 4) for b, p in zip(OUTCOME_BANDS, probs)}
    years = [sum(probs[k] * YEARS_GIVEN_OUTCOME[b][j] for k, b in enumerate(OUTCOME_BANDS)) for j in range(3)]
    years_d = {b: round(p, 4) for b, p in zip(YEARS_BANDS, years)}
    _fix_rounding(outcome)
    _fix_rounding(years_d)
    return {"outcome": outcome, "years": years_d}


def _fix_rounding(d: dict) -> None:
    """Make 4-decimal probabilities sum to exactly 1 by adjusting the largest one."""
    err = round(1 - sum(d.values()), 4)
    if err:
        k = max(d, key=d.get)
        d[k] = round(d[k] + err, 4)
