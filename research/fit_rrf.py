"""B1: fit RRF on train, four ways, from one set of generated questions.

    python research/fit_rrf.py --kev-dir ../kev --out-root OUT --cache-dir OUT/trl_cache

Serves base Kev-0.6B (the answerer for every condition) and fits, through TRL's real fit():
  C1a     combiner="elasticnet" (the library default), every question
  C1a-40  combiner="elasticnet", max_rules=40: the 40 questions Kev reads (matched control)
  C1b     combiner="vote" (the paper's)
  C2      combiner="decision", max_rules=40, base Kev as the decision model (zero-shot)
All use the same settings and seed, so TRL's disk cache gives every fit exactly C1a's
questions and answers; the script checks that, and that C1a-40's rules are among C2's (both
take TRL's top 40 by F0.5). Writes, under --out-root:
  data/models/{c1a,c1a40,c1b,c2}/model.json   RRF.save (no API keys)
  data/answers/rules.json               C2's rules_: the 40 questions Kev reads, best F0.5
                                        first; the column order of every answer matrix (B2)
  data/answers/questions.csv            each question's precision, recall and F0.5 on train
  data/answers/fit_report.json          cost estimate, usage per fit, timings, checks
Needs ANTHROPIC_API_KEY (Claude writes the questions), unless --fake-generator.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    KEV_BASE,
    DECISION_MAX_RULES,
    QUESTION,
    ROOT,
    RRF_SETTINGS,
    TASK,
    fake_writer,
    generator_llm,
    kev_llm,
    kev_server,
    load_split,
    usage_rows,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--splits", type=Path, default=ROOT / "data" / "splits")
    ap.add_argument("--out-root", type=Path, default=ROOT)
    ap.add_argument("--cache-dir", type=Path, required=True,
                    help="TRL's disk cache; answers.py must use the same one")
    ap.add_argument("--kev-dir", type=Path, default=ROOT.parent / "kev")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--port", type=int, default=8009)
    ap.add_argument("--fake-generator", action="store_true", help="offline tests only")
    ap.add_argument("--n-prompts", type=int, default=None, help="tests only; default: TRL's")
    ap.add_argument("--questions-per-prompt", type=int, default=None, help="tests only")
    ap.add_argument("--max-rules", type=int, default=DECISION_MAX_RULES,
                    help=f"questions Kev reads (default {DECISION_MAX_RULES}); change for tests only")
    args = ap.parse_args(argv)

    from think_reason_learn.llm import set_config
    from think_reason_learn.rrf import RRF

    set_config(cache_dir=args.cache_dir)
    models_dir = args.out_root / "data" / "models"
    answers_dir = args.out_root / "data" / "answers"
    answers_dir.mkdir(parents=True, exist_ok=True)
    overrides = {k: v for k, v in (("n_prompts", args.n_prompts),
                                   ("questions_per_prompt", args.questions_per_prompt))
                 if v is not None}
    report: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "kev": KEV_BASE,
                    "settings": {**RRF_SETTINGS, **overrides},
                    "max_rules": {"c1a40": args.max_rules, "c2": args.max_rules},
                    "fake_generator":
                    args.fake_generator, "fits": {}}

    def save_report() -> None:
        (answers_dir / "fit_report.json").write_text(json.dumps(report, indent=2, default=str))

    _, X, y = load_split(args.splits, "train")
    report["train"] = {"rows": len(X), "successful": y.count("successful")}
    with fake_writer(args.fake_generator), kev_server(
            args.kev_dir, port=args.port, device=args.device,
            log=args.out_root / "logs" / "kev_answerer.log") as url:
        kev = kev_llm(url)
        base = {"task": TASK, "generator": generator_llm(args.fake_generator),
                "answerer": kev, **RRF_SETTINGS, **overrides}
        conditions = {
            "c1a": {"combiner": "elasticnet"},
            "c1a40": {"combiner": "elasticnet", "max_rules": args.max_rules},
            "c1b": {"combiner": "vote"},
            "c2": {"combiner": "decision", "combiner_model": kev,
                   "combiner_question": QUESTION, "max_rules": args.max_rules},
        }
        report["estimate_c1a"] = usage_rows(RRF(**base).estimate_cost(X, y))
        save_report()
        fitted = {}
        for name, extra in conditions.items():
            t0 = time.time()
            model = RRF(**base, **extra).fit(X, y)
            model.save(models_dir / name)
            fitted[name] = model
            report["fits"][name] = {
                "seconds": round(time.time() - t0, 1),
                "rules": len(model.rules_),
                "questions": len(model.questions_),
                "threshold": model.threshold_,
                "usage": usage_rows(model.usage_),
                "cost_usd": round(model.usage_.cost_usd, 4),
            }
            print(f"{name}: {len(model.rules_)} rules of {len(model.questions_)} questions, "
                  f"{report['fits'][name]['seconds']} s, ${model.usage_.cost_usd:.4f}",
                  flush=True)
            save_report()

    # One set of questions for every condition (TRL's cache made the others reuse C1a's).
    questions = {n: list(m.questions_["question"]) for n, m in fitted.items()}
    same = all(q == questions["c1a"] for q in questions.values())
    c2 = fitted["c2"]
    # C1a-40 and C2 rank with the same TRL function, so C1a-40's rules are among C2's 40.
    matched = set(fitted["c1a40"].rules_) <= set(c2.rules_)
    report["checks"] = {"same_questions_all_conditions": same,
                        "c1a40_rules_within_c2_rules": matched,
                        "c2_rules": len(c2.rules_)}
    (answers_dir / "rules.json").write_text(json.dumps(list(c2.rules_), indent=2))
    c2.questions_.to_csv(answers_dir / "questions.csv", index=False)
    report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_report()
    if not same:
        print("CHECK FAILED: the conditions got different questions", flush=True)
        return 1
    if not matched:
        print("CHECK FAILED: C1a-40 has rules outside C2's 40", flush=True)
        return 1
    print(f"OK: {len(c2.rules_)} rules in rules.json; models in {models_dir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
