"""Assemble the memo (MASTER_PLAN section 8, step 7) and compute drivers.

Drivers flip each answered question and ask the decider again. With the mock that's instant, so the memo
carries them. With the real Kev on a CPU each decision takes seconds (about 5 s on 4 cores, so ~3 minutes for
40), so a slow decider (`slow = True`) returns the memo with `drivers_status: "pending"` and the service
fills them in afterwards (fill_drivers), a few at a time and most important first, while the investor reads.
"""

from __future__ import annotations

import logging

from .. import policy
from ..template import UNKNOWN, render, unknown_paths
from . import serialise
from .context import Pipeline
from .render import render_anonymous

VERSION = "0.1.0"
DISCLAIMER = (
    "Screening aid, not investment advice. The model estimates the chance of a large outcome (an exit, "
    "IPO or funding at or above the chosen target) from the founder's background on the day the company "
    "was founded. It was trained on generated data, so its accuracy on real founders is unknown. "
    "Public information only; nothing is stored after the session."
)
MAX_UNKNOWNS_IN_TRAINING = 2
DRIVER_CHUNK = 3  # flips per round trip in the background: a what-if waits behind at most this many (~15 s on a CPU)
log = logging.getLogger("screener.memo")


def plain(fields: dict) -> dict:
    return {k: v["value"] for k, v in fields.items()}


# ---------------------------------------------------------------------------- drivers

def field_flips(values: dict) -> list[tuple[str, str, dict]]:
    """Profile-mode drivers: (id, label, changes). One plausible alternative per known field."""
    flips = []

    def add(key, to, label=None):
        flips.append((key, label or f"{key.replace('_', ' ').capitalize()}: {values[key]} → {to}", {key: to}))

    alt = {
        "cofounders": {"solo": "1", "1": "solo", "2": "solo", "3+": "solo"},
        "background": {"technical": "business", "business": "technical", "mixed": "business", "domain specialist": "technical"},
        "work_experience": {"<5": "10-15", "5-10": "10-15", "10-15": "5-10", "15+": "5-10"},
        "industry_experience": {"deep": "none", "some": "deep", "none": "deep"},
    }
    for key, mapping in alt.items():
        if values.get(key) in mapping:
            add(key, mapping[values[key]])
    exits = values.get("prior_exits")
    if isinstance(exits, list):
        flips.append(("prior_exits", "Prior exits: none (and no prior startups)",
                      {"prior_exits": "none", "prior_startups": "none"}))
    elif exits == "none" and values.get("prior_startups") in ("none", UNKNOWN):
        flips.append(("prior_exits", "Prior exits: 1 acquisition, $50M-$500M",
                      {"prior_startups": [{"outcome": "acquired", "value_band": "$50M-$500M"}],
                       "prior_exits": [{"kind": "acquisition", "value_band": "$50M-$500M"}]}))
    edu = values.get("education")
    if isinstance(edu, list) and edu[0]["qs_rank"] != UNKNOWN:
        top = edu[0]["qs_rank"] in ("top 50", "51-100")
        to = "300+" if top else "top 50"
        new = [dict(edu[0], qs_rank=to)] + edu[1:]
        flips.append(("education[0].qs_rank", f"University rank: QS {edu[0]['qs_rank']} → QS {to}", {"education": new}))
    return flips


def answer_flips(answer_labels: list[str], ctx: Pipeline) -> list[tuple[int, dict, str]]:
    """(rule index, rule, flipped answer) for every answer with an opposite, most important first: by the size
    of the rule's elastic-net weight in rules.json (rules it dropped last), then in rules.json order."""
    rules = ctx.artifacts.rules["rules"]
    flips = [(i, r, to) for i, r in enumerate(rules)
             if (to := serialise.flip(answer_labels[i], ctx.artifacts.model)) is not None]
    def importance(f):
        coef = f[1].get("elastic_net_coef")
        return (coef is None, -abs(coef or 0), f[0])
    return sorted(flips, key=importance)


async def answer_drivers(flips, answer_labels: list[str], values: dict, base: float, pol: dict,
                         ctx: Pipeline) -> list[dict]:
    """Ask the decider about each flip (one batch) and describe the change."""
    inputs = []
    for i, _, to in flips:
        flipped = list(answer_labels)
        flipped[i] = to
        inputs.append({"answer_labels": flipped, "profile_text": "", "fields": values})
    dists = await ctx.decider.decide_batch(inputs, ctx)
    return [{"id": rule["id"], "kind": "answer", "label": rule["question"], "current": answer_labels[i],
             "flipped": to, "distributions": d,
             "delta": round(policy.score(d, pol["target"], pol["timeline_years"]) - base, 4)}
            for (i, rule, to), d in zip(flips, dists)]


async def fill_drivers(memo: dict, ctx: Pipeline) -> None:
    """Compute a memo's pending drivers in the background, a few at a time, updating the memo as they arrive."""
    labels = [a["answer"] for a in memo["answers"]]
    values, pol = plain(memo["fields"]), memo["verdict"]["policy"]
    base = policy.score(memo["distributions"], pol["target"], pol["timeline_years"])
    flips = answer_flips(labels, ctx)
    try:
        for start in range(0, len(flips), DRIVER_CHUNK):
            new = await answer_drivers(flips[start:start + DRIVER_CHUNK], labels, values, base, pol, ctx)
            memo["drivers"] = sorted(memo["drivers"] + new, key=lambda dr: -abs(dr["delta"]))
        memo["drivers_status"] = "complete"
    except Exception:  # noqa: BLE001 - keep what we have; the memo says the rest failed
        log.exception("drivers for %s stopped after %d of %d", memo["memo_id"], len(memo["drivers"]), len(flips))
        memo["drivers_status"] = "failed"


async def drivers(values: dict, dist: dict, answer_labels: list[str] | None, pol: dict, ctx: Pipeline) -> list[dict]:
    base = policy.score(dist, pol["target"], pol["timeline_years"])
    out = []
    if answer_labels is not None:
        out = await answer_drivers(answer_flips(answer_labels, ctx), answer_labels, values, base, pol, ctx)
    else:
        for fid, label, changes in field_flips(values):
            new = {**values, **changes}
            d = await ctx.decider.decide(answer_labels=None, profile_text=render(new), fields=new, ctx=ctx)
            out.append({"id": fid, "kind": "field", "label": label,
                        "current": {k: values.get(k) for k in changes}, "flipped": changes, "distributions": d,
                        "delta": round(policy.score(d, pol["target"], pol["timeline_years"]) - base, 4)})
    out.sort(key=lambda dr: -abs(dr["delta"]))
    return out


# ------------------------------------------------------------------------------- memo

def warnings(*, ctx: Pipeline, unknowns: list[str], conflicts: list[dict], pol: dict, research_note: str | None,
             founding: dict, issues: list[str] = (), redactions: list[dict] = ()) -> list[dict]:
    out = []
    if ctx.any_mock:
        names = {"agent": "research agent", "answerer": "answerer (base Kev)", "decider": "decider (production Kev)"}
        mocked = [names[n] for n, v in ctx.components().items() if v == "mock"] + \
                 [f"{n}.json" for n in ("rules", "thresholds", "model") if ctx.artifacts.is_mock(n)]
        msg = ("Everything runs on mocks for now, so every number here is illustrative only." if len(mocked) == 6
               else f"Mocked: {', '.join(mocked)}. Anything that depends on them is illustrative only.")
        out.append({"code": "mock_artifacts", "message": msg})
    if research_note:
        out.append({"code": "research_partial", "message": research_note})
    if founding["provenance"] == "assumed":
        out.append({"code": "founding_date_assumed", "message": (
            f"No founding date was given or found, so {founding['value']} was used as the cutoff. "
            "Add the real date for a fair screen.")})
    if len(unknowns) > MAX_UNKNOWNS_IN_TRAINING:
        out.append({"code": "many_unknowns", "message": (
            f"{len(unknowns)} fields are unknown. The model was trained on profiles with at most "
            f"{MAX_UNKNOWNS_IN_TRAINING} unknown fields, so treat this result with extra caution.")})
    for issue in issues:
        out.append({"code": "profile_inconsistent", "message": f"Profile check: {issue}."})
    if redactions:
        out.append({"code": "redacted", "message": (
            f"Removed {len(redactions)} real name(s) from the profile to keep it anonymous: "
            + ", ".join(r["path"] for r in redactions) + ".")})
    if conflicts:
        out.append({"code": "conflicts_present", "message": (
            f"{len(conflicts)} of your values disagree with what the agent found. Your values were used; check the conflicts.")})
    resolved = policy.resolve(ctx.artifacts.thresholds, pol)
    if resolved["n_positive"] == 0:
        out.append({"code": "thresholds_sparse", "message": (
            "No validation founder reached this target and timeline, so there's no bar to judge against and every "
            "founder shows Look closer. Try a longer timeline or a lower target.")})
    elif resolved["sparse"]:
        out.append({"code": "thresholds_sparse", "message": (
            "Few validation founders reached this target and timeline, so expected precision and recall are noisy.")})
    if pol.get("timeline_years") is not None:
        out.append({"code": "timeline_estimate", "message": (
            "With a timeline, the probability combines outcome and timeline as if they were independent, so it's an estimate.")})
    return out


async def build_memo(*, inp: dict, fields: dict, conflicts: list[dict], findings, founding: dict, ctx: Pipeline,
                     memo_id: str, job_id: str | None, emit=None, issues: list[str] = (), names: list[str] = (),
                     redactions: list[dict] = ()) -> dict:
    values = plain(fields)
    profile = render_anonymous(values, list(names))
    model = ctx.artifacts.model
    answers_mode = ctx.artifacts.decider_input == "answers"

    answer_labels, answers = None, None
    if answers_mode:
        if emit:
            await emit("stage", f"Answering {len(ctx.artifacts.rule_ids)} screening questions.", stage="answering")
        p_yes = await ctx.answerer.answer(profile, values, ctx)
        answer_labels = serialise.labels(p_yes, model)
        answers = [{"rule_id": rid, "p_yes": serialise.p_or_none(p), "answer": a}
                   for rid, p, a in zip(ctx.artifacts.rule_ids, p_yes, answer_labels)]
    if emit:
        await emit("stage", "Scoring outcome and timeline.", stage="deciding")
    dist = await ctx.decider.decide(answer_labels=answer_labels, profile_text=profile, fields=values, ctx=ctx)

    pol = policy.with_defaults(inp.get("policy"))
    verdict = policy.verdict(dist, ctx.artifacts.thresholds, pol, values)
    deferred = answer_labels is not None and getattr(ctx.decider, "slow", False)
    if emit:
        await emit("stage", "Writing the memo.", stage="writing_memo")
    unknowns = unknown_paths(values)
    ident = inp["founder"]
    return {
        "schema_version": VERSION,
        "memo_id": memo_id,
        "job_id": job_id,
        "client_ref": inp.get("client_ref"),
        "created_at": ctx.now(),
        "mock": ctx.any_mock,
        "founder": {
            "display_name": ident.get("name") or ident.get("company_name") or ident.get("website_url")
            or ident.get("linkedin_url") or "Unnamed founder",
            "company_name": ident.get("company_name"),
            "identifier": ident,
            "founding_date": founding,
        },
        "verdict": verdict,
        "distributions": dist,
        "fields": fields,
        "rendered_profile": profile,
        "decider": {"input_type": ctx.artifacts.decider_input, "model_id": model["model_id"],
                    "artifacts_dir": ctx.extra.get("artifacts_dir_label", str(ctx.artifacts.dir))},
        "answers": answers,
        "drivers": [] if deferred else await drivers(values, dist, answer_labels, verdict["policy"], ctx),
        "drivers_status": "pending" if deferred else "complete",
        "drivers_total": len(answer_flips(answer_labels, ctx)) if answer_labels is not None else None,
        "what_if": {"answer_changes": "supported" if answers_mode else "unsupported",
                    "field_changes": "needs_answerer" if answers_mode else "supported"},
        "facets": policy.facets(values),
        "sources": findings.sources,
        "conflicts": conflicts,
        "unknowns": unknowns,
        "notes": {"investor": inp.get("notes"), "post_founding": findings.post_founding},
        "warnings": warnings(ctx=ctx, unknowns=unknowns, conflicts=conflicts, pol=pol,
                             research_note=findings.note, founding=founding, issues=issues,
                             redactions=redactions),
        "disclaimer": DISCLAIMER,
    }
