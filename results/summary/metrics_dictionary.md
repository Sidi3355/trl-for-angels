# Metrics dictionary

What every column in `metrics.csv` and `predictions.csv` means. Plain-English definitions with
examples are in [GLOSSARY.md](../GLOSSARY.md). `research/evaluate.py` copies this file next to
every `metrics.csv` it writes.

## metrics.csv (one row per condition, split and threshold rule)

| Column | Meaning | Units | Better if |
|---|---|---|---|
| `condition` | short name: C1a, C1b, CTRL, C2, C3, C4, EXTRA | – | – |
| `name` | what the condition is, in words | – | – |
| `split` | `val` (where choices are made) or `test` (final scores, read once) | – | – |
| `threshold_protocol` | how the yes/no threshold was set: `val-tuned F0.5` (every condition) or `TRL native (train out-of-fold)` (TRL's own, C1a and C1b only) | – | – |
| `threshold` | the probability at or above which a founder is flagged as successful | probability, 0–1 | – |
| `n` | founders scored | count | – |
| `positives` | founders who really were successful | count | – |
| `predicted_positive` | founders the condition flagged as successful | count | – |
| `f05` | **main score**: F0.5, precision weighted twice as much as recall | 0–1 | higher |
| `precision` | of the flagged founders, the share who really succeeded | 0–1 | higher |
| `recall` | of the successful founders, the share that were flagged | 0–1 | higher |
| `brier` | average squared gap between P(success) and what happened | 0–1 | lower |
| `ece` | calibration error over 10 bins of P(success) | 0–1 | lower |
| `pr_auc` | ranking quality across all thresholds (precision-recall area) | 0–1 | higher |
| `<metric>_ci_low`, `<metric>_ci_high` | 95% confidence interval of that metric (test only; 1,000 stratified bootstrap resamples, threshold fixed from val) | same as the metric | narrower is more certain |
| `plain_reading` | the result in words, e.g. "of every 10 it flags, about 4 succeed" | – | – |

## predictions.csv (one row per founder and condition)

| Column | Meaning |
|---|---|
| `id` | the founder's id, the same in every file (from `data/splits/`) |
| `condition` | which condition made the prediction |
| `split` | `val` or `test` |
| `label` | what really happened: `successful` or `failed` |
| `p_success` | the condition's probability that the founder succeeds |
| `decision` | `successful` if `p_success` is at or above the val-tuned threshold, else `failed` |
