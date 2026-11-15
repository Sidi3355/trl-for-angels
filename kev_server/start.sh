#!/usr/bin/env bash
# For Docker or Linux/macOS shells; serve.py does the work (and is what Windows runs).
exec python "$(dirname "$0")/serve.py"
