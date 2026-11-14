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

*Final result pending* (F0.5 on test with its 95% CI, at D1).

**Provisional, val only** (`b3-provisional/`): CTRL 0.457 F0.5, C1a 0.446, C1a-40 0.426,
C1b 0.377. In plain words, C1a flags 36 of the 400 val founders and about 6 in every 10 it flags
really succeed, against 2 in 10 for a founder picked at random. All are far below 0.8, so the
data isn't too easy (sanity check B4 passed).

## What it means

*Pending.* For the research: the bar Kev must clear; C1a-40 against C1a, what limiting Kev
to 40 questions costs; and CTRL against C1a-40, how much is gained just by handling
combinations of answers. For the app: whether the questions carry
signal at all. Also the sanity check (B4): above about 0.8 F0.5 means the data is too easy.

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

**Plots in `b3-provisional/plots/` (val):**
- `reliability_c1a_vs_c1b_vs_ctrl_val.png`: C1a and CTRL follow the diagonal (calibrated).
  The vote (C1b) sits well below it: its score is the share of its questions answered yes,
  not a probability, so when it scores 0.9 only about 4 in 10 of those founders succeed.
- `reliability_c1a40_vs_ctrl_vs_c2_val.png`: the three learn stages that read the same 40
  questions; C1a-40 and CTRL track the diagonal, base Kev (C2) sits below it (overconfident).
- `reliability_c1a_vs_c2_val.png`: TRL's default against base Kev.
- `reliability_c1a_val.png`: C1a alone (the plot meant for C3 against C1a, before C3 exists).
