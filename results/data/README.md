# Dataset

**In short:** 3,000 anonymised founder profiles in `data/raw/full.jsonl`, each labelled with the
company's outcome band and years to outcome. 50 are based on real founders and companies; 2,950
are made up, modelled on those 50. Because most of the data is synthetic, results describe this
dataset only, not real-world accuracy (VCBench is the future real test).

## How it was made

| Rows | What | How |
|---|---|---|
| 1–50 | Real-grounded | `data/raw/sample50.jsonl`: each row based on a real company and founder (step A2). Sources, for review only: `data/raw/sample50_sources.md`. |
| 51–3,000 | Synthetic | `research/generate_dataset.py` (seed 42, reproducible byte for byte). |

The generator follows the section 10 prompt: the same template and allowed values, the same
consistency rules (experience matches job durations, exits match prior startups, degrees fit
roles, industry experience matches the jobs), and the same variety and anonymisation rules. It
builds each founder's career from pools of roles and generic employers, by background
(technical, business, mixed, domain specialist) and the startup's industry (about 80 industries).

**How outcomes are assigned (synthetic rows).** Each profile gets a *background score* from its
fields: industry experience, prior exits, team size, education, experience, the industry, and a
few interactions (for example a domain specialist with deep experience in health or finance).
Random noise is added, and within each batch of 50 the noisy score is ranked and cut into exact
counts: 25 shut down, 8 or 7 under $50M, 7 or 8 $50M-$500M, 5 $500M-$1B and 5 over $1B. Years
are drawn per outcome band (for example, over $1B is mostly 5-8 or over 8 years). So outcomes
depend on the profile, but only weakly, as with real founders.

## Key numbers

| Measure | Value | Plain reading |
|---|---|---|
| Rows, outcome bands | 1,500 / 450 / 450 / 300 / 300 | exactly 50 / 15 / 15 / 10 / 10%; every batch of 50 has the same mix |
| Research "yes" ($500M and above) | 600 (20%) | 1 in 5 founders |
| How predictable the label is (5-fold, profile fields only) | AUC 0.69 (logistic), 0.67 (boosted trees); best F0.5 0.36 | a simple model does better than chance but is often wrong; far below the plan's "too easy" line of 0.8 F0.5 |
| Best single field | AUC 0.59 | no single field gives the answer away |
| "Surprising" synthetic rows | 20% | background score rank at least 40 points away from the outcome's rank (16% of shut-downs have a top-30% background; 14% of $500M+ outcomes have a bottom-40% background). The prompt asked for about 30%; more noise would raise this but weaken the signal the research needs to compare learn stages |
| Rows with an unknown field | 478 (16%) | spread across all bands |
| Industries | 113 distinct labels; at least 15 in every batch of 50 | |

Full validator report: `results/data/validation_full.md` (`research/validate.py --profile full`).

## Limits

- Synthetic rows are plausible, not real: their outcomes come from the scoring rule above, so a
  model can only learn that rule (plus noise), not real founder dynamics.
- The real-grounded 50 were written differently from the synthetic 2,950, so they may look
  slightly different to a model.
- Kev-0.6B (the answerer) reads these profiles; its answers carry their own noise on top.
