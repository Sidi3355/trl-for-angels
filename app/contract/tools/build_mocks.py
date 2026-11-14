"""Build every mock and example in app/contract/ so they agree with each other and with the backend.

    python app/contract/tools/build_mocks.py

The artefact mocks (rules, thresholds, model) are generated here. The memos, progress events and
what-if example come from running the backend's own pipeline (app/backend/screener) on the three
fictional demo founders, so the committed mocks are exactly what the service returns.
Deterministic: seed 42 and a stepping clock. Every URL is on example.com.
"""

from __future__ import annotations

import asyncio
import copy
import csv
import io
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent
sys.path.insert(0, str(CONTRACT.parent / "backend"))

from screener import policy  # noqa: E402
from screener.artifacts import Artifacts  # noqa: E402
from screener.mocks.founders import DEMO_FOUNDERS  # noqa: E402
from screener.mocks.model import OUTCOME_BANDS, RULES, YEARS_GIVEN_OUTCOME, mock_decide, simulate_answers  # noqa: E402
from screener.pipeline import batch as batchmod  # noqa: E402
from screener.pipeline.context import Pipeline  # noqa: E402
from screener.pipeline.memo import DISCLAIMER  # noqa: E402
from screener.pipeline.models import MockAnswerer, MockDecider  # noqa: E402
from screener.pipeline.research import MockAgent  # noqa: E402
from screener.pipeline.screening import screen  # noqa: E402
from screener.pipeline.whatif import what_if  # noqa: E402
from screener.service import make_event  # noqa: E402

MOCKS = CONTRACT / "mocks"
EXAMPLES = CONTRACT / "examples"
VERSION = "0.1.0"
NOW = "2026-11-14T12:00:00Z"
START = datetime(2026, 11, 14, 11, 59, 0, tzinfo=timezone.utc)
SEED = 42
MODEL_ID = "kev-0.6b-prod-mock"


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------- artefacts

def build_rules() -> dict:
    return {
        "schema_version": VERSION,
        "mock": True,
        "source": {
            "trl_version": "0.3.0", "trl_commit": "3437d64", "generator": "mock", "answerer": "jev",
            "rrf_params": {"beta": 0.5, "random_state": 42, "combiner": "elasticnet"},
            "created_at": NOW, "n_train": None,
        },
        "task": "Predict whether this startup founder's company will succeed (exit, IPO or funding over $500M).",
        "rules": [{"id": rid, "index": i, "question": q, "elastic_net_coef": None}
                  for i, (rid, q, _, _, _) in enumerate(RULES)],
    }


def build_model() -> dict:
    return {
        "schema_version": VERSION,
        "mock": True,
        "model_id": MODEL_ID,
        "created_at": NOW,
        "endpoint": {"base_url": "https://mock-kev.example.com", "path": "/v1/systemone",
                     "auth": {"type": "none"}, "timeout_s": 30},
        "decider_input": "answers",
        "request": {
            "questions": {
                "outcome": {"type": "choice", "instructions": "What was the company's final outcome?",
                            "criteria": {b: None for b in OUTCOME_BANDS}},
                "years": {"type": "choice", "instructions": "How many years from founding to that outcome?",
                          "criteria": {"under 5": None, "5-8": None, "over 8": None}},
            },
            "response_format": "mock: research to confirm the kev.serve response shape",
        },
        "temperature": {"applied_by": "server", "outcome": None, "years": None},
        "answerer": {"spec": "jev", "via": "trl"},
        "answer_serialisation": {"format": "binary", "threshold": 0.5, "line_template": "{question} {answer}",
                                 "separator": "\n", "order": "rules.json"},
    }


def _sample(rng: random.Random, weights) -> int:
    r, acc = rng.random(), 0.0
    for i, w in enumerate(weights):
        acc += w
        if r < acc:
            return i
    return len(weights) - 1


def build_thresholds() -> dict:
    """Simulate a 400-founder val split with the mock model, then tabulate precision and recall."""
    rng = random.Random(SEED)
    val = []
    for _ in range(400):
        d = mock_decide(simulate_answers(rng))
        o = _sample(rng, [d["outcome"][b] for b in OUTCOME_BANDS])
        y = _sample(rng, YEARS_GIVEN_OUTCOME[OUTCOME_BANDS[o]])
        val.append((d, o, y))
    first = {t: OUTCOME_BANDS.index(policy.TARGET_FIRST_BAND[t]) for t in policy.TARGETS}
    within = {None: 3, 8: 2, 5: 1}  # the true years index must be below this
    grid = [round(i / 100, 2) for i in range(100)]
    tables = []
    for target in policy.TARGETS:
        for tl in policy.TIMELINES:
            scored = [(policy.score(d, target, tl), o >= first[target] and y < within[tl]) for d, o, y in val]
            n_pos = sum(lbl for _, lbl in scored)
            rows = []
            for t in grid:
                flagged = [lbl for s, lbl in scored if s >= t]
                tp = sum(flagged)
                rows.append({"threshold": t, "n_flagged": len(flagged), "tp": tp,
                             "precision": round(tp / len(flagged), 4) if flagged else None,
                             "recall": round(tp / n_pos, 4) if n_pos else None})
            tables.append({"target": target, "timeline_years": tl, "n": len(val), "n_positive": n_pos,
                           "base_rate": round(n_pos / len(val), 4), "rows": rows})
    return {
        "schema_version": VERSION,
        "mock": True,
        "source": {"split": "val", "n": len(val), "model_id": MODEL_ID, "created_at": NOW,
                   "note": "Mock: 400 val founders simulated with the mock model (seed 42), not real data."},
        "score": "p_outcome_at_or_above_target * p_years_within_timeline",
        "label": "true_outcome_at_or_above_target AND true_years_within_timeline",
        "grid": {"start": 0.0, "stop": 0.99, "step": 0.01},
        "tables": tables,
    }


# ----------------------------------------------------------------- pipeline outputs

class StepClock:
    """A deterministic clock: each reading is `step` seconds after the last."""

    def __init__(self, start: datetime, step: float = 2.0):
        self.t, self.step = start, timedelta(seconds=step)

    def __call__(self) -> datetime:
        now = self.t
        self.t += self.step
        return now


def pipeline(arts: Artifacts) -> Pipeline:
    return Pipeline(artifacts=arts, agent=MockAgent(), answerer=MockAnswerer(), decider=MockDecider(),
                    clock=StepClock(START), pace=0, extra={"artifacts_dir_label": "app/contract/mocks"})


async def run_founder(spec: dict, arts: Artifacts) -> tuple[dict, list[dict]]:
    ctx = pipeline(arts)
    events: list[dict] = []

    async def emit(type, message, *, stage=None, data=None):
        events.append(make_event(spec["job_id"], len(events), ctx.now(), type, message, stage, data))

    await emit("stage", "Screening queued.", stage="queued")
    memo = await screen(spec["input"], ctx, memo_id=spec["memo_id"], job_id=spec["job_id"], emit=emit)
    v = memo["verdict"]
    await emit("memo_ready", f"Memo ready: {v['decision']}.",
               data={"memo_id": memo["memo_id"], "decision": v["decision"], "probability": v["probability"]})
    await emit("stage", "Done.", stage="done")
    return memo, events


def build_batch(memos: list[dict], arts: Artifacts) -> tuple[dict, dict, str]:
    founders = []
    for spec in DEMO_FOUNDERS:
        inp = copy.deepcopy(spec["input"])
        inp.pop("policy", None)
        founders.append(inp)
    pol = {"target": "$500M", "timeline_years": None, "risk": "balanced"}
    req = {"schema_version": VERSION, "batch_ref": "demo-batch", "founders": founders, "policy": pol,
           "options": {"concurrency": 3, "research": True}}
    items = [batchmod.item_from_memo(i, m) for i, m in enumerate(memos)]
    resp = {
        "schema_version": VERSION, "batch_id": "batch_mock_001", "batch_ref": "demo-batch", "status": "complete",
        "created_at": NOW, "policy": policy.resolve(arts.thresholds, pol)["policy"],
        "progress": {"total": 3, "queued": 0, "running": 0, "complete": 3, "failed": 0},
        "counts": batchmod.counts(items), "items": items, "events_url": "/v1/batches/batch_mock_001/events",
        "mock": True, "disclaimer": DISCLAIMER,
    }
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=batchmod.CSV_COLUMNS, lineterminator="\n")
    w.writeheader()
    for f in founders:
        row = {"client_ref": f.get("client_ref", ""), "founding_date": f.get("founding_date", ""),
               "notes": f.get("notes") or "",
               **{k: v for k, v in f["founder"].items() if k in batchmod.CSV_COLUMNS},
               **{k: v for k, v in (f.get("fields") or {}).items() if k in batchmod.CSV_COLUMNS}}
        w.writerow(row)
    return req, resp, buf.getvalue()


async def main() -> None:
    arts = Artifacts(dir=MOCKS, rules=build_rules(), thresholds=build_thresholds(), model=build_model())
    runs = [await run_founder(spec, arts) for spec in DEMO_FOUNDERS]
    memos = [m for m, _ in runs]
    got, want = [m["verdict"]["decision"] for m in memos], [s["key"] for s in DEMO_FOUNDERS]
    if got != want:
        raise SystemExit(f"mock verdicts {got} don't match the intended {want}; retune the demo founders")

    dump(MOCKS / "rules.json", arts.rules)
    dump(MOCKS / "model.json", arts.model)
    dump(MOCKS / "thresholds.json", arts.thresholds)
    dump(MOCKS / "mock_memo.json", memos)

    for spec in DEMO_FOUNDERS:
        dump(EXAMPLES / f"investor_input_{spec['key']}.json", spec["input"])
    m0, ev0 = runs[0]
    dump(EXAMPLES / "screening_job.json", {
        "schema_version": VERSION, "job_id": m0["job_id"], "client_ref": m0["client_ref"], "status": "complete",
        "stage": "done", "created_at": ev0[0]["ts"], "events_url": f"/v1/screenings/{m0['job_id']}/events",
        "memo_id": m0["memo_id"], "memo_url": f"/v1/memos/{m0['memo_id']}", "error": None})
    (EXAMPLES / "progress_events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ev0))

    wi_req = {"schema_version": VERSION, "changes": [{"kind": "answer", "rule_id": "r12", "value": "yes"}]}
    dump(EXAMPLES / "what_if_request.json", wi_req)
    dump(EXAMPLES / "what_if_response.json", await what_if(memos[1], wi_req, pipeline(arts)))
    b_req, b_resp, b_csv = build_batch(memos, arts)
    dump(EXAMPLES / "batch_request.json", b_req)
    dump(EXAMPLES / "batch_response.json", b_resp)
    (EXAMPLES / "batch.csv").write_text(b_csv)

    for m in memos:
        v = m["verdict"]
        print(f"{m['memo_id']}: {v['decision']:8s} p={v['probability']:.3f}  adv>={v['policy']['advance_threshold']} "
              f"pass<{v['policy']['pass_threshold']}  unknowns={len(m['unknowns'])} conflicts={len(m['conflicts'])}")


if __name__ == "__main__":
    asyncio.run(main())
