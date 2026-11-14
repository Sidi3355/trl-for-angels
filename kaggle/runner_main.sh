#!/usr/bin/env bash
# Everything the Kaggle runner does after cloning this repo: install, run kaggle/run.sh,
# push results to the kaggle-results branch. Kept in the repo so changes need no re-import.
#
# Called by kaggle/runner.ipynb with REPO_URL, RESULTS_BRANCH, AUTH (an HTTP header built
# from the GITHUB_TOKEN secret) and the secrets in the environment. Never prints secrets.
set -uo pipefail
# Extra Kaggle Secrets, read here so the notebook never needs re-importing. Kaggle's own
# Python needs Kaggle's PYTHONPATH, so this runs before it's unset. Values are never printed.
for name in HF_TOKEN; do
  if [ -z "${!name:-}" ]; then
    value=$(python -c "from kaggle_secrets import UserSecretsClient as U; \
print(U().get_secret('$name').strip())" 2>/dev/null) || value=""
    if [ -n "$value" ]; then export "$name=$value"; echo "$name: attached"; else
      echo "$name: not attached"; fi
  fi
done
unset value
unset PYTHONPATH  # Kaggle's sitecustomize hook needs packages our venvs don't have

KEV_COMMIT="2074cc4"
TRL_FORK="https://github.com/Sidi3355/think-reason-learn.git"
TRL_BRANCH="feature/decision-combiner"
export REPO=/tmp/work/repo WORK=/tmp/work OUT=/kaggle/working/out
rm -rf "$OUT" && mkdir -p "$OUT"
LOG="$OUT/run.log"
# One folder per run, pushed twice: when the run starts (status only) and when it ends.
TASK=$(sed -n 's/^TASK="\(.*\)"$/\1/p' "$REPO/kaggle/run.sh" | head -1)
RUN_ID="$(date -u +%Y%m%d-%H%M%S)-${TASK:-unknown}"

status() { echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUT/status.txt"; }

push_results() {
  local dest
  (cd "$WORK" && rm -rf results)
  cd "$WORK" || return 1
  if ! git -c http.extraHeader="$AUTH" clone -q --depth 1 -b "$RESULTS_BRANCH" "$REPO_URL" results 2>/dev/null; then
    git -c http.extraHeader="$AUTH" clone -q --depth 1 "$REPO_URL" results || return 1
    (cd results && git checkout -q --orphan "$RESULTS_BRANCH" && git rm -rqf --ignore-unmatch .)
  fi
  dest="$WORK/results/runs/$RUN_ID"
  mkdir -p "$dest"
  (cd "$OUT" && find . -type f -size -5M ! -name '*.safetensors' ! -name '*.pt' ! -name '*.bin' \
     -exec cp --parents {} "$dest/" \;)
  cd results
  git config user.name "kaggle-runner"
  git config user.email "kaggle-runner@users.noreply.github.com"
  git add -A && git commit -q -m "Kaggle run $RUN_ID: $(cut -d' ' -f1 "$OUT/status.txt")"
  git -c http.extraHeader="$AUTH" push -q origin "$RESULTS_BRANCH" \
    && echo "Pushed runs/$RUN_ID ($(cat "$OUT/status.txt")) to the $RESULTS_BRANCH branch."
}

setup() {
  echo "== setup"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv \
    || { echo "NO GPU: set Settings > Accelerator to GPU T4"; return 1; }
  pip install -q uv || return 1
  cd "$WORK" || return 1
  [ -d kev ] || git clone -q https://github.com/jaredpalmer/kev.git || return 1
  git -C kev checkout -q "$KEV_COMMIT" || return 1
  (cd kev && python -m uv sync -q --extra serve) || return 1
  [ -d think-reason-learn ] || git clone -q -b "$TRL_BRANCH" "$TRL_FORK" || return 1
  [ -d trl-venv ] || python -m uv venv -q --python 3.13 trl-venv || return 1
  python -m uv pip install -q --python trl-venv/bin/python -e "think-reason-learn[anthropic]" \
    || return 1
  trl-venv/bin/python -c "import think_reason_learn as t; print('TRL', t.__version__)"
  kev/.venv/bin/python -c \
    "import torch; print('torch', torch.__version__, 'CUDA available:', torch.cuda.is_available())"
}

status started
push_results || echo "PUSH FAILED at start: check that GITHUB_TOKEN has Contents: Read and write"

{
  echo "repo commit: $(git -C "$REPO" rev-parse --short HEAD)"
  if setup; then
    echo "== run.sh"
    bash "$REPO/kaggle/run.sh"
    echo "run.sh exit: $?"
  else
    echo "setup failed"
    echo setup > "$OUT/task.txt"
  fi
} 2>&1 | tee "$LOG"

echo "== push"
if grep -q "^run.sh exit: 0$" "$LOG"; then status finished; else status failed; fi
push_results || echo "PUSH FAILED: check that GITHUB_TOKEN has Contents: Read and write"
