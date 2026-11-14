# 02 · Kev as released: C2 and EXTRA

## Question

Can Kev-0.6B, used as released with no training on this task, judge founder success: from
TRL's answers (**C2**), or from the founder profile alone (**EXTRA**)?

## What we did

**C2** is the new TRL learn stage (`combiner="decision"`, contributed to TRL): each founder's
answers to the 40 best questions (TRL's `max_rules=40`, best F0.5 on train first) are written
as text, one line per question ("Has the founder founded a company before? yes"), and Kev is
asked "Will this founder's company succeed (exit, IPO or funding
over $500M)?". Its probability is the score. **EXTRA** asks Kev the same question about the
founder profile itself, exactly as TRL sends it to the answerer. Nothing is trained; the
threshold is tuned on val for F0.5.

## Result

*Final result pending* (F0.5 and ECE on test, with CIs, at D1).

**Provisional, val only, C2** (`b3-provisional/`): F0.5 **0.340**, ECE **0.247**, against
0.426 and 0.036 for C1a-40, which reads the same 40 answers. In plain words, base Kev flags 171
of the 400 val founders, and only about 3 in every 10 it flags succeed; when it says 60%, about
25% really succeed. It ranks founders somewhat (PR-AUC 0.33 against a 0.20 base rate) but is
badly overconfident. That's expected: the released Kev-0.6B ships uncalibrated (temperature
1.0) and was never trained on this question. EXTRA is scored in the `c_kev` run.

## What it means

*Pending.* The starting point for fine-tuning (folder 03), and how much Kev knows about this
task before it's trained on it.

## Caveats

- Kev-0.6B is a small model, and as released it isn't calibrated for this question
  (temperature 1.0), so its raw probabilities may be over- or under-confident.
- The same Kev also answers the questions, so in C2 one model both answers and decides.

## Files

Same layout as folder 01: `<stage>/metrics.csv`, `predictions.csv`, `config.json`,
`metrics_dictionary.md`, and `plots/` (reliability plots with C2 or EXTRA).

**Plots in `b3-provisional/plots/` (val):**
- `reliability_c1a40_vs_ctrl_vs_c2_val.png`: base Kev (C2) against the two learn stages that
  read the same 40 answers; C2 sits below the diagonal at every level (overconfident).
- `reliability_c1a_vs_c2_val.png`: base Kev against TRL's default.
