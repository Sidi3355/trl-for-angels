"""Hugging Face hosting for the app: the Kev Space and the production model's repo.

    python research/hf_hub.py space --space-dir hf_space          # create or update the Space
    python research/hf_hub.py upload-model runs/prod/chosen        # publish D3's checkpoint
    python research/hf_hub.py set-decider                          # point the Space at it

Runs where HF_TOKEN is set (the Kaggle runner fetches it from the HF_TOKEN Kaggle Secret);
never prints it. The account is the token's owner (whoami), so no username is configured:
  Space  <user>/trl-for-angels-kev        (Docker, free CPU; see hf_space/README.md)
  model  <user>/trl-for-angels-kev-prod   (the production checkpoint, with temperatures.json)
Both are public: they hold no secrets, and the Space's endpoint itself needs the KEV_API_KEY
the owner sets in the Space's settings. Writes a JSON summary (--report) for the results branch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SPACE = "trl-for-angels-kev"
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
    sp = sub.add_parser("space", help="create or update the Kev Space from hf_space/")
    sp.add_argument("--space-dir", type=Path, required=True)
    up = sub.add_parser("upload-model", help="publish a production checkpoint folder")
    up.add_argument("folder", type=Path)
    up.add_argument("--extra", type=Path, nargs="*", default=[],
                    help="more files to add, e.g. the D3 report")
    sub.add_parser("set-decider", help="point the Space's decider at the model repo")
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args(argv)

    hf = api()
    user = hf.whoami()["name"]
    space_id, model_id = f"{user}/{SPACE}", f"{user}/{MODEL}"
    out: dict = {"user": user, "space": space_id, "model": model_id,
                 "space_url": f"https://huggingface.co/spaces/{space_id}",
                 "endpoint": f"https://{user.lower()}-{SPACE}.hf.space"}
    if args.cmd == "space":
        hf.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True,
                       private=False)
        commit = hf.upload_folder(repo_id=space_id, repo_type="space",
                                  folder_path=str(args.space_dir),
                                  commit_message="Kev answerer and decider (trl-for-angels)")
        out["space_commit"] = getattr(commit, "oid", str(commit))
    elif args.cmd == "upload-model":
        hf.create_repo(model_id, repo_type="model", exist_ok=True, private=False)
        commit = hf.upload_folder(repo_id=model_id, repo_type="model",
                                  folder_path=str(args.folder),
                                  commit_message="Production Kev-0.6B (trl-for-angels, D3)")
        for extra in args.extra:
            if extra.exists():
                hf.upload_file(path_or_fileobj=str(extra), path_in_repo=extra.name,
                               repo_id=model_id, repo_type="model")
        out["model_commit"] = getattr(commit, "oid", str(commit))
    elif args.cmd == "set-decider":
        # Setting a variable restarts the Space, which then loads the new decider.
        hf.add_space_variable(space_id, "DECIDER_MODEL", model_id)
        out["decider_model"] = model_id
    print(json.dumps(out, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        previous = json.loads(args.report.read_text()) if args.report.exists() else {}
        args.report.write_text(json.dumps({**previous, **out}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
