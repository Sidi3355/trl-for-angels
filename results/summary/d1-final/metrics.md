# Metrics (d1-final)

One row per condition, split and threshold rule. F0.5 (the main metric) weighs precision twice as much as recall; Brier and ECE are calibration errors (lower is better). Terms: [GLOSSARY](../../GLOSSARY.md).

| Condition | Split | Threshold | F0.5 | Precision | Recall | Brier | ECE | PR-AUC | What this means |
|---|---|---|---|---|---|---|---|---|---|
| C1a (RRF, elastic net (TRL default)) | val | val-tuned F0.5 | 0.446 | 0.556 | 0.250 | 0.143 | 0.030 | 0.403 | flags 36 of 400; of every 10 it flags, about 6 succeed; finds 25% of the successes |
| C1a (RRF, elastic net (TRL default)) | val | TRL native (train out-of-fold) | 0.432 | 0.543 | 0.237 | 0.143 | 0.030 | 0.403 | flags 35 of 400; of every 10 it flags, about 5 succeed; finds 24% of the successes |
| C1a (RRF, elastic net (TRL default)) | test | val-tuned F0.5 | 0.319 (0.221–0.417) | 0.383 (0.271–0.500) | 0.192 (0.125–0.267) | 0.153 (0.145–0.162) | 0.045 (0.027–0.076) | 0.319 (0.270–0.395) | flags 60 of 600; of every 10 it flags, about 4 succeed; finds 19% of the successes |
| C1a (RRF, elastic net (TRL default)) | test | TRL native (train out-of-fold) | 0.312 (0.218–0.404) | 0.379 (0.270–0.500) | 0.183 (0.117–0.258) | 0.153 (0.145–0.162) | 0.045 (0.027–0.076) | 0.319 (0.270–0.395) | flags 58 of 600; of every 10 it flags, about 4 succeed; finds 18% of the successes |
| C1a-40 (RRF, elastic net on the 40 questions Kev reads) | val | val-tuned F0.5 | 0.426 | 0.432 | 0.400 | 0.145 | 0.036 | 0.394 | flags 74 of 400; of every 10 it flags, about 4 succeed; finds 40% of the successes |
| C1a-40 (RRF, elastic net on the 40 questions Kev reads) | val | TRL native (train out-of-fold) | 0.421 | 0.431 | 0.388 | 0.145 | 0.036 | 0.394 | flags 72 of 400; of every 10 it flags, about 4 succeed; finds 39% of the successes |
| C1a-40 (RRF, elastic net on the 40 questions Kev reads) | test | val-tuned F0.5 | 0.306 (0.236–0.378) | 0.312 (0.241–0.385) | 0.283 (0.208–0.367) | 0.156 (0.149–0.163) | 0.035 (0.024–0.072) | 0.286 (0.245–0.353) | flags 109 of 600; of every 10 it flags, about 3 succeed; finds 28% of the successes |
| C1a-40 (RRF, elastic net on the 40 questions Kev reads) | test | TRL native (train out-of-fold) | 0.291 (0.216–0.366) | 0.301 (0.224–0.376) | 0.258 (0.183–0.333) | 0.156 (0.149–0.163) | 0.035 (0.024–0.072) | 0.286 (0.245–0.353) | flags 103 of 600; of every 10 it flags, about 3 succeed; finds 26% of the successes |
| C1b (RRF, vote (the paper's)) | val | val-tuned F0.5 | 0.377 | 0.358 | 0.475 | 0.215 | 0.220 | 0.321 | flags 106 of 400; of every 10 it flags, about 4 succeed; finds 48% of the successes |
| C1b (RRF, vote (the paper's)) | val | TRL native (train out-of-fold) | 0.372 | 0.363 | 0.412 | 0.215 | 0.220 | 0.321 | flags 91 of 400; of every 10 it flags, about 4 succeed; finds 41% of the successes |
| C1b (RRF, vote (the paper's)) | test | val-tuned F0.5 | 0.305 (0.249–0.354) | 0.286 (0.235–0.333) | 0.417 (0.333–0.500) | 0.249 (0.231–0.265) | 0.251 (0.232–0.273) | 0.264 (0.228–0.316) | flags 175 of 600; of every 10 it flags, about 3 succeed; finds 42% of the successes |
| C1b (RRF, vote (the paper's)) | test | TRL native (train out-of-fold) | 0.295 (0.235–0.353) | 0.284 (0.228–0.343) | 0.350 (0.267–0.433) | 0.249 (0.231–0.265) | 0.251 (0.232–0.273) | 0.264 (0.228–0.316) | flags 148 of 600; of every 10 it flags, about 3 succeed; finds 35% of the successes |
| CTRL (XGBoost on TRL's answers) | val | val-tuned F0.5 | 0.457 | 0.594 | 0.237 | 0.141 | 0.035 | 0.423 | flags 32 of 400; of every 10 it flags, about 6 succeed; finds 24% of the successes |
| CTRL (XGBoost on TRL's answers) | test | val-tuned F0.5 | 0.305 (0.205–0.399) | 0.375 (0.261–0.492) | 0.175 (0.108–0.250) | 0.154 (0.145–0.162) | 0.040 (0.024–0.075) | 0.317 (0.269–0.393) | flags 56 of 600; of every 10 it flags, about 4 succeed; finds 18% of the successes |
| C2 (base Kev on TRL's answers) | val | val-tuned F0.5 | 0.340 | 0.304 | 0.650 | 0.214 | 0.247 | 0.330 | flags 171 of 400; of every 10 it flags, about 3 succeed; finds 65% of the successes |
| C2 (base Kev on TRL's answers) | test | val-tuned F0.5 | 0.277 (0.242–0.312) | 0.244 (0.213–0.276) | 0.608 (0.517–0.692) | 0.230 (0.220–0.239) | 0.262 (0.251–0.271) | 0.268 (0.230–0.332) | flags 299 of 600; of every 10 it flags, about 2 succeed; finds 61% of the successes |
| EXTRA (base Kev on the founder text) | val | val-tuned F0.5 | 0.400 | 0.400 | 0.400 | 0.383 | 0.454 | 0.323 | flags 80 of 400; of every 10 it flags, about 4 succeed; finds 40% of the successes |
| EXTRA (base Kev on the founder text) | test | val-tuned F0.5 | 0.319 (0.246–0.394) | 0.322 (0.250–0.398) | 0.308 (0.225–0.400) | 0.408 (0.387–0.429) | 0.465 (0.446–0.483) | 0.259 (0.225–0.318) | flags 115 of 600; of every 10 it flags, about 3 succeed; finds 31% of the successes |
| C3 (fine-tuned Kev on TRL's answers) | val | val-tuned F0.5 | 0.426 | 0.593 | 0.200 | 0.146 | 0.024 | 0.403 | flags 27 of 400; of every 10 it flags, about 6 succeed; finds 20% of the successes |
| C3 (fine-tuned Kev on TRL's answers) | test | val-tuned F0.5 | 0.227 (0.121–0.332) | 0.333 (0.186–0.487) | 0.100 (0.050–0.158) | 0.156 (0.151–0.160) | 0.012 (0.008–0.045) | 0.285 (0.242–0.352) | flags 36 of 600; of every 10 it flags, about 3 succeed; finds 10% of the successes |
| C4 (fine-tuned Kev on the founder text) | val | val-tuned F0.5 | 0.428 | 0.472 | 0.312 | 0.146 | 0.025 | 0.404 | flags 53 of 400; of every 10 it flags, about 5 succeed; finds 31% of the successes |
| C4 (fine-tuned Kev on the founder text) | test | val-tuned F0.5 | 0.282 (0.191–0.368) | 0.333 (0.226–0.435) | 0.175 (0.108–0.242) | 0.155 (0.150–0.160) | 0.021 (0.014–0.051) | 0.285 (0.241–0.349) | flags 63 of 600; of every 10 it flags, about 3 succeed; finds 18% of the successes |

Test values carry stratified bootstrap 95% CIs (1000 resamples), with the threshold fixed from val.
