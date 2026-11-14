#!/usr/bin/env bash
# What the Kaggle runner notebook (kaggle/runner.ipynb) runs next.
# Claude edits TASK and pushes; the user just reruns the same notebook (Save & Run All).
# Results land on the kaggle-results branch under runs/<UTC time>-<task>/.
#
# Set by the runner: REPO (this repo, checked out), WORK (/tmp/work: kev/, trl-venv/),
# OUT (folder pushed to GitHub). Secrets arrive as env vars: ANTHROPIC_API_KEY (if attached).
set -uo pipefail

TASK="a3"

echo "$TASK" > "$OUT/task.txt"
git -C "$REPO" rev-parse --short HEAD > "$OUT/repo_commit.txt"
PY="$WORK/trl-venv/bin/python"

case "$TASK" in
  a3)
    "$PY" "$REPO/kaggle/a3_check.py" --kev-dir "$WORK/kev" \
      --out "$OUT/a3_report.json" --work "$OUT/a3_work"
    ;;
  a4)
    "$PY" "$REPO/kaggle/a4_check.py" --kev-dir "$WORK/kev" \
      --sample "$REPO/data/raw/sample50.jsonl" --out "$OUT/a4"
    ;;
  *)
    echo "unknown TASK $TASK" >&2
    exit 2
    ;;
esac
