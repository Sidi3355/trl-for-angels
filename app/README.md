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
| `backend/` | FastAPI service: screening, live progress (SSE), memos, what-if, batch, artefacts, and the research agent | Task 2: done, on mocks. Task 3: agent built and tested offline; real-founder test pending the key |
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

## The research agent (`AGENT=claude`)

`backend/screener/pipeline/agent.py` asks Claude (default `claude-opus-5-5`, effort `medium`) to research
one founder with web search and web fetch. It finishes by calling a strictly typed `submit_profile`
tool with `{value, source_url, confidence, evidence}` for every template field, plus the founding date,
its sources, post-founding facts and every real name it saw. Code then enforces the plan's rules:

- **Founding-date cutoff:** a field whose only source describes the time after founding becomes
  unknown. Post-founding facts go to the memo's notes, never to the model.
- **Confidence floor:** a value under `AGENT_MIN_CONFIDENCE` (0.5) becomes unknown, with the guess in a note.
- **Template values:** a value outside the template's allowed values becomes unknown.
- **Anonymisation** (`pipeline/render.py`): the founder's and company's names, and every name the agent
  saw, are removed from free-text values, and a rendered profile that still contains one is refused.
- **Spend caps** (`pipeline/budget.py`), costed from the API's own usage numbers:
  `AGENT_MAX_COST_PER_FOUNDER_USD` (default $1) and `AGENT_BUDGET_USD` for the whole process
  (default $5; it resets on restart). The hard cap is the spend limit on the key's workspace in the
  Claude Console: set one.
- Requests always go to `AGENT_BASE_URL` (`https://api.anthropic.com`), never to an
  `ANTHROPIC_BASE_URL` set in the environment. Refusals fall back server-side (`fallbacks: "default"`).

Try it on the five real test founders in `backend/tools/test_founders.json` (a dry run without `--spend`):

```bash
app/backend/.venv/bin/python app/backend/tools/research_founders.py --spend --only awotona
```

It prints each founder's rendered profile, every field's provenance and source, the post-founding
facts it kept out, and the cost. Results are saved in `app/backend/.research_runs/`, which is
git-ignored because it holds real people's research. In the Claude Code cloud sandbox, the key goes in
`SCREENER_ANTHROPIC_API_KEY`, because Claude Code itself reads `ANTHROPIC_API_KEY`.

## Configuration: one setting per mock-to-real swap

All settings are environment variables (or `app/backend/.env` locally; see `app/backend/.env.example`).

| Setting | Default | Real | What it switches |
|---|---|---|---|
| `ARTIFACTS_DIR` | `app/contract/mocks` | `shared/artifacts` | `rules.json`, `thresholds.json`, `model.json` |
| `AGENT` | `mock` | `claude` (needs `SCREENER_ANTHROPIC_API_KEY` or `ANTHROPIC_API_KEY`) | The research agent |
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
