"""Investor controls: from distributions + thresholds.json to advance / escalate / pass.

This is the reference implementation of MASTER_PLAN section 8 "Investor controls". The frontend runs
the same logic client-side (ported to TypeScript), so any change here must be mirrored there; the
mocks are generated with it and validate.py checks every mock verdict against it.

Probability for a target and timeline:
    P(outcome >= target) = sum of outcome bands at or above the target
    P(within timeline)   = P(years 'under 5') for 5, + P('5-8') for 8, 1 for any timeline
    score                = their product (an estimate when a timeline is set: assumes independence)

Risk appetite picks two thresholds from the val table for that target and timeline:
    advance threshold = highest threshold that still flags ADVANCE_RECALL[risk] of val winners
    pass threshold    = highest threshold that still keeps PASS_RECALL of val winners above it
    advance if score >= advance; pass if score < pass; escalate otherwise.
A bolder investor advances more founders (catches more winners, at lower precision). The pass
threshold is the same for every risk level: auto-pass only where at most 10% of val winners scored.
"""

from __future__ import annotations

OUTCOME_BANDS = ("shut down", "under $50M", "$50M-$500M", "$500M-$1B", "over $1B")
YEARS_BANDS = ("under 5", "5-8", "over 8")
TARGETS = ("$50M", "$500M", "$1B")
TIMELINES = (None, 8, 5)
TARGET_FIRST_BAND = {"$50M": "$50M-$500M", "$500M": "$500M-$1B", "$1B": "over $1B"}
TIMELINE_BANDS = {None: YEARS_BANDS, 8: ("under 5", "5-8"), 5: ("under 5",)}

ADVANCE_RECALL = {"cautious": 0.25, "balanced": 0.5, "bold": 0.75}
PASS_RECALL = 0.9
SPARSE_POSITIVES = 20  # below this many val winners, precision and recall are noisy

DEFAULT_POLICY = {"target": "$500M", "timeline_years": None, "risk": "balanced", "filters": {}}


def p_at_least(outcome: dict, target: str) -> float:
    start = OUTCOME_BANDS.index(TARGET_FIRST_BAND[target])
    return sum(outcome[b] for b in OUTCOME_BANDS[start:])


def p_within(years: dict, timeline_years: int | None) -> float:
    return sum(years[b] for b in TIMELINE_BANDS[timeline_years])


def score(distributions: dict, target: str, timeline_years: int | None) -> float:
    return p_at_least(distributions["outcome"], target) * p_within(distributions["years"], timeline_years)


def with_defaults(policy: dict | None) -> dict:
    out = dict(DEFAULT_POLICY)
    out.update({k: v for k, v in (policy or {}).items() if k in DEFAULT_POLICY})
    out["filters"] = dict(out.get("filters") or {})
    return out


def table_for(thresholds: dict, target: str, timeline_years: int | None) -> dict:
    for t in thresholds["tables"]:
        if t["target"] == target and t["timeline_years"] == timeline_years:
            return t
    raise KeyError(f"thresholds.json has no table for {target}, timeline {timeline_years}")


def _highest_threshold_with_recall(rows: list[dict], min_recall: float) -> dict | None:
    for row in sorted(rows, key=lambda r: r["threshold"], reverse=True):
        if row["recall"] is not None and row["recall"] >= min_recall:
            return row
    return None


def resolve(thresholds: dict, policy: dict | None) -> dict:
    """Thresholds and expected precision / recall for a policy."""
    p = with_defaults(policy)
    table = table_for(thresholds, p["target"], p["timeline_years"])
    adv = _highest_threshold_with_recall(table["rows"], ADVANCE_RECALL[p["risk"]])
    pas = _highest_threshold_with_recall(table["rows"], PASS_RECALL)
    return {
        "policy": {
            "target": p["target"],
            "timeline_years": p["timeline_years"],
            "risk": p["risk"],
            "filters": p["filters"],
            "advance_threshold": adv["threshold"] if adv else None,
            "pass_threshold": pas["threshold"] if pas else None,
        },
        "expected_precision": adv["precision"] if adv else None,
        "expected_recall": adv["recall"] if adv else None,
        "missed_winners_if_pass": round(1 - pas["recall"], 4) if pas else None,
        "sparse": table["n_positive"] < SPARSE_POSITIVES,
        "n_positive": table["n_positive"],
    }


def decide(prob: float, advance_threshold: float | None, pass_threshold: float | None) -> str:
    if advance_threshold is not None and prob >= advance_threshold:
        return "advance"
    if pass_threshold is not None and prob < pass_threshold:
        return "pass"
    return "escalate"


def facets(fields: dict) -> dict:
    """Filter values from merged template field values (plain values, no provenance)."""
    cof = fields.get("cofounders", "unknown")
    bg = fields.get("background", "unknown")
    ps = fields.get("prior_startups", "unknown")
    industry = fields.get("industry", "unknown")
    return {
        "sector": None if industry == "unknown" else industry,
        "team": None if cof == "unknown" else ("solo" if cof == "solo" else "team"),
        "technical": None if bg == "unknown" else bg in ("technical", "mixed"),
        "repeat_founder": None if ps == "unknown" else isinstance(ps, list),
    }


def filters_failed(f: dict, filters: dict | None) -> list[str]:
    """Filters the founder fails. An unknown value fails an active filter (it can't be confirmed)."""
    failed = []
    filters = filters or {}
    if filters.get("sectors"):
        if f["sector"] is None or f["sector"].lower() not in {s.lower() for s in filters["sectors"]}:
            failed.append("sectors")
    for key in ("team", "technical", "repeat_founder"):
        if filters.get(key) is not None and f[key] != filters[key]:
            failed.append(key)
    return failed


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def verdict(distributions: dict, thresholds: dict, policy: dict | None, fields: dict) -> dict:
    """The memo's verdict block for one policy."""
    r = resolve(thresholds, policy)
    pol = r["policy"]
    prob = score(distributions, pol["target"], pol["timeline_years"])
    decision = decide(prob, pol["advance_threshold"], pol["pass_threshold"])
    failed = filters_failed(facets(fields), pol["filters"])
    horizon = "" if pol["timeline_years"] is None else f" within {pol['timeline_years']} years"
    estimate = "an estimated " if pol["timeline_years"] is not None else ""
    summary = f"{decision.capitalize()}: {estimate}{_pct(prob)} chance of reaching {pol['target']} or more{horizon}."
    if pol["advance_threshold"] is not None and pol["pass_threshold"] is not None:
        summary += (
            f" At {pol['risk']} risk, founders advance from {_pct(pol['advance_threshold'])}"
            f" and pass below {_pct(pol['pass_threshold'])}."
        )
    if failed:
        summary += " Filtered out by: " + ", ".join(failed) + "."
    return {
        "decision": decision,
        "probability": round(prob, 4),
        "probability_is_estimate": pol["timeline_years"] is not None,
        "policy": pol,
        "expected_precision": r["expected_precision"],
        "expected_recall": r["expected_recall"],
        "missed_winners_if_pass": r["missed_winners_if_pass"],
        "filters_failed": failed,
        "summary": summary,
    }
