"""B5: Kev's training and scoring files for C3 (TRL's answers) and C4 (the founder text).

    python research/serialise.py

Reads, per split, the founders from data/splits/{split}.jsonl, and for C3 the answer matrix
data/answers/{split}.csv (an `id` column, then one column per rule with P(yes), in the order
of data/answers/rules.json). Writes Kev JSONL, one labelled request per founder
(MASTER_PLAN section 5):

    data/kev/c3/{split}.jsonl   state = the answers as text, built by TRL's own
                                think_reason_learn.rrf.answers_text (what the decision
                                combiner sends at prediction time)
    data/kev/c4/{split}.jsonl   state = the founder text exactly as TRL renders it for its
                                answerer (think_reason_learn.core._data.to_texts)

Both ask the same question, the one C2/C3 pass as RRF's combiner_question, so training and
prediction see identical text. Each record keeps its founder id in _meta.row_id.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

from think_reason_learn.core._data import to_texts
from think_reason_learn.rrf import answers_text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import POSITIVE, PROD_QUESTIONS, QUESTION, ROOT, SPLITS  # noqa: E402

QUESTION_ID = "success"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def read_answers(path: Path, rules: list[str]) -> dict[str, list[float]]:
    """id -> P(yes) per rule, checking the columns are exactly the rules, in order."""
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if header[0] != "id" or header[1:] != rules:
            raise ValueError(f"{path}: columns must be 'id' then the {len(rules)} rules "
                             "in rules.json order")
        out: dict[str, list[float]] = {}
        for row in reader:
            values = [float(x) if x not in ("", "nan", "NaN") else math.nan for x in row[1:]]
            out[row[0]] = values
    return out


def kev_record(state: str, label: str, row_id: str) -> dict:
    return {
        "state": state,
        "questions": {QUESTION_ID: {"type": "noul", "instructions": QUESTION,
                                    "label": label == POSITIVE}},
        "_meta": {"row_id": row_id},
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                    encoding="utf-8")


def serialise(splits_dir: Path, answers_dir: Path | None, out_dir: Path,
              splits: tuple[str, ...] = SPLITS) -> dict[str, dict[str, int]]:
    """Write the C4 files (always) and C3 files (when answers_dir has the answers).

    Returns record counts per condition and split.
    """
    counts: dict[str, dict[str, int]] = {"c3": {}, "c4": {}}
    rules = None
    if answers_dir is not None and (answers_dir / "rules.json").exists():
        rules = json.loads((answers_dir / "rules.json").read_text(encoding="utf-8"))
        if not isinstance(rules, list) or not all(isinstance(q, str) for q in rules):
            raise ValueError("rules.json must be a JSON list of question strings")
    for split in splits:
        founders = read_jsonl(splits_dir / f"{split}.jsonl")
        texts, _ = to_texts([f["input"] for f in founders])
        c4 = [kev_record(text, f["label"], f["id"]) for f, text in zip(founders, texts)]
        write_jsonl(out_dir / "c4" / f"{split}.jsonl", c4)
        counts["c4"][split] = len(c4)
        if rules is None:
            continue
        answers = read_answers(answers_dir / f"{split}.csv", rules)
        missing = [f["id"] for f in founders if f["id"] not in answers]
        if missing:
            raise ValueError(f"{split}: {len(missing)} founders have no answers, "
                             f"e.g. {missing[:3]}")
        c3 = [kev_record(answers_text(rules, answers[f["id"]]), f["label"], f["id"])
              for f in founders]
        write_jsonl(out_dir / "c3" / f"{split}.jsonl", c3)
        counts["c3"][split] = len(c3)
    return counts


def production(splits_dir: Path, answers_dir: Path, out_dir: Path, input_kind: str,
               splits: tuple[str, ...] = SPLITS) -> dict[str, int]:
    """D3's files: the winning input (c3: TRL's answers; c4: the founder text) with the
    production model's two choice questions, labelled with each founder's outcome and years.
    Writes out_dir/prod/{split}.jsonl."""
    if input_kind not in ("c3", "c4"):
        raise ValueError("input_kind is c3 (TRL's answers) or c4 (the founder text)")
    rules = None
    if input_kind == "c3":
        rules = json.loads((answers_dir / "rules.json").read_text(encoding="utf-8"))
    counts = {}
    for split in splits:
        founders = read_jsonl(splits_dir / f"{split}.jsonl")
        if rules is None:
            states, _ = to_texts([f["input"] for f in founders])
        else:
            answers = read_answers(answers_dir / f"{split}.csv", rules)
            states = [answers_text(rules, answers[f["id"]]) for f in founders]
        records = []
        for f, state in zip(founders, states):
            labels = {"outcome": f["outcome"], "years": f["years"]}
            questions = {}
            for qid, (text, options) in PROD_QUESTIONS.items():
                if labels[qid] not in options:
                    raise ValueError(f"{f['id']}: {qid} {labels[qid]!r} isn't an option")
                questions[qid] = {"type": "choice", "instructions": text,
                                  "criteria": dict(options), "label": labels[qid]}
            records.append({"state": state, "questions": questions,
                            "_meta": {"row_id": f["id"], "input": input_kind}})
        write_jsonl(out_dir / "prod" / f"{split}.jsonl", records)
        counts[split] = len(records)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--splits", type=Path, default=ROOT / "data" / "splits")
    ap.add_argument("--answers", type=Path, default=ROOT / "data" / "answers")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "kev")
    ap.add_argument("--production", choices=("c3", "c4"), default=None,
                    help="write only the production model's files, with this input (D3)")
    args = ap.parse_args(argv)
    if args.production:
        counts = production(args.splits, args.answers, args.out, args.production)
        print("prod (" + args.production + "): "
              + ", ".join(f"{k} {v}" for k, v in counts.items()))
        return 0
    counts = serialise(args.splits, args.answers, args.out)
    for cond, per_split in counts.items():
        if per_split:
            print(f"{cond}: " + ", ".join(f"{s} {n}" for s, n in per_split.items()))
        else:
            print(f"{cond}: skipped (no {args.answers / 'rules.json'} yet)")
    for cond in ("c3", "c4"):
        path = args.out / cond / "train.jsonl"
        if path.exists():
            first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            print(f"\nFirst {cond} train record, to check by eye:\n"
                  f"{json.dumps(first, indent=2, ensure_ascii=False)[:2000]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
