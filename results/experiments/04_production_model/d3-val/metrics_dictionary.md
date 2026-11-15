# Metrics dictionary (04_production_model, D3)

Terms are defined in plain English in [GLOSSARY.md](../../../GLOSSARY.md).

## metrics.csv (one row per model; val, 400 founders, 80 of whom reached $500M or more)

| Column | Meaning | Units | Better if |
|---|---|---|---|
| `model` | PROD (the production model: P(outcome is \$500M-\$1B or over \$1B)) or C3 (P(success)) | – | – |
| `score` | the probability scored | – | – |
| `threshold` | flag a founder at or above it; tuned on these same val founders for F0.5 | probability | – |
| `n`, `positives`, `predicted_positive` | founders, founders who succeeded, founders flagged | count | – |
| `f05` | F0.5, the research metric (precision weighted above recall) | 0–1 | higher |
| `precision` | share of flagged founders who succeeded | 0–1 | higher |
| `recall` | share of successful founders who were flagged | 0–1 | higher |
| `brier` | mean squared error of the probability | 0–1 | lower |
| `ece` | expected calibration error, 10 equal-width bins | 0–1 | lower |
| `pr_auc` | area under the precision–recall curve (threshold-free ranking); random is 0.20 | 0–1 | higher |
| `*_ci_low`, `*_ci_high` | stratified bootstrap 95% CI (1,000 resamples, seed 42), threshold fixed | – | – |

## paired.csv (PROD − C3, the same 400 founders)

`metric`, each side's value (`prod`, `c3`), `diff`, its paired bootstrap 95% CI (`ci_low`,
`ci_high`) and whether that CI excludes zero. Positive F0.5 and PR-AUC differences favour PROD;
negative Brier and ECE differences do.

## band_shares.csv (one row per question and band)

`actual` is the share of val founders in the band; `with_descriptions` the production model's
mean calibrated probability for it, asked as trained; `without_descriptions` the same when the
options were sent without their descriptions (Kaggle's first pass, not used).

## predictions.csv (one row per val founder)

`id`, the true `outcome` and `years`, each band's calibrated probability (`p_outcome_<band>`,
`p_years_<band>`), and `p_500m_or_more`, the sum of the two top outcome bands.
