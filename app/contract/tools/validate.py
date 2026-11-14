"""Validate the contract's mocks and examples (or real artefacts) against the schemas, plus the
cross-file rules a schema can't express.

    python app/contract/tools/validate.py                         # mocks + examples
    python app/contract/tools/validate.py --artifacts shared/artifacts   # real artefacts too

Needs app/contract/requirements.txt. Exits non-zero if anything fails. Uses the backend's own
template, policy and contract modules (app/backend/screener), so it checks what the service does.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent
sys.path.insert(0, str(CONTRACT.parent / "backend"))

from screener import policy  # noqa: E402
from screener.contract import Contract  # noqa: E402
from screener.template import TemplateError, consistency_issues, parse, render, unknown_paths  # noqa: E402

SCHEMAS = CONTRACT / "schemas"
ARTIFACT_SCHEMAS = CONTRACT / "artifacts"
CONTRACT_SCHEMAS = Contract(CONTRACT)
FAILURES: list[str] = []


def fail(where: str, msg: str) -> None:
    FAILURES.append(f"{where}: {msg}")


def check_schema(where: str, doc, schema_path: Path) -> None:
    for err in CONTRACT_SCHEMAS.errors(schema_path.name.removesuffix(".schema.json"), doc):
        fail(where, err)


def close(a: float, b: float, tol: float = 1e-3) -> bool:
    return math.isclose(a, b, abs_tol=tol)


# ------------------------------------------------------------------- cross-file checks

def check_rules(where: str, rules: dict) -> None:
    ids = [r["id"] for r in rules["rules"]]
    if len(set(ids)) != len(ids):
        fail(where, "rule ids are not unique")
    for pos, r in enumerate(rules["rules"]):
        if r["index"] != pos:
            fail(where, f"rule {r['id']} has index {r['index']} at position {pos}")


def check_thresholds(where: str, th: dict) -> None:
    pairs = {(t["target"], t["timeline_years"]) for t in th["tables"]}
    want = {(t, tl) for t in policy.TARGETS for tl in policy.TIMELINES}
    if pairs != want:
        fail(where, f"tables must cover every target and timeline once; missing {want - pairs}")
    g = th["grid"]
    n_grid = round((g["stop"] - g["start"]) / g["step"]) + 1
    for t in th["tables"]:
        name = f"{t['target']}/{t['timeline_years']}"
        rows = t["rows"]
        if len(rows) != n_grid:
            fail(where, f"{name}: {len(rows)} rows, grid implies {n_grid}")
        if [r["threshold"] for r in rows] != sorted(r["threshold"] for r in rows):
            fail(where, f"{name}: thresholds not ascending")
        if not close(t["base_rate"], t["n_positive"] / t["n"]):
            fail(where, f"{name}: base_rate != n_positive / n")
        prev = None
        for r in rows:
            if r["tp"] > r["n_flagged"] or r["tp"] > t["n_positive"]:
                fail(where, f"{name} @ {r['threshold']}: tp too large")
            if r["n_flagged"] and not close(r["precision"], r["tp"] / r["n_flagged"]):
                fail(where, f"{name} @ {r['threshold']}: precision != tp / n_flagged")
            if t["n_positive"] and not close(r["recall"], r["tp"] / t["n_positive"]):
                fail(where, f"{name} @ {r['threshold']}: recall != tp / n_positive")
            if prev is not None and r["n_flagged"] > prev:
                fail(where, f"{name} @ {r['threshold']}: n_flagged rises with the threshold")
            prev = r["n_flagged"]


def check_distributions(where: str, d: dict) -> None:
    for q in ("outcome", "years"):
        if not close(sum(d[q].values()), 1.0, 1e-4):
            fail(where, f"{q} distribution sums to {sum(d[q].values())}")


def check_memo(where: str, memo: dict, rules: dict, th: dict, model: dict) -> None:
    check_distributions(where, memo["distributions"])
    values = {k: v["value"] for k, v in memo["fields"].items()}

    # The rendered profile is the frozen template, rendered from exactly these fields.
    try:
        parsed = parse(memo["rendered_profile"])
    except TemplateError as e:
        fail(where, f"rendered_profile breaks the template: {e}")
    else:
        if render(parsed) != memo["rendered_profile"]:
            fail(where, "rendered_profile doesn't round-trip through the template parser")
    if render(values) != memo["rendered_profile"]:
        fail(where, "rendered_profile doesn't match the merged fields")
    for issue in consistency_issues(values):
        fail(where, f"profile consistency: {issue}")
    if sorted(memo["unknowns"]) != sorted(unknown_paths(values)):
        fail(where, f"unknowns {memo['unknowns']} != {unknown_paths(values)}")

    # Every source reference resolves; model inputs only use pre-founding sources.
    sources = {s["id"]: s for s in memo["sources"]}
    refs = [(k, sid) for k, v in memo["fields"].items() for sid in v["source_ids"]]
    refs += [("founding_date", sid) for sid in memo["founder"]["founding_date"]["source_ids"]]
    refs += [(f"conflict:{c['field']}", sid) for c in memo["conflicts"] for sid in c["agent_source_ids"]]
    for k, sid in refs:
        if sid not in sources:
            fail(where, f"{k} cites missing source {sid}")
        elif not k.startswith("conflict") and sources[sid]["before_founding"] is False:
            fail(where, f"{k} cites post-founding source {sid}: post-founding facts must stay in notes")
    for note in memo["notes"]["post_founding"]:
        for sid in note["source_ids"]:
            if sid not in sources:
                fail(where, f"post-founding note cites missing source {sid}")

    # Conflicts: the investor value is the one used.
    for c in memo["conflicts"]:
        f = memo["fields"].get(c["field"])
        if f and (f["value"] != c["investor_value"] or f["provenance"] not in ("investor", "investor_voice")):
            fail(where, f"conflict on {c['field']}: the field doesn't hold the investor value")

    # Verdict matches the distributions, thresholds.json and the policy rule.
    v = memo["verdict"]
    expect = policy.verdict(memo["distributions"], th, v["policy"], values)
    for key in ("decision", "probability", "probability_is_estimate", "expected_precision", "expected_recall",
                "missed_winners_if_pass", "filters_failed"):
        if expect[key] != v[key]:
            fail(where, f"verdict.{key} = {v[key]!r}, policy gives {expect[key]!r}")
    for key in ("advance_threshold", "pass_threshold"):
        if expect["policy"][key] != v["policy"][key]:
            fail(where, f"verdict.policy.{key} = {v['policy'][key]!r}, thresholds.json gives {expect['policy'][key]!r}")
    if memo["facets"] != policy.facets(values):
        fail(where, f"facets {memo['facets']} != {policy.facets(values)}")

    # Decider and answers agree with model.json and rules.json.
    if memo["decider"]["input_type"] != model["decider_input"]:
        fail(where, "decider.input_type differs from model.json")
    if model["decider_input"] == "answers":
        if memo["answers"] is None or [a["rule_id"] for a in memo["answers"]] != [r["id"] for r in rules["rules"]]:
            fail(where, "answers must list every rule in rules.json order")
        else:
            cut = model["answer_serialisation"].get("threshold", 0.5)
            for a in memo["answers"]:
                if model["answer_serialisation"]["format"] == "binary" and a["answer"] != ("yes" if a["p_yes"] >= cut else "no"):
                    fail(where, f"answer {a['rule_id']} doesn't match its p_yes at threshold {cut}")
    elif memo["answers"] is not None:
        fail(where, "answers must be null in profile mode")

    # Drivers: flipped distributions and deltas are consistent and sorted.
    base = policy.score(memo["distributions"], v["policy"]["target"], v["policy"]["timeline_years"])
    for d in memo["drivers"]:
        check_distributions(f"{where} driver {d['id']}", d["distributions"])
        got = policy.score(d["distributions"], v["policy"]["target"], v["policy"]["timeline_years"]) - base
        if not close(got, d["delta"]):
            fail(where, f"driver {d['id']}: delta {d['delta']} != {got:.4f}")
    deltas = [abs(d["delta"]) for d in memo["drivers"]]
    if deltas != sorted(deltas, reverse=True):
        fail(where, "drivers are not sorted by |delta|")


# ------------------------------------------------------------------------------- main

def load(path: Path):
    return json.loads(path.read_text())


def run(artifacts_dir: Path, examples: bool) -> None:
    where = str(artifacts_dir)
    rules = load(artifacts_dir / "rules.json")
    th = load(artifacts_dir / "thresholds.json")
    model = load(artifacts_dir / "model.json")
    check_schema(f"{where}/rules.json", rules, ARTIFACT_SCHEMAS / "rules.schema.json")
    check_schema(f"{where}/thresholds.json", th, ARTIFACT_SCHEMAS / "thresholds.schema.json")
    check_schema(f"{where}/model.json", model, ARTIFACT_SCHEMAS / "model.schema.json")
    check_rules(f"{where}/rules.json", rules)
    check_thresholds(f"{where}/thresholds.json", th)
    if FAILURES or not examples:
        return

    memos = load(artifacts_dir / "mock_memo.json")
    for i, memo in enumerate(memos):
        w = f"mock_memo.json[{i}] ({memo.get('memo_id')})"
        check_schema(w, memo, SCHEMAS / "memo.schema.json")
        if not FAILURES:
            check_memo(w, memo, rules, th, model)

    ex = CONTRACT / "examples"
    for path in sorted(ex.glob("investor_input_*.json")):
        check_schema(path.name, load(path), SCHEMAS / "investor_input.schema.json")
    for name, schema in [("screening_job.json", "screening_job"), ("what_if_request.json", "what_if_request"),
                         ("what_if_response.json", "what_if_response"), ("batch_request.json", "batch_request"),
                         ("batch_response.json", "batch_response"), ("push_key.json", "push_key"),
                         ("push_watch_request.json", "push_watch_request"), ("push_watch_response.json", "push_watch_response"),
                         ("note_transcript.json", "note_transcript"), ("note_sort_request.json", "note_sort_request"),
                         ("note_sort_response.json", "note_sort_response")]:
        check_schema(name, load(ex / name), SCHEMAS / f"{schema}.schema.json")
    seqs = []
    for n, line in enumerate((ex / "progress_events.jsonl").read_text().splitlines()):
        ev = json.loads(line)
        check_schema(f"progress_events.jsonl:{n + 1}", ev, SCHEMAS / "progress_event.schema.json")
        seqs.append(ev["seq"])
    if seqs != sorted(set(seqs)):
        fail("progress_events.jsonl", "seq must be strictly increasing")
    wi = load(ex / "what_if_response.json")
    check_distributions("what_if_response.json", wi["distributions"])
    b = load(ex / "batch_response.json")
    for it in b["items"]:
        memo = next((m for m in memos if m["memo_id"] == it["memo_id"]), None)
        if memo and (it["decision"], it["probability"]) != (memo["verdict"]["decision"], memo["verdict"]["probability"]):
            fail("batch_response.json", f"item {it['index']} disagrees with its memo")


def check_template_example() -> None:
    """The plan's own format example (shared/profile_template.md) must parse and re-render exactly."""
    text = (CONTRACT.parent.parent / "shared" / "profile_template.md").read_text()
    block = text.split("## Format example")[1].split("```text\n")[1].split("\n```")[0]
    try:
        if render(parse(block)) != block:
            fail("profile_template.md", "format example doesn't re-render identically")
    except TemplateError as e:
        fail("profile_template.md", f"format example doesn't parse: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifacts", type=Path, help="also validate a real artefacts folder (e.g. shared/artifacts)")
    args = ap.parse_args()
    for path in sorted(SCHEMAS.glob("*.json")) + sorted(ARTIFACT_SCHEMAS.glob("*.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    check_template_example()
    run(CONTRACT / "mocks", examples=True)
    if args.artifacts:
        run(args.artifacts, examples=False)
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} problem(s)")
        for f in FAILURES[:50]:
            print("  -", f)
        return 1
    print("OK: schemas, mocks and examples are valid and consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
