"""Copy a Kaggle run's data outputs from the kaggle-results branch into this repo's data/.

    python kaggle/import_run.py runs/20261114-160701-b1b2 [--dry-run]

A run pushes everything it wrote under OUT to runs/<id>/ on the kaggle-results branch
(kaggle/runner_main.sh). The next steps read data/answers, data/models and data/predictions
from the repo, so this copies runs/<id>/data/... to data/..., byte for byte, and lists each
file. A file that already exists with different contents is replaced only with --replace,
so an earlier run's outputs are never overwritten by accident. Logs and reports stay on the
results branch; they're linked from results/DECISIONS.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "origin/kaggle-results"


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True).stdout


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", help="runs/<id> on the kaggle-results branch")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true",
                    help="replace existing files whose contents differ")
    args = ap.parse_args(argv)

    git("fetch", "-q", "origin", "kaggle-results")
    run = args.run.rstrip("/")
    prefix = f"{run}/data/"
    files = [f for f in git("ls-tree", "-r", "--name-only", BRANCH, prefix).decode().splitlines()
             if f.startswith(prefix)]
    if not files:
        print(f"no data/ files under {run} on {BRANCH}", file=sys.stderr)
        return 1
    conflicts = 0
    for f in files:
        dest = ROOT / "data" / f[len(prefix):]
        blob = git("show", f"{BRANCH}:{f}")
        state = "new"
        if dest.exists():
            state = "same" if dest.read_bytes() == blob else "differs"
        if state == "differs" and not args.replace:
            conflicts += 1
            print(f"SKIP (differs; --replace to overwrite): {dest.relative_to(ROOT)}")
            continue
        print(f"{state:8} {dest.relative_to(ROOT)} ({len(blob):,} bytes)")
        if not args.dry_run and state != "same":
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
