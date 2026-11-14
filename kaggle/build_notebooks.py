"""Build the Kaggle notebooks in this folder from their tested scripts.

    python kaggle/build_notebooks.py

Each notebook is self-contained: it installs what it needs and embeds its script with
%%writefile, because this project's repo is private and Kaggle can't clone it without a token.
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
        code("!/tmp/work/trl-venv/bin/python /tmp/work/a3_check.py --kev-dir /tmp/work/kev "
             "--out /kaggle/working/a3_report.json"),
        code(SUMMARY),
    ])


def main() -> None:
    out = HERE / "a3_kev_check.ipynb"
    out.write_text(json.dumps(a3(), indent=1) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
