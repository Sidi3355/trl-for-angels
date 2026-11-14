# Decision log

Settled project decisions are in `MASTER_PLAN.md` section 3. This log records decisions made
while doing the work: date, decision, reason, evidence. Newest last.

## 2026-11-14 · A1 · TRL pinned at `3437d64`

- **Decision:** the fork's branch `feature/decision-combiner` starts at upstream commit `3437d64`.
- **Reason:** the plan pins this commit for reproducibility.
- **Evidence:** `git describe` gives `v0.3.0-3-g3437d64`, three commits after the `v0.3.0` tag
  (`35275a8`, `9f0619c`, `3437d64`). They change only the package description, a docs test and a
  merge, so library behaviour is v0.3.0's. The package reports version `0.3.0`. It was upstream
  `main`'s head on 2026-11-14.

## 2026-11-14 · A1 · Project environment

- **Decision:** a Python 3.13 venv (`uv`) holding the fork in editable mode with the `[anthropic]`
  extra, plus XGBoost and scikit-learn. Exact versions are in `requirements.lock.txt`.
- **Reason:** TRL requires Python ≥ 3.13. The OpenAI SDK is a core TRL dependency, so
  `[anthropic]` covers both possible generator providers. The `rl` extra (PyTorch) isn't needed
  in the project environment. The fork's own Poetry venv installs all extras for its tests.

## 2026-11-14 · A1 · Open item: TRL's cache location

- **Note:** TRL's disk cache defaults to `~/.cache/think_reason_learn/llm-cache-v2.sqlite`, which
  is outside the repo and is lost when the cloud container is reclaimed.
- **To decide at A4:** pass an explicit `cache_dir` inside the project (git-ignored or committed),
  so cached Jev answers and generated questions survive between sessions.
