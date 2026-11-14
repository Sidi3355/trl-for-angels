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
  B2B-sector questions. RRF doesn't remove near-duplicates semantically; that's library
  behaviour, so it stays. The elastic net copes with correlated columns, and in C2/C3 the
  answer appears twice in the serialised text.
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
