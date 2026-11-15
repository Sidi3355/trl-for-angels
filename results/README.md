# Results: start here

**What this project tests:** TRL writes yes/no questions about a founder and answers them.
Which final step (the "learn stage") turns those answers into the most accurate and best
calibrated prediction of founder success? Terms are explained in
[GLOSSARY.md](GLOSSARY.md).

**The answer, in three sentences (final, test, 600 founders):** no learn stage beat TRL's
default elastic net (C1a, 0.319 F0.5, 95% CI 0.221–0.417): every paired difference on F0.5
includes zero, including XGBoost and fine-tuned Kev. Fine-tuning made Kev's probabilities
trustworthy (calibration error ECE 0.262 → 0.012 reading TRL's answers, the best of any
condition), but timid: it never gives a founder more than about 0.4, so it flags few founders
and finds only 10% of the successes at a precision-favouring threshold. Kev reading the founder
profile directly (C4, no questions) did as well as Kev reading TRL's answers (C3), and the
paper's vote is far worse calibrated than the elastic net (ECE 0.251 against 0.045).

**Progress (2026-11-15):**

| Step | Status | Where |
|---|---|---|
| Dataset: 3,000 profiles, validated, split 2,000 / 400 / 600 | done | [data/](data/README.md) |
| TRL: Claude wrote 93 questions, Kev answered them for every founder | done ($0.49) | [data/questions.md](data/questions.md) |
| Baselines (C1a, C1a-40, C1b, CTRL) and base Kev (C2) scored on val; sanity check passed | done | [summary/b3-provisional/](summary/b3-provisional/metrics.md) |
| Fine-tuning Kev (C3, C4) on Kaggle | done | [experiments/03_kev_finetuned/](experiments/03_kev_finetuned/README.md) |
| The app's input chosen on val: C3 and C4 tied, C3 chosen (D2) | done | [DECISIONS.md](DECISIONS.md), [summary/d2-val/](summary/d2-val/metrics.md) |
| Final scores on test, with confidence intervals and paired comparisons (D1) | done | [summary/d1-final/](summary/d1-final/metrics.md), [paired](summary/d1-final/paired.md) |
| The app's model (D3) and risk table (D4), built on val; the app's three files exported | done | [experiments/04_production_model/](experiments/04_production_model/README.md) |

**Final test scores** (95% CIs; threshold tuned on val; full table with precision, recall,
Brier and PR-AUC in [summary/d1-final/metrics.md](summary/d1-final/metrics.md)):

| Condition | F0.5 | ECE (calibration error) |
|---|---|---|
| C1a: TRL's default, elastic net | **0.319** (0.221–0.417) | 0.045 (0.027–0.076) |
| C1a-40: elastic net on the 40 Kev reads | 0.306 (0.236–0.378) | 0.035 (0.024–0.072) |
| C1b: the paper's vote | 0.305 (0.249–0.354) | 0.251 (0.232–0.273) |
| CTRL: XGBoost on the 40 | 0.305 (0.205–0.399) | 0.040 (0.024–0.075) |
| C2: released Kev on TRL's answers | 0.277 (0.242–0.312) | 0.262 (0.251–0.271) |
| EXTRA: released Kev on the profile | 0.319 (0.246–0.394) | 0.465 (0.446–0.483) |
| C3: fine-tuned Kev on TRL's answers | 0.227 (0.121–0.332) | **0.012** (0.008–0.045) |
| C4: fine-tuned Kev on the profile | 0.282 (0.191–0.368) | 0.021 (0.014–0.051) |

A founder picked at random succeeds 2 times in 10; C1a's flagged founders succeed about 4 times
in 10.

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
