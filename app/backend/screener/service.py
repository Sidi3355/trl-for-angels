"""Jobs, batches and memos, held in memory only (MASTER_PLAN guardrail: nothing stored after the session).

Everything expires RETENTION_MINUTES after it finishes. One process holds all state, so the backend
runs as a single instance (see app/README.md, Deploy).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from . import policy
from .contract import Contract
from .pipeline import batch as batchmod
from .pipeline.context import Pipeline
from .pipeline.memo import DISCLAIMER
from .pipeline.screening import screen
from .pipeline.whatif import what_if

log = logging.getLogger("screener")
VERSION = "0.1.0"
FINISHED = ("complete", "failed", "partial")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def make_event(job_id: str, seq: int, ts: str, type: str, message: str, stage: str | None = None,
               data: dict | None = None) -> dict:
    """One progress event, as the contract's progress_event schema defines it."""
    ev = {"schema_version": VERSION, "job_id": job_id, "seq": seq, "ts": ts, "type": type, "message": message}
    if stage:
        ev["stage"] = stage
    if data is not None:
        ev["data"] = data
    return ev


@dataclass
class Job:
    """A screening or a batch: status plus an append-only event log that SSE clients follow."""
    id: str
    kind: str  # "screening" | "batch"
    created_at: str
    client_ref: str | None = None
    status: str = "queued"
    stage: str = "queued"
    memo_id: str | None = None
    error: dict | None = None
    events: list = field(default_factory=list)
    finished_at: object = None
    _changed: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def finished(self) -> bool:
        return self.status in FINISHED

    def events_after(self, seq: int) -> list[dict]:
        return self.events[seq + 1:] if seq + 1 < len(self.events) else []

    async def wait_for_more(self, seq: int, timeout: float) -> bool:
        if len(self.events) - 1 > seq or self.finished:
            return True
        changed = self._changed
        try:
            await asyncio.wait_for(changed.wait(), timeout)
            return True
        except TimeoutError:
            return False

    def notify(self) -> None:
        self._changed.set()
        self._changed = asyncio.Event()


@dataclass
class Batch:
    job: Job
    request: dict
    policy_used: dict
    items: list
    batch_ref: str | None = None


class NotFound(KeyError):
    pass


class InvalidRequest(ValueError):
    """A request body that breaks the contract (a 422, unlike a response that breaks it, which is a bug)."""

    def __init__(self, schema: str, errors: list[str]):
        super().__init__(f"the request doesn't match the {schema} schema")
        self.schema = schema
        self.errors = errors


class Service:
    def __init__(self, pipeline: Pipeline, contract: Contract, *, retention_minutes: int = 120,
                 max_concurrent: int = 4, batch_concurrency: int = 3, validate: bool = True):
        self.pipeline = pipeline
        self.contract = contract
        self.retention = timedelta(minutes=retention_minutes)
        self.validate = validate
        self.batch_concurrency = batch_concurrency
        self.slots = asyncio.Semaphore(max_concurrent)
        self.jobs: dict[str, Job] = {}
        self.memos: dict[str, tuple[dict, object]] = {}
        self.batches: dict[str, Batch] = {}
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------ helpers

    def _check(self, schema: str, doc: dict) -> dict:
        """Validate a response or event against the contract (catches drift; a failure is a bug)."""
        if self.validate:
            self.contract.check(schema, doc)
        return doc

    def _check_request(self, schema: str, doc) -> None:
        """Always validate request bodies; a failure is the caller's error (422)."""
        errors = self.contract.errors(schema, doc)
        if errors:
            raise InvalidRequest(schema, errors)

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _emit(self, job: Job, type: str, message: str, *, stage: str | None = None, data: dict | None = None):
        ev = make_event(job.id, len(job.events), self.pipeline.now(), type, message, stage, data)
        if stage:
            job.stage = stage
        self._check("progress_event", ev)
        job.events.append(ev)
        job.notify()

    def _finish(self, job: Job, status: str) -> None:
        job.status = status
        job.finished_at = self.pipeline.clock()

    def sweep(self) -> int:
        """Drop finished jobs, batches and memos older than the retention window."""
        cutoff = self.pipeline.clock() - self.retention
        old = [j for j in self.jobs.values() if j.finished and j.finished_at and j.finished_at < cutoff]
        for j in old:
            self.jobs.pop(j.id, None)
            self.batches.pop(j.id, None)
        stale = [m for m, (_, t) in self.memos.items() if t < cutoff]
        for m in stale:
            self.memos.pop(m, None)
        return len(old) + len(stale)

    def stats(self) -> dict:
        return {"jobs": len(self.jobs), "memos": len(self.memos), "batches": len(self.batches),
                "running": sum(not j.finished for j in self.jobs.values())}

    # --------------------------------------------------------------- screenings

    async def start_screening(self, inp: dict, *, policy_override: dict | None = None, start: bool = True) -> Job:
        self._check_request("investor_input", inp)
        job = Job(id=new_id("job"), kind="screening", created_at=self.pipeline.now(), client_ref=inp.get("client_ref"))
        self.jobs[job.id] = job
        await self._emit(job, "stage", "Screening queued.", stage="queued")
        if start:
            self._spawn(self.run_screening(job, inp, policy_override))
        return job

    async def run_screening(self, job: Job, inp: dict, policy_override: dict | None = None) -> dict | None:
        if policy_override:
            inp = {**inp, "policy": policy_override}
        async with self.slots:
            job.status = "running"

            async def emit(type, message, *, stage=None, data=None):
                await self._emit(job, type, message, stage=stage, data=data)

            try:
                memo = await screen(inp, self.pipeline, memo_id=new_id("memo"), job_id=job.id, emit=emit)
                self._check("memo", memo)
            except Exception as e:  # noqa: BLE001 - report every failure on the job
                log.exception("screening %s failed", job.id)
                job.error = {"code": type(e).__name__, "message": str(e)[:500], "retryable": False}
                self._finish(job, "failed")
                await self._emit(job, "error", "Screening failed.", data=job.error)
                await self._emit(job, "stage", "Failed.", stage="failed")
                return None
        self.memos[memo["memo_id"]] = (memo, self.pipeline.clock())
        job.memo_id = memo["memo_id"]
        self._finish(job, "complete")
        v = memo["verdict"]
        await self._emit(job, "memo_ready", f"Memo ready: {v['decision']}.",
                         data={"memo_id": memo["memo_id"], "decision": v["decision"], "probability": v["probability"]})
        await self._emit(job, "stage", "Done.", stage="done")
        return memo

    def job(self, job_id: str, kind: str = "screening") -> Job:
        job = self.jobs.get(job_id)
        if job is None or job.kind != kind:
            raise NotFound(job_id)
        return job

    def job_doc(self, job: Job) -> dict:
        return self._check("screening_job", {
            "schema_version": VERSION, "job_id": job.id, "client_ref": job.client_ref,
            "status": job.status,
            "stage": job.stage, "created_at": job.created_at, "events_url": f"/v1/screenings/{job.id}/events",
            "memo_id": job.memo_id, "memo_url": f"/v1/memos/{job.memo_id}" if job.memo_id else None,
            "error": job.error,
        })

    def memo(self, memo_id: str) -> dict:
        if memo_id not in self.memos:
            raise NotFound(memo_id)
        return self.memos[memo_id][0]

    async def what_if(self, memo_id: str, req: dict) -> dict:
        self._check_request("what_if_request", req)
        return self._check("what_if_response", await what_if(self.memo(memo_id), req, self.pipeline))

    # ------------------------------------------------------------------ batches

    async def start_batch(self, req: dict, *, start: bool = True) -> Batch:
        self._check_request("batch_request", req)
        pol = policy.with_defaults(req.get("policy"))
        job = Job(id=new_id("batch"), kind="batch", created_at=self.pipeline.now())
        items = [{"index": i, "client_ref": f.get("client_ref"), "label": batchmod.label(f), "status": "queued",
                  "memo_id": None, "memo_url": None, "decision": None, "probability": None, "distributions": None,
                  "facets": None, "filtered_out": False, "unknown_count": None, "conflict_count": None, "error": None}
                 for i, f in enumerate(req["founders"])]
        b = Batch(job=job, request=req, policy_used=policy.resolve(self.pipeline.artifacts.thresholds, pol)["policy"],
                  items=items, batch_ref=req.get("batch_ref"))
        self.jobs[job.id] = job
        self.batches[job.id] = b
        await self._emit(job, "stage", f"Batch of {len(items)} founder(s) queued.", stage="queued")
        if start:
            self._spawn(self.run_batch(b))
        return b

    async def run_batch(self, b: Batch) -> None:
        b.job.status = "running"
        options = b.request.get("options") or {}
        gate = asyncio.Semaphore(min(options.get("concurrency", self.batch_concurrency), self.batch_concurrency))
        pol = {k: b.policy_used[k] for k in ("target", "timeline_years", "risk", "filters") if k in b.policy_used}

        async def one(i: int, inp: dict):
            async with gate:
                item = b.items[i]
                inp = dict(inp)
                if "research" in options:
                    inp["options"] = {**(inp.get("options") or {}), "research": options["research"]}
                if "max_searches_per_founder" in options:
                    inp["options"] = {**(inp.get("options") or {}), "max_searches": options["max_searches_per_founder"]}
                item["status"] = "running"
                child = await self.start_screening(inp, start=False)
                memo = await self.run_screening(child, inp, policy_override=pol)
                if memo is None:
                    item.update(status="failed", error=child.error)
                else:
                    item.update(batchmod.item_from_memo(i, memo))
                await self._emit(b.job, "batch_item", f"{item['label']}: {item['decision'] or item['status']}.", data=item)

        await asyncio.gather(*(one(i, f) for i, f in enumerate(b.request["founders"])))
        failed = sum(it["status"] == "failed" for it in b.items)
        self._finish(b.job, "complete" if not failed else ("failed" if failed == len(b.items) else "partial"))
        c = batchmod.counts(b.items)
        await self._emit(b.job, "stage", f"Done: {c['advance']} advance, {c['escalate']} escalate, {c['pass']} pass.",
                         stage="done" if b.job.status != "failed" else "failed")

    def batch(self, batch_id: str) -> Batch:
        if batch_id not in self.batches:
            raise NotFound(batch_id)
        return self.batches[batch_id]

    def batch_doc(self, b: Batch) -> dict:
        items = b.items
        prog = {s: sum(it["status"] == s for it in items) for s in ("queued", "running", "complete", "failed")}
        return self._check("batch_response", {
            "schema_version": VERSION, "batch_id": b.job.id, "batch_ref": b.batch_ref, "status": b.job.status,
            "created_at": b.job.created_at, "policy": b.policy_used, "progress": {"total": len(items), **prog},
            "counts": batchmod.counts(items), "items": items, "events_url": f"/v1/batches/{b.job.id}/events",
            "mock": self.pipeline.any_mock, "disclaimer": DISCLAIMER,
        })
