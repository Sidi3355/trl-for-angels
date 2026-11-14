# 01 · Baselines: C1a, C1b and CTRL

## Question

How well do TRL's own learn stages, and a standard machine-learning control, predict founder
success from TRL's answers? These are the scores Kev has to beat.

## What we did

Claude wrote yes/no questions about the training founders, and base Kev-0.6B answered every
question for every founder, through TRL's real pipeline (`research/fit_rrf.py`,
`research/answers.py`). The answers were then combined three ways: TRL's default weighted sum
(**C1a**, elastic net), the RRF paper's vote (**C1b**), and XGBoost (**CTRL**, tuned on val,
`research/baselines.py`). All three use exactly the same questions and answers. Each
threshold was tuned on val for F0.5; for C1a and C1b, TRL's own built-in threshold is
reported too.

## Result

*Pending.* The headline will be F0.5 on test with its 95% CI, for example "out of every 10
founders C1a flags, about N succeed".

## What it means

*Pending.* For the research: the bar Kev must clear, and (CTRL against C1a) how much is
gained just by handling combinations of answers. For the app: whether the questions carry
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

Reliability plots are in `results/summary/<stage>/plots/`.
