# Data splits

**In short:** 3,000 rows were read from `data/raw/full.jsonl`. 3,000 were kept and 0 dropped because they don't parse. The kept rows are split into **2,000 train / 400 val / 600 test**, with the same mix of outcomes in each (stratified on outcome band, seed 42). No founder, and no group of duplicate profiles, appears in more than one split.

## What the words mean

- **Row (founder):** one anonymised founder profile and its company's outcome. Every row is a different founder, so splitting by founder means splitting by row.
- **Train, val and test:** three separate piles of founders. Train is what models learn from; val (validation) is used to make choices: thresholds, temperatures, which model the app uses; test is locked away and scored once, at the very end, so the final results are honest.
- **Outcome band:** the company's final outcome, one of five bands from "shut down" to "over \$1B". **Years** is the time from founding to that outcome.
- **Research label:** "successful" if the outcome is \$500M-\$1B or over \$1B, otherwise "failed". It is what the research models predict.
- **Stratified:** each split gets the same mix of outcome bands as the whole dataset, to within one row, so no split is by chance easier or harder than another.
- **Duplicate group:** profiles that are exact copies, or near copies (sharing 80% or more of their five-word phrases), of each other. A group is kept together in one split, so no model is tested on a founder it has, in effect, already seen.
- **Unknown field:** a profile detail the dataset marks as "unknown" on purpose (for example "Prior exits: unknown").

## Rows read, kept and dropped

|  | Rows |
|---|---|
| Read from the file | 3,000 |
| Kept | 3,000 |
| Dropped | 0 |

## Split sizes

| Split | What it is for | Rows | Share of kept rows |
|---|---|---|---|
| train | what models learn from | 2,000 | 66.7% |
| val | used to make choices: thresholds, temperatures, which model the app uses | 400 | 13.3% |
| test | locked away and scored once, at the very end | 600 | 20.0% |

## Outcome bands per split

Each cell is the number of founders, and in brackets that number as a share of the split. Reading across a row, the shares should be nearly equal.

| Outcome band | train | val | test | All |
|---|---|---|---|---|
| shut down | 1,000 (50.0%) | 200 (50.0%) | 300 (50.0%) | 1,500 (50.0%) |
| under \$50M | 300 (15.0%) | 60 (15.0%) | 90 (15.0%) | 450 (15.0%) |
| \$50M-\$500M | 300 (15.0%) | 60 (15.0%) | 90 (15.0%) | 450 (15.0%) |
| \$500M-\$1B | 200 (10.0%) | 40 (10.0%) | 60 (10.0%) | 300 (10.0%) |
| over \$1B | 200 (10.0%) | 40 (10.0%) | 60 (10.0%) | 300 (10.0%) |

## Years to outcome per split

| Years | train | val | test | All |
|---|---|---|---|---|
| under 5 | 873 (43.6%) | 186 (46.5%) | 263 (43.8%) | 1,322 (44.1%) |
| 5-8 | 785 (39.2%) | 154 (38.5%) | 236 (39.3%) | 1,175 (39.2%) |
| over 8 | 342 (17.1%) | 60 (15.0%) | 101 (16.8%) | 503 (16.8%) |

Years weren't used to stratify, so their mix can vary a little more between splits than the outcome bands do.

## Research label per split

| Label | train | val | test | All |
|---|---|---|---|---|
| successful | 400 (20.0%) | 80 (20.0%) | 120 (20.0%) | 600 (20.0%) |
| failed | 1,600 (80.0%) | 320 (80.0%) | 480 (80.0%) | 2,400 (80.0%) |

## Profiles with an unknown field, per split

|  | train | val | test | All |
|---|---|---|---|---|
| Rows with at least one unknown field | 306 (15.3%) | 63 (15.8%) | 109 (18.2%) | 478 (15.9%) |

## Duplicate groups

None: no two profiles are exact or near copies of each other.

## Leakage checks

Computed from the written split files. PASS means the check holds.

| Check | Result | Detail |
|---|---|---|
| Every kept row is in exactly one split | PASS | 3,000 rows, 3,000 ids, none missing, none repeated |
| No duplicate group is spread over two splits | PASS | 0 group(s) checked |
| No profile text appears in two splits | PASS | compared after normalising case, dashes and spaces |
| Each band's count in each split is within one row of its exact proportional share | PASS | largest gap 0.00 rows |

## How the split was made

1. Every row was parsed with `research/validate.py`. Rows without a valid outcome and years, or without a profile in the template, were dropped.
2. Each kept row got an id, `r` plus its position in the file (`r00001` is the first record; blank lines are skipped), and the research label.
3. Duplicates were found with validate.py's check (identical text after normalising case, dashes and spaces; or 80% or more of five-word phrases shared), and linked rows were joined into groups.
4. Each band's share of each split was worked out exactly, then rounded so that every band and every split adds up (each within one row of its exact share).
5. Groups of two or more rows were placed first, each wholly in one split chosen at random, weighted by the room left. Single rows were then dealt in a random order to fill each band's share of each split.
6. The random order comes from SHA-256 hashes of the seed (42) and each row's position, so the same file and seed give identical splits on any machine.

## Notes

- Input file SHA-256: `6861ba4172c6b5b4e8a306366dbece67905dabd917b3eef4296c9a8bc023da6c`.
- Near copies are found by comparing likely pairs rather than every pair, so a few may be missed. Exact copies are always found.

## Files

| File | What it is |
|---|---|
| `data/splits/train.jsonl` | the train split, one founder per line, with the fields `id`, `instruction`, `input`, `output`, `outcome`, `years`, `label` |
| `data/splits/val.jsonl` | the val split, one founder per line, with the fields `id`, `instruction`, `input`, `output`, `outcome`, `years`, `label` |
| `data/splits/test.jsonl` | the test split, one founder per line, with the fields `id`, `instruction`, `input`, `output`, `outcome`, `years`, `label` |
| `results/run_info.json` | key `splits.actual`: the sizes, seed and input file |
