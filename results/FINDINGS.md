# Findings

Plain-English findings, one short section per question, each with its key number (with a 95%
confidence interval) and a plot. Terms are in [GLOSSARY.md](GLOSSARY.md); condition names
(C1a … EXTRA) in [README.md](README.md#what-we-compared).

**Status:** no findings yet. The questions below are the ones the experiments will answer.
Each section gets filled in from the final test evaluation (stage `d1-final`), answer first.

## 1. Can a decision model replace TRL's final step?

Does Kev reading the answers as text (C2 as released, C3 fine-tuned) predict success better
than TRL's elastic net (C1a) and the paper's vote (C1b)?

*Pending.* Key number: F0.5 on test for C3 vs C1a, with CIs.
Plot: `summary/d1-final/plots/reliability_c3_vs_c1a_test.png`.

## 2. Is it Kev, or just handling combinations of answers?

If C3 beats C1a, does it also beat XGBoost (CTRL), which also combines answers non-linearly
but knows nothing about language?

*Pending.* Key number: F0.5 for C3 vs CTRL.

## 3. Does fine-tuning make Kev's probabilities trustworthy?

Does Kev's calibration improve from released (C2) to fine-tuned and temperature-fitted (C3)?
This is what lets the app's risk setting be trusted.

*Pending.* Key number: ECE for C2 vs C3. Plot: reliability diagram of C2, C3 and C1a.

## 4. Does Kev need TRL's questions at all?

Does Kev reading the founder profile directly (C4, and EXTRA as released) do as well as Kev
reading TRL's answers (C3)? If so, the questions mostly help explain, not predict.

*Pending.* Key number: F0.5 and ECE for C3 vs C4.

## 5. Is the dataset fair enough to learn from?

The sanity check: if even the simple baselines score above about 0.8 F0.5, the generated data
gives the answer away, and the comparison would be meaningless.

*Pending (B4).* Key number: F0.5 of C1a and CTRL.

## 6. What does each model pay attention to? (after the app works)

Flipping one answer at a time shows which questions move Kev's prediction most, compared with
the elastic net's weights and XGBoost's importances.

*Pending (Phase 3).*
