# The ceiling: the synthetic rule's own score (d1-final, test)

Synthetic test founders only (587, of whom 115 succeeded); the real-grounded rows have no background score. *Oracle* ranks founders by the noise-free background score that, plus noise, decided their outcome, so it is close to the best any model could do from the profile. F0.5 uses a threshold tuned on val; PR-AUC has a stratified bootstrap 95% CI (1000 resamples). Written by `research/oracle.py`.

| Condition | F0.5 | Precision | Recall | PR-AUC (95% CI) |
|---|---|---|---|---|
| oracle | 0.361 | 0.345 | 0.443 | 0.328 (0.282–0.392) |
| C1a | 0.327 | 0.313 | 0.400 | 0.304 (0.255–0.376) |
| C1a-40 | 0.295 | 0.299 | 0.278 | 0.278 (0.237–0.342) |
| C1b | 0.294 | 0.275 | 0.409 | 0.251 (0.218–0.300) |
| CTRL | 0.299 | 0.364 | 0.174 | 0.305 (0.257–0.381) |
| C2 | 0.265 | 0.233 | 0.591 | 0.261 (0.222–0.324) |
| EXTRA | 0.317 | 0.319 | 0.313 | 0.253 (0.219–0.307) |
| C3 | 0.232 | 0.333 | 0.104 | 0.277 (0.236–0.343) |
| C4 | 0.275 | 0.323 | 0.174 | 0.275 (0.233–0.334) |
