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


SAMPLE = HERE.parent / "data" / "raw" / "sample50.jsonl"
A4_ROWS, A4_STRONG, SEED = 20, 6, 42


def a4_rows(path: Path) -> list[dict]:
    """20 sample rows (6 successful, 14 not), chosen reproducibly; parse failures skipped."""
    import random
    import sys

    sys.path.insert(0, str(HERE.parent / "research"))
    from validate import STRONG, load, parse_record

    rows = load(path)
    parsed = [(row, parse_record(row, i)) for i, row in enumerate(rows, 1)]
    good = [(row, rec) for row, rec in parsed if rec.outcome is not None]
    strong = [row for row, rec in good if rec.outcome in STRONG]
    other = [row for row, rec in good if rec.outcome not in STRONG]
    rng = random.Random(SEED)
    picked = rng.sample(strong, min(A4_STRONG, len(strong)))
    picked += rng.sample(other, min(A4_ROWS - len(picked), len(other)))
    rng.shuffle(picked)
    return [{k: row[k] for k in ("instruction", "input", "output") if k in row} for row in picked]


SECRET_AND_RUN = """
import os
from kaggle_secrets import UserSecretsClient
os.environ["ANTHROPIC_API_KEY"] = UserSecretsClient().get_secret("ANTHROPIC_API_KEY")
!/tmp/work/trl-venv/bin/python /tmp/work/a4_check.py --kev-dir /tmp/work/kev --data /tmp/work/a4_rows.jsonl --out /kaggle/working/a4
"""

A4_SUMMARY = """
import json
r = json.load(open("/kaggle/working/a4/a4_report.json"))
print("VERDICT:", r.get("verdict"), "|", r.get("error") or "")
print("Generator check:", r.get("generator_check"))
est = r.get("estimate", {})
print("Estimated cost: this run $", est.get("this_run_usd"), "| full B1 fit on 2,000 rows $", est.get("b1_fit_2000_rows_usd"))
f = r.get("fit", {})
for k in ("seconds", "rules", "questions_generated", "answers_shape", "answers_missing", "cost_usd", "cost_per_founder_usd", "seconds_per_founder"):
    print(f"{k}: {f.get(k)}")
print("Rules:", *f.get("rules_list", []), sep="\\n  ")
"""


def a4(rows: list[dict]) -> dict:
    data = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    return notebook([
        md(f"""
# A4: TRL smoke test on Kaggle (trl-for-angels)

Fits TRL's RRF on {len(rows)} sample founders through TRL's real pipeline: **Claude Opus 5.5**
writes the questions (generator) and **Kev-0.6B** on this GPU answers them (answerer). Then
checks `answers()` and `predict_proba()`, and reports the cost per founder plus an estimate for
the full B1 fit. Small settings: `n_prompts=2`, `questions_per_prompt=5` (about $0.15 of
Claude); `beta=0.5`, `random_state=42`.

**Before running:**
1. Settings → **Accelerator: GPU T4** and **Internet: On**.
2. Add-ons → **Secrets**: attach `ANTHROPIC_API_KEY` (your Claude Console key) to this notebook.

**Run:** Run All, about 20–40 minutes. **Afterwards:** download `a4/a4_report.json` from the
Output panel and send it back, or paste the last cell's printout. `a4/trl_cache` keeps the
paid Claude replies.
"""),
        code(SETUP),
        code("%%writefile /tmp/work/a3_check.py\n" + (HERE / "a3_check.py").read_text()),
        code("%%writefile /tmp/work/validate.py\n" +
             (HERE.parent / "research" / "validate.py").read_text()),
        code("%%writefile /tmp/work/a4_check.py\n" + (HERE / "a4_check.py").read_text()),
        code("%%writefile /tmp/work/a4_rows.jsonl\n" + data + "\n"),
        code(SECRET_AND_RUN),
        code(A4_SUMMARY),
    ])


def main() -> None:
    out = HERE / "a3_kev_check.ipynb"
    out.write_text(json.dumps(a3(), indent=1) + "\n")
    print(f"wrote {out}")
    if SAMPLE.exists():
        out = HERE / "a4_rrf_smoke.ipynb"
        out.write_text(json.dumps(a4(a4_rows(SAMPLE)), indent=1) + "\n")
        print(f"wrote {out}")
    else:
        print(f"skipped A4: {SAMPLE.relative_to(HERE.parent)} isn't there yet")


if __name__ == "__main__":
    main()
