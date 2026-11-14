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
- **To decide at C1-train:** for C3, use both T4s, train 1 epoch, or a shorter serialisation;
  choose once the real state lengths are known. Every option fits one Kaggle session.

## 2026-11-14 · A1 · Open item: TRL's cache location

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
- **Conventions used:** years are whole elapsed years from founding to the outcome event; a
  founder who never attended university has the education line `- no degree`; a founder whose
  earlier startup was still running at founding has "1 still operating".
- **Validation:** `research/validate.py --profile sample50` passes with no errors or warnings
  (`results/data/validation_sample50.md`).
