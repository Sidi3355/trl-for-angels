"""Publish a fine-tuned Kev checkpoint to a free Hugging Face model repo.

    python research/hf_hub.py upload-model runs/prod/chosen --extra runs/prod/report.json
    python research/hf_hub.py upload-model runs/c3/chosen --name trl-for-angels-kev-c3

Runs where HF_TOKEN is set (the Kaggle runner fetches it from the HF_TOKEN Kaggle Secret);
never prints it. The repo is <token owner>/<name>, public: it holds no secrets. The default
name, trl-for-angels-kev-prod, is the production model; C3 and C4 are kept as
trl-for-angels-kev-c3 and -c4 for the interp steps (F2, F3). The Kev server (kev_server/)
loads the production model with DECIDER_MODEL. Hugging Face Spaces that run code need a paid
PRO plan, so the server runs on the owner's PC instead (kev_server/README.md).
Writes a JSON summary (--report) for the results branch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MODEL = "trl-for-angels-kev-prod"


def api():
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN isn't set: attach the HF_TOKEN Kaggle Secret")
    return HfApi(token=token)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("upload-model", help="publish a production checkpoint folder")
    up.add_argument("folder", type=Path)
    up.add_argument("--extra", type=Path, nargs="*", default=[],
                    help="more files to add, e.g. the D3 report")
    up.add_argument("--name", default=MODEL, help=f"repo name (default {MODEL})")
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args(argv)

    hf = api()
    user = hf.whoami()["name"]
    model_id = f"{user}/{args.name}"
    out: dict = {"user": user, "model": model_id,
                 "model_url": f"https://huggingface.co/{model_id}"}
    hf.create_repo(model_id, repo_type="model", exist_ok=True, private=False)
    commit = hf.upload_folder(repo_id=model_id, repo_type="model",
                              folder_path=str(args.folder),
                              commit_message=f"Kev-0.6B fine-tune: {args.name}")
    for extra in args.extra:
        if extra.exists():
            hf.upload_file(path_or_fileobj=str(extra), path_in_repo=extra.name,
                           repo_id=model_id, repo_type="model")
    out["model_commit"] = getattr(commit, "oid", str(commit))
    print(json.dumps(out, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        previous = json.loads(args.report.read_text()) if args.report.exists() else {}
        args.report.write_text(json.dumps({**previous, args.name: out}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
