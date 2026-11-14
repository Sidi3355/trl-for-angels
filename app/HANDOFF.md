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
**Every image and video goes into `app/media/`** (owner, 2026-11-14), including rejected and superseded ones:
numbered folders in the order the work happened, and an entry in `app/media/README.md` for each (what it shows,
status, whether the owner was sent it). Screen recordings: `app/media/tools/record-walkthrough.cjs`.

## Tasks and status

| # | Task | Status |
|---|---|---|
| 1 | API contract and mocks (`app/contract/`) | Done |
| 2 | FastAPI backend on mocks (`app/backend/`) | Done |
| 3 | Research agent, merge, render; test on 5 real founders | **Done.** 5 founders for $1.21 in total; the owner has seen the profiles and sources |
| 4 | Mobile-first Next.js app (`app/frontend/`): form, live progress, memo, client-side controls, what-ifs, disclaimer | **Done, on mocks; redesigned 2026-11-14** at the owner's request (simpler, product-grade, phone and desktop). Checked on an emulated iPhone 17 and a 1440px desktop, light and dark |
| 5 | PWA features: manifest, share target, web push; phone test instructions (iOS and Android differ) | **Done (2026-11-14):** push notifications, `/share` with Android share target and iPhone Shortcut steps. Real push delivery can't be tested from this sandbox (push services unreachable); checked with a simulated subscription |
| 6 | Hosting: frontend on Vercel, backend on Railway, both on mocks | **Deployed** (2026-11-14). Waiting for the owner's test on the iPhone |
| 7 | Batch mode UI: CSV upload, triage view | **Done (2026-11-14):** `/batch`, checked end to end on phone and desktop |

## Next step (task 6: the owner tests on the iPhone)

Deployed on 2026-11-14; `app/README.md`, "Deploy", has the settings and addresses.

- **Backend (Railway, set up by the owner):** `https://trl-for-angels-production.up.railway.app`, branch
  `app-track`, mocks. Variables: `RAILWAY_DOCKERFILE_PATH`, `ACCESS_TOKEN` (the owner's passcode; never ask
  for it) and `CORS_ORIGIN_REGEX`. The "Railway config file" setting didn't take; the variable did.
- **Frontend (Vercel, set up through the connector):** framework Next.js, root `app/frontend`, Node 22,
  `NEXT_PUBLIC_API_URL` = the Railway domain, Ignored Build Step now builds only `app-track` and `main`. Phone URL: the `app-track` branch
  alias, `https://trl-for-angels-git-app-track-siddarths-projects-2714c925.vercel.app`, behind Vercel's login.
- This sandbox can't reach `railway.app` or `vercel.app` (network policy), so checks on the live app come
  from the owner or from the Vercel connector's logs.
- `main` was merged from `app-track` with the owner's OK (2026-11-14), and both branches were level after it.
  Further merges into `main` still wait for the owner.

Then: the owner's UI feedback, task 5 (PWA: home-screen icon, iOS Shortcut share, push), task 7 (batch UI),
or real research on the hosted backend (`AGENT=claude` plus the key, about $0.25 per founder).

### Task 3 notes, for later

- Research runs in this sandbox need `AGENT_MAX_FETCHES=0`: the API refuses web fetch from here.
- After the five-founder check the prompt was fixed twice (QS source; founding team from recent pages).
  The second fix is untested: re-running `young` and `paananen` (about $0.40) would check it.
- Still open: the owner to confirm in the Claude Console that the usage landed on their key.

## Decisions made

- **Redesign (2026-11-14, owner: "make it look amazing, feel like a fully fledged product, less complicated").**
  Founders list as home (first called "Deals"; renamed because the owner found the investor jargon unclear);
  one smart search box; "Your bar" is a single global setting in a sheet (not controls
  on every memo); memo leads with the verdict and a to-scale gauge; detail behind progressive disclosure.
  Inter + Space Grotesk; cool neutrals with one ink-blue accent; chart ramps validated with the dataviz
  skill. Installable (manifest and icons); push and share stay in task 5.
- **Second redesign (2026-11-14, owner: "still looks AI generated, make it look cool", asked for Fable 5.2):**
  a Claude Fable 5.2 design agent chose "the odds slip": ink on paper, colour only for the verdict slab,
  Archivo at three widths, floating dock on phones. Reviewed here: logic untouched, tests and build pass,
  every verdict colour, not-found, passcode and overflow at 390px checked; the gauge marker was changed to a
  solid needle (the hollow ring read as a zero).
- **Verdict labels for angels (owner, 2026-11-14): "Meet / Look closer / Pass"** on screen, replacing "Advance /
  Escalate / Pass" (fund language: a solo angel has nobody to escalate to). Display only: the contract,
  backend, policy and research keep `advance` / `escalate` / `pass` as the internal values. MASTER_PLAN still
  uses the old words; the owner may update it.
- **No passcode (owner, 2026-11-14):** `ACCESS_TOKEN` stays unset. Vercel's login wall stays on, so only the
  owner's Vercel team can open the app. Revisit before switching on real research (`AGENT=claude`), which spends credits.
- **Vercel free plan:** about 100 deployments a day. On 2026-11-14 the limit was hit (many were failed builds of
  the research branch, now skipped by the Ignored Build Step). Batch pushes to `app-track`.
- **Voice (8b) is go** (owner asked about ElevenLabs, 2026-11-14). Waiting on: the key in Railway as
  `ELEVENLABS_API_KEY` (and the secure form for this sandbox), a voice choice, and whether the hackathon
  has an ElevenLabs prize. Free tier only (zero-budget amendment).

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
  `AGENT_BASE_URL=https://api.anthropic.com` explicitly. Confirmed on the first paid call: the proxy
  passes the owner's key through.
- The API refuses the web fetch tool from this sandbox ("restricted network access"). It's a platform
  restriction, so don't work around it: set `AGENT_MAX_FETCHES=0` here, and the agent runs on web search
  alone. Hosted deployments (Railway) keep web fetch on.
- Tests clear every setting from the environment (`tests/conftest.py`), so a key set in the sandbox
  doesn't change them.
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
- **Voice features (8b):** the owner said go on 2026-11-14; see "Decisions made" for what's still needed.
- **Later keys:** TypeSafe (Jev) and the Kev endpoint, when the research outputs land.
