# Validation: `sample50.jsonl`

**Verdict: PASS.** 50 rows read, 50 parsed, 0 dataset check(s) failed, 0 row(s) with errors, 0 row(s) with warnings to review. Profile: `sample50`.

FAIL means a rule from MASTER_PLAN section 10 is broken. WARN means a heuristic flagged something to look at by eye; it may be fine.

## Dataset checks

| Check | Status | Detail |
|---|---|---|
| Dropped rows | PASS | 0 of 50 rows don't parse |
| Row count | PASS | 50 rows, target 50 |
| Outcome counts | PASS | shut down: 25 (target 25); under $50M: 8 (target 8); $50M-$500M: 7 (target 7); $500M-$1B: 5 (target 5); over $1B: 5 (target 5) |
| Research label share | INFO | 10 of 50 'yes' ($500M and above): 20% |
| Shuffled | PASS | longest run of one outcome: 3 |
| Timelines by outcome | PASS | shut down over 8 years: 16% (should be a minority); over $1B under 5 years: 0% (should be rare) |
| Traits in both strong and shut-down records | PASS | top-50 university: 3 strong / 13 shut down / 24 total; unranked or no degree: 3 strong / 5 shut down / 12 total; big-tech-sized employer (5,000+): 5 strong / 12 shut down / 20 total; solo founder: 1 strong / 2 shut down / 4 total; first-time founder: 7 strong / 15 shut down / 33 total; repeat founder: 3 strong / 10 shut down / 17 total; prior exit: 1 strong / 7 shut down / 10 total |
| Similar length across bands | PASS | strong vs shut down length gap +3%; shut down: 614 chars, 2.4 jobs, 1.3 degrees; under $50M: 566 chars, 2.2 jobs, 1.2 degrees; $50M-$500M: 614 chars, 2.4 jobs, 1.6 degrees; $500M-$1B: 581 chars, 2.2 jobs, 1.2 degrees; over $1B: 689 chars, 3.0 jobs, 1.4 degrees |
| Industries | PASS | 47 distinct (need 15): news media (2), email software (2), social media (2), social messaging (1), consumer software (1), electric aviation (1), packaged food (1), online car marketplace (1), autonomous vehicles (1), enterprise email software (1), developer tools (1), computer vision (1), digital therapeutics (1), ride-sharing (1), e-commerce (1), consumer robotics (1), consumer audio hardware (1), consumer drones (1), media software (1), podcasting (1), electric vehicles (1), insurtech (1), digital reading (1), diagnostics (1), data infrastructure (1), home services (1), crowdfunding (1), fashion e-commerce (1), cloud infrastructure (1), self-driving software (1), food and beverage (1), personal care products (1), freight logistics (1), cybersecurity (1), online checkout payments (1), consumer photo software (1), agtech (1), consumer fintech (1), productivity software (1), digital media (1), autonomous trucking (1), food delivery (1), agricultural robotics (1), online pharmacy (1), biotech (1), primary care (1), anonymous social apps (1) |
| Mix of founder types | PASS | {"co-founders": {"1": 32, "2": 12, "solo": 4, "3+": 2}, "background": {"technical": 18, "business": 17, "mixed": 10, "domain specialist": 5}, "experience": {"<5": 17, "5-10": 16, "15+": 11, "10-15": 6}, "degrees": {"bsc": 21, "ba": 16, "msc": 12, "other": 6, "no degree": 5, "mba": 4, "phd": 3}} |
| Duplicates (exact and near) | PASS | exact groups: none; near pairs (rows, similarity): none |
| Same career path (roles + industries) | PASS | rows sharing a path: none |
| Records with unknown fields | PASS | 8, target 8; by outcome {'shut down': 3, '$50M-$500M': 1, 'over $1B': 1, 'under $50M': 2, '$500M-$1B': 1}; fields {'employees': 2, 'prior exits': 1, 'QS band': 6} |
| Single-field predictiveness (AUC, out-of-fold) | PASS | background: 0.684; industry experience: 0.549; industry: 0.535; has MBA: 0.515; has PhD: 0.512; prior exits: 0.5; largest employer size: 0.433; number of jobs: 0.411; best university band: 0.375; no degree: 0.345; has unknown field: 0.325; number of degrees: 0.321; prior startups: 0.297; co-founders: 0.281; experience: 0.201; profile length (quartile): 0.182 (small sample: noisy) |

## Rows with errors

None.

## Rows with warnings

None.

## For manual review (not checkable by script)

- [ ] Grounding: records at $500M and above are based on real founders and the outcome and years are correct for that company (can't be checked by a script).
- [ ] No household-name companies or widely famous founders behind the records.
- [ ] About 15 records (sample) or 30% (full) are 'surprising': strong backgrounds that shut down and modest ones that reached large outcomes, spread across bands.
- [ ] Degrees, fields and roles fit together, beyond the technical-background heuristic.
- [ ] Profiles read as realistic and varied, with no shared template.
