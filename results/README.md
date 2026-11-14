# Results: start here

**What this project tests:** TRL writes yes/no questions about a founder and answers them.
Which final step (the "learn stage") turns those answers into the most accurate and best
calibrated prediction of founder success? Terms are explained in
[GLOSSARY.md](GLOSSARY.md).

**The answer:** not yet. The experiments are built and tested, but the dataset is still being
generated. Once the final evaluation runs, this page will give the answer in three sentences.

**What can be claimed:** results hold for this generated dataset, with Kev-0.6B as the
answerer. Real-world accuracy is not claimed; VCBench is the future real-data test.

## What we compared

Every condition uses the same founders, the same questions and the same answers, so only the
final step differs.

| Name | In plain words | What it reads | Trained on this task? |
|---|---|---|---|
| **C1a** | TRL's default: a weighted sum of the answers (elastic net) | the answers | yes (train) |
| **C1b** | the RRF paper's method: count the yes answers of the best questions (vote) | the answers | yes (train) |
| **CTRL** | a standard machine-learning control (XGBoost) | the answers | yes (train; tuned on val) |
| **C2** | Kev as released, reading the answers as text | the answers, as text | no |
| **C3** | Kev fine-tuned to read the answers as text | the answers, as text | yes (train) |
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
| [DECISIONS.md](DECISIONS.md) | decision log: date, decision, reason, evidence |
| `run_info.json` | TRL commit and version, model IDs, seeds, split sizes, measurements |
| [data/](data/README.md) | what the dataset is, how it was made, its limits, and per-split stats |
| [experiments/01_baselines/](experiments/01_baselines/README.md) | C1a, C1b and CTRL |
| [experiments/02_kev_zero_shot/](experiments/02_kev_zero_shot/README.md) | C2 and EXTRA |
| [experiments/03_kev_finetuned/](experiments/03_kev_finetuned/README.md) | C3 and C4 |
| [experiments/04_production_model/](experiments/04_production_model/README.md) | the app's model and its risk-threshold table |
| `experiments/05_interp_flips/` to `07_interp_sae/` | what the models rely on (after the app works) |
| `summary/<stage>/` | the metrics table for every condition, and the final plots |

Results are never overwritten: each run goes in a folder named after its stage (for example
`b3-provisional` or `d1-final`), and any rerun is explained in DECISIONS.md.
