# Decision log

Settled project decisions are in `MASTER_PLAN.md` section 3. This log records decisions made
while doing the work: date, decision, reason, evidence. Newest last.

## 2026-11-14 · A1 · TRL pinned at `3437d64`

- **Decision:** the fork's branch `feature/decision-combiner` starts at upstream commit `3437d64`.
- **Reason:** the plan pins this commit for reproducibility.
- **Evidence:** `git describe` gives `v0.3.0-3-g3437d64`, three commits after the `v0.3.0` tag
  (`35275a8`, `9f0619c`, `3437d64`). They change only the package description, a docs test and a
  merge, so library behaviour is v0.3.0's. The package reports version `0.3.0`. It was upstream
  `main`'s head on 2026-11-14.

## 2026-11-14 · A1 · Fork

- **Decision:** TRL work happens in the fork `Sidi3355/think-reason-learn`, on branch
  `feature/decision-combiner`, which is pushed there. The local clone's remotes are `origin` (the
  fork) and `upstream` (Vela). The pull request (G4) goes from this branch to upstream `main`.
- **Evidence:** the fork's `main` was at `3437d64` when it was created, the same commit as the pin.

## 2026-11-14 · A1 · Project environment

- **Decision:** a Python 3.13 venv (`uv`) holding the fork in editable mode with the `[anthropic]`
  extra, plus XGBoost and scikit-learn. Exact versions are in `requirements.lock.txt`.
- **Reason:** TRL requires Python ≥ 3.13. The OpenAI SDK is a core TRL dependency, so
  `[anthropic]` covers both possible generator providers. The `rl` extra (PyTorch) isn't needed
  in the project environment. The fork's own Poetry venv installs all extras for its tests.

## 2026-11-14 · Kev replaces Jev as the answerer (user decision)

- **Decision:** every answer-based condition uses a self-hosted base Kev as the answerer, held
  constant, instead of TypeSafe's Jev. Recorded as amendment 0 in `MASTER_PLAN.md`.
- **Reason:** TypeSafe publishes no free tier or trial credits, and its direct API is reported to be
  in early access behind a waitlist. The plan already allowed base Kev as the fallback answerer.
- **Evidence:** third-party pricing pages (Sept 2026) quote about $0.04 per million input tokens,
  output free, with no free tier. TypeSafe's own pricing page couldn't be confirmed.
- **Consequence:** Kev now plays two roles: the answerer for all conditions, and the learn stage
  in C2–C4. They are separate roles, but the write-up should say so. No TypeSafe key is needed.
- **Open:** which Kev checkpoint answers (see the probe below).

## 2026-11-14 · A3 prep · Kev-0.6B as an answerer: first probe

- **What:** served `jaredpalmer/kev-0.6b` (Hub snapshot `dece6dba`) on CPU and asked 8 factual
  yes/no questions about the plan's example profile.
- **Result:** 3 of 8 confidently wrong: "founded a startup before?" 0.95 (profile says none),
  "top-50 university?" 0.77 (QS 101-300), "solo founder?" 0.91 (1 co-founder). Right on prior
  exit (0.09), technical (0.01), business (1.00), 5,000+ employer (0.10), first startup (0.77).
  The server ran at temperature 1.0 (uncalibrated).
- **Reading:** one profile and 8 questions, so not a measurement, but a warning: a weak answerer
  makes every answer-based condition weaker. Kev's own README reports Kev-0.6B at 0.62 accuracy
  on new sources against 0.82 for Kev-4B.

## 2026-11-14 · A3 prep · Kev checkpoint still valid

- **Note:** Kev 1.0 now leads with Kev-0.8B, 4B, 9B (Qwen3.5) and 27B (Qwen3.8).
  `jaredpalmer/kev-0.6b` is kept as the "previous generation" small model and is exactly what the
  plan describes: a rank-16 LoRA and pointer head on `Qwen/Qwen3-0.6B-Base`. The plan's choice of
  0.6B for the learn stage (attention-only Qwen3 base, for interp) stands.

## 2026-11-14 · A3 prep · TRL spec for a Kev endpoint, and a TRL bug

- **Verified spec:** `LLM("kev-0.6b", base_url="http://<host>:8009/v1/systemone",
  kind="decision", api_key="local")`. One call through TRL's `LLMSession` returned
  probabilities (`research/checks/kev_endpoint.py`).
- **Plan's spec was wrong:** `"systemone:kev-0.6b"` resolves as a custom OpenAI-protocol
  reasoning model, because `systemone` is a wire protocol in TRL, not a provider.
- **TRL bug for the PR (G4):** with no `api_key`, TRL's System One adapter sends
  `Authorization: Bearer ` (empty), which the HTTP client rejects as an illegal header. A custom
  decision endpoint should omit the header when there is no key.

## 2026-11-14 · Zero budget: Kaggle for all GPU work, Kev-0.6B as the answerer (user decision)

- **Decision:** no spending. GPU work runs in Kaggle notebooks on a free T4. The answerer is
  Kev-0.6B, the same checkpoint as the learn stage.
- **Reason:** the user can't spend money and will train on Kaggle. A T4 has no bf16, so Kev
  runs in fp32 there: Kev-0.6B needs about 2.4 GB, but Kev-4B needs about 16 GB for its weights
  alone and won't fit. Kev-0.8B (Qwen3.5) uses fused kernels that may not run on a T4. Kev's
  PyTorch build (2.8, CUDA 12.8) most likely doesn't support the P100, so notebooks use the T4.
- **Cost of the choice:** noisier answers (see the Kev-0.6B probe above), and one model both
  answers and decides. Both go in the write-up's limitations.
- **Considered:** Kev-4B as the answerer (much more accurate, about $1–2 of GPU on Modal) and
  Modal's reported $30/month free credit. Not used: the user can't risk any spending, and
  `modal.com` is blocked from this session's network anyway.
- **Generator:** Claude through the user's existing Claude Console API credits
  (`anthropic:claude-opus-5-5` proposed; confirmed at A4).

## 2026-11-14 · A3 prep · Kev's fine-tuning command needs two fixes

- **`--max_state`:** Kev trains on states of at most 384 tokens by default and drops longer
  records ("dropped 4 of 4 records that exceed the training context"). A C3 state (about 100
  serialised answers) measured 1,468 tokens with synthetic questions, so every C3 record would be
  dropped. Pass `--max_state 4096`.
- **Recipe arguments:** Kev's own fine-tune script copies the starting checkpoint's architecture
  into `kev.train`. For `kev-0.6b`: base `Qwen/Qwen3-0.6B-Base` at revision `da87bfb6`, LoRA 16,
  head 256, LoRA targets all, `p_none_pair` 0.25, trained at lr 1e-4 and batch 8, temperature 1.0
  (uncalibrated). The plan's command omitted these.
- **Evidence:** a local CPU run of `kaggle/a3_check.py`. The endpoint, TRL speed path and
  short-state training all worked. The long-state training ran out of CPU memory, which is why
  the T4 run checks it.

## 2026-11-14 · A3 · Kev on a Kaggle T4: passed

- **Run:** `kaggle-results` branch, `runs/20261114-124358-a3/` (runner at repo commit `dddaa04`).
- **Environment:** Tesla T4 (sm 7.5, in torch 2.8+cu128's arch list), driver 580, no native bf16,
  so Kev runs in fp32. Kaggle gave two T4s; one was used.
- **Endpoint (A3 "done when"):** Kev-0.6B served on CUDA in fp32 (loaded in 36 s), and one call
  through TRL's `LLMSession` returned probabilities identical to the CPU run.
- **Answering speed:** 4,000 answers (40 profiles × 100 questions) in 38 s through TRL, about
  104 answers/s, so all ~300,000 answers take about 0.8 GPU-hours.
- **Fine-tuning with Kev's recipe, `--max_state 4096`, fp32:**
  - short states (C4-like, about 141 tokens): batch 8, 1.24 s/step, 8.1 GB peak, so 2,000 records
    × 2 epochs take about 0.17 h.
  - long states (C3-like, 1,468 tokens with synthetic questions): batch 8 runs out of memory
    on 15 GB; with gradient checkpointing it works at 24.6 s/step and 5.7 GB, so about 3.4 h for
    2 epochs. Real RRF questions may be longer, which would push this up.
- **Reproduced:** a second run with the new runner (`runs/20261114-124701-a3/`, repo commit
  `5fdf335`) passed with matching numbers (108 answers/s; 0.17 h and 3.34 h projected), and
  its start and finish status notes reached GitHub.
- **To decide at C1-train:** for C3, use both T4s, train 1 epoch, or a shorter serialisation;
  choose once the real state lengths are known. Every option fits one Kaggle session.

## 2026-11-14 · B5b · TRL decision combiner: design choices

- **Where:** fork branch `feature/decision-combiner`, commit `ddf3518`. It's the preferred
  route from MASTER_PLAN 4b.4, a new RRF combiner (`combiner="decision"`, `combiner_model=...`,
  `combiner_question=...`), not the fallback wrapper.
- **Which questions the decision model reads:** every question RRF scored, best by F-beta first
  (the best `max_rules` if set): the same ranked set the elastic net starts from, before its
  L1 penalty drops any. So C2 and C3 read all ~100 answers, and `rules_` fixes their order.
- **Text format:** `rrf.answers_text`, one line per rule: `<question> yes` (P(yes) ≥ 0.5),
  `no`, or `unknown` (unanswered). This is the plan's yes/no option, with `unknown` added for
  missing answers. B5 must build C3's training states with this same function.
- **Question asked:** `combiner_question`. The research passes the plan's Kev instruction,
  "Will this founder's company succeed (exit, IPO or funding over $500M)?", for C2, C3 and
  training. The default, when none is given, names the task and the positive class.
- **Threshold:** TRL's `best_threshold` (F-beta, with the RRF's `beta`) on the scored training
  samples. For C3 that's optimistic, because Kev is fine-tuned on those samples. The primary
  comparison tunes every threshold on val anyway (4b.6).
- **Checks:** 404 TRL tests pass (a `rrf-decision` case joins the contract tests), and ruff,
  ruff format and strict pyright are clean. A fit with a real Kev-0.6B server as both
  answerer and decider returned probabilities (exits 0.50–0.52, no exit 0.35–0.42, toy data).
  Sphinx's `-W` build already fails upstream on 116 scikit-learn docstring warnings; this
  change adds none.
- **Also fixed:** a System One server with no key now gets no key header. The empty
  `Bearer ` header was illegal and stopped every call, including from any saved and reloaded
  model, since saving drops keys.

## 2026-11-14 · Hosting Kev for the app: the owner's PC and a free tunnel (supersedes the Space)

- **What happened:** the `hf_setup` run (`kaggle-results: runs/20261114-142314-hf_setup/`)
  reached Hugging Face with the owner's token, but creating the Space failed with
  `402 Payment Required`: "Static Spaces are free for everyone, but hosting Gradio and Docker
  Spaces on free cpu-basic requires a PRO subscription." Nothing was created or charged.
- **Decision (user):** for the demo, the owner's Windows PC runs `kev_server/serve.py` (the same
  two `kev.serve` processes and front door, now launched from plain Python, so no bash or
  Docker is needed), with `cloudflared tunnel` giving it a free address. Cached demo founders
  stay the backup. Considered: cached-only (no live screening), and an Oracle Cloud Always
  Free VM (needs a card to sign up).
- **Still on Hugging Face, free:** the production checkpoint, in a public model repo, uploaded
  by `d_prod` (`research/hf_hub.py upload-model`). Model repos don't need PRO.
- **Checked here:** `serve.py` started both servers on CPU; `/health` ready; 401 without the
  key; a System One call with the key answered. Kev installed cleanly from a source archive of
  commit `2074cc4`, which is how the Windows steps install it. Not yet run on Windows itself.

## 2026-11-14 · Hosting Kev for the app: a free Hugging Face Space (user decision) (superseded below)

- **Decision:** the app's two Kev servers (base Kev answering, the production model deciding)
  run on a free CPU Docker Space, and the production weights live in a Hugging Face model repo.
- **Reason:** zero budget, and Kaggle can't serve a live endpoint. Modal's free credit wasn't
  an option (possible card, and `modal.com` is blocked from this session).
- **Design:** `hf_space/` runs `kev.serve` (Kev `2074cc4`, CPU torch 2.8, fp32) twice, with a
  small front door (`proxy.py`) routing `/answerer` and `/decider` and checking `KEV_API_KEY`.
  The decider serves raw probabilities; the app applies `model.json`'s per-question
  temperatures. Until D3 publishes the production model, the decider is base Kev as a stand-in,
  and `/health` says so.
- **Public repos:** the Space and model repo are public. They hold no secrets, and the endpoint
  needs the key. The owner can switch them to private, at the cost of an `HF_TOKEN` secret on
  the Space.
- **Checked locally (no Docker):** both servers came up on CPU behind the front door. TRL calls
  through it returned probabilities from both, and a request without the key got 401.

## 2026-11-14 · Research pipeline: how the Kaggle stages fit together

- **Stages** (`kaggle/run.sh` tasks; each Kaggle run is self-contained, because nothing on
  Kaggle survives between runs):
  1. `a4`: RRF smoke test on 20 sample rows (Claude + Kev).
  2. `b1b2`: fit C1a, C1b and C2 on train from one set of Claude questions (TRL's cache gives
     all three the same questions, which the script checks); Kev's answers for every split;
     TRL's own predictions for C1a, C1b and C2 on val and test.
  3. `c_kev`: C3 and C4 fine-tuned in parallel on the two T4s, each choosing base, ep1 or ep2
     by val log-loss and fitting its temperature on val; then EXTRA, C4 and C3 scored through
     TRL (C3 = the saved C2 RRF with the C3 checkpoint as its combiner).
  4. Locally, no GPU: CTRL (`baselines.py`) and evaluation (`evaluate.py`).
- **What persists:** the runner pushes each run's small outputs (under 5 MB, no weights) to
  `kaggle-results`, and they're copied into this branch (`data/answers`, `data/models`,
  `data/predictions`). Fine-tuned checkpoints are not kept yet. The production model (D3)
  and the app's serving (E1) will need a place for weights; decide then (likely a free
  Hugging Face model repo).
- **Checkpoint choice:** Kev only snapshots full-weight runs, so C3/C4 train one epoch, then
  a second from it, and keep whichever of base/ep1/ep2 has the lowest val log-loss.

## 2026-11-14 · A1 · Open item: TRL's cache location (closed)

- **Closed:** each Kaggle run sets `cache_dir` explicitly (`$WORK/trl_cache`) and uses it
  only within that run; every result TRL produces is saved as files, so no cache needs to
  survive between runs.

## 2026-11-14 · A1 · Open item: TRL's cache location (as first noted)

- **Note:** TRL's disk cache defaults to `~/.cache/think_reason_learn/llm-cache-v2.sqlite`, which
  is outside the repo and is lost when the cloud container is reclaimed.
- **To decide at A4:** pass an explicit `cache_dir` inside the project (git-ignored or committed),
  so cached Jev answers and generated questions survive between sessions.

## 2026-11-14 · A2 · 50-row sample written by Claude, grounded in real companies (user decision)

- **Decision:** the 50-row quality-check sample (`data/raw/sample50.jsonl`) was written by
  Claude Code from the section 10a prompt instead of by Adaption. Each row is based on a real
  company and founder, listed in `data/raw/sample50_sources.md` (for review only, never model
  input). For the 3,000-row run the user allows made-up profiles modelled on these 50.
- **Evidence:** 38 of the 50 outcomes and dates were checked by web search on 2026-11-14. The
  other 12 (PillPack, Quip, Heptio, RXBAR, Signal Sciences, Rapportive, Branch Media, 99dresses,
  Canoo, uBiome, Homejoy, Starsky Robotics) come from the public record as known; the search
  budget ran out before they could be re-checked. Founder details are bucketed into the
  template's bands; details that weren't public are filled with plausible values, flagged per
  row. Companies whose outcome was ambiguous (Kite, Stockwell, Lift Labs, AppHarvest) were
  swapped for ones with a clear outcome.
- **Conventions used (approved by the user, 2026-11-14; the 3,000-row run follows them):** years are whole elapsed years from founding to the outcome event; a
  founder who never attended university has the education line `- no degree`; a founder whose
  earlier startup was still running at founding has "1 still operating".
- **Validation:** `research/validate.py --profile sample50` passes with no errors or warnings
  (`results/data/validation_sample50.md`).

## 2026-11-14 · A2 · Sample re-checked by the research session

- **Re-validation:** the current validator (with the exact all-pairs near-duplicate check added
  after the sample's first validation) also passes it: no errors, no warnings, no near
  duplicates (`results/data/validation_sample50_recheck.md`). Counts match exactly; 20% are
  successful; 47 industries; 8 rows with unknown fields; no single field gives the outcome away
  (the highest out-of-fold AUC is background, 0.68, on 50 rows).
- **Read by eye:** realistic careers, sourced outcomes. Two notes for the 3,000-row run
  (made-up profiles modelled on these 50):
  - Industries are very specific (47 distinct in 50 rows, e.g. "enterprise email software",
    "electric aviation"), so each has one or two founders. That gives models almost nothing
    to learn from industry, and with verbatim job titles ("Chief Technology Officer for Hosted
    Applications") it can point back to a real company, against the "no unique phrases"
    rule. Use broad industries (the plan's list) and generic titles in the full run.
  - Several sampled companies are well known (PillPack, Quip, Canoo, Heptio) though the
    prompt prefers lesser-known ones. That's fine for a quality check, and moot for made-up
    profiles.
- **A2 is done:** the validator passes, and the user approved the conventions.

## 2026-11-14 · A4 · TRL smoke test passed (Claude writes the questions, Kev answers)

- **Run:** `kaggle-results: runs/20261114-153153-a4` (repo commit `df5a5aa`), Kaggle T4, fp32.
  RRF fitted on 20 rows of `data/raw/sample50.jsonl` (6 successful, seed 42) with
  `generator="anthropic:claude-opus-5-5"`, Kev-0.6B as the answerer, `beta=0.5`,
  `random_state=42`, and a small run (`n_prompts=2`, 5 questions per prompt). Verdict: PASS.
- **Generator confirmed:** Claude Opus 5.5 through TRL, with the user's key from Kaggle Secrets.
  10 questions generated, 9 kept as `rules_`.
- **Answers:** `rrf.answers()` returned a 20 × 9 matrix with no missing values, and
  `predict_proba` returned 20 × 2 (`failed`, `successful`). Kev's answers look sensible by eye
  (e.g. 0.99 for "deep prior experience" on a profile that says so).
- **Cost:**
  - **This fit:** $0.11 actual, all of it the generator (TRL's estimate beforehand was $0.17;
    the estimate counts the full output-token allowance, so it's an upper bound). Kev costs
    nothing (free Kaggle GPU).
  - **B1 (2,000 rows, library defaults):** TRL estimates at most **$0.71** for question
    generation. Answering is free. So the whole TRL phase costs well under $1 in Claude credits.
- **Time:** the fit took 31 s, about 1.6 s per founder including generation. Kev's answering
  speed is as measured at A3 (about 104 answers per second), so B1 plus B2 (about 100
  rules × 3,000 founders) is about 50 minutes on the GPU.
- **Noted, not changed (TRL fidelity):** TRL kept two near-identical questions ("Does the
  profile state [that] the founder has deep prior experience…") and two overlapping
  B2B-sector questions. That's upstream TRL's design: its filter for near-copies
  (`hamming_threshold=0.15`) applies only to the vote combiner (C1b), while the elastic net
  (C1a) takes every question and leaves redundancy to its L1 penalty. The decision combiner
  (C2, C3) follows the elastic net, so a near-copy's answer appears twice in the serialised
  text. Left as is.
- **Harmless log noise:** "Error in sitecustomize … No module named 'wrapt'" still appears in
  some subprocesses on Kaggle; it doesn't stop them (exit 0).
- **A4 is done.**

## 2026-11-14 · A5 · 3,000-row dataset: the real 50 plus 2,950 synthetic (user decision)

- **Decision:** `data/raw/full.jsonl` is the 50 real-grounded sample rows followed by 2,950
  synthetic rows from `research/generate_dataset.py` (seed 42). The user allowed made-up profiles
  "based on the 50 real ones" instead of grounding all 3,000 in real companies.
- **How outcomes work:** a background score from the profile plus Gaussian noise (sd 0.62),
  ranked within each batch of 50 into exact band counts. Details in `results/data/README.md`.
- **Noise level chosen:** 0.62 gives AUC 0.69 and F0.5 0.36 for a logistic model on profile
  fields. Raising it to 0.72–0.82 lifted the "surprising" share only from 20% to about 24% while
  dropping boosted-tree AUC to about 0.6, which would leave the learn-stage comparison too noisy.
  So the surprising share is 20%, below the prompt's "about 30%".
- **Validation (A5 "done when"):** `validate.py --profile full` passes with no errors or
  warnings: band proportions exact (within ±3 points required), 0 rows dropped (under 2%
  required), no duplicates or shared career paths.

## 2026-11-14 · A5/A6 · Full dataset re-checked, then split

- **Re-check:** the research session's validator (the newer one, with the exact all-pairs
  near-duplicate check) also passes `data/raw/full.jsonl`: no errors, no warnings, no near
  duplicates.
- **Read in the generator:** synthetic outcomes come from `background_score`, which is mostly
  additive with five small interactions, plus noise (sd 0.62). Years depend only on the outcome
  band. Both are now listed under the dataset's limits (`results/data/README.md`), since they
  bound what the research can claim (interactions) and what the timeline control can know.
- **A6:** `research/splits.py`, seed 42: 2,000 / 400 / 600, exactly 20% successful in each, the
  band mix identical across splits, no duplicate groups, no id in two splits. The 50
  real-grounded rows fell 31 / 6 / 13. Report: `results/data/stats.md`; input hash in
  `results/run_info.json`.

## 2026-11-14 · B1 · Kev reads the best 40 questions; C1a-40 added (user decision)

- **Decision:** C2, C3 and the production model read only the **40 best questions** (TRL's own
  `max_rules=40`, ranked by F0.5 on train, best first) instead of all ~100 that RRF generates
  by default. A new matched control, **C1a-40**, is TRL's elastic net with the same
  `max_rules=40`. C1a (all questions) and C1b (vote) stay as TRL ships them.
- **Why:** time on the free T4 (no bf16, so Kev trains in fp32). An answer line averages 30
  tokens (Qwen tokenizer, measured on the A4 questions), so:

  | Questions Kev reads | Tokens per state | C3 fine-tune, 2 epochs |
  |---|---|---|
  | ~100 (all) | ~3,070 | ~7 h |
  | 60 | ~1,870 | ~4.3 h |
  | **40 (chosen)** | **~1,260** | **~2.9 h** |
  | 30 | ~960 | ~2.2 h |

  The hours come from A3's measured training speed for long states (about 480 tokens per
  second, batch 8, gradient checkpointing), plus about half an hour for checkpoint selection
  and predictions. The production model would cost the same again if C3's input wins at D2.
  Kev's trainer offers only fp32 or bf16, so fp16 isn't an option without changing Kev.
- **Why C1a-40:** with the cap, Kev sees less than C1a. C1a-40 reads exactly what Kev reads,
  so "C3 versus C1a-40" isolates the learn stage, and "C1a versus C1a-40" shows what the cap
  itself costs. It's free: the same cached questions and answers, refit in seconds.
- **Checked in code:** `fit_rrf.py` stops if any fit got different questions, or if C1a-40 has
  a rule outside C2's 40 (both rank with TRL's same `rank`, no Hamming filter, no base-rate
  drop). Dry run on 30 real train rows with a fake question writer and CPU Kev, cap 2 of 4:
  every check passes, and the answer matrices hold C2's 2 questions.
- **Consequences:**
  - The answer matrices (`data/answers/{split}.csv`) and `rules.json` hold the 40 questions
    in C2's order. So CTRL (XGBoost) reads the same 40 as C1a-40 and C3.
  - The app answers 40 questions per founder instead of ~100 (about 2.5× less Kev work).
  - **A deviation from library defaults** (MASTER_PLAN 4b.3), to be stated in the README, the
    paper and the TRL pull request.

## 2026-11-14 · C1-train · C3 and C4 kept on Hugging Face

- **Decision:** at the end of the `c_kev` run, the chosen C3 and C4 checkpoints are uploaded to
  free public Hugging Face model repos, `<user>/trl-for-angels-kev-c3` and `-c4`, with their
  training reports (`research/hf_hub.py upload-model --name ...`), using the `HF_TOKEN`
  Kaggle Secret.
- **Why:** the checkpoints are too big for GitHub, so without this they're lost when the Kaggle
  run ends. Scoring doesn't need them (predictions are made in the same run), but the probes
  and patching steps (F2, F3) and a paper's reproducibility do.
- **If the upload fails,** the run carries on: predictions are already saved.

## 2026-11-14 · B1/B2 · Questions written, answered and fitted through TRL

- **Run:** `kaggle-results: runs/20261114-160701-b1b2` (repo commit `22f39d4`), 86 minutes on
  a Kaggle T4. Outputs copied into `data/answers/`, `data/models/` and `data/predictions/`
  with `kaggle/import_run.py`.
- **Questions:** Claude Opus 5.5 wrote **93** questions (TRL defaults: 10 prompts × 10, minus
  unusable ones). Kept as rules: C1a 63 (elastic net's non-zero weights), C1a-40 38, C1b 21
  (vote), C2 40 (`max_rules=40`). Each question's train precision, recall and F0.5:
  `data/answers/questions.csv`. The 40 Kev reads, best first: `data/answers/rules.json`.
- **Checks passed:** every fit got the same 93 questions; C1a-40's rules are all among C2's
  40; the answer matrices (2,000 / 400 / 600 founders × 40 questions) have no missing answers.
- **Cost:** **$0.49** of Claude credits (TRL's estimate beforehand: at most $0.72). Kev: $0.
- **Time:** C1a fit 47 min (Kev answering 93 questions for 2,000 founders, about 186k answers,
  plus question writing); C2 fit 11 min (2,000 decision calls on 872-token texts, about 3 per
  second); C1a-40 and C1b seconds (cached answers); B2 19 min.

## 2026-11-14 · B3/B4 · Baselines on val, sanity check passed (test not read)

- **CTRL:** XGBoost chose max depth 2, learning rate 0.1, min child weight 5 (best val log-loss
  0.443 of 12 candidates; `data/predictions/ctrl_config.json`).
- **Val scores** (F0.5 at the val-tuned threshold; provisional, since the val threshold is
  tuned on the same founders it's scored on; `results/summary/b3-provisional/`):

  | Condition | F0.5 | Precision | Recall | ECE |
  |---|---|---|---|---|
  | CTRL (XGBoost, 40 questions) | 0.457 | 0.594 | 0.237 | 0.035 |
  | C1a (elastic net, all 93) | 0.446 | 0.556 | 0.250 | 0.030 |
  | C1a-40 (elastic net, 40) | 0.426 | 0.432 | 0.400 | 0.036 |
  | C1b (vote) | 0.377 | 0.358 | 0.475 | 0.220 |
  | C2 (base Kev, 40, zero-shot) | 0.340 | 0.304 | 0.650 | 0.247 |

  TRL's own train-tuned thresholds give nearly the same F0.5 for C1a (0.432), C1a-40 (0.421)
  and C1b (0.372).
- **B4 sanity check: passed.** The best val F0.5 is 0.457, far below the 0.8 "too easy" line,
  so the data isn't regenerated. Test predictions exist but haven't been read; they're scored
  once, at D1.
- **First readings (val, to be confirmed on test with CIs):** the questions carry real signal
  (PR-AUC about 0.40 against a base rate of 0.20). Base Kev zero-shot (C2) ranks worse
  (PR-AUC 0.33) and is badly calibrated (ECE 0.25): it says yes too often, which is
  expected, since the released Kev-0.6B ships uncalibrated (temperature 1.0) and wasn't
  trained for this question. That's the gap C3 (fine-tuned and temperature-calibrated) is
  meant to close.
- **C3 input length, measured:** every C3 text is 872 tokens (Qwen tokenizer; same length
  for every founder, since each line ends in a one-token yes or no), not the ~1,264 estimated
  from the A4 questions. C4's profiles average 173 tokens (max 316). None exceed
  `--max_state 4096`. Revised C3 fine-tune: about 2 hours for 2 epochs, about 2.5–3 hours
  with checkpoint selection and predictions.
- **Next:** `c_kev` (runner switched).

## 2026-11-14 · Records · Write-up added for the paper trail

- **Added:** `results/RUNS.md` (every Kaggle run: task, exact code commit, result, where its
  log is), `results/data/questions.md` (all 93 questions with train scores and which condition
  uses each; generated by `research/questions_report.py`), and the progress table on
  `results/README.md`.
- **Process change:** `research/evaluate.py` now also copies each reliability plot into the
  folder of every experiment it shows (section 9c). For the existing `b3-provisional` stage
  the same copies were made by hand with the same rule; nothing in it was changed or
  rescored.

## 2026-11-14 · C1-train · First c_kev run failed after training; fixed and rerun

- **Run:** `kaggle-results: runs/20261114-173802-c_kev` (repo commit `e44ead9`), failed after
  98 minutes with "no chosen c3 checkpoint".
- **Cause (a bug in `research/train_kev.py`):** training used `--max_state 4096` correctly,
  but the val scoring that chooses the checkpoint used Kev's `LocalPredictor` with its default
  limits, Kev's 384-token training context. Every C3 state is 873 tokens, so scoring the first
  candidate raised `ContextOverflow: state exceeds 384 tokens: 873`. C4's profiles (under 384)
  were unaffected. The run script then stopped at the missing C3 checkpoint, before scoring or
  uploading C4, so neither model's weights survived the Kaggle session.
- **What the failed run still showed:**
  - **C3 trains as expected:** 2 epochs, 250 steps each, 48 and 49 min, peak 4.4 GB on the
    T4, every record kept.
  - **C4 finished:** it chose ep2 (val log-loss 1.086 for the released Kev, 0.475 after
    epoch 1, 0.470 after epoch 2), with temperature 1.275, and val ECE fell from 0.057 raw to
    0.022 calibrated. These are logged in `runs/.../kev/train_c4.log` and reproduced by the
    rerun with the same seed.
- **Fixes:**
  1. Scoring now uses the same limits as training (`kev.model.training_context(4096)`).
     Checked locally on real 873-token C3 states with base Kev, the exact call that failed.
  2. The released checkpoint is scored **before** any training, and each epoch right after it
     trains, so a scoring problem shows in minutes, not after the training time.
  3. `kaggle/run.sh`: each trained model is uploaded to Hugging Face **before** it's scored;
     EXTRA is scored whatever happens to training; one condition failing no longer stops the
     other. `d_prod` also uploads before predicting.
  4. Dry runs on real rows: EXTRA, C4 and C3 scoring through TRL (`kev_predict.py`, CPU, base
     Kev standing in for the trained checkpoints), and the whole `train_kev.py` flow in
     miniature (8 rows, 1 step per epoch).
- **Cost:** about 1.7 hours of Kaggle GPU time; no money.

## 2026-11-14 · D3/D4 · Production chain dry-run before it's needed

- **Why:** after the c_kev failure, every step still to run was dry-run locally on real rows
  first, exactly as `kaggle/run.sh` runs it (CPU, base Kev, 8 training rows, 1 step per
  epoch), so problems show here rather than on Kaggle.
- **Checked, for both possible D2 winners (C3 and C4):** `serialise.py --production` on the
  real splits; `train_kev.py --condition prod` (C3 with long-state checkpointing); the copies
  the run makes; `kev_predict.py --condition prod`; `thresholds.py` (D4); `export_artifacts.py`
  (all three app files match the app contract). Also `evaluate.py` on val with Kev
  prediction files (D1's path; test not read).
- **Found and fixed:** the d_prod run saved the production report and temperatures only under
  `kev/`, while `export_artifacts.py` reads `data/models/prod/`. The run now writes them there
  too. Also added a "Kev family" reliability plot (C2, EXTRA, C3, C4), so EXTRA appears in a
  plot.
- **The c_kev rerun** (`runs/20261114-192753-c_kev`) started at 19:27 UTC with the scoring fix.

## 2026-11-14 · C1-train, C2-temp · C3 and C4 fine-tuned (c_kev rerun)

- **Run:** `runs/20261114-192753-c_kev` on the `kaggle-results` branch, repo commit `1fd795e`,
  19:27–21:40 UTC, two T4s (C3 on one, C4 on the other), fp32, finished with exit 0.
- **Recipe (both):** from `jaredpalmer/kev-0.6b`, lr 2e-5, batch 8, 2 epochs of 250 steps,
  `--max_state 4096`, checkpoint and temperature chosen on val (section 9b C1-train).
- **Val log-loss** (the released Kev, then after each epoch; lower is better; a constant
  20% guess scores 0.500):

  | | Released Kev | Epoch 1 | Epoch 2 | Chosen | Temperature | Val ECE raw → calibrated |
  |---|---|---|---|---|---|---|
  | C3 (Kev on TRL's 40 answers) | 0.618 | 0.458 | 0.455 | ep2 | 1.072 | 0.031 → 0.024 |
  | C4 (Kev on the founder text) | 1.086 | 0.475 | 0.470 | ep2 | 1.275 | 0.058 → 0.025 |

  Both "done when" checks pass: val loss improved over the released Kev, and calibrated val
  ECE is no worse than raw. C4's epoch 2 repeats the failed run's numbers (same seed).
- **Time:** C3 49 min per epoch (gradient checkpointing, peak 4.4 GB); C4 8.5 min per epoch
  (peak 13.1 GB). Scoring every founder through TRL: C3 15 min, C4 1.4 min, EXTRA 1.3 min.
- **Kept on Hugging Face** for the interp steps (F2, F3):
  [Sidi3355/trl-for-angels-kev-c3](https://huggingface.co/Sidi3355/trl-for-angels-kev-c3)
  (commit `840f3e9`) and
  [Sidi3355/trl-for-angels-kev-c4](https://huggingface.co/Sidi3355/trl-for-angels-kev-c4)
  (commit `704f8d4`).
- **Imported:** `data/predictions/kev_{c3,c4,extra}_{val,test}.csv` (`kaggle/import_run.py`).
  Test predictions were written by the run but not scored until D1.
- **Cost:** about 2.2 hours of Kaggle GPU time; no money.

## 2026-11-14 · D2 · The app's model reads TRL's answers (C3's input)

- **Decision:** the production model (D3) is trained on C3's input, TRL's 40 answers as text,
  not C4's founder text. Made on val only, before test was read (D1 ran after this entry).
- **Evidence (val, 400 founders; `results/summary/d2-val/`):**

  | | F0.5 | Precision | Recall | ECE | Brier | PR-AUC |
  |---|---|---|---|---|---|---|
  | C3 (fine-tuned Kev on TRL's answers) | 0.426 | 0.593 | 0.200 | 0.024 | 0.146 | 0.403 |
  | C4 (fine-tuned Kev on the founder text) | 0.428 | 0.472 | 0.312 | 0.025 | 0.146 | 0.404 |

  The plan's two criteria, val F0.5 and ECE, are tied. A paired, stratified bootstrap of the
  F0.5 difference (C3 − C4; 1,000 resamples, seed 42, threshold re-tuned in each) gives
  −0.007, 95% CI −0.107 to +0.101, with C3 ahead in 45% of resamples. The two models' P(success)
  correlate at 0.82.
- **Tie-break (Kev's own val measures, from each run's report):** C3 has the lower calibrated
  log-loss (0.454 vs 0.460) and selective risk (AURC 0.097 vs 0.116). It can also decide far
  more founders confidently: at ≤5% error it covers 20.5% of val founders against C4's 2.8%,
  which matters for the app's autonomous *pass*.
- **Product reasons:** with C3's input, the memo's drivers and what-ifs are TRL's questions
  (MASTER_PLAN section 8, step 7), and the app runs TRL's whole pipeline, the contribution the
  research is about.
- **Cost of the choice:** D3 takes about 2 hours instead of 25 minutes, and the app asks the
  Kev answerer 40 questions per founder before deciding.
- **Chosen by:** the owner, from these numbers (C3, the recommended option).

## 2026-11-15 · D3 · Production model trained; its val predictions asked without the options' descriptions, so redone

- **Run:** `runs/20261114-224030-d_prod` on the `kaggle-results` branch, repo commit `d5a461a`,
  22:40–01:56 UTC (3 h 16 min), fp32 on a T4, finished with exit 0.
- **Training (C3's input, the two choice questions `outcome` and `years`):** from
  `jaredpalmer/kev-0.6b`, lr 2e-5, batch 8, 2 epochs of 250 steps (87 min each: two questions
  per founder), `--max_state 4096`. Kev's own val evaluation (400 founders × 2 questions, with the
  options' descriptions, as trained): mean log-loss 2.010 (released Kev) → 1.172 (epoch 1) →
  1.163 (epoch 2, chosen) → 1.161 calibrated. Temperatures: outcome 1.149, years 0.871 (below 1:
  the years answers were too cautious, so they are sharpened). Val ECE 0.027 → 0.021, so the "done
  when" checks pass. Saved to Hugging Face:
  [Sidi3355/trl-for-angels-kev-prod](https://huggingface.co/Sidi3355/trl-for-angels-kev-prod)
  (weights at commit `fc8409c`; `report.json` added at `f1bb43f`).
- **Found:** the run's val distributions (`prod_val.csv`, the input to D4) were asked through
  TRL, whose System One adapter always sent a choice question's options with **empty
  descriptions** (`criteria: {"shut down": null, ...}`), while the model was trained, and its
  temperatures fitted, with the descriptions (`"shut down": "the company closed"`, ...). Caught by
  serving the published checkpoint on CPU and asking 3 val founders exactly as the app will (from
  `model.json`): the answers differed from Kaggle's by up to 0.18. Asked without descriptions, they
  matched Kaggle's to 0.00007, so the checkpoint is right and only the request differed. The
  symptom was already visible in the band check: on average 35% "shut down" against 50% actual.
- **Research results are not affected:** C3, C4 and EXTRA ask one yes/no question, which has no
  options. Their TRL-scored val log-loss equals Kev's own evaluation (C3 0.4542 and 0.4542; C4
  0.4598 and 0.4599).
- **Fix:** the TRL fork's `ChoiceQuestion` takes optional `descriptions`, sent as System One
  criteria, and part of the cache key only when given (fork commit `d9d1380`, with tests; ruff,
  pyright and pytest pass). `research/kev_predict.py` now passes them. The 400 val founders are
  being rescored through TRL, on CPU in the development container, from the Hugging Face
  checkpoint (fp32, the same numbers as the T4 to 0.0001). Kaggle's file is kept as
  `data/predictions/prod_val_no_descriptions.csv` (not used), and the D4 table, built from it
  first and never published, was deleted.
