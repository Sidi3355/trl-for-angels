# Metrics (d2-val)

One row per condition, split and threshold rule. F0.5 (the main metric) weighs precision twice as much as recall; Brier and ECE are calibration errors (lower is better). Terms: [GLOSSARY](../../GLOSSARY.md).

| Condition | Split | Threshold | F0.5 | Precision | Recall | Brier | ECE | PR-AUC | What this means |
|---|---|---|---|---|---|---|---|---|---|
| C1a (RRF, elastic net (TRL default)) | val | val-tuned F0.5 | 0.446 | 0.556 | 0.250 | 0.143 | 0.030 | 0.403 | flags 36 of 400; of every 10 it flags, about 6 succeed; finds 25% of the successes |
| C1a (RRF, elastic net (TRL default)) | val | TRL native (train out-of-fold) | 0.432 | 0.543 | 0.237 | 0.143 | 0.030 | 0.403 | flags 35 of 400; of every 10 it flags, about 5 succeed; finds 24% of the successes |
| C1a-40 (RRF, elastic net on the 40 questions Kev reads) | val | val-tuned F0.5 | 0.426 | 0.432 | 0.400 | 0.145 | 0.036 | 0.394 | flags 74 of 400; of every 10 it flags, about 4 succeed; finds 40% of the successes |
| C1a-40 (RRF, elastic net on the 40 questions Kev reads) | val | TRL native (train out-of-fold) | 0.421 | 0.431 | 0.388 | 0.145 | 0.036 | 0.394 | flags 72 of 400; of every 10 it flags, about 4 succeed; finds 39% of the successes |
| C1b (RRF, vote (the paper's)) | val | val-tuned F0.5 | 0.377 | 0.358 | 0.475 | 0.215 | 0.220 | 0.321 | flags 106 of 400; of every 10 it flags, about 4 succeed; finds 48% of the successes |
| C1b (RRF, vote (the paper's)) | val | TRL native (train out-of-fold) | 0.372 | 0.363 | 0.412 | 0.215 | 0.220 | 0.321 | flags 91 of 400; of every 10 it flags, about 4 succeed; finds 41% of the successes |
| CTRL (XGBoost on TRL's answers) | val | val-tuned F0.5 | 0.457 | 0.594 | 0.237 | 0.141 | 0.035 | 0.423 | flags 32 of 400; of every 10 it flags, about 6 succeed; finds 24% of the successes |
| C2 (base Kev on TRL's answers) | val | val-tuned F0.5 | 0.340 | 0.304 | 0.650 | 0.214 | 0.247 | 0.330 | flags 171 of 400; of every 10 it flags, about 3 succeed; finds 65% of the successes |
| EXTRA (base Kev on the founder text) | val | val-tuned F0.5 | 0.400 | 0.400 | 0.400 | 0.383 | 0.454 | 0.323 | flags 80 of 400; of every 10 it flags, about 4 succeed; finds 40% of the successes |
| C3 (fine-tuned Kev on TRL's answers) | val | val-tuned F0.5 | 0.426 | 0.593 | 0.200 | 0.146 | 0.024 | 0.403 | flags 27 of 400; of every 10 it flags, about 6 succeed; finds 20% of the successes |
| C4 (fine-tuned Kev on the founder text) | val | val-tuned F0.5 | 0.428 | 0.472 | 0.312 | 0.146 | 0.025 | 0.404 | flags 53 of 400; of every 10 it flags, about 5 succeed; finds 31% of the successes |

Validation only: test has not been read.
