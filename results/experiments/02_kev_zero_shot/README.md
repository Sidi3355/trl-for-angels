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

**Final, test** (`d1-final/`; 95% CIs from 1,000 stratified bootstrap resamples; threshold
tuned on val):

| | F0.5 | Precision | Recall | ECE | Brier | PR-AUC |
|---|---|---|---|---|---|---|
| C2 (released Kev on TRL's 40 answers) | 0.277 (0.242–0.312) | 0.244 | 0.608 | 0.262 (0.251–0.271) | 0.230 | 0.268 |
| EXTRA (released Kev on the founder text) | 0.319 (0.246–0.394) | 0.322 | 0.308 | 0.465 (0.446–0.483) | 0.408 | 0.259 |
| C1a (TRL's default, for reference) | 0.319 (0.221–0.417) | 0.383 | 0.192 | 0.045 (0.027–0.076) | 0.153 | 0.319 |

In plain words: released Kev ranks founders a little (PR-AUC about 0.26 against 0.20 at
random), and its F0.5 isn't distinguishable from TRL's default (C2 − C1a −0.042, CI −0.127 to
+0.046). But its probabilities are far too high. Reading the profile (EXTRA), its median
founder gets 0.73 when 1 in 5 succeed, and when it says over 0.9, about 3 in 10 succeed. C2's
ECE is worse than C1a's by 0.216 (CI +0.182 to +0.237; `results/summary/d1-final/paired.md`).

**Val** (`b3-provisional/`, `d2-val/`): C2 0.340 F0.5, ECE 0.247; EXTRA 0.400, ECE 0.454.

## What it means

The starting point for fine-tuning (folder 03): released Kev-0.6B knows a little about this
task but isn't calibrated for it, as expected for a model shipped at temperature 1.0 and never
trained on this question. Fine-tuning brings ECE down to 0.012 (C3) and 0.021 (C4). Its
probabilities couldn't drive an app's actions as released.

## Caveats

- Kev-0.6B is a small model, and as released it isn't calibrated for this question
  (temperature 1.0), so its raw probabilities may be over- or under-confident.
- The same Kev also answers the questions, so in C2 one model both answers and decides.

## Files

Same layout as folder 01: `<stage>/metrics.csv`, `predictions.csv`, `config.json`,
`metrics_dictionary.md`, and `plots/` (reliability plots with C2 or EXTRA).

**Plots in `d1-final/plots/` (test):**
- `reliability_c2_vs_extra_vs_c3_vs_c4_test.png`: the Kev family. C2 and EXTRA sit well below
  the diagonal at every level (overconfident); fine-tuned C3 and C4 sit on it.
- `reliability_c1a_vs_c2_vs_c3_vs_c4_test.png`, `reliability_c1a40_vs_ctrl_vs_c2_vs_c3_test.png`:
  released Kev against TRL's learn stages (captions in folder 03's README).

**Plots in `b3-provisional/plots/` (val):**
- `reliability_c1a40_vs_ctrl_vs_c2_val.png`: base Kev (C2) against the two learn stages that
  read the same 40 answers; C2 sits below the diagonal at every level (overconfident).
- `reliability_c1a_vs_c2_val.png`: base Kev against TRL's default.
