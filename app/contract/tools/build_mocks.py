"""Build every mock and example in app/contract/ from compact specs, so they agree with each other.

    python app/contract/tools/build_mocks.py

Writes mocks/{rules,thresholds,model,mock_memo}.json and examples/*. Deterministic (seed 42).
The three founders are fictional; every URL is on example.com.
"""

from __future__ import annotations

import copy
import csv
import io
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import policy  # noqa: E402
from mock_model import (  # noqa: E402
    OUTCOME_BANDS, RULES, YEARS_GIVEN_OUTCOME, binary, mock_answer, mock_decide, simulate_answers,
)
from template import FIELD_KEYS, UNKNOWN, consistency_issues, render, unknown_paths  # noqa: E402

CONTRACT = HERE.parent
MOCKS = CONTRACT / "mocks"
EXAMPLES = CONTRACT / "examples"
VERSION = "0.1.0"
NOW = "2026-11-14T12:00:00Z"
SEED = 42
DISCLAIMER = (
    "Screening aid, not investment advice. The model estimates the chance of a large outcome (an exit, "
    "IPO or funding at or above the chosen target) from the founder's background on the day the company "
    "was founded. It was trained on generated data, so its accuracy on real founders is unknown. "
    "Public information only; nothing is stored after the session."
)
MOCK_WARNING = {"code": "mock_artifacts", "message": "Mock artefacts and a mock model: every number here is illustrative only."}
MODEL_ID = "kev-0.6b-prod-mock"


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------- artefacts

def build_rules() -> dict:
    return {
        "schema_version": VERSION,
        "mock": True,
        "source": {
            "trl_version": "0.3.0",
            "trl_commit": "3437d64",
            "generator": "mock",
            "answerer": "jev",
            "rrf_params": {"beta": 0.5, "random_state": 42, "combiner": "elasticnet"},
            "created_at": NOW,
            "n_train": None,
        },
        "task": "Predict whether this startup founder's company will succeed (exit, IPO or funding over $500M).",
        "rules": [
            {"id": rid, "index": i, "question": q, "elastic_net_coef": None}
            for i, (rid, q, _, _, _) in enumerate(RULES)
        ],
    }


def build_model() -> dict:
    return {
        "schema_version": VERSION,
        "mock": True,
        "model_id": MODEL_ID,
        "created_at": NOW,
        "endpoint": {
            "base_url": "https://mock-kev.example.com",
            "path": "/v1/systemone",
            "auth": {"type": "none"},
            "timeout_s": 30,
        },
        "decider_input": "answers",
        "request": {
            "questions": {
                "outcome": {
                    "type": "choice",
                    "instructions": "What was the company's final outcome?",
                    "criteria": {b: None for b in OUTCOME_BANDS},
                },
                "years": {
                    "type": "choice",
                    "instructions": "How many years from founding to that outcome?",
                    "criteria": {"under 5": None, "5-8": None, "over 8": None},
                },
            },
            "response_format": "mock: research to confirm the kev.serve response shape",
        },
        "temperature": {"applied_by": "server", "outcome": None, "years": None},
        "answerer": {"spec": "jev", "via": "trl"},
        "answer_serialisation": {
            "format": "binary",
            "threshold": 0.5,
            "line_template": "{question} {answer}",
            "separator": "\n",
            "order": "rules.json",
        },
    }


def _sample(rng: random.Random, weights) -> int:
    r, acc = rng.random(), 0.0
    for i, w in enumerate(weights):
        acc += w
        if r < acc:
            return i
    return len(weights) - 1


def build_thresholds() -> dict:
    """Simulate a 400-founder val split with the mock model, then tabulate precision and recall."""
    rng = random.Random(SEED)
    val = []
    for _ in range(400):
        x = simulate_answers(rng)
        d = mock_decide(x)
        o = _sample(rng, [d["outcome"][b] for b in OUTCOME_BANDS])
        y = _sample(rng, YEARS_GIVEN_OUTCOME[OUTCOME_BANDS[o]])
        val.append((d, o, y))

    first = {t: OUTCOME_BANDS.index(policy.TARGET_FIRST_BAND[t]) for t in policy.TARGETS}
    within = {None: 3, 8: 2, 5: 1}  # true years index must be below this
    grid = [round(i / 100, 2) for i in range(100)]
    tables = []
    for target in policy.TARGETS:
        for tl in policy.TIMELINES:
            scored = [(policy.score(d, target, tl), o >= first[target] and y < within[tl]) for d, o, y in val]
            n_pos = sum(lbl for _, lbl in scored)
            rows = []
            for t in grid:
                flagged = [lbl for s, lbl in scored if s >= t]
                tp = sum(flagged)
                rows.append({
                    "threshold": t,
                    "n_flagged": len(flagged),
                    "tp": tp,
                    "precision": round(tp / len(flagged), 4) if flagged else None,
                    "recall": round(tp / n_pos, 4) if n_pos else None,
                })
            tables.append({
                "target": target, "timeline_years": tl, "n": len(val), "n_positive": n_pos,
                "base_rate": round(n_pos / len(val), 4), "rows": rows,
            })
    return {
        "schema_version": VERSION,
        "mock": True,
        "source": {
            "split": "val", "n": len(val), "model_id": MODEL_ID, "created_at": NOW,
            "note": "Mock: 400 val founders simulated with the mock model (seed 42), not real data.",
        },
        "score": "p_outcome_at_or_above_target * p_years_within_timeline",
        "label": "true_outcome_at_or_above_target AND true_years_within_timeline",
        "grid": {"start": 0.0, "stop": 0.99, "step": 0.01},
        "tables": tables,
    }


# --------------------------------------------------------------------------- founders

def src(sid, url, title, publisher, published, before, used_for):
    return {"id": sid, "url": url, "title": title, "publisher": publisher, "published_date": published,
            "accessed_at": NOW, "before_founding": before, "used_for": used_for}


FOUNDERS = [
    {
        "key": "advance",
        "memo_id": "memo_mock_001",
        "job_id": "job_mock_001",
        "input": {
            "schema_version": VERSION,
            "client_ref": "row-1",
            "founder": {
                "name": "Ada Moreno",
                "company_name": "Tallyframe",
                "linkedin_url": "https://example.com/mock/ada-moreno/linkedin",
                "website_url": "https://example.com/mock/tallyframe",
            },
            "founding_date": "2024-03",
            "fields": {"industry": "developer tools", "cofounders": "2"},
            "notes": "Met at demo day. Deep payments-infrastructure background; says they have 40 design partners.",
            "policy": {"target": "$500M", "timeline_years": None, "risk": "balanced"},
        },
        "agent": {
            "industry": ("developer tools", ["s2"], 0.9),
            "background": ("technical", ["s1"], 0.9),
            "work_experience": ("10-15", ["s1"], 0.85),
            "industry_experience": ("deep", ["s1", "s2"], 0.8),
            "education": ([{"degree": "MSc", "field": "Computer Science", "qs_rank": "top 50"}], ["s1"], 0.9),
            "jobs": ([
                {"role": "Software Engineer", "company": "a large search and advertising company", "company_size": "5,000+", "industry": "Internet", "duration": "3-5"},
                {"role": "Senior Software Engineer", "company": "a payments company", "company_size": "1,001-5,000", "industry": "Fintech", "duration": "3-5"},
                {"role": "Engineering Manager", "company": "a developer tools company", "company_size": "201-1,000", "industry": "Developer Tools", "duration": "3-5"},
            ], ["s1"], 0.85),
            "prior_startups": ([{"outcome": "acquired", "value_band": "$50M-$500M"}], ["s3"], 0.9),
            "prior_exits": ([{"kind": "acquisition", "value_band": "$50M-$500M"}], ["s3"], 0.85),
        },
        "sources": [
            src("s1", "https://example.com/mock/ada-moreno/linkedin", "Ada Moreno - professional profile (mock)", "example.com", None, True,
                ["background", "work_experience", "industry_experience", "education", "jobs"]),
            src("s2", "https://example.com/mock/tallyframe/about", "About Tallyframe (mock)", "example.com", "2024-03", True,
                ["industry", "industry_experience"]),
            src("s3", "https://example.com/mock/news/ledgerkit-acquired", "Payments API startup Ledgerkit acquired (mock news)", "example.com", "2021-06", True,
                ["prior_startups", "prior_exits"]),
            src("s4", "https://example.com/mock/news/tallyframe-seed", "Tallyframe raises a seed round (mock news)", "example.com", "2024-09", False,
                ["notes"]),
        ],
        "post_founding": [{"text": "Raised a seed round about six months after founding.", "source_ids": ["s4"]}],
        "founding_date": {"value": "2024-03", "provenance": "investor", "source_ids": []},
    },
    {
        "key": "escalate",
        "memo_id": "memo_mock_002",
        "job_id": "job_mock_002",
        "input": {
            "schema_version": VERSION,
            "client_ref": "row-2",
            "founder": {
                "name": "Samir Haddad",
                "company_name": "Clearpath Clinical",
                "website_url": "https://example.com/mock/clearpath",
            },
            "founding_date": "2025-01",
            "fields": {"industry": "healthtech", "cofounders": "solo", "work_experience": "10-15"},
            "voice_fields": ["work_experience"],
            "notes": "Met at a clinical AI meetup. Says three hospital pilots are lined up. Solo for now, hiring a CTO.",
            "policy": {"target": "$500M", "timeline_years": None, "risk": "balanced"},
        },
        "agent": {
            "industry": ("healthtech", ["s1"], 0.85),
            "cofounders": ("solo", ["s3"], 0.6),
            "background": ("domain specialist", ["s1"], 0.9),
            "work_experience": ("15+", ["s1"], 0.7),
            "industry_experience": ("deep", ["s1"], 0.85),
            "education": ([
                {"degree": "MD", "field": "Medicine", "qs_rank": "101-300"},
                {"degree": "MSc", "field": "Health Informatics", "qs_rank": "unknown"},
            ], ["s1", "s2"], 0.8),
            "jobs": ([
                {"role": "Resident Physician", "company": "a teaching hospital", "company_size": "5,000+", "industry": "Healthcare", "duration": "3-5"},
                {"role": "Attending Physician", "company": "a regional hospital network", "company_size": "5,000+", "industry": "Healthcare", "duration": "5+"},
                {"role": "Clinical Lead", "company": "a digital health company", "company_size": "unknown", "industry": "Healthtech", "duration": "2-3"},
            ], ["s1"], 0.75),
            "prior_startups": ("none", ["s1"], 0.7),
            "prior_exits": ("none", ["s1"], 0.7),
        },
        "sources": [
            src("s1", "https://example.com/mock/samir-haddad/profile", "Dr Samir Haddad - professional profile (mock)", "example.com", None, True,
                ["industry", "background", "work_experience", "industry_experience", "education", "jobs", "prior_startups", "prior_exits"]),
            src("s2", "https://example.com/mock/university/health-informatics-alumni", "Health informatics alumni list (mock)", "example.com", "2019", True,
                ["education"]),
            src("s3", "https://example.com/mock/clearpath/team", "Clearpath Clinical - team page (mock)", "example.com", "2025-01", True,
                ["cofounders"]),
            src("s4", "https://example.com/mock/news/clearpath-pilots", "Clearpath Clinical announces hospital pilots (mock news)", "example.com", "2025-05", False,
                ["notes"]),
        ],
        "post_founding": [{"text": "Announced pilots with hospital partners about four months after founding.", "source_ids": ["s4"]}],
        "founding_date": {"value": "2025-01", "provenance": "investor", "source_ids": []},
    },
    {
        "key": "pass",
        "memo_id": "memo_mock_003",
        "job_id": "job_mock_003",
        "input": {
            "schema_version": VERSION,
            "client_ref": "row-3",
            "founder": {"name": "Jordan Pike", "website_url": "https://example.com/mock/loopcart"},
            "notes": "Inbound through the website form.",
            "policy": {"target": "$500M", "timeline_years": None, "risk": "balanced"},
        },
        "agent": {
            "industry": ("e-commerce", ["s2"], 0.8),
            "background": ("business", ["s1"], 0.75),
            "work_experience": ("<5", ["s1"], 0.7),
            "industry_experience": ("some", ["s1"], 0.6),
            "education": ([{"degree": "BA", "field": "Economics", "qs_rank": "300+"}], ["s1"], 0.7),
            "jobs": ([
                {"role": "Marketing Associate", "company": "a consumer goods company", "company_size": "1,001-5,000", "industry": "Consumer Goods", "duration": "1-2"},
                {"role": "Growth Manager", "company": "an online travel company", "company_size": "201-1,000", "industry": "Travel", "duration": "1-2"},
            ], ["s1"], 0.7),
        },
        "sources": [
            src("s1", "https://example.com/mock/jordan-pike/profile", "Jordan Pike - professional profile (mock)", "example.com", None, True,
                ["background", "work_experience", "industry_experience", "education", "jobs"]),
            src("s2", "https://example.com/mock/loopcart", "Loopcart - home page (mock)", "example.com", "2025-06", True,
                ["industry", "founding_date"]),
            src("s3", "https://example.com/mock/news/loopcart-preseed", "Loopcart raises a pre-seed round (mock news)", "example.com", "2025-10", False,
                ["notes"]),
        ],
        "post_founding": [{"text": "Raised a pre-seed round about four months after founding.", "source_ids": ["s3"]}],
        "founding_date": {"value": "2025-06", "provenance": "agent", "source_ids": ["s2"]},
    },
]


def merge(spec: dict) -> tuple[dict, list[dict]]:
    """Simple stand-in for merge.py: investor values win, contradicting agent values become conflicts."""
    inv = spec["input"].get("fields", {})
    voice = set(spec["input"].get("voice_fields", []))
    fields, conflicts = {}, []
    for key in FIELD_KEYS:
        agent = spec["agent"].get(key)
        if key in inv and inv[key] != UNKNOWN:
            fields[key] = {"value": inv[key], "provenance": "investor_voice" if key in voice else "investor",
                           "source_ids": [], "confidence": None}
            if agent and agent[0] != UNKNOWN and agent[0] != inv[key]:
                conflicts.append({"field": key, "investor_value": inv[key], "agent_value": agent[0],
                                  "agent_source_ids": agent[1], "resolution": "investor_value_used",
                                  "note": f"Agent confidence {agent[2]:.0%}."})
        elif agent and agent[0] != UNKNOWN:
            fields[key] = {"value": agent[0], "provenance": "agent", "source_ids": agent[1], "confidence": agent[2]}
        else:
            fields[key] = {"value": UNKNOWN, "provenance": "unknown", "source_ids": [], "confidence": None}
    return fields, conflicts


def drivers(x: list[int], base: dict, pol: dict) -> list[dict]:
    base_p = policy.score(base, pol["target"], pol["timeline_years"])
    out = []
    for i, (rid, question, *_rest) in enumerate(RULES):
        flipped = list(x)
        flipped[i] = 1 - x[i]
        d = mock_decide(flipped)
        delta = policy.score(d, pol["target"], pol["timeline_years"]) - base_p
        out.append({"id": rid, "kind": "answer", "label": question,
                    "current": "yes" if x[i] else "no", "flipped": "yes" if flipped[i] else "no",
                    "distributions": d, "delta": round(delta, 4)})
    out.sort(key=lambda dr: -abs(dr["delta"]))
    return out


def build_memo(spec: dict, thresholds: dict) -> dict:
    fields, conflicts = merge(spec)
    values = {k: v["value"] for k, v in fields.items()}
    issues = consistency_issues(values)
    if issues:
        raise SystemExit(f"{spec['key']}: template consistency issues: {issues}")
    p_yes = mock_answer(values)
    x = binary(p_yes)
    dist = mock_decide(x)
    pol = policy.with_defaults(spec["input"].get("policy"))
    verdict = policy.verdict(dist, thresholds, pol, values)
    unknowns = unknown_paths(values)
    warnings = [MOCK_WARNING]
    if len(unknowns) > 2:
        warnings.append({"code": "many_unknowns", "message": (
            f"{len(unknowns)} fields are unknown. The model was trained on profiles with at most 2 unknown "
            "fields, so treat this result with extra caution.")})
    if conflicts:
        warnings.append({"code": "conflicts_present", "message": (
            f"{len(conflicts)} of your values disagree with what the agent found. Your values were used; check the conflicts.")})
    if policy.resolve(thresholds, pol)["sparse"]:
        warnings.append({"code": "thresholds_sparse", "message": "Few val founders reached this target and timeline, so expected precision and recall are noisy."})
    ident = spec["input"]["founder"]
    return {
        "schema_version": VERSION,
        "memo_id": spec["memo_id"],
        "job_id": spec["job_id"],
        "client_ref": spec["input"].get("client_ref"),
        "created_at": NOW,
        "mock": True,
        "founder": {
            "display_name": ident.get("name", "Unnamed founder"),
            "company_name": ident.get("company_name"),
            "identifier": ident,
            "founding_date": spec["founding_date"],
        },
        "verdict": verdict,
        "distributions": dist,
        "fields": fields,
        "rendered_profile": render(values),
        "decider": {"input_type": "answers", "model_id": MODEL_ID, "artifacts_dir": "app/contract/mocks"},
        "answers": [{"rule_id": rid, "p_yes": p, "answer": "yes" if xi else "no"}
                    for (rid, *_), p, xi in zip(RULES, p_yes, x)],
        "drivers": drivers(x, dist, verdict["policy"]),
        "what_if": {"answer_changes": "supported", "field_changes": "needs_answerer"},
        "facets": policy.facets(values),
        "sources": spec["sources"],
        "conflicts": conflicts,
        "unknowns": unknowns,
        "notes": {"investor": spec["input"].get("notes"), "post_founding": spec["post_founding"]},
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }


# --------------------------------------------------------------------------- examples

def build_progress_events(memo: dict) -> list[dict]:
    jid = memo["job_id"]
    evs = [
        ("stage", "queued", "Screening queued.", None),
        ("stage", "researching", "Researching Ada Moreno (information from before 2024-03 only).", None),
        ("search", None, "Searching: Ada Moreno Tallyframe founder background", {"query": "Ada Moreno Tallyframe founder background"}),
        ("source", None, "Found a professional profile.", {"source": memo["sources"][0]}),
        ("field", None, "Background: technical.", {"key": "background", **memo["fields"]["background"]}),
        ("field", None, "Work experience: 10-15 years.", {"key": "work_experience", **memo["fields"]["work_experience"]}),
        ("search", None, "Searching: Ledgerkit acquisition", {"query": "Ledgerkit acquisition"}),
        ("source", None, "Found news of a prior acquisition.", {"source": memo["sources"][2]}),
        ("field", None, "Prior exits: 1 acquisition as co-founder, $50M-$500M.", {"key": "prior_exits", **memo["fields"]["prior_exits"]}),
        ("source", None, "Found a seed round from after founding: memo notes only.", {"source": memo["sources"][3]}),
        ("stage", "merging", "Merging your 2 fields with 7 found by the agent. No conflicts.", None),
        ("stage", "rendering", "Rendering the anonymised profile.", None),
        ("stage", "answering", "Answering 20 screening questions.", None),
        ("stage", "deciding", "Scoring outcome and timeline.", None),
        ("stage", "writing_memo", "Writing the memo.", None),
        ("memo_ready", None, "Memo ready: advance.", {"memo_id": memo["memo_id"], "decision": memo["verdict"]["decision"],
                                                       "probability": memo["verdict"]["probability"]}),
        ("stage", "done", "Done.", None),
    ]
    out = []
    for seq, (typ, stage, msg, data) in enumerate(evs):
        ev = {"schema_version": VERSION, "job_id": jid, "seq": seq, "ts": f"2026-11-14T11:59:{seq * 3:02d}Z",
              "type": typ, "message": msg}
        if stage:
            ev["stage"] = stage
        if data is not None:
            ev["data"] = data
        out.append(ev)
    return out


def build_what_if(memo: dict) -> tuple[dict, dict]:
    """Founder 2: what if they had a co-founder? (answer change, Kev only)."""
    req = {"schema_version": VERSION, "changes": [{"kind": "answer", "rule_id": "r12", "value": "yes"}]}
    x = [1 if a["answer"] == "yes" else 0 for a in memo["answers"]]
    x[[r[0] for r in RULES].index("r12")] = 1
    d = mock_decide(x)
    values = {k: v["value"] for k, v in memo["fields"].items()}
    resp = {
        "schema_version": VERSION, "memo_id": memo["memo_id"], "changes": req["changes"], "used_answerer": False,
        "baseline": memo["distributions"], "distributions": d,
        "verdict": policy.verdict(d, THRESHOLDS, memo["verdict"]["policy"], values),
        "rendered_profile": None, "answers_changed": ["r12"], "mock": True,
    }
    return req, resp


def batch_item(i: int, memo: dict) -> dict:
    return {
        "index": i, "client_ref": memo["client_ref"], "label": memo["founder"]["display_name"],
        "status": "complete", "memo_id": memo["memo_id"], "memo_url": f"/v1/memos/{memo['memo_id']}",
        "decision": memo["verdict"]["decision"], "probability": memo["verdict"]["probability"],
        "distributions": memo["distributions"], "facets": memo["facets"],
        "filtered_out": bool(memo["verdict"]["filters_failed"]),
        "unknown_count": len(memo["unknowns"]), "conflict_count": len(memo["conflicts"]), "error": None,
    }


CSV_COLUMNS = ["client_ref", "name", "company_name", "linkedin_url", "website_url", "founding_date", "notes",
               "industry", "cofounders", "background", "work_experience", "industry_experience"]


def build_batch(memos: list[dict]) -> tuple[dict, dict, str]:
    founders = []
    for spec in FOUNDERS:
        inp = copy.deepcopy(spec["input"])
        inp.pop("policy", None)
        founders.append(inp)
    pol = {"target": "$500M", "timeline_years": None, "risk": "balanced"}
    req = {"schema_version": VERSION, "batch_ref": "demo-batch", "founders": founders, "policy": pol,
           "options": {"concurrency": 3, "research": True}}
    items = [batch_item(i, m) for i, m in enumerate(memos)]
    counts = {"advance": 0, "escalate": 0, "pass": 0, "filtered_out": 0}
    for it in items:
        counts["filtered_out" if it["filtered_out"] else it["decision"]] += 1
    resp = {
        "schema_version": VERSION, "batch_id": "batch_mock_001", "batch_ref": "demo-batch", "status": "complete",
        "created_at": NOW, "policy": policy.resolve(THRESHOLDS, pol)["policy"],
        "progress": {"total": 3, "queued": 0, "running": 0, "complete": 3, "failed": 0},
        "counts": counts, "items": items, "events_url": "/v1/batches/batch_mock_001/events", "mock": True,
        "disclaimer": DISCLAIMER,
    }
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    w.writeheader()
    for f in founders:
        row = {"client_ref": f.get("client_ref", ""), "founding_date": f.get("founding_date", ""),
               "notes": f.get("notes") or "", **{k: v for k, v in f["founder"].items() if k in CSV_COLUMNS}}
        row.update({k: v for k, v in f.get("fields", {}).items() if k in CSV_COLUMNS})
        w.writerow(row)
    return req, resp, buf.getvalue()


THRESHOLDS: dict = {}


def main() -> None:
    global THRESHOLDS
    rules, model = build_rules(), build_model()
    THRESHOLDS = build_thresholds()
    memos = [build_memo(spec, THRESHOLDS) for spec in FOUNDERS]
    got = [m["verdict"]["decision"] for m in memos]
    want = [s["key"] for s in FOUNDERS]
    if got != want:
        raise SystemExit(f"mock verdicts {got} don't match the intended {want}; retune the founder specs")

    dump(MOCKS / "rules.json", rules)
    dump(MOCKS / "model.json", model)
    dump(MOCKS / "thresholds.json", THRESHOLDS)
    dump(MOCKS / "mock_memo.json", memos)

    for spec in FOUNDERS:
        dump(EXAMPLES / f"investor_input_{spec['key']}.json", spec["input"])
    job = {"schema_version": VERSION, "job_id": memos[0]["job_id"], "client_ref": memos[0]["client_ref"],
           "status": "complete", "stage": "done", "created_at": NOW,
           "events_url": f"/v1/screenings/{memos[0]['job_id']}/events", "memo_id": memos[0]["memo_id"],
           "memo_url": f"/v1/memos/{memos[0]['memo_id']}", "error": None}
    dump(EXAMPLES / "screening_job.json", job)
    (EXAMPLES / "progress_events.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in build_progress_events(memos[0])))
    wi_req, wi_resp = build_what_if(memos[1])
    dump(EXAMPLES / "what_if_request.json", wi_req)
    dump(EXAMPLES / "what_if_response.json", wi_resp)
    b_req, b_resp, b_csv = build_batch(memos)
    dump(EXAMPLES / "batch_request.json", b_req)
    dump(EXAMPLES / "batch_response.json", b_resp)
    (EXAMPLES / "batch.csv").write_text(b_csv)

    for m in memos:
        v = m["verdict"]
        print(f"{m['memo_id']}: {v['decision']:8s} p={v['probability']:.3f}  "
              f"adv>={v['policy']['advance_threshold']} pass<{v['policy']['pass_threshold']}  "
              f"unknowns={len(m['unknowns'])} conflicts={len(m['conflicts'])}")


if __name__ == "__main__":
    main()
