"""Build the Kaggle notebooks in this folder from their tested scripts.

    python kaggle/build_notebooks.py

- runner.ipynb: the one notebook the user runs. It clones this private repo with the
  GITHUB_TOKEN Kaggle Secret, runs kaggle/run.sh, and pushes the outputs to the
  kaggle-results branch, where Claude reads them.
- a3_kev_check.ipynb: the self-contained A3 check (no token needed), kept as a fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEV_COMMIT = "2074cc4"
TRL_FORK = "https://github.com/Sidi3355/think-reason-learn.git"
TRL_BRANCH = "feature/decision-combiner"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"},
            "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True,
                       "isGpuEnabled": True},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP = f"""
%%bash
# Installs Kev (pinned) and our TRL fork into their own Python 3.13 environments under /tmp/work.
set -euo pipefail
# Kaggle's PYTHONPATH carries a sitecustomize hook that needs packages our venvs don't have.
unset PYTHONPATH
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv \\
  || {{ echo "NO GPU: set Settings > Accelerator to GPU T4, then restart"; exit 1; }}
pip install -q uv
mkdir -p /tmp/work && cd /tmp/work
[ -d kev ] || git clone -q https://github.com/jaredpalmer/kev.git
git -C kev checkout -q {KEV_COMMIT}
(cd kev && python -m uv sync -q --extra serve)
[ -d think-reason-learn ] || git clone -q -b {TRL_BRANCH} {TRL_FORK}
[ -d trl-venv ] || python -m uv venv -q --python 3.13 trl-venv
python -m uv pip install -q --python trl-venv/bin/python -e "think-reason-learn[anthropic]"
trl-venv/bin/python -c "import think_reason_learn as t; print('TRL', t.__version__)"
kev/.venv/bin/python -c "import torch; print('torch', torch.__version__, 'CUDA available:', torch.cuda.is_available())"
"""

SUMMARY = """
import json
r = json.load(open("/kaggle/working/a3_report.json"))
print("VERDICT:", r.get("verdict"))
print("GPU:", r.get("environment", {}).get("device"), "| torch", r.get("environment", {}).get("torch"))
print("Server:", r.get("server"))
print("Endpoint:", r.get("endpoint"))
print("Speed:", r.get("speed"))
for k in ("train_short", "train_long"):
    t = r.get(k, {})
    last = (t.get("attempts") or [{}])[-1]
    print(f"{k}: works={t.get('works')} tokens={t.get('state_tokens')} "
          f"projected_hours={t.get('projected_hours_2000x2epochs')} "
          f"batch={last.get('batch')} checkpointing={last.get('checkpointing')} "
          f"step_s={last.get('median_step_seconds')} peak_MiB={last.get('peak_device_mib')} "
          f"rejected={last.get('rejected_records')} error={t.get('error') or last.get('returncode')}")
"""


def a3() -> dict:
    script = (HERE / "a3_check.py").read_text()
    return notebook([
        md("""
# A3: Kev on a Kaggle GPU (trl-for-angels)

Checks, on a free Kaggle T4:

1. **Serve** Kev-0.6B (`jaredpalmer/kev-0.6b`) on the GPU, in fp32 (the T4 has no bf16).
2. **Endpoint**: one call through TRL's real `LLMSession` (step A3's "done when").
3. **Answering speed** through TRL, projected to the full run (~300,000 answers).
4. **Fine-tuning** on this GPU with Kev's own recipe, on short (C4-like) and long (C3-like)
   states, projected to the full C3 and C4 runs.

All profiles and labels in this notebook are synthetic, for timing only.

**Before running:** Settings → **Accelerator: GPU T4** (x1 is enough) and **Internet: On**
(needs a phone-verified Kaggle account). No secrets are needed for this notebook.

**Run:** Run All. Expect about 30–60 minutes, mostly installs, model download and the
fine-tuning test.

**Afterwards:** download `a3_report.json` from the Output panel (right side, under
/kaggle/working) and send it back, or paste the last cell's printout.
"""),
        code(SETUP),
        code("%%writefile /tmp/work/a3_check.py\n" + script),
        code("!env -u PYTHONPATH /tmp/work/trl-venv/bin/python /tmp/work/a3_check.py "
             "--kev-dir /tmp/work/kev --out /kaggle/working/a3_report.json"),
        code(SUMMARY),
    ])


REPO_URL = "https://github.com/Sidi3355/trl-for-angels.git"
REPO_BRANCH = "claude/determined-albattani-dl2cyy"
RESULTS_BRANCH = "kaggle-results"

# The token only ever travels in an HTTP header built from the env var; nothing echoes it.
AUTH = ('AUTH="AUTHORIZATION: basic $(printf \'x-access-token:%s\' "$GITHUB_TOKEN" '
        '| base64 -w0)"')

RUNNER_SECRETS = """
# Secrets from Add-ons > Secrets, into this kernel's environment (never printed).
import os
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
for name in ("GITHUB_TOKEN", "ANTHROPIC_API_KEY"):
    try:
        os.environ[name] = secrets.get_secret(name)
        print(f"{name}: attached")
    except Exception:
        print(f"{name}: not attached")
assert os.environ.get("GITHUB_TOKEN"), "Attach the GITHUB_TOKEN secret (Add-ons > Secrets)"
"""

RUNNER_CLONE = f"""
%%bash
# This project's repo, at the branch Claude works on.
set -euo pipefail
{AUTH}
mkdir -p /tmp/work && cd /tmp/work && rm -rf repo
git -c http.extraHeader="$AUTH" clone -q --depth 1 -b {REPO_BRANCH} {REPO_URL} repo
git -C repo log --oneline -1
"""

RUNNER_RUN = """
%%bash
# Runs whatever kaggle/run.sh says. Never fails the cell, so the results still get pushed.
unset PYTHONPATH
export REPO=/tmp/work/repo WORK=/tmp/work OUT=/kaggle/working/out
rm -rf "$OUT" && mkdir -p "$OUT"
bash "$REPO/kaggle/run.sh" 2>&1 | tee "$OUT/run.log"
echo "run.sh exit: ${PIPESTATUS[0]}" | tee -a "$OUT/run.log"
"""

RUNNER_PUSH = f"""
%%bash
# Pushes this run's small files (no model weights) to the {RESULTS_BRANCH} branch.
set -euo pipefail
{AUTH}
OUT=/kaggle/working/out
STAMP=$(date -u +%Y%m%d-%H%M%S)
TASK=$(cat "$OUT/task.txt" 2>/dev/null || echo unknown)
cd /tmp/work && rm -rf results
if ! git -c http.extraHeader="$AUTH" clone -q --depth 1 -b {RESULTS_BRANCH} {REPO_URL} results 2>/dev/null; then
  git -c http.extraHeader="$AUTH" clone -q --depth 1 {REPO_URL} results
  (cd results && git checkout -q --orphan {RESULTS_BRANCH} && git rm -rqf --ignore-unmatch .)
fi
DEST="/tmp/work/results/runs/$STAMP-$TASK"
mkdir -p "$DEST"
(cd "$OUT" && find . -type f -size -5M ! -name '*.safetensors' ! -name '*.pt' ! -name '*.bin' \\
   -exec cp --parents {{}} "$DEST/" \\;)
cd results
git config user.name "kaggle-runner"
git config user.email "kaggle-runner@users.noreply.github.com"
git add -A && git commit -q -m "Kaggle run $STAMP ($TASK)"
git -c http.extraHeader="$AUTH" push -q origin {RESULTS_BRANCH}
echo "Pushed runs/$STAMP-$TASK to the {RESULTS_BRANCH} branch."
"""


def runner() -> dict:
    return notebook([
        md(f"""
# trl-for-angels: Kaggle runner

The only notebook you need. Each run it pulls the project from GitHub, runs the task in
`kaggle/run.sh` (Claude picks it), and pushes the results to the `{RESULTS_BRANCH}` branch,
where Claude reads them. You don't need to watch it.

**One-time setup**
1. Settings → **Accelerator: GPU T4** and **Internet: On**.
2. Add-ons → **Secrets**, attached to this notebook:
   - `GITHUB_TOKEN`: a fine-grained GitHub token for `Sidi3355/trl-for-angels` only, with
     **Contents: Read and write**.
   - `ANTHROPIC_API_KEY`: your Claude Console key (needed from step A4).

**Each run:** **Save Version → Save & Run All (Commit) → Save**. It runs in the background
on Kaggle; close the tab if you like. Then tell Claude it's started.
"""),
        code(RUNNER_SECRETS),
        code(RUNNER_CLONE),
        code(SETUP),
        code(RUNNER_RUN),
        code(RUNNER_PUSH),
    ])


def main() -> None:
    out = HERE / "a3_kev_check.ipynb"
    out.write_text(json.dumps(a3(), indent=1) + "\n")
    print(f"wrote {out}")
    out = HERE / "runner.ipynb"
    out.write_text(json.dumps(runner(), indent=1) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
