"""Export the research results as the app's three artefacts, in the app contract's format.

    python research/export_artifacts.py --prod-input c3 --endpoint https://<kev host>

The app (app-track) loads exactly three files from ARTIFACTS_DIR, each checked against a JSON
Schema in app/contract/artifacts/:
  rules.json        the questions, in the order every answer matrix uses (C2's rules_), with
                    C1a's elastic-net weight where C1a kept the rule
  thresholds.json   D4's precision/recall table per target outcome and timeline, from val
  model.json        the production model (D3): endpoint, its two choice questions, the
                    per-question temperatures (applied by the client: the server runs raw),
                    the answerer, and how answers become its input text
This script builds them from the research outputs and validates each against the schemas
before writing, so the app can't load a file that doesn't fit its contract.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thresholds as th  # noqa: E402
from common import GENERATOR, PROD_QUESTIONS, ROOT, RRF_SETTINGS, TASK  # noqa: E402

SCHEMA_VERSION = "0.1.0"
GRID = [round(x, 2) for x in np.arange(0.0, 0.99001, 0.01)]  # the contract's grid
TIMELINE_YEARS = {"any": None, "5 years": 5, "8 years": 8}
KEV_RESPONSE = (
    'kev.serve /v1/systemone returns {"answers": {"outcome": {"type": "choice", "choice": '
    '"<option>", "confidence": <c>, "probabilities": {"<option>": <p>, ...}}, "years": '
    '{...}}, "usage": {...}}. The server runs raw (KEV_TEMPERATURE=1.0); apply each '
    "question's temperature as p^(1/T), renormalised (research/common.apply_temperature).")


def now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def kev_spec(url: str) -> str:
    return (f'LLM("kev-0.6b", base_url="{url.rstrip("/")}/v1/systemone", kind="decision") '
            "(TRL; jaredpalmer/kev-0.6b, served in fp32)")


def rules_doc(answers_dir: Path, models_dir: Path, answerer_url: str, trl_commit: str,
              n_train: int | None) -> dict:
    from think_reason_learn.rrf import RRF

    rules = json.loads((answers_dir / "rules.json").read_text())
    c1a = RRF.load(models_dir / "c1a")
    coefs = {}
    if c1a.combiner_ is not None:
        coefs = {q: float(c) for q, c in zip(c1a.rules_, c1a.combiner_.coef)}
    return {
        "schema_version": SCHEMA_VERSION, "mock": False,
        "source": {"trl_version": "0.3.0", "trl_commit": trl_commit, "generator": GENERATOR,
                   "answerer": kev_spec(answerer_url),
                   "rrf_params": {**RRF_SETTINGS, "combiner": "decision (C2's rules_: every "
                                  "question, best F0.5 first)"},
                   "created_at": now(), "n_train": n_train},
        "task": TASK,
        "rules": [{"id": f"r{i + 1:03d}", "index": i, "question": q,
                   "elastic_net_coef": coefs.get(q)} for i, q in enumerate(rules)],
    }


def thresholds_doc(prod_val: Path, model_id: str) -> dict:
    d = th.load(prod_val)
    tables = []
    for target in th.TARGETS:
        for timeline, years in TIMELINE_YEARS.items():
            p, y = th.scores_and_labels(d, target, timeline)
            rows = []
            for t in GRID:
                flagged = p >= t - 1e-9
                n_flagged, tp = int(flagged.sum()), int((flagged & y).sum())
                rows.append({"threshold": t, "n_flagged": n_flagged, "tp": tp,
                             "precision": tp / n_flagged if n_flagged else 0.0,
                             "recall": tp / int(y.sum()) if y.sum() else 0.0})
            tables.append({"target": target, "timeline_years": years, "n": len(p),
                           "n_positive": int(y.sum()), "base_rate": float(y.mean()),
                           "rows": rows})
    return {
        "schema_version": SCHEMA_VERSION, "mock": False,
        "source": {"split": "val", "n": len(d["id"]), "model_id": model_id, "created_at": now(),
                   "note": "Production model's calibrated distributions on val (D4). Timeline "
                           "probabilities assume outcome and years are independent: estimates. "
                           "Precision is 0 where nothing is flagged."},
        "score": "p_outcome_at_or_above_target * p_years_within_timeline",
        "label": "true_outcome_at_or_above_target AND true_years_within_timeline",
        "grid": {"start": GRID[0], "stop": GRID[-1], "step": 0.01},
        "tables": tables,
    }


def model_doc(prod_dir: Path, prod_input: str, endpoint: str, model_id: str,
              answerer_url: str, auth: str) -> dict:
    temps = json.loads((prod_dir / "temperatures.json").read_text())["per_question"]
    report_path = prod_dir / "report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    doc = {
        "schema_version": SCHEMA_VERSION, "mock": False, "model_id": model_id,
        "created_at": now(),
        "endpoint": {"base_url": endpoint.rstrip("/"), "path": "/v1/systemone",
                     "auth": {"type": auth} if auth == "none" else
                     {"type": auth, "env_var": "KEV_API_KEY"}, "timeout_s": 60},
        "decider_input": "answers" if prod_input == "c3" else "profile",
        "request": {"questions": {qid: {"type": "choice", "instructions": text,
                                        "criteria": dict(options)}
                                  for qid, (text, options) in PROD_QUESTIONS.items()},
                    "response_format": KEV_RESPONSE},
        "temperature": {"applied_by": "client", "outcome": temps["outcome"],
                        "years": temps["years"]},
        "answerer": {"spec": kev_spec(answerer_url), "via": "trl"},
        "validation": {"split": "val", "chosen_checkpoint": report.get("chosen"),
                       "val_raw": report.get("val_raw", {}).get(report.get("chosen", ""), {}),
                       "val_calibrated": report.get("val_calibrated", {})},
    }
    if prod_input == "c3":
        doc["answer_serialisation"] = {"format": "binary", "threshold": 0.5,
                                       "line_template": "{question} {answer}",
                                       "separator": "\n", "order": "rules.json"}
    return doc


def validate(doc: dict, schema_path: Path) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads(schema_path.read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: e.path)
    if errors:
        raise ValueError(f"{schema_path.name}: " + "; ".join(
            f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors[:5]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prod-input", choices=("c3", "c4"), required=True,
                    help="D2's choice: c3 (TRL's answers) or c4 (the founder text)")
    ap.add_argument("--endpoint", required=True, help="where the production Kev is served")
    ap.add_argument("--auth", choices=("none", "bearer"), default="none")
    ap.add_argument("--answerer-url", default="http://127.0.0.1:8009",
                    help="where base Kev, the answerer, is served")
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--answers", type=Path, default=ROOT / "data" / "answers")
    ap.add_argument("--models", type=Path, default=ROOT / "data" / "models")
    ap.add_argument("--prod-dir", type=Path, default=ROOT / "data" / "models" / "prod",
                    help="temperatures.json and report.json from the D3 run")
    ap.add_argument("--prod-val", type=Path,
                    default=ROOT / "data" / "predictions" / "prod_val.csv")
    ap.add_argument("--contract", type=Path, default=ROOT / "app" / "contract" / "artifacts")
    ap.add_argument("--out", type=Path, default=ROOT / "shared" / "artifacts")
    ap.add_argument("--trl-commit", default="ddf3518")
    args = ap.parse_args(argv)

    model_id = args.model_id or f"kev-0.6b-prod-{args.prod_input}"
    n_train = None
    train = ROOT / "data" / "splits" / "train.jsonl"
    if train.exists():
        n_train = sum(1 for line in train.read_text().splitlines() if line.strip())
    docs = {
        "rules": rules_doc(args.answers, args.models, args.answerer_url, args.trl_commit,
                           n_train),
        "thresholds": thresholds_doc(args.prod_val, model_id),
        "model": model_doc(args.prod_dir, args.prod_input, args.endpoint, model_id,
                           args.answerer_url, args.auth),
    }
    for name, doc in docs.items():
        validate(doc, args.contract / f"{name}.schema.json")
    args.out.mkdir(parents=True, exist_ok=True)
    for name, doc in docs.items():
        (args.out / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {', '.join(f'{n}.json' for n in docs)} to {args.out}; all match the contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
