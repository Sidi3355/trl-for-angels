# App: deal-screening agent for angel investors

The product half of the project (`MASTER_PLAN.md` sections 8 and 8b). An investor enters what they know
about a founder, or shares a LinkedIn or website link. A research agent fills in the rest from public,
pre-founding information. The app then renders the frozen profile template, scores it with the
production Kev model, and returns a memo with an advance, escalate or pass verdict and controls the
investor can tune.

**Screening aid, not investment advice.** The model is trained on generated data; no real-world
accuracy is claimed.

## Layout

| Folder | What it is | Status |
|---|---|---|
| `contract/` | JSON Schemas for every request, response and artefact, plus mocks and validators. See `contract/README.md`. | Task 1: done |
| `backend/` | FastAPI service: screening, live progress (SSE), memos, what-if, batch, artefacts | Task 2: done, on mocks. Real agent in task 3 |
| `frontend/` | Mobile-first Next.js PWA: form, live progress, memo, controls, batch triage | Tasks 4, 5, 7 |

## Run the backend locally

Python 3.13 (3.12 works). From the repo root:

```bash
uv venv app/backend/.venv --python 3.13
uv pip install --python app/backend/.venv/bin/python -r app/backend/requirements-dev.txt
app/backend/.venv/bin/uvicorn screener.main:app --app-dir app/backend --reload --port 8000
```

Then open `http://localhost:8000/docs` for the interactive API, or try it from a terminal:

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/v1/screenings -H 'Content-Type: application/json' -d @app/contract/examples/investor_input_escalate.json
curl -sN localhost:8000/v1/screenings/<job_id>/events
curl -s -X POST localhost:8000/v1/batches -H 'Content-Type: text/csv' --data-binary @app/contract/examples/batch.csv
```

The three fictional demo founders (`GET /v1/demo/founders`) get canned research. Anyone else gets only
the fields you enter, because mock mode runs no web research. A mock screening takes about 5 seconds,
so the progress view has something to show; set `MOCK_PACE=0` to make it instant.

Tests (every response is checked against the contract, and the service must reproduce the committed
mock memos exactly):

```bash
cd app/backend && .venv/bin/python -m pytest
python app/contract/tools/validate.py      # contract, mocks and examples
python app/contract/tools/build_mocks.py   # regenerate mocks after a contract or pipeline change
```

## Configuration: one setting per mock-to-real swap

All settings are environment variables (or `app/backend/.env` locally; see `app/backend/.env.example`).

| Setting | Default | Real | What it switches |
|---|---|---|---|
| `ARTIFACTS_DIR` | `app/contract/mocks` | `shared/artifacts` | `rules.json`, `thresholds.json`, `model.json` |
| `AGENT` | `mock` | `claude` (task 3; needs `ANTHROPIC_API_KEY`) | The research agent |
| `ANSWERER` | `mock` | `jev` (needs `TYPESAFE_API_KEY`) | Answers to the rules (answers mode only) |
| `DECIDER` | `mock` | `kev` (endpoint from `model.json`) | Outcome and years distributions |

Each swap is independent. For example, the real artefacts work while Jev and Kev are still mocked, and
`model.json`'s `decider_input` switches between answers mode and profile mode with no code change.
Before switching `ARTIFACTS_DIR`, run `python app/contract/tools/validate.py --artifacts shared/artifacts`.
If a real component is selected but can't run (a missing key, or not built yet), the server still starts:
`/health` says `degraded` and explains, and screening requests return 503 with the reason.

Other settings: `CORS_ORIGINS` and `CORS_ORIGIN_REGEX` (the frontend's address), `ACCESS_TOKEN`
(optional shared passcode for `/v1`), `RETENTION_MINUTES` (default 120), `MAX_CONCURRENT_SCREENINGS`,
`BATCH_MAX_CONCURRENCY`, `MOCK_PACE` and `VALIDATE_RESPONSES`.

## What's mocked, and how to switch to the real artefacts

The research session produces three artefacts in `shared/artifacts/` (see `shared/README.md`). Until they
exist, the app uses mocks with the same file names and structure:

| Artefact | Mock | Real (when ready) | What the mock stands in for |
|---|---|---|---|
| `rules.json` | `app/contract/mocks/rules.json` (20 questions) | `shared/artifacts/rules.json` (about 100) | RRF's question list (step B1) |
| `thresholds.json` | `app/contract/mocks/thresholds.json` | `shared/artifacts/thresholds.json` | The val precision and recall table (step D4) |
| `model.json` | `app/contract/mocks/model.json` | `shared/artifacts/model.json` | The production Kev endpoint and input type (steps D2, D3) |

The answerer (Jev), decider (Kev) and research agent are mocked by `backend/screener/mocks/` until their
keys and endpoint exist. Every memo made with any mock carries `"mock": true` and a visible warning
saying which parts are mocked.

## Privacy and storage

Jobs, memos and batches live in the backend's memory only, and are deleted `RETENTION_MINUTES` after they
finish (MASTER_PLAN guardrail: nothing stored after the session). Because state is in memory, the
backend runs as a single instance. Logs never contain keys; `/health` shows only whether each key is set.

## Secrets

Keys come from environment variables only, never from the repo: `ANTHROPIC_API_KEY` (research agent),
`TYPESAFE_API_KEY` (Jev), `KEV_API_KEY` if the Kev endpoint needs one, `ELEVENLABS_API_KEY` (voice
features), and the `VAPID_*` push-notification keys. `app/backend/.env.example` lists every setting.

## Deploy

Planned for task 6: the frontend on Vercel (root directory `app/frontend`), the backend on Railway.
Note: automatic Vercel builds are switched off for now (the project's "Ignored Build Step" is set to
`exit 0`), because the repo has no frontend yet and every push made a failed build. Task 6 removes it.
