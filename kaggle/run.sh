#!/usr/bin/env bash
# What the Kaggle runner notebook (kaggle/runner.ipynb) runs next.
# Claude edits TASK and pushes; the user just reruns the same notebook (Save & Run All).
# Results land on the kaggle-results branch under runs/<UTC time>-<task>/.
#
# Set by the runner: REPO (this repo, checked out), WORK (/tmp/work: kev/, trl-venv/),
# OUT (folder pushed to GitHub). Secrets arrive as env vars: ANTHROPIC_API_KEY (if attached).
set -uo pipefail

# d_prod (D3): the production model on C3's input (TRL's 40 answers), chosen at D2. Needs data/splits and data/answers. About 2 hours.
TASK="d_prod"

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
  b1b2)
    # B1 fit (C1a, C1b, C2 from one set of Claude questions), then B2 answers and TRL
    # predictions, sharing TRL's cache (kept out of OUT: too big to push).
    "$PY" "$REPO/research/fit_rrf.py" --splits "$REPO/data/splits" --out-root "$OUT" \
      --cache-dir "$WORK/trl_cache" --kev-dir "$WORK/kev" \
    && "$PY" "$REPO/research/answers.py" --splits "$REPO/data/splits" --out-root "$OUT" \
      --cache-dir "$WORK/trl_cache" --kev-dir "$WORK/kev"
    ;;
  c_kev)
    # B5 files, then C3 (GPU 0) and C4 (GPU 1) fine-tuned at the same time, each choosing
    # its checkpoint and temperature on val. Then, per condition that trained: keep it on
    # Hugging Face first (so the weights outlive the run), then score it through TRL. EXTRA
    # needs no training and is scored regardless. One condition failing doesn't stop the
    # other; the run fails at the end if anything did.
    # Needs data/splits, data/answers and data/models from the b1b2 run in the repo.
    KPY="$WORK/kev/.venv/bin/python"
    "$PY" "$REPO/research/serialise.py" --splits "$REPO/data/splits" \
      --answers "$REPO/data/answers" --out "$WORK/kev_data" || exit 1
    mkdir -p "$OUT/kev"
    for spec in c3:0 c4:1; do
      cond=${spec%%:*}; gpu=${spec##*:}
      (cd "$WORK/kev" && CUDA_VISIBLE_DEVICES=$gpu "$KPY" "$REPO/research/train_kev.py" \
        --condition "$cond" --kev-dir "$WORK/kev" --data "$WORK/kev_data" \
        --out "$WORK/runs/$cond" > "$OUT/kev/train_$cond.log" 2>&1) &
    done
    wait
    failed=""
    "$PY" "$REPO/research/kev_predict.py" --condition extra --kev-dir "$WORK/kev" \
      --splits "$REPO/data/splits" --models "$REPO/data/models" --out-root "$OUT" \
      || failed="$failed extra"
    for cond in c4 c3; do
      cp "$WORK/runs/$cond/report.json" "$OUT/kev/${cond}_report.json" 2>/dev/null
      cp "$WORK/runs/$cond/"ep*.log "$OUT/kev/" 2>/dev/null
      if [ ! -d "$WORK/runs/$cond/chosen" ]; then
        echo "no chosen $cond checkpoint: see kev/train_$cond.log" >&2
        failed="$failed $cond"; continue
      fi
      # Keep C3 and C4 for the interp steps (F2, F3): too big for GitHub, so Hugging Face.
      if [ -n "${HF_TOKEN:-}" ]; then
        "$WORK/kev/.venv/bin/python" "$REPO/research/hf_hub.py" --report "$OUT/hf.json" \
          upload-model "$WORK/runs/$cond/chosen" --name "trl-for-angels-kev-$cond" \
          --extra "$WORK/runs/$cond/report.json" \
          || echo "upload of $cond failed (it is still scored below)" >&2
      else
        echo "HF_TOKEN not attached: $cond was not kept" >&2
      fi
      "$PY" "$REPO/research/kev_predict.py" --condition "$cond" \
        --run "$WORK/runs/$cond/chosen" --kev-dir "$WORK/kev" --splits "$REPO/data/splits" \
        --models "$REPO/data/models" --out-root "$OUT" || failed="$failed $cond"
    done
    if [ -n "$failed" ]; then echo "failed:$failed" >&2; exit 1; fi
    ;;
  d_prod)
    # D3: the production model on the input chosen on val at D2 (PROD_INPUT: c3 or c4),
    # with the outcome and years choice questions and a temperature per question; then its
    # calibrated distributions on val for the D4 threshold table.
    PROD_INPUT="c3"  # D2 (2026-11-14): C3 and C4 tied on val; C3 chosen (results/DECISIONS.md)
    KPY="$WORK/kev/.venv/bin/python"
    "$PY" "$REPO/research/serialise.py" --splits "$REPO/data/splits" \
      --answers "$REPO/data/answers" --out "$WORK/kev_data" --production "$PROD_INPUT" || exit 1
    long=""; [ "$PROD_INPUT" = c3 ] && long="--long-states"
    mkdir -p "$OUT/kev"
    (cd "$WORK/kev" && CUDA_VISIBLE_DEVICES=0 "$KPY" "$REPO/research/train_kev.py" \
      --condition prod $long --kev-dir "$WORK/kev" --data "$WORK/kev_data" \
      --out "$WORK/runs/prod" > "$OUT/kev/train_prod.log" 2>&1) || exit 1
    cp "$WORK/runs/prod/report.json" "$OUT/kev/prod_report.json"
    cp "$WORK/runs/prod/chosen/temperatures.json" "$OUT/kev/prod_temperatures.json"
    # Where export_artifacts.py reads them (data/models/prod/), via kaggle/import_run.py.
    mkdir -p "$OUT/data/models/prod"
    cp "$WORK/runs/prod/report.json" "$WORK/runs/prod/chosen/temperatures.json" \
      "$OUT/data/models/prod/"
    # Publish the production model to a free Hugging Face model repo, for kev_server/.
    if [ -n "${HF_TOKEN:-}" ]; then
      "$WORK/kev/.venv/bin/python" "$REPO/research/hf_hub.py" --report "$OUT/hf.json" \
        upload-model "$WORK/runs/prod/chosen" --extra "$WORK/runs/prod/report.json"
    else
      echo "HF_TOKEN not attached: the production model was not published" >&2
    fi
    "$PY" "$REPO/research/kev_predict.py" --condition prod --run "$WORK/runs/prod/chosen" \
      --kev-dir "$WORK/kev" --prod-data "$WORK/kev_data/prod" --out-root "$OUT" \
      --gpus 0,0 --predict-splits val || exit 1
    ;;
  *)
    echo "unknown TASK $TASK" >&2
    exit 2
    ;;
esac
