# App: Halomark, a deal-screening agent for angel investors

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
| `frontend/` | Installable mobile-first Next.js app: founders list, screening, live progress, memo, your bar, what-ifs, notifications, sharing in, screening a list | Tasks 4, 5 and 7: done, on mocks |
| `media/` | Every screenshot and video made while building the app, good and bad, in order, with an index. See `media/README.md`. | Kept up to date |

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

- **Dashboard** (`/`, the home page and the dock's first tab): "Who's the founder?" (the quick screen box), this
  session at your bar in four tiles (screened, Meet, Look closer, Pass; each opens Founders filtered), the latest
  five founders, your bar, the odds check from `src/data/calibration.json`, and shortcuts to a list and a voice note.
- **Founders** (`/founders`; `?show=advance|escalate|pass` opens a filter): everyone screened this session at your
  bar, filterable by verdict, with example founders. The list lives in `sessionStorage`, so it goes when the app closes.
- **Settings** (`/settings`, the dock's fourth tab): appearance, your bar, notifications (whether this browser can
  show them), this session (clear the founders, forget a passcode, show the intro again), service status, links
  (your profile, How it works, accuracy, model card, plans, Terms, Privacy) and Delete all my data.
- **Navigation:** phones have a five-tab dock (Dashboard, Founders, + Screen, Settings, You), icons over labels;
  desktops a sidebar with Dashboard, Founders, Screen a list, How it works, Plans and Settings, the account chip
  and a compact appearance toggle.
- **Your bar** (a sheet, opened from Founders, the sidebar, any memo or You): target outcome, timeline, risk
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
- **How it works** (`/about`): the pipeline in six plain steps (research agent, anonymised profile, TRL's questions
  answered by Kev, a fine-tuned calibrated Kev, your bar, the verdict), how to read a verdict, the name, sharing
  from other apps, and privacy in short. Links to:
  - **Model card** (`/model-card`): the model, what it predicts, the training data (3,000 profiles, 2,950
    generated), the founding-date cutoff, anonymisation, known limits. Facts from the research branch's
    `results/METHODS.md` and `results/data/README.md`; keep them in step.
  - **How accurate are the odds?** (`/calibration`): one reliability chart, three numbers in plain words, one
    limits line. Every number comes from `src/data/calibration.json`, written by
    `scripts/calibration-from-results.py` from a research results folder (now: `b3-provisional`, TRL's C1a on
    validation). To swap in final numbers, rerun the script on `results/summary/d1-final/` (or the production
    model's calibration) and redeploy: no code changes.
- **You** (`/account`, the dock's last tab): a sign-in look-alike that creates an investor profile **on this
  device only** (localStorage, no server account): name, optional email, sectors, stage, cheque size, geography,
  default target, timeline and risk. Saving it sets Your bar; "Only my sectors" turns sectors into the bar's
  filter; the bar's Reset returns to the profile's defaults. Settings live on `/settings`; its **Delete all my data**
  (`lib/profile.ts`) removes every `screener.`/`halomark.` key from both storages and the push subscription.
- **First-run intro** (`components/Onboarding.tsx`): three skippable screens (what Halomark does, what a
  percentage means, try a sample founder), shown once per device, replayable from You. Not shown over `/share`,
  `/terms` or `/privacy`.
- **Terms** (`/terms`) and **Privacy** (`/privacy`): drafts, marked "not legal advice; to be reviewed". They
  describe the app as it is: public information only, research on named founders, nothing kept on the servers
  after the session (memos in memory up to about two hours; logs carry no names or notes), the profile on the
  device, and the services used (Anthropic, ElevenLabs, Kev on the owner's PC through a Cloudflare tunnel,
  Vercel, Railway, browser push services). Update them whenever data handling changes.
- **Appearance:** System, Light or Dark, on You (Settings) and as three icons in the desktop sidebar
  (`lib/theme.ts`, `components/ThemeToggle.tsx`). The choice is kept on the device (`screener.theme`; System stores
  nothing) and applied before first paint by an inline script in `<head>`, as in Next's "preventing flash before
  hydration" guide. `globals.css` keeps two identical copies of the dark colours: one under the system-dark media
  query (unless the person chose Light), one under `[data-theme="dark"]`. The status-bar colour follows the choice.
- **Plans** (`/plans`): a mockup of Free, Pro and Syndicate with a monthly/yearly toggle and "Coming soon"
  buttons. No payment code; prices are illustrative.
- **Installable:** `app/manifest.ts` and `public/icons/`, so "Add to Home Screen" opens it full-screen with its
  own icon.
- **Notifications** (task 5): "Notify me when it's ready" on the progress and list screens. `public/sw.js` shows
  the notification and opens the memo; `src/lib/push.ts` subscribes; the backend (`screener/push.py`) sends one
  notification per watched job, stating the verdict at the investor's bar, then forgets the subscription. Keys
  are generated at startup unless `VAPID_PRIVATE_KEY` is set. iPhones allow web push only once the app is on the
  Home Screen, so there the button becomes that instruction.
- **Share into Halomark** (task 5): `/share?url=…` shows what came in and screens it with one tap. Android gets it
  through the manifest's `share_target`; iPhones through a Shortcut, with steps and a copyable link on How it works.
- **Screen a list** (task 7, `/batch`): upload or paste a CSV (template download included, up to 200 founders), then
  watch them sort into Meet / Look closer / Pass at your bar; each finished founder joins the Founders list.
- **Voice notes** (task E5, MASTER_PLAN 8b speech-to-text only; the owner dropped the spoken briefing and the
  voice agent): on Screen a founder, **Record** (up to a minute) sends the audio to `POST /v1/notes/transcribe`
  (ElevenLabs Scribe `scribe_v3`, batch, filler words removed). The words join **Your notes**, then
  `POST /v1/notes/sort` (Claude Opus 5.5 at low effort, JSON-schema output) fills the form: each value tagged
  "From your voice note", sent as `voice_fields` and shown in the memo as "You (voice)". Typed or pasted notes get
  a **Fill the form from my notes** link for the same step ("From your notes"). Rules, enforced in code
  (`backend/screener/pipeline/notes.py`): a value must fit the template and quote the note, names never go into
  fields, education and jobs are left to research (a partial list would replace the agent's fuller one), and
  facts from after founding are listed as kept out. A value you picked by hand is never overwritten. The notes
  themselves still never reach the model, and the recording isn't kept. Without the Claude key the transcript
  still lands in the notes, with a note that form filling is off; without the ElevenLabs key a recording returns
  a marked example. Recording uses `MediaRecorder` (webm on Chrome and Android, mp4 on iPhone Safari).
- **Scrolling:** on phones the dock steps aside while you scroll down and returns when you scroll up; the memo's
  what-if bar appears only once the verdict has scrolled out of view.
- **Design system ("the odds slip", second redesign by a Claude Fable 5.2 design pass):** black ink on neutral
  paper, colour kept for the verdict alone, shown as a full-colour slab (green Meet, amber Look closer, ink Pass)
  with the chance in large condensed figures and a to-scale gauge whose zones differ by pattern as well as tone.
  One variable family, Archivo, at three widths (condensed figures, normal text, wide labels). The brand's
  stamp-pad blue is the accent: primary buttons, the active sidebar item, eyebrows, link underlines, focus rings,
  avatars and the dashboard's "Screened" tile (each verdict tile is tinted in its own verdict colour). Selections
  in segmented controls and chips stay ink. A floating dock on phones, a sidebar on desktop. Tokens in
  `src/app/globals.css`, building blocks in `src/components/ui.tsx`. Chart colours were checked with the dataviz
  skill's palette validator against both themes' surfaces.
- **Brand: Halomark** (renamed from Screener on 2026-11-14; identity by a Claude Fable 5.2 design pass). The mark is a
  hallmark punch (the cut-corner stamp an assay office strikes into tested gold) with an angel's halo struck into
  it, used as the app icon in stamp-pad blue (`#1f3bd0`). Inside the app the name is HAL◯MARK (Archivo at its
  widest width, weight 800, capitals) with the halo alone as its O, in the text colour (owner's call: cleaner than
  the boxed mark in the header). The boxed mark appears in the app only where About explains the name; verdict
  tiles are struck in the same cut-corner shape (`.punch`). The geometry lives
  once in `src/lib/mark.ts`; `node scripts/make-brand-assets.cjs` (after `next build`) regenerates every icon,
  the SVG favicon and the link-preview image from it. Internal names stay `screener` (the backend package,
  `SCREENER_ANTHROPIC_API_KEY`, storage keys), so nothing on the hosts changes.
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
| `ANSWERER` | `mock` | `kev` (base Kev at `KEV_URL`/answerer; `KEV_API_KEY`) | Answers to the rules (answers mode only) |
| `DECIDER` | `mock` | `kev` (the production Kev at `KEV_URL`/decider; `KEV_API_KEY`) | Outcome and years distributions |
| `KEV_URL` | unset | `https://<words>.trycloudflare.com` | The Kev server's address (changes each time its tunnel starts) |
| `TRANSCRIBER` | `auto`: `elevenlabs` if `ELEVENLABS_API_KEY` is set, else `mock` | `elevenlabs` | Voice notes' speech-to-text (`scribe_v3`) |
| `NOTE_SORTER` | `auto`: `claude` if the Claude key is set, else `off` | `claude` | Notes -> form fields (`mock`: keyword stand-in) |

Each swap is independent. For example, the real artefacts work while Kev is still mocked, and
`model.json`'s `decider_input` switches between answers mode and profile mode with no code change.
Before switching `ARTIFACTS_DIR`, run `python app/contract/tools/validate.py --artifacts shared/artifacts`.
If a real component is selected but can't run (a missing key, or not built yet), the server still starts:
`/health` says `degraded` and explains, and screening requests return 503 with the reason.

Other settings: `CORS_ORIGINS` and `CORS_ORIGIN_REGEX` (the frontend's address), `ACCESS_TOKEN`
(optional shared passcode for `/v1`), `RETENTION_MINUTES` (default 120), `MAX_CONCURRENT_SCREENINGS`,
`BATCH_MAX_CONCURRENCY`, `MOCK_PACE`, `VALIDATE_RESPONSES`, and for Kev `KEV_TIMEOUT_S` (default 180 s per request: answering
takes ~7 s on idle cores but over a minute on a busy CPU) and `KEV_MAX_RETRIES` (default 1, so a PC that's off fails a screening quickly).

## The real models (`ANSWERER=kev`, `DECIDER=kev`)

`backend/screener/pipeline/kev.py`, following research's `docs/app_integration.md`. Both models run on research's
`kev_server` (on the owner's PC, behind a free Cloudflare tunnel; setup in `kev_server/README.md` on the research
branch): base `jaredpalmer/kev-0.6b` at `/answerer/v1/systemone`, the production model at `/decider/v1/systemone`.

- **Through TRL.** Every Kev call goes through TRL's `LLM` and `LLMSession` (the project's fork, pinned in
  `requirements.txt` at the commit research exported with), with TRL's reply cache off, so nothing is kept.
- **The answerer** asks base Kev the 40 questions in `rules.json` about the anonymised profile. A question it
  leaves unanswered reads `unknown` (and the memo's `p_yes` is `null`).
- **The decider** reads TRL's `answers_text` (the exact text Kev was trained on: `<question> yes|no|unknown`, one
  line per rule) and gets `model.json`'s two choice questions word for word, option descriptions included. The
  server runs raw; the backend applies `model.json`'s temperature per question (`p^(1/T)`, renormalised).
- **Drivers** (what moves the verdict) flip each answered question once and ask the decider again. The real Kev
  takes about 5 s per decision on a CPU, so the memo comes back with `drivers_status: "pending"` as soon as the
  verdict is ready, and the drivers fill in afterwards (three per round trip, by the size of the rule's
  elastic-net weight in `rules.json`, largest first) once the memo is first opened. The memo page polls and shows
  "N of 40 done". A list (batch) only starts a founder's drivers when that memo is opened.
- **Measured (2026-11-15, the real models on this sandbox's 4 CPUs, research's real artefacts):** answering 40
  questions about 7 s, the verdict about 5 s, memo on screen 14 s after tapping a founder, the first five drivers
  at 38 s, all 40 at about 3.5 minutes. A what-if waits behind at most one round trip of drivers. The owner's PC
  may be faster or slower.
- **`KEV_URL`** overrides `model.json`'s placeholder endpoint for both models: after restarting the tunnel, paste
  the new address into Railway. `/health` shows `kev: {reachable, ready, decider_stand_in}` from the Kev
  server's own health check (cached for 30 seconds).
- **If Kev is down or `KEV_URL` isn't set,** the backend still runs. Before researching a founder (which costs
  money) it checks that the Kev server is up, ready and accepts our key (cached 20 s); if not, the screening stops
  at once saying what's wrong and that nothing was researched or charged. The example founders skip that check:
  they have canned research and the demo cache. Messages name the host, never the key. A what-if that needs
  Kev while it's down returns 503 `model_unavailable`.
- **Demo cache** (`backend/screener/data/kev_demo_cache.json`, research's "keep the demo cache as the backup"):
  the real Kev's replies for the three fictional example founders, drivers included, built with
  `backend/tools/build_kev_demo_cache.py` against the real models. The examples then answer at once and still
  work while the PC is off. It's used only with the `model.json` (`model_id`) and `rules.json` (its questions)
  it was built for, and only for exactly the same text, so it never answers for anyone else. Rebuild it when
  research exports a new model; `KEV_DEMO_CACHE=false` turns it off.
- **Example founders with real research:** with `AGENT=claude` the three example founders still get their canned
  research (recognised by their placeholder `example.com/mock/...` addresses, never by name alone), so they cost
  nothing and can't pick up a real person who shares a made-up name.
- **Against the base rate:** the verdict shows "All founders: 20%" under the chance (the share of validation
  founders who reached the bar's target and timeline), because the model's chances are cautious.
- **Bar with no data:** no validation founder reached $1B within 5 years, so that combination has no thresholds.
  The bar sheet says "Not enough data", the verdict says there's no bar, and every founder shows Look closer.

## What's mocked, and how to switch to the real artefacts

The research session produces three artefacts in `shared/artifacts/` (see `shared/README.md`). Until they
exist, the app uses mocks with the same file names and structure:

| Artefact | Mock | Real (when ready) | What the mock stands in for |
|---|---|---|---|
| `rules.json` | `app/contract/mocks/rules.json` (20 questions) | `shared/artifacts/rules.json` (40) | RRF's question list (step B1) |
| `thresholds.json` | `app/contract/mocks/thresholds.json` | `shared/artifacts/thresholds.json` | The val precision and recall table (step D4) |
| `model.json` | `app/contract/mocks/model.json` | `shared/artifacts/model.json` | The production Kev endpoint and input type (steps D2, D3) |

The real files are in `shared/artifacts/` (copied unchanged from the research branch at `4cc539d` on 2026-11-15, at
the owner's request) and pass `validate.py --artifacts`. The answerer
(base Kev), decider (production Kev) and research agent are mocked by `backend/screener/mocks/` until they're
switched on. Every memo made with any mock carries `"mock": true` and a visible warning
saying which parts are mocked.

## Privacy and storage

Jobs, memos and batches live in the backend's memory only, and are deleted `RETENTION_MINUTES` after they
finish (MASTER_PLAN guardrail: nothing stored after the session). Because state is in memory, the
backend runs as a single instance. Logs never contain keys; `/health` shows only whether each key is set.

## Secrets

Keys come from environment variables only, never from the repo: `ANTHROPIC_API_KEY` (research agent),
`KEV_API_KEY` (the Kev server's passcode, the same value as on the PC), `ELEVENLABS_API_KEY` (voice
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
| `AGENT` | `claude` for real web research (uses `ANTHROPIC_API_KEY`, about $0.25 a founder; caps: `AGENT_BUDGET_USD`, default $5 per restart, and `AGENT_MAX_COST_PER_FOUNDER_USD`, default $1). Leave out to stay on mocks. |
| `ARTIFACTS_DIR`, `ANSWERER`, `DECIDER`, `KEV_API_KEY` | The real models: `shared/artifacts`, `kev`, `kev`, and the Kev server's passcode. Safe to set while the PC is off: the example founders answer from the demo cache. |
| `KEV_URL` | The Kev server's tunnel address, pasted each time the tunnel starts. Unset: only the example founders can be screened. |
| `ELEVENLABS_API_KEY` | Voice notes' speech-to-text. Without it a recording returns a marked example transcript. |
| `ANTHROPIC_API_KEY` | Also turns on filling the form from notes (about 1–2 cents a note on Claude Opus 5.5), even while `AGENT` stays `mock`. |

**Frontend (Vercel).** Project `trl-for-angels`: root directory `app/frontend`, framework Next.js, Node 22,
and `NEXT_PUBLIC_API_URL` set to the Railway domain (read at build time, so change it and redeploy). Pushes to
`app-track` and `main` build; the Ignored Build Step skips every other branch (the research branch has no frontend). Each branch gets a stable address, `trl-for-angels-git-<branch>-siddarths-projects-2714c925.vercel.app`;
all deployments are behind Vercel's login (the project's deployment protection), so you sign in to Vercel
once on the phone.

**Live now (2026-11-14):** backend `https://trl-for-angels-production.up.railway.app` (branch `app-track`,
mocks); frontend `https://trl-for-angels-git-app-track-siddarths-projects-2714c925.vercel.app`.
