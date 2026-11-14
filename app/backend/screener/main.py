"""FastAPI app: the endpoints in app/contract/README.md ("API surface").

Run locally:  uvicorn screener.main:app --reload --app-dir app/backend
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .artifacts import NAMES as ARTIFACT_NAMES
from .artifacts import load_artifacts
from .config import Settings, secret
from .contract import Contract, ContractError
from .mocks.founders import DEMO_FOUNDERS
from .pipeline.batch import CsvError, parse_csv
from .pipeline.context import NotConfigured, Pipeline
from .pipeline.models import JevAnswerer, KevDecider, MockAnswerer, MockDecider
from .pipeline.research import ClaudeAgent, MockAgent
from .pipeline.whatif import WhatIfError
from .service import InvalidRequest, NotFound, Service

log = logging.getLogger("screener")
VERSION = "0.1.0"
SSE_KEEPALIVE_S = 15


def build_components(settings: Settings, artifacts) -> tuple[dict, dict]:
    """Instantiate the configured agent, answerer and decider; collect what isn't available."""
    built, errors = {}, {}
    makers = {
        "agent": {"mock": MockAgent,
                  "claude": lambda: ClaudeAgent(secret(settings.anthropic_api_key), settings.agent_model,
                                                settings.agent_max_searches)},
        "answerer": {"mock": MockAnswerer, "jev": lambda: JevAnswerer(secret(settings.typesafe_api_key))},
        "decider": {"mock": MockDecider, "kev": lambda: KevDecider(secret(settings.kev_api_key), artifacts.model)},
    }
    for part, options in makers.items():
        choice = getattr(settings, part)
        try:
            built[part] = options[choice]()
        except NotConfigured as e:
            errors[part] = str(e)
    return built, errors


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.errors = {}
        app.state.service = None
        app.state.artifacts = None
        contract = Contract(settings.path(settings.contract_dir))
        try:
            artifacts = load_artifacts(settings.path(settings.artifacts_dir), contract)
            app.state.artifacts = artifacts
        except (FileNotFoundError, ContractError, json.JSONDecodeError) as e:
            app.state.errors["artifacts"] = str(e)
            log.error("artefacts not loaded: %s", e)
        if app.state.artifacts is not None:
            parts, errors = build_components(settings, app.state.artifacts)
            app.state.errors.update(errors)
            if not errors:
                pipeline = Pipeline(artifacts=app.state.artifacts, pace=settings.mock_pace,
                                    extra={"artifacts_dir_label": settings.artifacts_dir}, **parts)
                app.state.service = Service(
                    pipeline, contract, retention_minutes=settings.retention_minutes,
                    max_concurrent=settings.max_concurrent_screenings,
                    batch_concurrency=settings.batch_max_concurrency, validate=settings.validate_responses)
        for part, msg in app.state.errors.items():
            log.error("not configured: %s: %s", part, msg)
        sweeper = asyncio.create_task(_sweep_forever(app))
        try:
            yield
        finally:
            sweeper.cancel()

    app = FastAPI(
        title="Angel screening API",
        version=VERSION,
        description="Deal-screening agent backend. Request and response shapes are the JSON Schemas in "
                    "app/contract/schemas. Screening aid, not investment advice.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Access-Token", "Last-Event-ID"],
    )
    _install_error_handlers(app)
    app.get("/health", tags=["health"])(health)
    app.include_router(_router(settings))
    return app


async def _sweep_forever(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(60)
        if app.state.service is not None:
            app.state.service.sweep()


# ------------------------------------------------------------------------- errors

def _error(status: int, code: str, message: str, *, retryable: bool = False, details: list | None = None):
    body = {"error": {"code": code, "message": message, "retryable": retryable}}
    if details:
        body["details"] = details
    return JSONResponse(body, status_code=status)


class BadRequest(ValueError):
    pass


class _Unauthorized(Exception):
    pass


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(_Unauthorized)
    async def _unauth(_, e: _Unauthorized):
        return _error(401, "unauthorized", "missing or wrong access token (X-Access-Token)")

    @app.exception_handler(InvalidRequest)
    async def _invalid(_, e: InvalidRequest):
        return _error(422, "invalid_request", str(e), details=e.errors)

    @app.exception_handler(CsvError)
    async def _csv(_, e: CsvError):
        return _error(422, "invalid_csv", str(e), details=e.details)

    @app.exception_handler(WhatIfError)
    async def _whatif(_, e: WhatIfError):
        return _error(422, "invalid_what_if", str(e))

    @app.exception_handler(BadRequest)
    async def _bad(_, e: BadRequest):
        return _error(400, "bad_request", str(e))

    @app.exception_handler(NotFound)
    async def _missing(_, e: NotFound):
        return _error(404, "not_found", f"{e.args[0]} not found (it may have expired: nothing is kept after the session)")

    @app.exception_handler(NotConfigured)
    async def _unconfigured(_, e: NotConfigured):
        return _error(503, "not_configured", str(e), retryable=True)

    @app.exception_handler(ContractError)
    async def _drift(_, e: ContractError):
        log.error("response broke the contract: %s", e)
        return _error(500, "contract_violation", "the server produced a response that breaks the contract",
                      details=e.errors[:20])


# ------------------------------------------------------------------------- routes

async def health(request: Request) -> dict:
    s: Settings = request.app.state.settings
    svc: Service | None = request.app.state.service
    arts = request.app.state.artifacts
    errors = request.app.state.errors
    return {
        "status": "ok" if svc is not None else "degraded",
        "version": VERSION,
        "env": s.env,
        "components": {"agent": s.agent, "answerer": s.answerer, "decider": s.decider},
        "artifacts": arts.summary() if arts else None,
        "mock": svc.pipeline.any_mock if svc else None,
        "errors": errors,
        "keys": s.key_status(),
        "jobs": svc.stats() if svc else None,
    }


def service(request: Request) -> Service:
    svc = request.app.state.service
    if svc is None:
        raise NotConfigured("the backend isn't fully configured: " + "; ".join(
            f"{k}: {v}" for k, v in request.app.state.errors.items()))
    return svc


async def _json_body(request: Request):
    try:
        return await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise BadRequest("the request body must be JSON") from None


def _sse(job, after: int, request: Request) -> StreamingResponse:
    async def stream():
        yield "retry: 3000\n\n"
        seq = after
        while True:
            for ev in job.events_after(seq):
                yield f"id: {ev['seq']}\nevent: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                seq = ev["seq"]
            if job.finished and not job.events_after(seq):
                return
            if not await job.wait_for_more(seq, SSE_KEEPALIVE_S):
                if await request.is_disconnected():
                    return
                yield ": keep-alive\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _events(job, request: Request, after: int | None, last_event_id: str | None, fmt: str):
    start = after if after is not None else (int(last_event_id) if last_event_id and last_event_id.isdigit() else -1)
    if fmt == "json":
        return job.events_after(start)
    return _sse(job, start, request)


def _csv_row_error(err: str, req: dict) -> str:
    """'founders/0/fields/cofounders: ...' -> 'row 1, cofounders: ...' for spreadsheet users."""
    m = re.match(r"^founders/(\d+)/(?:fields/|founder/)?([^:]*): (.*)$", err)
    if not m:
        return err
    ref = req["founders"][int(m[1])].get("client_ref", f"row-{int(m[1]) + 1}")
    return f"{ref.replace('-', ' ')}, {m[2] or 'row'}: {m[3]}"


def _router(settings: Settings) -> APIRouter:
    async def access(x_access_token: str | None = Header(default=None),
                     access_token: str | None = Query(default=None, include_in_schema=False)):
        want = secret(settings.access_token)
        if want and want not in (x_access_token, access_token):
            raise _Unauthorized()

    r = APIRouter(prefix="/v1", dependencies=[Depends(access)])

    @r.post("/screenings", status_code=202, tags=["screenings"],
            summary="Screen one founder (body: contract investor_input)")
    async def create_screening(request: Request, svc: Service = Depends(service)):
        job = await svc.start_screening(await _json_body(request))
        return JSONResponse(svc.job_doc(job), status_code=202, headers={"Location": f"/v1/screenings/{job.id}"})

    @r.get("/screenings/{job_id}", tags=["screenings"])
    async def get_screening(job_id: str, svc: Service = Depends(service)):
        return svc.job_doc(svc.job(job_id))

    @r.get("/screenings/{job_id}/events", tags=["screenings"],
           summary="Progress events: SSE (resumable with Last-Event-ID or ?after=), or ?format=json")
    async def screening_events(job_id: str, request: Request, after: int | None = None,
                               format: Literal["sse", "json"] = "sse",
                               last_event_id: str | None = Header(default=None),
                               svc: Service = Depends(service)):
        return _events(svc.job(job_id), request, after, last_event_id, format)

    @r.get("/memos/{memo_id}", tags=["memos"])
    async def get_memo(memo_id: str, svc: Service = Depends(service)):
        return svc.memo(memo_id)

    @r.post("/memos/{memo_id}/what-if", tags=["memos"], summary="Re-run the decider with changes (body: what_if_request)")
    async def memo_what_if(memo_id: str, request: Request, svc: Service = Depends(service)):
        return await svc.what_if(memo_id, await _json_body(request))

    @r.post("/batches", status_code=202, tags=["batches"],
            summary="Screen a list: JSON batch_request, or a CSV body (Content-Type: text/csv)")
    async def create_batch(request: Request, svc: Service = Depends(service),
                           target: Literal["$50M", "$500M", "$1B"] | None = None,
                           timeline_years: Literal[5, 8] | None = None,
                           risk: Literal["cautious", "balanced", "bold"] | None = None):
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype in ("text/csv", "application/csv", "text/plain"):
            pol = {k: v for k, v in {"target": target, "timeline_years": timeline_years, "risk": risk}.items() if v}
            try:
                text = (await request.body()).decode("utf-8-sig")
            except UnicodeDecodeError:
                raise BadRequest("the CSV must be UTF-8") from None
            req = parse_csv(text, pol or None)
            try:
                b = await svc.start_batch(req)
            except InvalidRequest as e:
                e.errors = [_csv_row_error(err, req) for err in e.errors]
                raise
        else:
            b = await svc.start_batch(await _json_body(request))
        return JSONResponse(svc.batch_doc(b), status_code=202, headers={"Location": f"/v1/batches/{b.job.id}"})

    @r.get("/batches/{batch_id}", tags=["batches"])
    async def get_batch(batch_id: str, svc: Service = Depends(service)):
        return svc.batch_doc(svc.batch(batch_id))

    @r.get("/batches/{batch_id}/events", tags=["batches"])
    async def batch_events(batch_id: str, request: Request, after: int | None = None,
                           format: Literal["sse", "json"] = "sse",
                           last_event_id: str | None = Header(default=None),
                           svc: Service = Depends(service)):
        return _events(svc.batch(batch_id).job, request, after, last_event_id, format)

    @r.get("/artifacts/{name}", tags=["artifacts"],
           summary="The active rules.json, thresholds.json or model.json (the client computes controls from them)")
    async def get_artifact(name: Literal["rules", "thresholds", "model"], svc: Service = Depends(service)):
        assert name in ARTIFACT_NAMES
        return JSONResponse(svc.pipeline.artifacts.get(name), headers={"Cache-Control": "max-age=300"})

    @r.get("/demo/founders", tags=["demo"], summary="Investor inputs for the three fictional demo founders")
    async def demo_founders():
        return [spec["input"] for spec in DEMO_FOUNDERS]

    return r


app = create_app()
