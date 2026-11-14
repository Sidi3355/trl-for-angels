# trl-for-angels

A calibrated deal-screening agent for angel investors, built on Vela Research's
[Think Reason Learn (TRL)](https://github.com/Vela-Research/think-reason-learn).

**Results: start at [`results/README.md`](results/README.md).**

The full design, settled decisions and step order are in [`MASTER_PLAN.md`](MASTER_PLAN.md).

## What's here

| Folder | What it holds |
|---|---|
| `data/` | `raw/` generated datasets, `splits/` train/val/test, `answers/` cached Jev answer matrices |
| `research/` | the research pipeline: splits, RRF fit, baselines, Kev conditions, evaluation, interp |
| `app/` | the deal-screening agent: research agent, merge, render, decide, policy, API, `frontend/` |
| `results/` | every result, written for non-researchers (see `results/README.md`) |

## Setup

TRL is used from our fork, checked out next to this repo, on branch `feature/decision-combiner`
(based on upstream commit `3437d64`, TRL 0.3.0). TRL needs Python 3.13.

```bash
git clone https://github.com/Vela-Research/think-reason-learn.git ../think-reason-learn
git -C ../think-reason-learn switch -c feature/decision-combiner 3437d64
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env   # then fill in the keys
```

`requirements.lock.txt` records the exact versions last installed.

To run TRL's own checks in the fork (dev tools in its own Poetry venv):

```bash
cd ../think-reason-learn && poetry install --with dev --all-extras && poetry run pytest -q
```

## Status

Hackathon project, in progress. Data is generated, so no real-world accuracy is claimed.
