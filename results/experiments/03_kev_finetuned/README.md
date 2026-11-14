# 03 · Kev fine-tuned: C3 and C4

## Question

Does Kev-0.6B predict founder success better, and with more trustworthy probabilities, once
it's trained on the training founders: reading TRL's answers (**C3**) or the founder profile
(**C4**)?

## What we did

Kev was fine-tuned from the released checkpoint with Kev's own recipe on the 2,000 training
founders (`research/train_kev.py`, on a free Kaggle T4): one epoch, then a second from it. The
checkpoint with the lowest val log-loss (released, epoch 1 or epoch 2) was kept, and its
temperature was fitted on val so its probabilities are calibrated. **C3** reads the same
answer text as C2, through the same TRL learn stage; **C4** reads the profile, as EXTRA does.
Thresholds are tuned on val for F0.5, then applied once to the 600 test founders.

## Result

**Final, test** (`d1-final/`; 95% CIs from 1,000 stratified bootstrap resamples):

| | F0.5 | Precision | Recall | ECE | Brier | PR-AUC |
|---|---|---|---|---|---|---|
| C3 (fine-tuned Kev on TRL's answers) | 0.227 (0.121–0.332) | 0.333 | 0.100 | **0.012** (0.008–0.045) | 0.156 | 0.285 |
| C4 (fine-tuned Kev on the founder text) | 0.282 (0.191–0.368) | 0.333 | 0.175 | 0.021 (0.014–0.051) | 0.155 | 0.285 |
| C1a (TRL's default, for reference) | 0.319 (0.221–0.417) | 0.383 | 0.192 | 0.045 (0.027–0.076) | 0.153 | 0.319 |

In plain words: C3 flags 36 of the 600 test founders and about 3 in every 10 it flags
succeed (against 2 in 10 at random), but it finds only 1 in 10 of the founders who succeeded.
Its probabilities, though, mean what they say: ECE 0.012 is the best of any condition.

**Training (val; from the Kaggle run's reports):** both chose epoch 2. Val log-loss went from
0.618 (released Kev) to 0.455 for C3, and from 1.086 to 0.470 for C4 (a constant 20% guess
scores 0.500). Temperatures 1.072 (C3) and 1.275 (C4). Full numbers:
`results/DECISIONS.md` (C1-train, C2-temp).

**Paired comparisons on test** (`results/summary/d1-final/paired.md`):

- **Fine-tuning fixes Kev's calibration, by a wide margin:** ECE 0.262 → 0.012 reading
  TRL's answers (C2 → C3; difference −0.249, CI −0.258 to −0.215) and 0.465 → 0.021 reading
  the profile (EXTRA → C4; −0.444, CI −0.462 to −0.407). Brier improves as much.
- **It doesn't make Kev more accurate than TRL's default:** C3 − C1a is −0.092 F0.5 (CI
  −0.206 to +0.012) and C4 − C1a is −0.037 (CI −0.133 to +0.060). Neither CI excludes zero,
  in either direction.
- **TRL's answers or the profile, as Kev's input:** no detectable difference. C3 − C4 is
  −0.055 F0.5 (CI −0.169 to +0.052), and PR-AUC is identical (0.285 each).

## What it means

- **For the research:** a fine-tuned decision model is a calibrated learn stage for TRL, as
  well calibrated as the elastic net or better, but on this data it doesn't rank founders any
  better. Its probabilities are *timid*: on test, C3 never says more than 0.39 and C4 never
  more than 0.46, while the elastic net goes up to 0.75. Kev has learned the base rate and a
  modest shift, so few founders clear a precision-favouring threshold, which is why its
  recall and F0.5 are low. Kev reading the profile directly (C4, no think or reason steps)
  does as well as Kev reading TRL's answers (C3).
- **For the app:** C3 and C4 tied on val, so D2 chose C3's input on val, before test was read
  (`results/DECISIONS.md`, D2). The test results don't change that choice: picking on test
  would make the test score meaningless. What carries over is the lesson about thresholds:
  C3's threshold, tuned on val's 80 successes, flagged founders with 0.59 precision on val but
  0.33 on test. The app's risk table (folder 04) shows precision and
  recall at every threshold, not a single cut-off.

## Caveats

- Generated data, and a small model (0.6B parameters) on a free GPU: two epochs at most,
  chosen on val; longer training or a larger Kev wasn't tried.
- Val has only 80 successful founders, so val-tuned thresholds are noisy: every condition
  scored 0.06–0.20 F0.5 lower on test than on val, C1a with TRL's own threshold too (0.432 →
  0.312), which isn't tuned on val at all.
- C3's threshold, if taken from TRL's fit, would be optimistic, because Kev was trained on
  the same founders; the comparison tunes every threshold on val instead.

## Files

Same layout as folder 01 (`<stage>/metrics.csv`, `predictions.csv`, `config.json`,
`metrics_dictionary.md`, `plots/`). Stages: `d2-val/` (val only, the D2 choice) and
`d1-final/` (val and test). Training reports are on the `kaggle-results` branch
(`runs/20261114-192753-c_kev/kev/c3_report.json`, `c4_report.json`), and the checkpoints are on
Hugging Face: [Sidi3355/trl-for-angels-kev-c3](https://huggingface.co/Sidi3355/trl-for-angels-kev-c3)
and [Sidi3355/trl-for-angels-kev-c4](https://huggingface.co/Sidi3355/trl-for-angels-kev-c4).

**Plots in `d1-final/plots/` (test):**
- `reliability_c3_vs_c1a_test.png`: C3 hugs the diagonal, but only between 0.05 and 0.40; the
  elastic net (C1a) spreads to 0.75 and falls below the diagonal at the top.
- `reliability_c1a_vs_c2_vs_c3_vs_c4_test.png`: TRL's default against Kev before (C2) and
  after (C3, C4) fine-tuning. C2 sits well below the diagonal (overconfident); C3 and C4 sit on it.
- `reliability_c2_vs_extra_vs_c3_vs_c4_test.png`: the Kev family. Both released-Kev conditions
  (C2, EXTRA) are overconfident, EXTRA most (it says over 0.9 for founders who succeed about
  3 times in 10); both fine-tuned ones are calibrated.
- `reliability_c1a40_vs_ctrl_vs_c2_vs_c3_test.png`: the four learn stages that read the same
  40 answers.
