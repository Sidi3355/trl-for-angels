# Validation: `full.jsonl`

**Verdict: PASS.** 3000 rows read, 3000 parsed, 0 dataset check(s) failed, 0 row(s) with errors, 0 row(s) with warnings to review. Profile: `full`.

FAIL means a rule from MASTER_PLAN section 10 is broken. WARN means a heuristic flagged something to look at by eye; it may be fine.

## Dataset checks

| Check | Status | Detail |
|---|---|---|
| Dropped rows | PASS | 0 of 3000 (0.0%); limit 2% |
| Row count | PASS | 3000 rows, target 3000 |
| Outcome counts | PASS | shut down: 1500 (50.0%, target 50%, +0.0 pp); under $50M: 450 (15.0%, target 15%, +0.0 pp); $50M-$500M: 450 (15.0%, target 15%, +0.0 pp); $500M-$1B: 300 (10.0%, target 10%, +0.0 pp); over $1B: 300 (10.0%, target 10%, +0.0 pp) |
| Research label share | INFO | 600 of 3000 'yes' ($500M and above): 20% |
| Shuffled | PASS | longest run of one outcome: 5 |
| Timelines by outcome | PASS | shut down over 8 years: 11% (should be a minority); over $1B under 5 years: 7% (should be rare) |
| Traits in both strong and shut-down records | PASS | top-50 university: 250 strong / 378 shut down / 952 total; unranked or no degree: 127 strong / 393 shut down / 733 total; big-tech-sized employer (5,000+): 295 strong / 636 shut down / 1368 total; solo founder: 46 strong / 295 shut down / 458 total; first-time founder: 364 strong / 1116 shut down / 2093 total; repeat founder: 220 strong / 343 shut down / 816 total; prior exit: 119 strong / 139 shut down / 385 total |
| Similar length across bands | PASS | strong vs shut down length gap +10%; shut down: 637 chars, 2.7 jobs, 1.4 degrees; under $50M: 675 chars, 3.0 jobs, 1.5 degrees; $50M-$500M: 687 chars, 3.1 jobs, 1.6 degrees; $500M-$1B: 697 chars, 3.2 jobs, 1.6 degrees; over $1B: 705 chars, 3.2 jobs, 1.7 degrees |
| Industries | PASS | 113 distinct (need 25): b2b saas (83), cybersecurity (77), payments (77), online education (76), e-commerce (75), online marketplaces (68), developer tools (63), biotech (62), social media (55), food delivery (55), cloud infrastructure (53), machine learning platforms (53), personal finance (53), food and beverage (52), travel (50), consumer electronics (48), consumer goods (47), data infrastructure (46), logistics (46), last-mile delivery (46), small business lending (45), marketing technology (44), fashion e-commerce (42), insurance technology (42), digital media (41), medical devices (41), advertising technology (41), consumer lending (40), supply chain analytics (39), drug discovery (38), real estate technology (37), agriculture technology (36), recruiting (36), primary care (35), fitness (35), accounting automation (35), urban mobility (35), consumer robotics (34), solar energy (34), customer support automation (34), beauty products (34), mobile games (34), mental health (33), wealth management (33), diagnostics (32), home services (32), retail technology (31), freight brokerage (29), autonomous vehicles (28), drones (28), wearables (28), energy storage (28), automotive retail (28), semiconductors (28), online dating (27), online pharmacy (26), sports technology (25), staffing marketplaces (24), music streaming (23), legal technology (23), video streaming (23), government technology (22), hospitality (22), construction technology (22), core banking technology (22), restaurant technology (22), electric vehicles (21), pet care (21), clinical trials (21), payroll and benefits (21), indoor farming (20), audio content (20), telecommunications (20), event ticketing (19), industrial robotics (19), property management (18), senior care (17), early childhood education (17), 3d printing (16), language learning (14), esports (14), water technology (12), home security (12), space technology (11), news media (2), email software (2), social messaging (1), consumer software (1), electric aviation (1), packaged food (1), online car marketplace (1), enterprise email software (1), computer vision (1), digital therapeutics (1), ride-sharing (1), consumer audio hardware (1), consumer drones (1), media software (1), podcasting (1), insurtech (1), digital reading (1), crowdfunding (1), self-driving software (1), personal care products (1), freight logistics (1), online checkout payments (1), consumer photo software (1), agtech (1), consumer fintech (1), productivity software (1), autonomous trucking (1), agricultural robotics (1), anonymous social apps (1) |
| Industries per 50 rows (file order) | PASS | every full block has >= 15 |
| Mix of founder types | PASS | {"co-founders": {"1": 1295, "2": 767, "3+": 480, "solo": 458}, "background": {"technical": 1043, "business": 901, "mixed": 637, "domain specialist": 419}, "experience": {"5-10": 1046, "<5": 721, "10-15": 692, "15+": 541}, "degrees": {"bsc": 1482, "msc": 622, "mba": 589, "ba": 481, "other": 476, "beng": 463, "phd": 243, "no degree": 182, "ma": 18}} |
| Duplicates (exact and near) | PASS | exact groups: none; near pairs (rows, similarity): none |
| Same career path (roles + industries) | PASS | rows sharing a path: none |
| Records with unknown fields | PASS | 478 (16%), target 10%-20%; by outcome {'shut down': 237, '$50M-$500M': 73, 'over $1B': 42, 'under $50M': 74, '$500M-$1B': 52}; fields {'employees': 206, 'prior exits': 87, 'QS band': 102, 'prior startups': 91, 'job duration': 111} |
| Single-field predictiveness (AUC, out-of-fold) | PASS | industry: 0.599; background: 0.594; industry experience: 0.582; best university band: 0.578; profile length (quartile): 0.556; number of degrees: 0.553; number of jobs: 0.552; experience: 0.551; co-founders: 0.54; prior startups: 0.537; prior exits: 0.532; has PhD: 0.527; largest employer size: 0.525; no degree: 0.506; has MBA: 0.494; has unknown field: 0.467 |

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
