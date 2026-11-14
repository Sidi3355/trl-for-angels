# 02 · Kev as released: C2 and EXTRA

## Question

Can Kev-0.6B, used as released with no training on this task, judge founder success: from
TRL's answers (**C2**), or from the founder profile alone (**EXTRA**)?

## What we did

**C2** is the new TRL learn stage (`combiner="decision"`, contributed to TRL): each founder's
answers are written as text, one line per question ("Has the founder founded a company
before? yes"), and Kev is asked "Will this founder's company succeed (exit, IPO or funding
over $500M)?". Its probability is the score. **EXTRA** asks Kev the same question about the
founder profile itself, exactly as TRL sends it to the answerer. Nothing is trained; the
threshold is tuned on val for F0.5.

## Result

*Pending.* F0.5 and ECE on test, with CIs.

## What it means

*Pending.* The starting point for fine-tuning (folder 03), and how much Kev knows about this
task before it's trained on it.

## Caveats

- Kev-0.6B is a small model, and as released it isn't calibrated for this question
  (temperature 1.0), so its raw probabilities may be over- or under-confident.
- The same Kev also answers the questions, so in C2 one model both answers and decides.

## Files

Same layout as folder 01: `<stage>/metrics.csv`, `predictions.csv`, `config.json`,
`metrics_dictionary.md`.
