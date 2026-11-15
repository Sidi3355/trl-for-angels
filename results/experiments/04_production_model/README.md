# 04 · The app's model and its risk table

## Question

How likely is a founder to reach each outcome band, and how soon? And at each risk setting,
what share of the founders the app advances actually get there?

## What we did

Kev was fine-tuned once more with the input chosen on val in folder 03 (C3's: TRL's 40 answers
as text). This time it answers two questions instead of one: which outcome band the company
reaches (shut down / under $50M / $50M-$500M / $500M-$1B / over $1B), and how many years that
takes (under 5 / 5-8 / over 8). Each question got its own temperature, fitted on val.
`research/thresholds.py` builds the table behind the app's controls from the model's val
predictions. For each target ($50M, $500M, $1B) and timeline (any, 5 or 8 years) it gives, at
every threshold, the share of advanced founders who got there (precision) and the share of
those who got there who were advanced (recall). Everything here uses the 400 val founders;
test is never used for the app.

## Result

**The distributions are calibrated on average.** Across the 400 val founders the model's mean
probability for each band is within 2 points of the real share. Shut down is predicted at
52% against an actual 50%; $500M-$1B at 11% against 10%; over $1B at 9% against 10%. Each years
band is within 1 point. The plot `d3-val/plots/band_shares_val.png` shows this.

**As a success score it matches C3.** Adding the two top bands gives P($500M or more), the
research target. On val its PR-AUC is 0.357 (CI 0.293–0.454) against C3's 0.403, and its ECE is
0.040 (CI 0.014–0.075) against 0.024. Neither paired difference excludes zero: PR-AUC −0.047
(CI −0.114 to +0.026), ECE +0.016 (CI −0.028 to +0.033). The two scores correlate at 0.94.
It is timid like C3: no val founder gets more than 0.37. At its F0.5-best threshold (0.27) it
flags 92 of 400 founders, and about 4 in 10 of them reached $500M (against 2 in 10 at random).

**The risk settings** (`d4-final/thresholds.md`; target $500M, any timeline; 20% of val
founders got there):

| Setting | Advance at | Advanced | Of those, reached $500M | Of all who did, advanced | Turned away by "pass" |
|---|---|---|---|---|---|
| Conservative | 0.26 | 28% | 35% | 50% | 1% |
| Balanced | 0.23 | 40% | 32% | 65% | 8% |
| Aggressive | 0.15 | 64% | 28% | 89% | 11% |

In plain words, at *balanced* about 3 in 10 advanced founders reached $500M, against 2 in 10
at random. For $1B (any timeline), *conservative* advances 7% of founders, and about 2 in 10 of
them got there (against 1 in 10 at random). **$1B within 5 years has no val founders**, so the
table has nothing to say for it, and the app should show "not enough data".

**Training** (Kaggle T4, fp32; Kev's own val evaluation, 400 founders × 2 questions): mean
log-loss went from 2.010 (released Kev, never trained on these questions) to 1.172 after epoch
1 and 1.163 after epoch 2 (chosen), then 1.161 once calibrated. Temperatures: outcome 1.149,
years 0.871 (below 1, so the years answers are sharpened). Val ECE fell from 0.027 to 0.021.
The two epochs took 87 minutes each. The model is on Hugging Face:
[Sidi3355/trl-for-angels-kev-prod](https://huggingface.co/Sidi3355/trl-for-angels-kev-prod).

## What it means

- **For the app:** the probabilities the investor sees are honest on average, and the
  precision and recall shown for each risk setting are measured, not assumed. The app's
  controls read `app/thresholds.json`, and its three files are in `shared/artifacts/`. The most
  likely band is "shut down" for every founder, because half of all founders shut down, so the
  app should show each target's probability, never a single "predicted outcome".
- **For the research:** asking for five bands and a timeline costs nothing measurable against
  C3's one yes/no question, so a decision model can give investors the richer distribution
  for free.
- **A lesson for TRL:** a decision model has to be asked exactly as it was trained. The Kaggle
  run first asked through TRL, which always sent a choice question's options *without* their
  descriptions. Asked that way, the same model put 35% on "shut down" instead of 52% (orange
  bars in `band_shares_val.png`). The TRL fork now sends descriptions (`ChoiceQuestion(...,
  descriptions=...)`, commit `d9d1380`), and val was rescored with them (`DECISIONS.md`, D3).

## Caveats

- One set of 400 val founders chose the checkpoint, fitted the temperatures, set the
  thresholds and measured them, so these numbers are somewhat optimistic. Test is kept for the
  research conditions only.
- Rare targets rest on few founders: 40 reached $1B, 28 reached $1B within 8 years, and none
  within 5 years. Their rows in the table are rough.
- Timeline probabilities multiply the outcome and years answers as if they were independent,
  so they're estimates, labelled as such in the app.
- Val was rescored on CPU in the development container (fp32), not on the T4. On the same
  inputs the two agree to 0.0001.
- Not a research result: research comparisons come from folders 01–03 only.

## Files

| File | What it is |
|---|---|
| `d3-val/metrics.csv` | P($500M or more) against C3 on val, every metric with bootstrap CIs (`metrics_dictionary.md` explains the columns) |
| `d3-val/paired.csv` | the production model minus C3, on the same founders, with paired CIs |
| `d3-val/band_shares.csv` | each band's mean predicted share, asked as trained and without descriptions, against the real share |
| `d3-val/predictions.csv` | every val founder's calibrated outcome and years distributions, and P($500M or more) |
| `d3-val/reliability_table.csv` | the bins behind the reliability plot |
| `d3-val/config.json` | the model, its Hugging Face commit, the temperatures and how it was scored |
| `d4-final/thresholds.md` | the risk presets per target and timeline, in plain English |
| `d4-final/thresholds.json` | the full table (the same content as `app/thresholds.json`) |
| `d4-final/band_check.json` | average predicted share of each band against the real share on val |

**Plots in `d3-val/plots/` (val):**
- `band_shares_val.png`: each band's real share (grey) against the model's mean prediction,
  asked as trained (blue) and with the options sent without their descriptions (orange). Blue
  sits on grey; orange underweights "shut down" by 15 points.
- `reliability_prod_vs_c3_val.png`: the production model's P($500M or more) against C3's
  P(success). Both stay below 0.4 and close to the diagonal; the production model is a little
  too high below 0.15 (none of its 9 founders under 0.10 succeeded).
