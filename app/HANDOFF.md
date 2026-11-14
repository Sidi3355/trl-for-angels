# App track: handoff for a new session

Read this first, then `MASTER_PLAN.md` (the settled plan), `app/README.md` and `app/contract/README.md`.
It holds the owner's brief and the decisions made so far, which live nowhere else in the repo.

## The brief (from the project owner)

You build the **app track** (MASTER_PLAN sections 8 and 8b), in parallel with a separate Claude Code
session that runs the research. Build against mocks now; swap in the real research outputs when they land.

- **Where:** work only in `app/`, on branch `app-track` (rebased on `main`). Push only to `app-track`.
  Merge into `main` only when the owner says so.
- **Never edit** `research/`, `data/`, `results/` or `MASTER_PLAN.md` (the owner once allowed a one-off
  edit: section 8b, already on `main`).
- **`shared/`** is the only folder both sessions touch. `shared/README.md` and `shared/profile_template.md`
  were created by the app session and are now read-only. **Never write to `shared/artifacts/`**: the
  research session owns it.
- **Mocks** live in `app/contract/mocks/` with the real file names. Switching to real artefacts is one
  setting: `ARTIFACTS_DIR=shared/artifacts`.
- If you need anything from the research side (an artefact, a field, a format), **tell the owner**; they
  pass it on. Don't create it yourself.
- The founder profile template is **frozen**: render it exactly, line for line.

**Working rules:** do tasks in order, **stop after each one, show the result, and wait for the go-ahead**.
Ask before anything that costs money, deploys publicly or needs an account action. Keys only from env
vars, never committed. Keep everything swappable. Keep `app/README.md` up to date. Note anything in
MASTER_PLAN.md that looks inconsistent instead of silently working around it.

## Tasks and status

| # | Task | Status |
|---|---|---|
| 1 | API contract and mocks (`app/contract/`) | Done |
| 2 | FastAPI backend on mocks (`app/backend/`) | Done |
| 3 | Research agent, merge, render; test on 5 real founders | **In progress:** built and tested offline (29 tests). Next: the paid run on real founders |
| 4 | Mobile-first Next.js PWA (`app/frontend/`): form, live progress, memo, client-side controls, what-ifs, disclaimer | Not started |
| 5 | PWA features: manifest, share target, web push; phone test instructions (iOS and Android differ) | Not started |
| 6 | Hosting: frontend on Vercel, backend on Railway, both on mocks | Not started |
| 7 | Batch mode UI: CSV upload, triage view | Not started (the backend side exists) |

## Next step (task 3, part 2)

1. Recreate the venv (it isn't committed):
   `uv venv app/backend/.venv --python 3.13 && uv pip install --python app/backend/.venv/bin/python -r app/backend/requirements-dev.txt`
2. Check `SCREENER_ANTHROPIC_API_KEY` is set (never print it). If not, ask the owner to add it as an
   environment variable in the cloud environment's settings. Not `ANTHROPIC_API_KEY`: Claude Code itself reads that.
3. Run **one** founder: `app/backend/.venv/bin/python app/backend/tools/research_founders.py --spend --only awotona`
4. Show the owner the rendered profile, the field sources, the post-founding notes kept out, and the
   cost. Ask them to confirm in the Claude Console that the usage landed on their key.
5. Run the other four (`dubugras`, `young`, `paananen`, `cheung`) only after they approve. Then stop:
   task 3 is done when the owner has seen the rendered profiles plus sources.

## Decisions made

- **PWA (Next.js), not Expo.** The owner's phone is an **iPhone 17 on the latest iOS**. iOS doesn't support
  the Web Share Target API, so sharing on iPhone uses an iOS Shortcut that opens `/share?url=...`. Web
  push works on iPhone once the app is added to the Home Screen.
- **Hosting:** frontend on **Vercel**, backend on **Railway**: a single always-on process, because jobs,
  memos and push subscriptions live in memory and nothing is stored after the session.
- **Research agent:** `claude-opus-5-5`, effort `medium`, server-side refusal fallback on. Caps: 10 searches
  and $1 per founder, $5 in total (`AGENT_MAX_COST_PER_FOUNDER_USD`, `AGENT_BUDGET_USD`). The owner may also
  set a spend limit on the key's workspace in the Claude Console; recommend it before task 6.
- **Test founders** (`app/backend/tools/test_founders.json`): Tope Awotona, Henrique Dubugras, Tracy Young,
  Ilkka Paananen, Adora Cheung. Each tests something different; reference facts are in the file.
- **Risk appetite rule** (`screener/policy.py`): advance threshold = highest threshold still flagging 25% /
  50% / 75% of val winners (cautious / balanced / bold); pass below the threshold keeping 90% of winners.
- Education and jobs merge as whole lists (an investor list replaces the agent's).

## Sandbox quirks (Claude Code cloud environment)

- The secure credential form refuses Anthropic hosts ("authenticated by the session itself"), so the key
  goes in as an environment variable. Using the session's own Anthropic access is ruled out: it would
  bill the owner's Claude plan with no spend cap.
- `ANTHROPIC_BASE_URL` is set in the sandbox to Claude Code's own gateway. The agent always uses
  `AGENT_BASE_URL=https://api.anthropic.com` explicitly. Confirm on the first paid call that the proxy
  passes the owner's key through. If it doesn't, run the test on Railway instead.
- A Vercel connector is available in this environment. The Vercel project `trl-for-angels` has
  **"Ignored Build Step" set to `exit 0`**, so pushes don't trigger failing builds. **In task 6:** remove
  it, set the root directory to `app/frontend` and the framework to Next.js.

## Open items with the owner

- **For the research session** (owner to relay; full list in `shared/README.md` and
  `app/contract/README.md`, "For the research session"):
  - confirm the proposed artefact formats in `app/contract/artifacts/`
  - the full production request in `model.json`
  - a TRL-faithful way to get Jev answers (for example the pickled RRF)
  - 3 to 5 real rendered profiles from `data/raw/sample50.jsonl`
  - counts in `thresholds.json`
  - binary serialisation turns P(yes) = 0.5 for an unknown into "yes"
- **MASTER_PLAN follow-ups** the owner hasn't decided on, after the 8b voice section:
  - step E3 still says voice notes are a stretch goal
  - the cut-line list doesn't place the briefing or the voice agent
  - the Day 2 timeline line
  - the keys list lacks ElevenLabs
- **Plan inconsistencies flagged:**
  - artefact paths (`data/answers/rules.json`, `app/thresholds.json`) vs `shared/artifacts/`
  - drivers and what-ifs differ between answers mode and profile mode
  - the timeline × target independence assumption is biased (shut-downs are fast)
  - agent profiles will have more unknowns than the training data
  - template ambiguities (listed in `app/contract/README.md`)
  - thresholds built on val are optimistic and sparse for 5-year targets
- **Voice features (8b):** don't build until the owner says go. Needs an ElevenLabs key, and whether the
  hackathon has an ElevenLabs prize or credits (that decides how prominent to make it).
- **Later keys:** TypeSafe (Jev) and the Kev endpoint, when the research outputs land.
