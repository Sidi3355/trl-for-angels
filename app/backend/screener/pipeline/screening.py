"""One screening, end to end (MASTER_PLAN section 8 pipeline, steps 1-7)."""

from __future__ import annotations

from ..template import FIELD_LABELS, consistency_issues
from .context import Emitter, Pipeline, no_emit
from .memo import build_memo, plain
from .merge import founding_date, merge
from .render import anonymise, names_to_redact
from .research import Findings


def _n(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


async def screen(inp: dict, ctx: Pipeline, *, memo_id: str, job_id: str | None, emit: Emitter = no_emit) -> dict:
    options = inp.get("options") or {}
    if options.get("research", True):
        findings = await ctx.agent.research(inp, ctx, emit)
    else:
        note = "Research was switched off for this screening, so only your fields were used."
        await emit("stage", "Skipping research (switched off).", stage="researching")
        findings = Findings(ran=False, note=note)

    fields, conflicts = merge(inp, findings)
    n_inv = sum(v["provenance"] in ("investor", "investor_voice") for v in fields.values())
    n_agent = sum(v["provenance"] == "agent" for v in fields.values())
    await emit("stage", f"Merging {_n(n_inv, 'field')} from you with {_n(n_agent, 'field')} from the agent: "
                        f"{_n(len(conflicts), 'conflict') if conflicts else 'no conflicts'}.", stage="merging")
    for c in conflicts:
        await emit("conflict", f"{FIELD_LABELS.get(c['field'], c['field'])}: you said {c['investor_value']}, "
                               f"the agent found {c['agent_value']}. Using yours.", data=c)
    names = names_to_redact(inp["founder"], findings.names_seen)
    fields, redactions = anonymise(fields, names)
    for r in redactions:
        await emit("warning", f"Removed a real name from {r['path']} to keep the profile anonymous.",
                   data={"code": "redacted", "message": f"{r['path']}: now {r['now']!r}"})
    founding = founding_date(inp, findings, ctx.now())
    issues = consistency_issues(plain(fields))
    for issue in issues:
        await emit("warning", f"Profile check: {issue}.", data={"code": "profile_inconsistent", "message": issue})
    await emit("stage", "Rendering the anonymised profile.", stage="rendering")
    return await build_memo(inp=inp, fields=fields, conflicts=conflicts, findings=findings, founding=founding,
                            ctx=ctx, memo_id=memo_id, job_id=job_id, emit=emit, issues=issues, names=names,
                            redactions=redactions)
