"""What-if toggles: re-run only the decider with some inputs changed (no new research).

Answer changes need only a decider call. Field changes re-render the profile and, in answers mode,
re-run the answerer too (used_answerer: true), so they're slower and cost more with the real Jev.
"""

from __future__ import annotations

from .. import policy
from ..template import consistency_issues, render
from . import serialise
from .context import Pipeline
from .memo import VERSION, plain


class WhatIfError(ValueError):
    pass


async def what_if(memo: dict, req: dict, ctx: Pipeline) -> dict:
    model, rule_ids = ctx.artifacts.model, ctx.artifacts.rule_ids
    values = plain(memo["fields"])
    base_labels = [a["answer"] for a in memo["answers"]] if memo["answers"] is not None else None
    labels = list(base_labels) if base_labels is not None else None
    if labels is not None and [a["rule_id"] for a in memo["answers"]] != rule_ids:
        raise WhatIfError("this memo was scored with a different rules.json; screen the founder again")

    field_changes = [c for c in req["changes"] if c["kind"] == "field"]
    answer_changes = [c for c in req["changes"] if c["kind"] == "answer"]
    used_answerer, rendered = False, None

    if field_changes:
        values = {**values, **{c["key"]: c["value"] for c in field_changes}}
        issues = consistency_issues(values)
        if issues:
            raise WhatIfError("the changed profile breaks the template's consistency rules: " + "; ".join(issues))
        rendered = render(values)
        if labels is not None:
            labels = serialise.labels(await ctx.answerer.answer(rendered, values, ctx), model)
            used_answerer = True

    if answer_changes:
        if labels is None:
            raise WhatIfError("answer changes need the answers decider; this model reads the profile, so change fields instead")
        banded = model["answer_serialisation"]["format"] == "banded"
        for c in answer_changes:
            if c["rule_id"] not in rule_ids:
                raise WhatIfError(f"unknown rule {c['rule_id']}")
            labels[rule_ids.index(c["rule_id"])] = ("likely " + c["value"]) if banded else c["value"]

    dist = await ctx.decider.decide(answer_labels=labels, profile_text=rendered or memo["rendered_profile"],
                                    fields=values, ctx=ctx)
    pol = policy.with_defaults(req.get("policy") or memo["verdict"]["policy"])
    changed = [rid for rid, a, b in zip(rule_ids, base_labels or [], labels or []) if a != b]
    return {
        "schema_version": VERSION,
        "memo_id": memo["memo_id"],
        "changes": req["changes"],
        "used_answerer": used_answerer,
        "baseline": memo["distributions"],
        "distributions": dist,
        "verdict": policy.verdict(dist, ctx.artifacts.thresholds, pol, values),
        "rendered_profile": rendered,
        "answers_changed": changed,
        "mock": ctx.any_mock,
    }
