# App contract

The shapes of everything that moves between the frontend, the backend and the research artefacts.
The backend (task 2) and the frontend (task 4) are built against these schemas, and the mocks follow
them exactly, so swapping mocks for real artefacts is a config change only.

Contract version: `0.1.0` (every document carries `schema_version`).

## What's here

| Path | What it is |
|---|---|
| `schemas/common.schema.json` | Shared definitions: the 9 template fields and their allowed values, provenance, distributions, policy, verdict, sources |
| `schemas/investor_input.schema.json` | **(a)** Request to screen one founder: form fields, free-text notes, founder identifier, founding date |
| `schemas/memo.schema.json` | **(b)** The memo: verdict, outcome and years distributions, drivers, per-field values with provenance, sources, conflicts, unknowns, disclaimer |
| `schemas/batch_request.schema.json`, `batch_response.schema.json` | **(c)** Batch screening and the triage result |
| `schemas/screening_job.schema.json`, `progress_event.schema.json` | The background job and its live progress stream (SSE) |
| `schemas/what_if_request.schema.json`, `what_if_response.schema.json` | What-if toggles (re-run the decider only) |
| `artifacts/*.schema.json` | **Proposed** formats for the research outputs `rules.json`, `thresholds.json`, `model.json`, for the research session to confirm |
| `mocks/` | Mock artefacts with the real file names (`rules.json`, `thresholds.json`, `model.json`) plus `mock_memo.json` (3 founders) |
| `examples/` | One valid example of every other request and response, plus `batch.csv` |
| `tools/build_mocks.py` | Regenerates `mocks/` and `examples/`. The memos, events and what-if come from running the backend's own pipeline on the demo founders |
| `tools/validate.py` | Validates everything: schemas plus cross-file rules (verdicts, sources, template grammar) |

The logic these tools use lives in the backend package, so the service and the mocks can't drift:
`app/backend/screener/template.py` (renders and parses the frozen template), `screener/policy.py`
(the investor controls; the frontend ports it), `screener/mocks/model.py` (mock answerer and decider,
**not the real model**) and `screener/mocks/founders.py` (the three fictional demo founders).

```bash
pip install -r app/contract/requirements.txt
python app/contract/tools/build_mocks.py     # regenerate mocks/ and examples/ (deterministic)
python app/contract/tools/validate.py        # schemas + cross-file consistency
python app/contract/tools/validate.py --artifacts shared/artifacts   # once the real artefacts exist
```

## API surface (implemented in `app/backend`)

| Method and path | Body | Returns |
|---|---|---|
| `GET /health` | | status, and whether each artefact is mock or real |
| `POST /v1/screenings` | investor input | screening job (202) |
| `GET /v1/screenings/{job_id}` | | screening job |
| `GET /v1/screenings/{job_id}/events` | | SSE stream of progress events; resumable with `Last-Event-ID` |
| `GET /v1/memos/{memo_id}` | | memo |
| `POST /v1/memos/{memo_id}/what-if` | what-if request | what-if response |
| `POST /v1/batches` | batch request (JSON) or a CSV file | batch response (202) |
| `GET /v1/batches/{batch_id}` and `/events` | | batch response; SSE stream of `batch_item` events |
| `GET /v1/artifacts/{rules,thresholds,model}` | | the active artefacts, so the client can compute controls itself |
| `GET /v1/demo/founders` | | investor inputs for the three fictional demo founders |
| `GET /v1/push/key` | | push key: the server's public VAPID key, for the browser's push subscription |
| `POST /v1/screenings/{job_id}/notify` | push watch request | push watch response (202): one notification when it finishes, at the investor's bar |
| `POST /v1/batches/{batch_id}/notify` | push watch request | push watch response (202): one notification when the list is done |
| `POST /v1/notes/transcribe` | the recorded audio (`audio/webm`, `audio/mp4`, …; up to 8 MB) | note transcript: the voice note's words. The audio isn't kept |
| `POST /v1/notes/sort` | note sort request | note sort response: template fields found in the notes for the investor to check; later facts listed in `kept_out` |

Errors always look like `{"error": {"code", "message", "retryable"}, "details": [...]}`: 400 bad JSON,
401 wrong access token, 404 not found or expired, 422 breaks the contract (details name the field, or the
CSV row), 503 a component isn't configured. Event streams also accept `?after=N` and `?format=json`.

## Rules the schemas encode

**Template fields.** The 9 fields are the template's slots: `industry`, `cofounders`, `background`,
`work_experience`, `industry_experience`, `education` (1–3 entries), `jobs` (1–6, oldest first),
`prior_startups`, `prior_exits`. Values are the template's allowed values, character for character
(`"201-1,000"`, `"top 50"`, `"domain specialist"`). Any value can be `"unknown"`.

**Provenance.** Every merged field in the memo carries `provenance`: `investor`, `investor_voice` (shown as
"investor (voice)", from MASTER_PLAN 8b), `agent` or `unknown`. Agent values must cite at least one
source and give a confidence. Unknown values have no sources.

**Merge.** Investor values win. An agent value that disagrees becomes a `conflicts` entry, never a silent
overwrite. `education` and `jobs` merge as whole lists (an investor list replaces the agent's), because
entries can't be matched reliably; sub-fields inside an entry can still be `"unknown"`. `unknowns` lists
every unknown path, e.g. `jobs[2].company_size`.

**Founding-date cutoff.** Only information from before the founding date reaches the model. Every source
records `before_founding`; fields may only cite pre-founding sources. Post-founding facts (traction,
funding, later roles) go to `notes.post_founding`, and investor notes go to `notes.investor`: both are
memo-only. If no founding date is given or found, the screening date is used and the memo warns.

**Distributions and controls.** The memo carries the full `outcome` and `years` distributions, so the
client computes every control instantly:

- P(outcome ≥ target) is the sum of the bands at or above `$50M`, `$500M` or `$1B`.
- P(within timeline) is P(`under 5`) for 5 years, plus P(`5-8`) for 8 years, and 1 for any timeline.
- The verdict probability is their product. With a timeline it's labelled an estimate (independence assumed).

**Risk appetite → thresholds** (`tools/policy.py`, proposed). For the chosen target and timeline, the val
table gives the thresholds:

| Risk | Advance when the score is at or above the threshold that still flags this share of val winners |
|---|---|
| cautious | 25% (fewer, surer advances) |
| balanced | 50% |
| bold | 75% (more advances, lower precision) |

Pass applies below the highest threshold that keeps 90% of val winners above it, at every risk level.
Everything in between is escalated. The memo shows expected precision and recall at the advance
threshold, and the share of winners lost by auto-passing. Tables with under 20 positives get a warning.

**Drivers.** In answers mode each driver is one rule's answer flipped, with its full flipped
distributions, so the client can re-rank drivers for any target. In profile mode drivers are field changes.

**What-if.** Answer changes only re-run Kev. Field changes re-render the profile, and in answers mode
they also need new answers from base Kev (`field_changes: "needs_answerer"`), so they're slower and cost more.

**Filters** use `facets`: `sector` (industry), `team` (solo or team), `technical` (background technical
or mixed), `repeat_founder` (has prior startups). An unknown value fails an active filter.

**Disclaimer.** Every memo and batch response carries it, starting "Screening aid, not investment advice."

## Batch CSV columns

`client_ref, name, company_name, linkedin_url, website_url, founding_date, notes, industry, cofounders,
background, work_experience, industry_experience`. Only one of name, LinkedIn URL or website is
needed; the rest are optional and use the template's allowed values. See `examples/batch.csv`.

## Template ambiguities (provisional choices, to check against real data)

The template is frozen, but some cases aren't pinned down by it. `tools/template.py` makes these choices
until the research session sends real rendered profiles (requested in `shared/README.md`):

1. **Solo founders** render literally as "founded with solo co-founder(s)".
2. **"No degree"** renders as "- no degree in [field], …"; the template doesn't show this line.
3. **A whole unknown section** (no education or jobs found) renders as "- unknown" under its heading.
4. **An unknown job duration** renders as "unknown years"; only "unknown employees", "QS unknown" and
   "Prior exits: unknown" are shown in the plan.
5. **Several prior startups** render as "2 shut down, 1 acquired under $50M", from the template's examples.
6. **Several prior exits** render as "1 acquisition and 1 IPO as co-founder, under $50M, over $1B".

## For the research session

The artefact formats in `artifacts/` are proposals, built from the plan. Please confirm or amend them;
the app's mocks will be changed to match. Open questions:

- **`model.json`:** the exact production request (question names, instructions, option labels), the
  `kev.serve` response shape, who applies the temperature, the answerer, the answer serialisation, and
  endpoint auth.
- **Ties in binary serialisation:** with "yes when P(yes) ≥ 0.5", an answerer that returns exactly 0.5
  for an unknown field turns unknowns into "yes". Worth checking how the answerer (base Kev) answers questions about
  unknown fields.
- **`thresholds.json`:** the score must be computed exactly as the app does (the product above) and the
  labels from the true joint outcome and years. The mock shows the sparsity problem: in 400 simulated
  val founders only 4 reach $500M within 5 years, and 2 reach $1B within 5 years.
- **TRL fidelity at screening time:** the pickled RRF (to call `rrf.answers([text])`), or another way to
  get answers through TRL's own pipeline.
