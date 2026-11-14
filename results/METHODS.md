# Methods

Everything needed to describe, check or repeat this study, in one place, written so it can go
into a paper's methods section. Plain-English terms are defined in [GLOSSARY.md](GLOSSARY.md),
the reasons for each choice (with dates and evidence) are in [DECISIONS.md](DECISIONS.md), and
the exact versions, seeds, costs and timings are in [run_info.json](run_info.json). Numbers
marked *pending* are filled in as each step runs.

## 1. Question

TRL (Think, Reason, Learn; Vela Research) predicts in three steps: a language model **thinks**
up yes/no questions, a second model **reasons** by answering them for every founder, and a
**learn** step turns the answers into a prediction. With the think and reason steps held fixed,
which learn step gives the most accurate and best-calibrated prediction of founder success?

## 2. Data

- **Records:** 3,000 anonymised founder profiles (`data/raw/full.jsonl`), each describing the
  founder on the day their company was founded, in one fixed template (industry and
  co-founders; background and experience; 1–3 degrees; 1–6 jobs, oldest first; prior startups;
  prior exits). Each record has two labels: the outcome band (shut down, under $50M,
  $50M-$500M, $500M-$1B, over $1B) and the years to that outcome (under 5, 5-8, over 8).
- **Sources:** 50 records are based on real founders and companies (`data/raw/sample50.jsonl`,
  sources in `data/raw/sample50_sources.md`, outcomes checked by web search). The other 2,950
  are synthetic, from `research/generate_dataset.py` (seed 42, byte-for-byte reproducible),
  modelled on those 50. In the synthetic rows a *background score* (mostly additive over the
  profile fields, plus five small interactions) plus Gaussian noise (sd 0.62) is ranked within
  each batch of 50 and cut into exact band counts; years are drawn from fixed odds per band.
  Details and limits: [data/README.md](data/README.md).
- **Research label:** *successful* if the outcome is $500M-$1B or over $1B, otherwise *failed*:
  600 of 3,000 (20%).
- **Validation:** `research/validate.py --profile full` checks the template, the allowed
  values, internal consistency (experience against job lengths, exits against prior startups),
  banned evaluative words, band counts, exact and near duplicates (all pairs), shared career
  paths, and whether any single field predicts the label (out-of-fold AUC). Result: pass, no
  errors or warnings; best single field AUC 0.60 ([data/validation_full.md](data/validation_full.md)).
- **Difficulty:** a logistic regression on the profile fields reaches AUC 0.69 and F0.5 0.36
  (5-fold), well below the plan's "too easy" line of F0.5 0.8.

## 3. Splits

2,000 train / 400 val / 600 test, stratified on outcome band, seed 42 (`research/splits.py`;
order from SHA-256 hashes, so the same input gives identical files). Each split is exactly 20%
successful; exact and near-duplicate profiles would be kept in one split (there were none).
Train is the only data any model learns from; **every choice** (thresholds, temperatures,
checkpoints, the XGBoost settings, the app's model) **is made on val**; test is read once, at
the end. Per-split counts: [data/stats.md](data/stats.md).

## 4. The fixed think and reason steps (TRL)

- **Library:** TRL 0.3.0, from a fork of `Vela-Research/think-reason-learn` at upstream
  commit `3437d64`, branch `feature/decision-combiner`. The fork adds the decision combiner
  (section 5) and one fix: a System One endpoint can be called without an API key. Every model call goes through TRL's own `RRF.fit`, `.answers`,
  `.predict_proba`, `.predict`, `LLM` and `LLMSession`, with TRL's disk cache.
- **Method:** RRF (Random Rule Forest) with library defaults (10 prompts × 10 questions,
  30 examples per prompt, balanced classes, 3-fold CV), except `beta=0.5` (F0.5, the VCBench
  metric) and `random_state=42`; and, for the conditions that read 40 questions, `max_rules=40`
  (section 6).
- **Task given to TRL:** "Predict whether this startup founder's company will succeed (exit,
  IPO or funding over $500M)."
- **Think (questions):** Claude Opus 5.5 (`anthropic:claude-opus-5-5`, max output 16,000
  tokens, the user's API key). One set of questions, written once, is used by every condition.
- **Reason (answers):** base Kev-0.6B (`jaredpalmer/kev-0.6b`, an open reconstruction of
  TypeSafe's Jev: Qwen3-0.6B-Base with a rank-16 LoRA and a pointer head), self-hosted with
  `kev.serve` in fp32 on a Kaggle T4, reached through TRL as
  `LLM("kev-0.6b", base_url=".../v1/systemone", kind="decision")`. Kev replaced Jev, TRL's
  default answerer, because Jev has no free tier. The same Kev answers for every condition.
- **Answer matrix:** P(yes) per founder and question, for every split, cached once
  (`data/answers/{split}.csv`).

## 5. A new TRL learn step: the decision combiner

Added to the fork as `RRF(combiner="decision", combiner_model=..., combiner_question=...)`.
Each founder's answers are written as text, one line per question in rule order, the question
followed by `yes` (P(yes) ≥ 0.5), `no`, or `unknown` (TRL's `answers_text`). A decision model
behind TypeSafe's System One API is then asked one yes/no question about that text ("Will this
founder's company succeed (exit, IPO or funding over $500M)?"), and its probability is the
prediction. TRL's `best_threshold` sets the threshold on train. The combiner passes TRL's
`check_classifier` and contract tests offline (404 tests; ruff, pyright strict), and is drafted
as a pull request to TRL (`docs/trl_pr_description.md`).

## 6. Conditions compared

| ID | Learn step | Reads | Trained on |
|---|---|---|---|
| C1a | RRF elastic net (TRL default) | all questions' answers | train |
| C1a-40 | RRF elastic net, `max_rules=40` | the best 40 questions' answers | train |
| C1b | RRF vote (the paper's method, VCBench entry) | its own selected questions | train |
| CTRL | XGBoost | the best 40 questions' answers | train (settings chosen on val) |
| C2 | base Kev-0.6B as the decision combiner (zero-shot) | the best 40, as text | nothing |
| C3 | fine-tuned Kev-0.6B as the decision combiner | the best 40, as text | train |
| C4 | fine-tuned Kev-0.6B, no questions | the founder text, as TRL renders it | train |
| EXTRA | base Kev-0.6B, no questions | the founder text, as TRL renders it | nothing |

- **The best 40:** TRL's own ranking of the questions by F0.5 on train (`max_rules=40`, no
  Hamming filter, no base-rate drop), best first. Kev reads 40 rather than all ~100 to keep
  each text near 1,300 tokens instead of about 3,000, which makes C3's fine-tune about
  3 hours instead of about 7 on the T4. C1a-40 reads exactly the same 40, so C3 against
  C1a-40 isolates the learn step, and C1a against C1a-40 shows what the cap costs.
- **CTRL:** XGBoost, grid over max depth {2, 3, 4} × learning rate {0.03, 0.1} × min child
  weight {1, 5}; 2,000 trees with early stopping (50 rounds) on val log-loss, subsample and
  column sample 0.8, seed 42; the best val log-loss wins (`research/baselines.py`). It
  separates "Kev helps" from "any non-linear learner helps".
- **C4 and EXTRA** read the founder text through TRL's own rendering helper (`to_texts`), the
  exact text TRL sends its answerer, so they differ from the TRL conditions only by skipping
  the think and reason steps.

## 7. Fine-tuning Kev (C3, C4)

- **Data:** one JSONL request per train founder (`research/serialise.py`): the state (C3: the
  answers as text from `answers_text`; C4: the rendered profile), and one `noul` (yes/no)
  question labelled with the research label.
- **Recipe** (`research/train_kev.py`, Kev's own trainer, Kev commit `2074cc4`): start from the
  released `jaredpalmer/kev-0.6b` (`--init_from`), with its architecture settings copied from
  the checkpoint's metadata (LoRA rank 16, targets, head, special embeddings); learning rate
  2e-5; batch 8; `--max_state 4096` (Kev's default of 384 tokens would silently drop every C3
  record); fp32 (the T4 has no bf16); seed 42; gradient checkpointing for C3's long texts.
- **Checkpoint choice:** one epoch from the release (ep1), then one more from ep1 (ep2); the
  lowest val log-loss of base, ep1 and ep2 is kept.
- **Calibration:** one temperature per model, fitted on val by minimum log-loss (Kev's
  `fit_temperature`), and written into the checkpoint. The released Kev-0.6B ships
  uncalibrated (temperature 1.0).
- **Compute:** two Kaggle T4s, C3 and C4 in parallel, one each. Measured training speed for
  long texts: about 480 tokens per second (A3). Actual: C3 49 min per epoch (873-token states,
  gradient checkpointing, peak 4.4 GB), C4 8.5 min per epoch (peak 13.1 GB).
- **Outcome:** both kept epoch 2. Val log-loss 0.618 → 0.455 (C3) and 1.086 → 0.470 (C4);
  temperatures 1.072 and 1.275 (`results/DECISIONS.md`, C1-train). Checkpoints are public on
  Hugging Face (`Sidi3355/trl-for-angels-kev-c3`, `-c4`).

## 8. Scoring

- **One threshold rule for every condition:** the F0.5-best threshold on val (TRL's
  `best_threshold`), applied unchanged to test. For C1a, C1a-40 and C1b, TRL's own as-shipped
  decision (`predict()`, threshold tuned out of fold on train) is reported as well.
- **Metrics on test:** F0.5 (main), precision, recall, Brier score, ECE (10 equal-width bins,
  weighted), PR-AUC, and a reliability diagram per condition (`research/evaluate.py`,
  `research/metrics.py`).
- **Uncertainty:** 95% percentile intervals from 1,000 bootstrap resamples, stratified
  (positives and negatives resampled separately), with the threshold fixed from val.
- **Paired comparisons:** for planned pairs (each learn stage against C1a; C3 against C1a-40,
  CTRL, C2 and C4; C4 against EXTRA; C1a-40 against C1a), the difference itself, with a paired
  stratified bootstrap 95% CI (the same resampled founders for both, 1,000 resamples, seed 42,
  thresholds fixed from val; `research/paired.py`). The pairs were fixed from the research
  question before the script was run.
- **Order:** the val-only table (`d2-val`) and the D2 choice were made and committed before the
  one test evaluation (`d1-final`).
- **No result is overwritten:** each scoring run writes its own folder
  (`results/summary/<stage>/`), and the script refuses to reuse one.

## 9. Production model (the app)

Trained after the research with the same recipe, on whichever input (C3's answers or C4's
profile) wins **on val**. They tied on val (F0.5 0.426 vs 0.428; paired bootstrap CI for the
difference −0.107 to +0.101), so the tie was broken on Kev's own val measures (log-loss,
selective risk) and on explainability: C3's input was chosen (`results/DECISIONS.md`, D2).
It is trained with two `choice` questions instead of one: outcome (five bands) and years (three), each with its own temperature fitted on val. The app's risk-threshold table
(precision and recall at each threshold, per target outcome and timeline) comes from val
(`research/thresholds.py`).

## 10. Interpretability (after the app works)

Answer flips (single and paired, against C1a's coefficients and CTRL's importances),
layer-wise probes at Kev's `<decide>` token, activation patching, and sparse-autoencoder
features (stretch). Because the synthetic outcome rule is known (`background_score`), what each
model relies on can be compared with the true weights.

## 11. Reproducibility

| What | Where |
|---|---|
| Versions, commits, model IDs, seeds, costs, timings | [run_info.json](run_info.json) |
| Every decision, with reason and evidence | [DECISIONS.md](DECISIONS.md) |
| Dataset generator (seed 42) and validator | `research/generate_dataset.py`, `research/validate.py` |
| GPU runs (Kaggle) | `kaggle/run.sh`; logs and outputs on the `kaggle-results` branch, `runs/<UTC time>-<task>/` |
| Generated questions and answers | `data/answers/` (rules, questions with train F0.5, answer matrices) |
| Saved TRL models | `data/models/<condition>/model.json` (TRL's `save`, no keys) |
| Every prediction | `data/predictions/`, and per experiment `results/experiments/*/<stage>/predictions.csv` |
| Tests | `tests/` (this repo), the fork's `tests/` |

## 12. Limitations

- **Mostly synthetic data.** 2,950 of 3,000 outcomes come from a known scoring rule plus noise,
  so results describe this dataset, not real founders. No real-world accuracy is claimed;
  VCBench is the intended real test.
- **Kev, not Jev, answers the questions,** so the C1 results are TRL with an open 0.6B
  answerer, not TRL as Vela runs it.
- **Kev reads the best 40 questions, not all of them** (section 6), a deviation from TRL's
  defaults made for compute; C1a-40 measures its effect.
- **Small positive class:** 400 successful founders in train, 120 in test, hence the
  confidence intervals.
- **Years depend only on the outcome band** in the synthetic rows, so the app's timeline
  estimate carries no information beyond the outcome.
- **Compute limits:** free T4s in fp32; two epochs at most per fine-tune.

## 13. Costs

| Step | Cost |
|---|---|
| A4 smoke test (20 founders) | $0.11 (Claude) |
| B1 question writing (2,000 founders) | $0.49 (Claude; TRL's estimate was at most $0.71) |
| All Kev work (answering, fine-tuning, scoring) | $0: free Kaggle GPUs (about 6 hours of Kaggle runs before the production model, including one failed run) |
