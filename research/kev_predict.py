"""B6 and C3/C4 scoring: Kev's predictions on val and test, all through TRL.

    python research/kev_predict.py --condition extra --kev-dir <kev>
    python research/kev_predict.py --condition c4 --run runs/c4/chosen --kev-dir <kev>
    python research/kev_predict.py --condition c3 --run runs/c3/chosen --kev-dir <kev>

  extra  base Kev-0.6B reads the founder text as TRL renders it (to_texts) and answers the
         research question (zero-shot)
  c4     the fine-tuned C4 checkpoint, the same way
  c3     TRL's decision combiner: the saved C2 RRF (data/models/c2) with combiner_model set to
         the fine-tuned C3 checkpoint, so base Kev answers the rules and C3 decides, through
         RRF.predict_proba exactly as C2 does
Every call goes through TRL's LLMSession. Writes data/predictions/kev_<condition>_<split>.csv
with the same columns as TRL's predictions. On a Kaggle T4 pair, base Kev (the answerer)
serves on GPU 0 and the checkpoint being scored on GPU 1.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KEV_BASE, POSITIVE, QUESTION, ROOT, kev_llm, kev_server, load_split  # noqa: E402


def direct_scores(url: str, name: str, texts: list[str]) -> list[float]:
    """Kev's P(yes) to the research question about each founder text, through LLMSession."""
    from think_reason_learn.core._data import to_texts
    from think_reason_learn.llm import LLMSession, YesNoQuestion
    from think_reason_learn.llm._loop import run_sync
    from think_reason_learn.llm._spec import resolve

    rendered, _ = to_texts(texts)  # exactly what TRL sends its answerer
    endpoint = resolve(kev_llm(url, name))

    async def ask():
        return await LLMSession().answer([endpoint], rendered,
                                         {"success": YesNoQuestion(QUESTION)}, role="decider")

    replies = run_sync(ask())
    return [r["success"].probability() if r["success"] is not None else float("nan")
            for r in replies]


def write(path: Path, split: str, condition: str, ids, labels, scores) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "split", "condition", "label", "p_success", "trl_decision"])
        for rid, label, p in zip(ids, labels, scores):
            w.writerow([rid, split, condition, label, f"{p:.6g}", ""])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--condition", choices=("extra", "c3", "c4"), required=True)
    ap.add_argument("--run", default=None, help="checkpoint to score (c3, c4)")
    ap.add_argument("--kev-dir", type=Path, default=ROOT.parent / "kev")
    ap.add_argument("--splits", type=Path, default=ROOT / "data" / "splits")
    ap.add_argument("--out-root", type=Path, default=ROOT)
    ap.add_argument("--models", type=Path, default=None, help="default: <out-root>/data/models")
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--gpus", default="0,1", help="answerer GPU, scored checkpoint GPU")
    ap.add_argument("--port", type=int, default=8010, help="port for the scored checkpoint")
    ap.add_argument("--predict-splits", default="val,test")
    args = ap.parse_args(argv)
    if args.condition in ("c3", "c4") and not args.run:
        ap.error(f"--run is needed for {args.condition}")

    from think_reason_learn.llm import set_config
    from think_reason_learn.rrf import RRF

    if args.cache_dir:
        set_config(cache_dir=args.cache_dir)
    gpu_answerer, gpu_scored = (args.gpus.split(",") + [None, None])[:2]
    if args.device != "cuda":
        gpu_answerer = gpu_scored = None
    run = args.run or KEV_BASE
    name = f"kev-{args.condition}"  # its own name, so TRL's cache never mixes checkpoints
    logs = args.out_root / "logs"
    with ExitStack() as stack:
        url = stack.enter_context(kev_server(args.kev_dir, run=run, port=args.port,
                                             device=args.device, gpu=gpu_scored,
                                             log=logs / f"kev_{args.condition}.log"))
        model = None
        if args.condition == "c3":
            model = RRF.load((args.models or args.out_root / "data" / "models") / "c2")
            port = urlparse(model.answerer.base_url).port or 8009
            stack.enter_context(kev_server(args.kev_dir, port=port, device=args.device,
                                           gpu=gpu_answerer, log=logs / "kev_answerer_c3.log"))
            model.set_params(combiner_model=kev_llm(url, name))
        for split in args.predict_splits.split(","):
            ids, X, y = load_split(args.splits, split)
            t0 = time.time()
            if model is not None:
                pos = list(model.classes_).index(POSITIVE)
                scores = list(model.predict_proba(X)[:, pos])
            else:
                scores = direct_scores(url, name, X)
            write(args.out_root / "data" / "predictions" / f"kev_{args.condition}_{split}.csv",
                  split, args.condition, ids, y, scores)
            print(f"{args.condition} {split}: {len(ids)} founders, {time.time() - t0:.0f} s",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
