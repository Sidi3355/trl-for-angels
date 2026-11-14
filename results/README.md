# Results: start here

**What this project tests:** TRL writes yes/no questions about a founder and answers them.
Which final step (the "learn stage") turns those answers into the most accurate and best
calibrated prediction of founder success? Terms are explained in
[GLOSSARY.md](GLOSSARY.md).

**The answer:** not yet; it comes from the final test evaluation (D1). This page will then
give it in three sentences.

**Progress (2026-11-14):**

| Step | Status | Where |
|---|---|---|
| Dataset: 3,000 profiles, validated, split 2,000 / 400 / 600 | done | [data/](data/README.md) |
| TRL: Claude wrote 93 questions, Kev answered them for every founder | done ($0.49) | [data/questions.md](data/questions.md) |
| Baselines (C1a, C1a-40, C1b, CTRL) and base Kev (C2) scored on val; sanity check passed | done, provisional | [summary/b3-provisional/](summary/b3-provisional/metrics.md) |
| Fine-tuning Kev (C3, C4) on Kaggle | running | [RUNS.md](RUNS.md) |
| Final scores on test, with confidence intervals (D1) | next | |
| The app's model and risk table (D3, D4) | after D1 | |

**What can be claimed:** results hold for this generated dataset, with Kev-0.6B as the
answerer. Real-world accuracy is not claimed; VCBench is the future real-data test.

## What we compared

Every condition uses the same founders and the same questions and answers, so only the final
step differs. TRL's Claude-written questions number about 100; Kev reads the **best 40** (by
F0.5 on train), so C1a-40 and CTRL read those same 40, while C1a and C1b are TRL as shipped.

| Name | In plain words | What it reads | Trained on this task? |
|---|---|---|---|
| **C1a** | TRL's default: a weighted sum of the answers (elastic net) | all the answers | yes (train) |
| **C1a-40** | the same weighted sum, on only the 40 questions Kev reads (a fair match for C2 and C3) | the best 40 answers | yes (train) |
| **C1b** | the RRF paper's method: count the yes answers of the best questions (vote) | the answers | yes (train) |
| **CTRL** | a standard machine-learning control (XGBoost) | the best 40 answers | yes (train; tuned on val) |
| **C2** | Kev as released, reading the answers as text | the best 40 answers, as text | no |
| **C3** | Kev fine-tuned to read the answers as text | the best 40 answers, as text | yes (train) |
| **C4** | Kev fine-tuned to read the founder profile directly, with no questions | the profile | yes (train) |
| **EXTRA** | Kev as released, reading the founder profile directly | the profile | no |

**How to read a score:** the main score is **F0.5**, which balances precision (how many
flagged founders really succeed) and recall (how many successes get flagged), with precision
counting twice as much. Calibration is shown by **ECE** and **Brier** (lower is better) and by
reliability diagrams. Every test score has a 95% confidence interval.

## Map of this folder

| File or folder | What it is |
|---|---|
| [FINDINGS.md](FINDINGS.md) | plain-English findings, one short section each, with the key number and plot |
| [GLOSSARY.md](GLOSSARY.md) | every technical term in one or two plain sentences |
| [METHODS.md](METHODS.md) | the full method in one place (data, TRL settings, conditions, fine-tuning, scoring, limits), written for a paper |
| [DECISIONS.md](DECISIONS.md) | decision log: date, decision, reason, evidence |
| [RUNS.md](RUNS.md) | every GPU run on Kaggle: task, exact code, result, where its log is |
| `run_info.json` | TRL commit and version, model IDs, seeds, split sizes, measurements |
| [data/](data/README.md) | what the dataset is, how it was made, its limits, and per-split stats |
| [data/questions.md](data/questions.md) | the 93 questions Claude wrote, and which condition uses each |
| [experiments/01_baselines/](experiments/01_baselines/README.md) | C1a, C1a-40, C1b and CTRL |
| [experiments/02_kev_zero_shot/](experiments/02_kev_zero_shot/README.md) | C2 and EXTRA |
| [experiments/03_kev_finetuned/](experiments/03_kev_finetuned/README.md) | C3 and C4 |
| [experiments/04_production_model/](experiments/04_production_model/README.md) | the app's model and its risk-threshold table |
| `experiments/05_interp_flips/` to `07_interp_sae/` | what the models rely on (after the app works) |
| `summary/<stage>/` | the metrics table for every condition, and the final plots |

Results are never overwritten: each run goes in a folder named after its stage (for example
`b3-provisional` or `d1-final`), and any rerun is explained in DECISIONS.md.
