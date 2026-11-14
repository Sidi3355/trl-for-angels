#!/usr/bin/env bash
# Two kev.serve processes on localhost, and the front door (proxy.py) on the Space's port.
set -euo pipefail
ANSWERER_MODEL="${ANSWERER_MODEL:-jaredpalmer/kev-0.6b}"
DECIDER_MODEL="${DECIDER_MODEL:-jaredpalmer/kev-0.6b}"
export KEV_DTYPE="${KEV_DTYPE:-fp32}"
env -u KEV_API_KEY python -m kev.serve --run "$ANSWERER_MODEL" --port 8009 --device cpu &
# The decider serves raw probabilities: the app applies its per-question temperatures.
env -u KEV_API_KEY KEV_TEMPERATURE=1.0 python -m kev.serve --run "$DECIDER_MODEL" --port 8010 \
  --device cpu &
exec python -m uvicorn proxy:app --host 0.0.0.0 --port "${PORT:-7860}"
