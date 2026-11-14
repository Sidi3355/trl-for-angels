# 04 · The app's model and its risk table

## Question

How likely is a founder to reach each outcome band, and how soon? And at each risk setting,
what share of the founders the app advances actually get there?

## What we did

Kev was fine-tuned once more, with the input type that won on val in folder 03, to answer two
questions instead of one: which outcome band the company reaches (shut down / under $50M /
$50M-$500M / $500M-$1B / over $1B), and how many years that takes (under 5 / 5-8 / over 8).
Each question got its own temperature, fitted on val. From its val predictions,
`research/thresholds.py` builds the table behind the app's controls. For each target ($50M,
$500M, $1B) and timeline (any, 5 or 8 years), it gives the share of advanced founders who got
there (precision) and the share of those who got there that were advanced (recall), at every
threshold.

## Result

*Pending.* Whether the predicted band shares match the real ones on val, and what each risk
setting means, for example "at balanced, about N in 10 advanced founders reach $500M".

## What it means

*Pending.* This is what the app's sliders read (`app/thresholds.json`), so an investor sees
honest odds for the setting they choose.

## Caveats

- Timeline probabilities multiply the outcome and years answers as if they were independent,
  so they're estimates and are labelled as such in the app.
- All numbers come from 400 val founders; rare targets ($1B within 5 years) rest on few cases.
- Not a research result: research comparisons come from folders 01–03 only.

## Files

| File | What it is |
|---|---|
| `<stage>/thresholds.md` | the risk presets per target and timeline, in plain English |
| `<stage>/thresholds.json` | the full table (the same content as `app/thresholds.json`) |
| `<stage>/band_check.json` | average predicted share of each band against the real share on val |
