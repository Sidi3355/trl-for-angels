# 01 · Baselines: C1a, C1a-40, C1b and CTRL

## Question

How well do TRL's own learn stages, and a standard machine-learning control, predict founder
success from TRL's answers? These are the scores Kev has to beat.

## What we did

Claude wrote yes/no questions about the training founders, and base Kev-0.6B answered every
question for every founder, through TRL's real pipeline (`research/fit_rrf.py`,
`research/answers.py`). The answers were then combined four ways: TRL's default weighted sum
over every question (**C1a**, elastic net); the same weighted sum over only the 40 best
questions, the ones Kev reads (**C1a-40**); the RRF paper's vote (**C1b**); and XGBoost on those
same 40 (**CTRL**, tuned on val, `research/baselines.py`). All four start from exactly the same
questions and answers. Each
threshold was tuned on val for F0.5; for C1a and C1b, TRL's own built-in threshold is
reported too.

## Result

**Final, test** (`d1-final/`; 95% CIs from 1,000 stratified bootstrap resamples; threshold
tuned on val):

| | F0.5 | Precision | Recall | ECE | Brier | PR-AUC |
|---|---|---|---|---|---|---|
| C1a (TRL default, elastic net, all 93 questions) | **0.319** (0.221–0.417) | 0.383 | 0.192 | 0.045 | 0.153 | **0.319** |
| C1a with TRL's own threshold (as shipped) | 0.312 (0.218–0.404) | 0.379 | 0.183 | 0.045 | 0.153 | 0.319 |
| C1a-40 (elastic net, the 40 Kev reads) | 0.306 (0.236–0.378) | 0.312 | 0.283 | 0.035 | 0.156 | 0.286 |
| C1b (the paper's vote) | 0.305 (0.249–0.354) | 0.286 | 0.417 | 0.251 | 0.249 | 0.264 |
| CTRL (XGBoost, the same 40) | 0.305 (0.205–0.399) | 0.375 | 0.175 | 0.040 | 0.154 | 0.317 |

In plain words: C1a flags 60 of the 600 test founders, and about 4 in every 10 it flags really
succeed, against 2 in 10 for a founder picked at random; it finds about 1 in 5 of the founders
who succeeded. All are far below 0.8, so the data isn't too easy (sanity check B4).

**Paired comparisons on test** (`results/summary/d1-final/paired.md`): none of the four
differs from C1a on F0.5 (every CI includes zero). The vote (C1b) is far worse calibrated than
the elastic net (ECE +0.206, CI +0.170 to +0.233) and ranks worse (PR-AUC −0.055, CI −0.115 to
−0.005). XGBoost (CTRL) matches the elastic net on every metric. Keeping only 40 questions
costs the elastic net a little ranking (PR-AUC −0.033, CI −0.071 to −0.000) but no F0.5.

**Val** (`b3-provisional/`, `d2-val/`): CTRL 0.457 F0.5, C1a 0.446, C1a-40 0.426, C1b 0.377.
Every condition scored lower on test than on val (C1a 0.446 → 0.319), C1a with TRL's own
threshold too (0.432 → 0.312), which isn't tuned on val at all. Because every condition
dropped, the val founders were most likely easier than the test founders by chance (only 80
and 120 successes), not over-tuned.

## What it means

- **For the research:** TRL's default elastic net is the bar, and nothing in this project
  clears it on F0.5. Handling combinations of answers (XGBoost) adds nothing measurable over
  a weighted sum, so the answers' signal is mostly additive. The paper's vote ranks about as
  well but its score isn't a probability (ECE 0.25), which matters for any product that acts
  on the number.
- **For the app:** the questions do carry signal (precision about 2× the base rate, PR-AUC
  0.32 against 0.20 at random), modest on this data.

## Caveats

- Generated data, and Kev-0.6B as the answerer (Jev wasn't free), so the answers are noisier
  than with a bigger answerer.
- TRL's built-in threshold is tuned on train, so it can be optimistic; the main comparison
  uses the val-tuned threshold for every condition.

## Files

Written by `research/evaluate.py` into a folder per stage (`<stage>/`):

| File | What it is |
|---|---|
| `metrics.csv` | every metric per condition and threshold rule (columns: `metrics_dictionary.md`) |
| `predictions.csv` | one row per founder: id, true label, P(success), the decision |
| `config.json` | the threshold rule, bootstrap size, seed and bins |
| `metrics_dictionary.md` | what each column means |

| `plots/` | reliability plots with at least one of this folder's conditions (copies of `results/summary/<stage>/plots/`) |

**Plots in `d1-final/plots/` (test):**
- `reliability_c1a_vs_c1b_vs_ctrl_test.png`: C1a and CTRL track the diagonal up to about 0.4;
  above that, bins hold only a few founders and wobble (CTRL's top bin has fewer than 5). The
  vote (C1b) sits below the diagonal everywhere: when it scores 0.9, about 4 in 10 succeed.
- `reliability_c3_vs_c1a_test.png`, `reliability_c1a_vs_c2_vs_c3_vs_c4_test.png`,
  `reliability_c1a40_vs_ctrl_vs_c2_vs_c3_test.png`: the baselines against Kev (captions in
  folder 03's README).

**Plots in `b3-provisional/plots/` (val):**
- `reliability_c1a_vs_c1b_vs_ctrl_val.png`: C1a and CTRL follow the diagonal (calibrated).
  The vote (C1b) sits well below it: its score is the share of its questions answered yes,
  not a probability, so when it scores 0.9 only about 4 in 10 of those founders succeed.
- `reliability_c1a40_vs_ctrl_vs_c2_val.png`: the three learn stages that read the same 40
  questions; C1a-40 and CTRL track the diagonal, base Kev (C2) sits below it (overconfident).
- `reliability_c1a_vs_c2_val.png`: TRL's default against base Kev.
- `reliability_c1a_val.png`: C1a alone (the plot meant for C3 against C1a, before C3 exists).
