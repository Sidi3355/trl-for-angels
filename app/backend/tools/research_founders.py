"""Run the real research agent on test founders and print what it found (task 3 check).

    # dry run: shows what would run and the worst-case spend, calls nothing
    app/backend/.venv/bin/python app/backend/tools/research_founders.py
    # one founder for real, then stop
    app/backend/.venv/bin/python app/backend/tools/research_founders.py --spend --only awotona

Needs SCREENER_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY on a host). Every call goes to
https://api.anthropic.com, never the sandbox's own Claude connection. Spend stops at
AGENT_MAX_COST_PER_FOUNDER_USD per founder and AGENT_BUDGET_USD in total. Results are written to
app/backend/.research_runs/ (git-ignored: it holds real people's research).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from screener.artifacts import load_artifacts  # noqa: E402
from screener.config import Settings, secret  # noqa: E402
from screener.contract import get_contract  # noqa: E402
from screener.pipeline.agent import ClaudeAgent  # noqa: E402
from screener.pipeline.budget import Budget  # noqa: E402
from screener.pipeline.context import Pipeline  # noqa: E402
from screener.pipeline.models import MockAnswerer, MockDecider  # noqa: E402
from screener.pipeline.screening import screen  # noqa: E402

OUT = BACKEND / ".research_runs"


def show(memo: dict, ref: dict, cost: float, secs: float) -> None:
    print("\n--- rendered profile (what the model sees) ---")
    print(memo["rendered_profile"])
    print("\n--- fields ---")
    for key, f in memo["fields"].items():
        src = ", ".join(f["source_ids"]) or "-"
        conf = f"{f['confidence']:.0%}" if f["confidence"] is not None else ""
        val = f["value"] if not isinstance(f["value"], list) else f"{len(f['value'])} entries"
        print(f"  {key:20s} {str(val)[:45]:45s} {f['provenance']:9s} {conf:5s} {src}"
              + (f"   note: {f['note']}" if f.get("note") else ""))
    fd = memo["founder"]["founding_date"]
    print(f"  {'founding date':20s} {fd['value']:45s} {fd['provenance']:9s}       {', '.join(fd['source_ids']) or '-'}")
    print("\n--- sources ---")
    for s in memo["sources"]:
        when = "before founding" if s["before_founding"] else ("AFTER founding" if s["before_founding"] is False else "unverified")
        print(f"  {s['id']}: {s['title'][:70]} ({when})\n      {s['url']}\n      used for: {', '.join(s['used_for']) or '-'}")
    if memo["notes"]["post_founding"]:
        print("\n--- post-founding facts (memo only, never sent to the model) ---")
        for n in memo["notes"]["post_founding"]:
            print(f"  - {n['text']} [{', '.join(n['source_ids'])}]")
    print("\n--- check against public reference ---")
    print(f"  reference: founded {ref['founded']}; co-founders {ref['cofounders']}; {ref['notes']}")
    print(f"  unknowns: {', '.join(memo['unknowns']) or 'none'}   warnings: {', '.join(w['code'] for w in memo['warnings'])}")
    print(f"  cost: ${cost:.3f}   time: {secs:.0f}s")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spend", action="store_true", help="actually call the Claude API (costs money)")
    ap.add_argument("--only", nargs="*", help="founder keys to run (default: all)")
    args = ap.parse_args()

    spec = json.loads((Path(__file__).parent / "test_founders.json").read_text())["founders"]
    chosen = [f for f in spec if not args.only or f["key"] in args.only]
    s = Settings()
    worst = min(len(chosen) * s.agent_max_cost_per_founder_usd, s.agent_budget_usd)
    print(f"Founders: {', '.join(f['key'] for f in chosen)}")
    print(f"Model {s.agent_model} (effort {s.agent_effort}) at {s.agent_base_url}; up to {s.agent_max_searches} "
          f"searches each. Caps: ${s.agent_max_cost_per_founder_usd:.2f} per founder, ${s.agent_budget_usd:.2f} "
          f"total. Worst case for this run: ${worst:.2f}.")
    if not args.spend:
        print("Dry run: nothing was called. Add --spend to run it.")
        return 0
    if not secret(s.anthropic_api_key):
        print("No key: set SCREENER_ANTHROPIC_API_KEY.")
        return 2

    contract = get_contract(s.path(s.contract_dir))
    arts = load_artifacts(s.path(s.artifacts_dir), contract)
    budget = Budget(total_usd=s.agent_budget_usd, per_founder_usd=s.agent_max_cost_per_founder_usd)
    agent = ClaudeAgent(api_key=secret(s.anthropic_api_key), model=s.agent_model, base_url=s.agent_base_url,
                        max_searches=s.agent_max_searches, max_fetches=s.agent_max_fetches, effort=s.agent_effort,
                        max_tokens=s.agent_max_tokens, min_confidence=s.agent_min_confidence, budget=budget,
                        contract=contract)
    ctx = Pipeline(artifacts=arts, agent=agent, answerer=MockAnswerer(), decider=MockDecider(), pace=0)
    OUT.mkdir(exist_ok=True)

    async def emit(type, message, *, stage=None, data=None):
        print(f"  [{time.strftime('%H:%M:%S')}] {type:8s} {message}")

    for f in chosen:
        if budget.exhausted:
            print(f"\nTotal budget reached (${budget.spent_usd:.2f}); stopping before {f['key']}.")
            break
        print(f"\n================ {f['key']}: {f['tests']} ================")
        before, t0 = budget.spent_usd, time.time()
        memo = await screen(f["input"], ctx, memo_id=f"memo_{f['key']}", job_id=None, emit=emit)
        contract.check("memo", memo)
        cost = budget.spent_usd - before
        (OUT / f"{f['key']}.json").write_text(json.dumps(memo, indent=2, ensure_ascii=False))
        show(memo, f["reference"], cost, time.time() - t0)

    print(f"\nTotal spent: ${budget.spent_usd:.3f} over {budget.runs} founder(s), {budget.searches} searches. "
          f"Memos saved in {OUT.relative_to(BACKEND.parents[1])}/ (not committed).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
