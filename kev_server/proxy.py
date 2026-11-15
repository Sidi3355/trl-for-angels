"""The Space's front door: one port, two kev.serve backends, an optional bearer key.

/answerer/... goes to base Kev (localhost:8009), /decider/... to the production model
(localhost:8010). Requests and replies pass through unchanged, so clients see kev.serve's own
System One API. With KEV_API_KEY set, every request needs Authorization: Bearer <key>.
"""

from __future__ import annotations

import hmac
import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

BACKENDS = {"answerer": "http://127.0.0.1:8009", "decider": "http://127.0.0.1:8010"}
API_KEY = os.environ.get("KEV_API_KEY") or None
DECIDER = os.environ.get("DECIDER_MODEL") or None
PASS_HEADERS = ("content-type", "x-typesafe-request-id")

app = FastAPI(title="trl-for-angels Kev")
client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=5.0))


def _authorised(request: Request) -> bool:
    if API_KEY is None:
        return True
    given = request.headers.get("authorization", "")
    return hmac.compare_digest(given, f"Bearer {API_KEY}")


async def _up(url: str) -> dict | None:
    try:
        r = await client.get(f"{url}/v1/models", timeout=5)
        return r.json()["models"][0] if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None


@app.get("/health")
async def health() -> JSONResponse:
    status = {}
    for name, url in BACKENDS.items():
        m = await _up(url)
        status[name] = {"ready": m is not None,
                        **({"run": m.get("run"), "temperature": m.get("temperature")} if m else {})}
    status["decider"]["stand_in"] = DECIDER is None
    ready = all(v["ready"] for k, v in status.items() if isinstance(v, dict) and "ready" in v)
    return JSONResponse({"ready": ready, **status}, status_code=200 if ready else 503)


@app.api_route("/{role}/{path:path}", methods=["GET", "POST"])
async def forward(role: str, path: str, request: Request) -> Response:
    if role not in BACKENDS:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    if not _authorised(request):
        return JSONResponse({"detail": "missing or wrong bearer key"}, status_code=401)
    try:
        upstream = await client.request(
            request.method, f"{BACKENDS[role]}/{path}", content=await request.body(),
            headers={"content-type": request.headers.get("content-type", "application/json")})
    except httpx.ConnectError:
        return JSONResponse({"detail": f"{role} is still loading; retry shortly"},
                            status_code=503)
    headers = {k: v for k, v in upstream.headers.items() if k.lower() in PASS_HEADERS}
    return Response(upstream.content, status_code=upstream.status_code, headers=headers)
