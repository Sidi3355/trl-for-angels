# Dataset

**In short:** 3,000 made-up but realistic founder profiles, each describing a founder on the
day their company was founded, labelled with how big the company's outcome was and how long
it took. Results describe this dataset, not the real world. Per-split counts are in
`stats.md` (written by `research/splits.py`, step A6).

**Status:** generation is under way. A 50-row sample comes first (step A2); it must pass the
validator (`research/validate.py`) and a read-through before the full 3,000 rows (A5).

## How it was made

- **Tool:** Adaption, from the prompts in `MASTER_PLAN.md` sections 10a (sample) and 10 (full).
- **Grounding:** each profile is based on a real founder and real outcome where possible,
  especially the successful ones, preferring lesser-known companies; otherwise it's a
  founder typical of that outcome.
- **Fixed template:** every profile follows the same lines: industry and co-founders;
  background and experience; 1–3 education entries; 1–6 jobs, oldest first; prior startups;
  prior exits. Only the allowed values are used, for example years of experience as
  `<5 / 5-10 / 10-15 / 15+`.
- **Anonymised:** no names of people, companies, products, universities or places, and no
  exact dates. Employers are described generically ("a payments company").
- **Founding-date cutoff:** only what was true on the day the company was founded. No later
  jobs, funding or traction, so no model can see the future.
- **Built against shortcuts:** no single detail is allowed to give the outcome away. For
  example, top-50 universities, solo founders and prior exits all appear among both shut-down
  and successful founders, about 30% of records are deliberately "surprising", and profile
  length doesn't depend on outcome.

## Labels

| Label | Values | Share (target) |
|---|---|---|
| Outcome | shut down / under $50M / $50M-$500M / $500M-$1B / over $1B | 50% / 15% / 15% / 10% / 10% |
| Years to that outcome | under 5 / 5-8 / over 8 | (not fixed) |
| **Research label** | **successful** = $500M-$1B or over $1B; otherwise failed | about 20% successful |

The outcome is the exit or IPO value, or total funding if the company is still private and has
raised over $500M; "shut down" if it closed. Companies were founded in 2010–2019, outcomes as
of 2025.

## Splits

| Split | Rows | Used for |
|---|---|---|
| train | 2,000 | everything the models learn from |
| val | 400 | every choice: thresholds, temperatures, checkpoints, which model the app uses |
| test | 600 | the final scores only, read once |

Splits are stratified on outcome band (same mix in each) with seed 42, and near-duplicate
profiles are kept in the same split, so no model is tested on a founder it has, in effect,
already seen.

## Limits

- **Generated, not observed.** An AI wrote these profiles. Patterns in them may be the AI's
  ideas of what success looks like, not the real world's. A model that does well here may
  not do well on real founders.
- **Grounding can't be fully checked.** Whether each profile matches a real founder and the
  real outcome can't be verified by a script.
- **Small successful group.** About 400 successful founders in train and 120 in test, so test
  scores carry real uncertainty; that's why every score has a confidence interval.
