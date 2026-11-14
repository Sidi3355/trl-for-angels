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
status, whether the owner was sent it). Screen recordings: `app/media/tools/record-walkthrough.cjs`. To keep the
repo light, take phone screenshots at 2× (`deviceScaleFactor: 2`, about half the size of 3×) and keep only the
video versions that matter. `app/backend/Dockerfile.dockerignore` keeps `app/media` out of the backend's build.

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
| E5 | Voice notes (speech-to-text; MASTER_PLAN 8b) | **Done (2026-11-14), on example transcripts until the key is on Railway.** Record, transcribe (ElevenLabs), fill the form (Claude); typed notes too. Checked end to end in a browser with a fake microphone and the mock services. No real ElevenLabs call made yet: the onboarding's test waits for the owner's yes |
| 8 | New screens (owner's request, 2026-11-14): first-run intro, How it works plus model card, calibration page, on-device profile ("You"), Terms and Privacy drafts, Plans mockup | **Done (2026-11-14)**, on mocks. Checked on an emulated iPhone 17 and a 1440px desktop, light and dark (`app/media/12-new-screens`) |

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
- **Name: Halomark (owner, 2026-11-14)**, replacing "Screener": a halo for angels, and a near-homophone of
  hallmark, the stamp that certifies tested gold. Identity by a Claude Fable 5.2 design pass: a cut-corner
  hallmark punch with a halo struck into it, used as the O of HAL◯MARK; stamp-pad blue for the mark only.
  Rejected directions (an HM maker's mark, a halo as the H's crossbar, a halo alone) are in
  `app/media/08-halomark-brand/directions.png`. The blue is the main judgement call: an ink-only mark is the
  fallback (`--brand` in globals.css and the colours in `src/lib/mark.ts`, then rerun the icon script).
  User-visible names only: `screener` stays as the backend package, env var and storage-key prefix.
  **Wordmark (owner, 2026-11-14):** in the app the O is the halo alone, in the text colour, not the blue boxed
  mark; the boxed mark is the app icon (and the illustration in About's "The name").
- **Verdict labels for angels (owner, 2026-11-14): "Meet / Look closer / Pass"** on screen, replacing "Advance /
  Escalate / Pass" (fund language: a solo angel has nobody to escalate to). Display only: the contract,
  backend, policy and research keep `advance` / `escalate` / `pass` as the internal values. MASTER_PLAN still
  uses the old words; the owner may update it.
- **No passcode (owner, 2026-11-14):** `ACCESS_TOKEN` stays unset. Vercel's login wall stays on, so only the
  owner's Vercel team can open the app. Revisit before switching on real research (`AGENT=claude`), which spends credits.
- **app-track merged into main (owner, 2026-11-14 evening):** clean merge, only `app/` changed. Adds ~100 MB of
  `app/media` to main; the Kaggle runner shallow-clones the research branch, so only a later merge of main there
  would make its clones bigger (seconds, not breakage).
- **New screens (owner, 2026-11-14), decisions made building them:**
  - **Navigation:** the phone dock is Founders · Screen · **You** (was About). You holds the profile, the
    settings that used to sit on How it works, links to How it works, the model card, calibration, Plans, Terms
    and Privacy, and Delete all my data. The desktop sidebar adds Plans and an account chip, with Terms and
    Privacy in its footer.
  - **Profile on the device only (owner's decision):** localStorage key `screener.profile`; no server account,
    no database. The "sign-in" asks for a name and an optional email and says plainly that nothing is sent. The
    profile's default target, timeline and risk set Your bar on save, "Only my sectors" sets the bar's sector
    filter, and the bar's Reset returns to the profile's defaults. Stage, cheque size and geography aren't used by
    the model (the page says so). Delete all my data removes every `screener.`/`halomark.` key from local and
    session storage and the push subscription, then reloads.
  - **Intro:** shown once per device (`screener.onboarded`), skippable at every step, replayable from You, not
    shown over `/share`, `/terms` or `/privacy`. Its last step starts a sample founder.
  - **Calibration numbers are provisional and not Halomark's own model:** `b3-provisional`, TRL's standard model
    (C1a, RRF elastic net) on the 400 validation founders, because the production Kev isn't scored yet. The page
    says so. The research session publishes `results/summary/d1-final/` and the production model's calibration;
    then rerun `app/frontend/scripts/calibration-from-results.py` on it (the JSON is the only thing that changes).
  - **Model card** facts come from the research branch's `results/METHODS.md` and `results/data/README.md`
    (read 2026-11-14). Update it if they change, especially once the production model is chosen (C3 or C4).
  - **Terms and Privacy are drafts** ("not legal advice; to be reviewed"); still to decide: provider, contact,
    legal basis for researching named founders, governing law. Building them showed the backend logged founder
    names (research agent) and note values (sorter); both now log only keys, counts and costs, so "nothing kept
    after the session" holds for our logs too.
  - **Plans:** Free (5 a month), Pro ($29/month, $290/year: 100 a month, lists, voice notes, notifications),
    Syndicate ($99/month for 5 members: shared founders, memos, bar). Illustrative, US dollars, "Coming soon",
    no payment code. Everything stays free in the prototype.
- **Light/dark toggle (owner, 2026-11-14):** System (default), Light or Dark, on You and in the desktop sidebar,
  saved on the device as `screener.theme` (so Delete all my data resets it). The You page now shows Settings and its
  links whether or not there's a profile: before, a phone without a profile couldn't reach How it works, Terms or
  Privacy.
- **Dashboard and Settings tabs (owner, 2026-11-14):** five tabs on phones (Dashboard, Founders, + Screen,
  Settings, You), the same pages in the desktop sidebar. The Dashboard is the home page (`/`, also the installed
  app's start page); the Founders list moved to `/founders`. Settings (appearance, your bar, notifications, session,
  service, links, delete all data) moved off You, which is now just the profile.
- **A little more colour (owner, 2026-11-14: "a bit of brand colours as well as accent colours"):** the accent
  token is now the brand's stamp-pad blue (`#1f3bd0` light, `#8fa0ff` dark, with a pale tint for highlights) instead
  of ink. It colours primary buttons, the active sidebar item, eyebrows, link underlines, focus rings, avatars, the
  intro's dots and the featured plan. The dashboard tiles are tinted: Screened in the blue tint, each verdict in
  its own verdict tint. Selections in segmented controls and chips stay ink, and the verdict slab is unchanged, so
  colour still means "verdict" wherever it's large. The phone dock is dark in both themes, so its Screen button uses
  separate `--dock-accent` tokens (the on-dark blue in both): the light-mode blue measured 2.4:1 on the dock, the
  on-dark blue 7.9:1. Every text and icon pair checked at 4.5:1 or better. To go back to ink, set `--accent`,
  `--accent-hover`, `--accent-ink` and `--accent-soft` in globals.css (both dark copies too).
- **Vercel free plan:** about 100 deployments a day. On 2026-11-14 the limit was hit (many were failed builds of
  the research branch, now skipped by the Ignored Build Step). Batch pushes to `app-track`.
- **Voice (8b): speech-to-text only (owner, 2026-11-14).** No spoken memo briefing (E6) and no voice agent (E7):
  the owner dropped both to save credits, so no voice was chosen. MASTER_PLAN 8b still lists them; the owner may
  update it. ElevenLabs free plan (10,000 credits a month), notes capped at 60 seconds.
- **Notes fill the form (owner chose option C, 2026-11-14):** a voice note fills the form as soon as it's
  transcribed; typed notes get a "Fill the form from my notes" link. The investor checks every value; a
  hand-picked answer is never overwritten. Notes still never reach the model (TRL and Kev read only the rendered
  template). Education and jobs are never filled from notes (the merge would replace the agent's whole list).
- **Note sorter: Claude Opus 5.5 at low effort** (the Claude API guidance's default model; cheaper models are
  the owner's call). About 1–2 cents a note, charged to `AGENT_BUDGET_USD`. `NOTE_SORTER_MODEL=claude-haiku-5-5`
  would cost roughly a fortieth of that if the owner wants it.
- **ElevenLabs key:** set up with the ElevenLabs onboarding CLI (`onboard init` and `check` in `app/backend`,
  which also asked for `load_dotenv` in `screener/config.py`). In this sandbox the key is a network secret on the
  owner's Default cloud environment for `api.elevenlabs.io` (the proxy adds it; `app/backend/.env` holds only a
  placeholder, git-ignored). Railway needs its own `ELEVENLABS_API_KEY`, plus `ANTHROPIC_API_KEY` to fill forms.

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
- **Voice notes on the live app:** `ELEVENLABS_API_KEY` and `ANTHROPIC_API_KEY` are set on Railway (owner,
  2026-11-14; `/health` shows `transcriber: elevenlabs`, `note_sorter: claude`). Railway only applied them after
  the staged-changes Deploy. Next: the frontend deploy, then the first real note recorded on the iPhone. The
  onboarding's own test (a short text-to-speech clip) is optional; recommended to skip it.
- **Later keys:** TypeSafe (Jev) and the Kev endpoint, when the research outputs land.
