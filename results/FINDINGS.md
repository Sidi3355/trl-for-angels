# Findings

Plain-English findings, one short section per question, each with its key number (with a 95%
confidence interval) and a plot. Terms are in [GLOSSARY.md](GLOSSARY.md); condition names
(C1a … EXTRA) in [README.md](README.md#what-we-compared).

**Status:** findings 1–5 are final, from the one test evaluation (stage `d1-final`, 600
founders, 120 of whom succeeded). Every comparison below is **paired**: both conditions scored
on the same founders, and the CI is for the difference itself
([summary/d1-final/paired.md](summary/d1-final/paired.md)). Thresholds were tuned on val and
applied unchanged to test. Results hold for this generated dataset, with Kev-0.6B as the
answerer.

## 1. Can a decision model replace TRL's final step?

**It can replace it, but it isn't better.** Fine-tuned Kev reading TRL's answers (C3) scored
**0.227 F0.5** on test (CI 0.121–0.332) against **0.319** for TRL's default elastic net (C1a, CI
0.221–0.417). The difference, −0.092 (CI −0.206 to +0.012), isn't distinguishable from zero,
in either direction. Released Kev (C2) scored 0.277 (difference −0.042, CI −0.127 to +0.046),
and the paper's vote (C1b) 0.305 (−0.015, CI −0.099 to +0.081). Threshold-free ranking (PR-AUC)
says the same: C3 0.285, C1a 0.319, difference −0.034 (CI −0.085 to +0.017).

In plain words: of every 10 founders C1a flags, about 4 succeed; of every 10 C3 flags, about 3.
A founder picked at random succeeds 2 times in 10.

- Plot: `summary/d1-final/plots/reliability_c3_vs_c1a_test.png`.
- Caveat: C3's low F0.5 is mostly its threshold (finding 3); its ranking is closer to C1a's.

## 2. Is it Kev, or just handling combinations of answers?

**Neither adds anything on this data.** XGBoost (CTRL) reads the same 40 answers and can
use any combination of them; it matched the elastic net almost exactly (F0.5 0.305 vs 0.319,
difference −0.014, CI −0.096 to +0.071; PR-AUC 0.317 vs 0.319). Fine-tuned Kev against XGBoost
is −0.078 F0.5 (CI −0.200 to +0.034), and against the elastic net on the same 40 questions
(C1a-40) −0.078 (CI −0.184 to +0.019). So the answers' signal here is essentially additive: a
weighted sum captures it, and neither trees nor a language model finds more.

- Plot: `summary/d1-final/plots/reliability_c1a40_vs_ctrl_vs_c2_vs_c3_test.png`.

## 3. Does fine-tuning make Kev's probabilities trustworthy?

**Yes, by a wide margin, and it's the clearest result of the project.** Calibration error
(ECE) fell from **0.262 to 0.012** when Kev reads TRL's answers (C2 → C3; difference −0.249, CI
−0.258 to −0.215) and from **0.465 to 0.021** when it reads the profile (EXTRA → C4; −0.444, CI
−0.462 to −0.407). C3's 0.012 is the lowest of any condition (the elastic net's is 0.045;
difference −0.033, CI −0.059 to +0.003). In plain words: when released Kev reading the profile says a
founder has over a 90% chance, about 3 in 10 such founders succeed; when fine-tuned Kev says 30%, about 3 in 10 do.

**But the probabilities are timid.** On test, C3 never gives a founder more than 0.39, and C4
never more than 0.46, while the elastic net reaches 0.75. Kev has learned the base rate and a
modest shift around it. Few founders clear a precision-favouring threshold, so C3 finds only
10% of the successes, against 19% for C1a, and that is what costs it F0.5. For an app, a
calibrated but narrow score is safe to act on but separates founders less.

- Plots: `summary/d1-final/plots/reliability_c1a_vs_c2_vs_c3_vs_c4_test.png` and
  `reliability_c2_vs_extra_vs_c3_vs_c4_test.png`.
- Caveat: two epochs on a 0.6B model on a free GPU; a longer or larger fine-tune might widen
  the range. Not tried.

## 4. Does Kev need TRL's questions at all?

**Not for prediction, on this data.** Kev fine-tuned on the founder profile itself (C4, no
think or reason steps) matched Kev fine-tuned on TRL's answers (C3): F0.5 0.282 vs 0.227
(C3 − C4 −0.055, CI −0.169 to +0.052), identical PR-AUC (0.285 each), the same Brier (0.155 vs
0.156) and similar ECE (0.021 vs 0.012). On val the two were tied (0.428 vs 0.426), so the app
uses C3's input, chosen before test was read, because the questions explain each verdict
(`DECISIONS.md`, D2). Released Kev on the profile (EXTRA, 0.319) also matched C1a on F0.5 but is
badly overconfident (ECE 0.465).

So on this dataset the questions mostly help **explain** (which question drove a verdict), not
**predict**. Caveat: the profiles are short and templated (about 170 tokens), which suits
reading them directly; longer, messier real profiles might favour the questions.

- Plot: `summary/d1-final/plots/reliability_c2_vs_extra_vs_c3_vs_c4_test.png`.

## 5. Is the dataset fair enough to learn from?

**Yes: the data is hard enough to be a fair test.** The best score on test is 0.319 F0.5 (C1a
and EXTRA), far below the 0.8 line that would mean the generated data gives the answer away
(sanity check B4; on val, the best was XGBoost's 0.457). The questions carry real but modest
signal (C1a's PR-AUC 0.319 against 0.20 for random ranking), and most of the outcome is noise,
as with real founders.

Every condition scored lower on test than on val (C1a 0.446 → 0.319), C1a with TRL's own
threshold too (0.432 → 0.312), which isn't tuned on val. Because they all dropped, the val
founders were most likely easier than the test founders by chance (80 and 120 successes), not
over-tuned.

- Plot: `summary/d1-final/plots/reliability_c1a_vs_c1b_vs_ctrl_test.png`.

## Also measured

- **The paper's vote isn't a probability.** C1b ranks about as well as the elastic net on F0.5
  (0.305 vs 0.319) but is far worse calibrated (ECE 0.251 vs 0.045; difference +0.206, CI
  +0.170 to +0.233) and ranks worse (PR-AUC −0.055, CI −0.115 to −0.005): when it scores 0.9,
  about 4 in 10 succeed.
- **Keeping 40 of 93 questions costs the elastic net a little ranking** (PR-AUC −0.033, CI
  −0.071 to −0.000) but no F0.5 (−0.014, CI −0.079 to +0.057).

- **A decision model must be asked exactly as it was trained.** The app's model (five outcome
  bands and three timelines, trained with a one-line description of each option) put 35% on
  "shut down" on average when the options were sent without their descriptions, and 52% (the
  real share is 50%) when sent with them; single founders moved by up to 0.18. TRL used to send
  no descriptions; our fork now does. Plot:
  `experiments/04_production_model/d3-val/plots/band_shares_val.png`.
- **Asking for the whole distribution costs nothing measurable.** The app's model, read as
  P($500M or more), ranks val founders about as well as C3's single yes/no answer (PR-AUC 0.357
  vs 0.403, paired difference CI −0.114 to +0.026), and its band shares match the real ones
  within 2 points (val only; folder 04).

## 6. What does each model pay attention to? (after the app works)

Flipping one answer at a time shows which questions move Kev's prediction most, compared with
the elastic net's weights and XGBoost's importances.

*Pending (Phase 3).*
