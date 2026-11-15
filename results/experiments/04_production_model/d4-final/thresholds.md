# Risk thresholds (d4-final)

Built from the production model's predictions for the 400 val founders. The app reads these numbers from `app/thresholds.json`; nothing here uses test.

**How to read a row:** with this preset, the app advances founders whose probability of reaching the target in time is at or above *advance at*, passes those below *pass below*, and escalates the rest. *Expected precision* is the share of advanced val founders who actually got there; *missed* is the share of those who got there that the pass rule would have turned away.

Timelines combine the outcome and years questions as if they were independent, so those probabilities are estimates.

| Target | Timeline | Base rate | Preset | Advance at | Pass below | Expected precision | Recall | Advanced | Missed | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| $50M | any | 35% | conservative | 0.42 | 0.19 | 51% | 46% | 32% | 4% |  |
| $50M | any | 35% | balanced | 0.22 | 0.21 | 41% | 88% | 76% | 9% |  |
| $50M | any | 35% | aggressive | 0.19 | 0.19 | 37% | 96% | 91% | 4% |  |
| $50M | 5 years | 8% | conservative | 0.15 | 0.10 | 10% | 64% | 55% | 0% |  |
| $50M | 5 years | 8% | balanced | 0.15 | 0.11 | 10% | 64% | 55% | 6% |  |
| $50M | 5 years | 8% | aggressive | 0.12 | 0.12 | 9% | 85% | 76% | 15% |  |
| $50M | 8 years | 26% | conservative | 0.29 | 0.16 | 36% | 66% | 49% | 2% |  |
| $50M | 8 years | 26% | balanced | 0.26 | 0.19 | 35% | 75% | 56% | 9% |  |
| $50M | 8 years | 26% | aggressive | 0.19 | 0.19 | 31% | 91% | 78% | 9% |  |
| $500M | any | 20% | conservative | 0.26 | 0.12 | 35% | 50% | 28% | 1% |  |
| $500M | any | 20% | balanced | 0.23 | 0.13 | 32% | 65% | 40% | 8% |  |
| $500M | any | 20% | aggressive | 0.15 | 0.15 | 28% | 89% | 64% | 11% |  |
| $500M | 5 years | 3% | conservative | 0.12 | 0.06 | 10% | 15% | 5% | 0% |  |
| $500M | 5 years | 3% | balanced | 0.09 | 0.09 | 6% | 92% | 53% | 8% |  |
| $500M | 5 years | 3% | aggressive | 0.09 | 0.09 | 6% | 92% | 53% | 8% |  |
| $500M | 8 years | 14% | conservative | 0.20 | 0.11 | 25% | 62% | 36% | 3% |  |
| $500M | 8 years | 14% | balanced | 0.19 | 0.13 | 25% | 69% | 41% | 9% |  |
| $500M | 8 years | 14% | aggressive | 0.14 | 0.14 | 21% | 88% | 60% | 12% |  |
| $1B | any | 10% | conservative | 0.16 | 0.05 | 22% | 15% | 7% | 0% |  |
| $1B | any | 10% | balanced | 0.14 | 0.07 | 23% | 40% | 17% | 10% |  |
| $1B | any | 10% | aggressive | 0.08 | 0.08 | 15% | 82% | 56% | 18% |  |
| $1B | 5 years | 0% | conservative | 1.00 | 0.00 | – | – | 0% | – | no founder (or every founder) reached this target on val; nothing advanced |
| $1B | 5 years | 0% | balanced | 1.00 | 0.00 | – | – | 0% | – | no founder (or every founder) reached this target on val; nothing advanced |
| $1B | 5 years | 0% | aggressive | 1.00 | 0.00 | – | – | 0% | – | no founder (or every founder) reached this target on val; nothing advanced |
| $1B | 8 years | 7% | conservative | 0.13 | 0.06 | 23% | 18% | 6% | 4% |  |
| $1B | 8 years | 7% | balanced | 0.12 | 0.06 | 20% | 32% | 11% | 4% |  |
| $1B | 8 years | 7% | aggressive | 0.06 | 0.06 | 11% | 96% | 62% | 4% |  |

## Do the band distributions look sensible? (D3)

The model's average predicted share of each band against the actual share on val. Close numbers mean the distributions are calibrated on average.

| Question | Band | Mean predicted | Actual |
|---|---|---|---|
| outcome | shut down | 52% | 50% |
| outcome | under \$50M | 14% | 15% |
| outcome | \$50M-\$500M | 14% | 15% |
| outcome | \$500M-\$1B | 11% | 10% |
| outcome | over \$1B | 9% | 10% |
| years | under 5 | 47% | 46% |
| years | 5-8 | 38% | 38% |
| years | over 8 | 15% | 15% |
