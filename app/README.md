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
| `backend/` | FastAPI service: screening, batch, progress streaming, what-if, research agent, merge, render | Task 2 (skeleton), task 3 (agent) |
| `frontend/` | Mobile-first Next.js PWA: form, live progress, memo, controls, batch triage | Tasks 4, 5, 7 |

## Run locally

```bash
pip install -r app/contract/requirements.txt
python app/contract/tools/validate.py      # check the contract, mocks and examples
python app/contract/tools/build_mocks.py   # regenerate the mocks after a contract change
```

The backend and frontend instructions arrive with tasks 2 and 4.

## What's mocked, and how to switch to the real artefacts

The research session produces three artefacts in `shared/artifacts/` (see `shared/README.md`). Until they
exist, the app uses mocks with the same file names and structure:

| Artefact | Mock | Real (when ready) | What the mock stands in for |
|---|---|---|---|
| `rules.json` | `app/contract/mocks/rules.json` (20 questions) | `shared/artifacts/rules.json` (about 100) | RRF's question list (step B1) |
| `thresholds.json` | `app/contract/mocks/thresholds.json` | `shared/artifacts/thresholds.json` | The val precision and recall table (step D4) |
| `model.json` | `app/contract/mocks/model.json` | `shared/artifacts/model.json` | The production Kev endpoint and input type (steps D2, D3) |

Switching is one setting: `ARTIFACTS_DIR=shared/artifacts` (default `app/contract/mocks`; added in task 2).
Before switching, run `python app/contract/tools/validate.py --artifacts shared/artifacts`.

The answerer (Jev) and decider (Kev) are also mocked, by `contract/tools/mock_model.py`, until their keys
and endpoint exist. Every mock memo carries `"mock": true` and a visible warning.

## Secrets

Keys come from environment variables only, never from the repo: `ANTHROPIC_API_KEY` (research agent),
`TYPESAFE_API_KEY` (Jev), `KEV_API_KEY` if the Kev endpoint needs one, `ELEVENLABS_API_KEY` (voice
features), and the push-notification keys. `app/backend/.env.example` (task 2) lists them all.

## Deploy

Planned for task 6: the frontend on Vercel (root directory `app/frontend`), the backend on Railway.
