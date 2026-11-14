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
| `backend/` | FastAPI service: screening, live progress (SSE), memos, what-if, batch, artefacts, and the research agent | Task 2: done, on mocks. Task 3: done (agent tested on 5 real founders) |
| `frontend/` | Installable mobile-first Next.js app: founders list, screening, live progress, memo, your bar, what-ifs | Task 4: done and redesigned, on mocks. Push and share (task 5) and batch UI (task 7) to come |

## Run the frontend locally

Node 20.9 or later. With the backend running on port 8000 (below):

```bash
cd app/frontend
npm ci
npm run dev          # http://localhost:3000; the backend's default CORS setting allows it
npm test             # the client-side controls must reproduce the backend's verdicts exactly
npm run typecheck
```

`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) points it at another backend. It is read at
build time, so set it before `npm run build` or in Vercel's environment variables.

What the frontend does, screen by screen (redesigned 2026-11-14 as an installable product: a bottom tab bar
on phones, a sidebar on desktop, light and dark themes):

- **Founders** (`/`): one search-style box to screen a founder by name, LinkedIn or website, and the founders
  screened this session with their verdict at your bar, filterable by advance, escalate or pass. Three
  fictional examples run in one tap. The list lives in `sessionStorage`, so it goes when the app closes.
- **Your bar** (a sheet, opened from Founders, the sidebar, any memo or About): target outcome, timeline, risk
  appetite and hard filters, with a plain reading of what the setting means on validation founders. Set once,
  applied to every verdict instantly (`localStorage`: a preference, not founder data).
- **Screen** (`/new`): the founder, plus optional facts you already know (tap-to-pick chips), notes and the
  research switch.
- **Progress** (`/screenings/[jobId]`): a progress bar, the pipeline steps and a short live feed over
  server-sent events; it opens the memo when it's ready, and falls back to polling the job if the stream drops.
- **Memo** (`/memos/[memoId]`): the verdict with the chance and a to-scale gauge (pinned on the left on
  desktop); the factors that move the score, ranked at your bar, each one tap away from a what-if that the
  backend re-scores; how it could end (outcome and timing charts); the founder at founding with sources;
  things worth knowing (conflicts, unknowns, warnings); notes; sources; and, under the hood, the exact
  anonymised text and answers the model read.
- **How it works** (`/about`): the four steps, how to read a verdict, settings (your bar, clear the session,
  forget the passcode, service status) and privacy.
- **Installable:** `app/manifest.ts` and `public/icons/`, so "Add to Home Screen" opens it full-screen with its
  own icon. Push and the share Shortcut are task 5.
- **Design system ("the odds slip", second redesign by a Claude Fable 5.2 design pass):** black ink on neutral
  paper, colour kept for the verdict alone, shown as a full-colour slab (green advance, amber escalate, ink pass)
  with the chance in large condensed figures and a to-scale gauge whose zones differ by pattern as well as tone.
  One variable family, Archivo, at three widths (condensed figures, normal text, wide labels). Buttons and
  selections are ink, not a brand colour. A floating dock on phones, a sidebar on desktop. Tokens in
  `src/app/globals.css`, building blocks in `src/components/ui.tsx`. Chart colours were checked with the dataviz
  skill's palette validator against both themes' surfaces.
- **Logic:** `src/lib/policy.ts` ports `backend/screener/policy.py` (tested against the mock verdicts);
  `src/lib/bar.ts` applies the bar to the Deals list; `src/lib/api.ts` talks to the backend.
- **Passcode:** if the backend has `ACCESS_TOKEN` set, the app asks for it on the first refused request and
  keeps it in `sessionStorage` only.

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
one founder with web search and web fetch. It finishes by calling a typed `submit_profile` tool with
`{value, source_url, confidence, evidence}` for every template field, plus the founding date, its sources,
post-founding facts and every real name it saw. The schema is too large for the API's strict mode, so
every submission is validated against it in code, and an invalid one goes back to the model with the
errors. Code then enforces the plan's rules:

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

In the Claude Code cloud sandbox, prefix it with `AGENT_MAX_FETCHES=0`: the API refuses web fetch from
restricted-network sandboxes, so the agent there runs on web search alone.

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

The frontend goes on Vercel (root directory `app/frontend`) and the backend on Railway.

**Backend (Railway).** `backend/Dockerfile` builds from the repo root and keeps the repo layout, because
the service reads `app/contract` and `shared/`. `backend/railway.json` points Railway at it and adds the
`/health` check. One-time setup in Railway's dashboard: create a project from the GitHub repo, set the
service's branch, add the variables below, and generate a domain. Keep it to one replica: jobs and memos
live in memory. In practice the "Railway config file" setting didn't take effect (Railway kept guessing
with Railpack and failed with "No start command detected"), so `RAILWAY_DOCKERFILE_PATH` is the reliable
way to point Railway at the Dockerfile. Leave Root Directory empty.

| Variable | Value |
|---|---|
| `RAILWAY_DOCKERFILE_PATH` | `app/backend/Dockerfile` |
| `ACCESS_TOKEN` | A passcode of your choice. The app asks for it once per session. |
| `CORS_ORIGIN_REGEX` | `https://trl-for-angels[a-z0-9-]*\.vercel\.app` (production and preview URLs) |
| `AGENT`, `SCREENER_ANTHROPIC_API_KEY` | Only for real research: `AGENT=claude` and the key. Leave out to stay on mocks. |

**Frontend (Vercel).** Project `trl-for-angels`: root directory `app/frontend`, framework Next.js, Node 22,
and `NEXT_PUBLIC_API_URL` set to the Railway domain (read at build time, so change it and redeploy). Pushes to
`app-track` and `main` build; the Ignored Build Step skips every other branch (the research branch has no frontend). Each branch gets a stable address, `trl-for-angels-git-<branch>-siddarths-projects-2714c925.vercel.app`;
all deployments are behind Vercel's login (the project's deployment protection), so you sign in to Vercel
once on the phone.

**Live now (2026-11-14):** backend `https://trl-for-angels-production.up.railway.app` (branch `app-track`,
mocks); frontend `https://trl-for-angels-git-app-track-siddarths-projects-2714c925.vercel.app`.
