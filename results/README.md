# Results: start here

**What this project tests:** with TRL's question-writing and question-answering steps held fixed,
which final decision step (the "learn stage") gives the most accurate and best-calibrated
predictions of founder success? Terms are explained in [`GLOSSARY.md`](GLOSSARY.md).

**The answer:** not yet. No experiments have run. This page will carry the answer in three
sentences once the final evaluation is done.

## Map of this folder

| File or folder | What it is |
|---|---|
| `FINDINGS.md` | plain-English findings, one short section each, with the key number and plot |
| `GLOSSARY.md` | every technical term in one or two plain sentences |
| `DECISIONS.md` | decision log: date, decision, reason, evidence |
| `run_info.json` | TRL commit and version, model IDs, seeds, split sizes, dates, costs |
| `data/` | what the dataset is, how it was made, its limits, and per-split stats |
| `experiments/01_baselines/` | C1a, C1b (TRL's RRF) and CTRL (XGBoost) |
| `experiments/02_kev_zero_shot/` | C2 and EXTRA (Kev with no training) |
| `experiments/03_kev_finetuned/` | C3 and C4 (fine-tuned Kev) |
| `experiments/04_production_model/` | the model that powers the app |
| `experiments/05_interp_flips/` | what each model relies on, by flipping answers |
| `experiments/06_interp_probes/` | where inside Kev the decision forms |
| `experiments/07_interp_sae/` | hidden concepts Kev builds |
| `summary/` | one table of every condition's metrics with confidence intervals, and the final plots |
