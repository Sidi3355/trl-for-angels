"""Batch mode: CSV parsing and the triage summary (MASTER_PLAN section 8, 'Batch mode')."""

from __future__ import annotations

import csv
import io
import re

VERSION = "0.1.0"
IDENTIFIER_COLUMNS = ("name", "company_name", "linkedin_url", "website_url")
FIELD_COLUMNS = ("industry", "cofounders", "background", "work_experience", "industry_experience")
CSV_COLUMNS = ("client_ref", *IDENTIFIER_COLUMNS, "founding_date", "notes", *FIELD_COLUMNS)
MAX_ROWS = 200


class CsvError(ValueError):
    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


def _col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def parse_csv(text: str, policy: dict | None = None) -> dict:
    """CSV text -> batch request. Header names are matched loosely ('LinkedIn URL' -> linkedin_url);
    columns that aren't in CSV_COLUMNS are ignored; empty cells mean 'not provided'."""
    text = text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CsvError("the CSV is empty")
    header = {h: _col(h) for h in reader.fieldnames if h is not None}
    if not set(header.values()) & {"name", "linkedin_url", "website_url"}:
        raise CsvError("the CSV needs a name, linkedin_url or website_url column",
                       [f"allowed columns: {', '.join(CSV_COLUMNS)}"])
    founders, problems = [], []
    for n, raw in enumerate(reader, start=1):
        row = {header[k]: (v or "").strip() for k, v in raw.items() if k in header and header[k] in CSV_COLUMNS}
        if not any(row.values()):
            continue
        if len(founders) >= MAX_ROWS:
            raise CsvError(f"a batch holds at most {MAX_ROWS} founders")
        ident = {k: row[k] for k in IDENTIFIER_COLUMNS if row.get(k)}
        if not ({"name", "linkedin_url", "website_url"} & ident.keys()):
            problems.append(f"row {n}: needs a name, linkedin_url or website_url")
            continue
        inp = {"schema_version": VERSION, "client_ref": row.get("client_ref") or f"row-{n}", "founder": ident}
        if row.get("founding_date"):
            inp["founding_date"] = row["founding_date"]
        if row.get("notes"):
            inp["notes"] = row["notes"]
        fields = {k: row[k] for k in FIELD_COLUMNS if row.get(k)}
        if fields:
            inp["fields"] = fields
        founders.append(inp)
    if problems:
        raise CsvError("some rows can't be screened", problems)
    if not founders:
        raise CsvError("the CSV has no founder rows")
    req = {"schema_version": VERSION, "founders": founders}
    if policy:
        req["policy"] = policy
    return req


def label(inp: dict) -> str:
    f = inp["founder"]
    return f.get("name") or f.get("company_name") or f.get("website_url") or f.get("linkedin_url") or "Unnamed founder"


def item_from_memo(index: int, memo: dict) -> dict:
    return {
        "index": index, "client_ref": memo.get("client_ref"), "label": memo["founder"]["display_name"],
        "status": "complete", "memo_id": memo["memo_id"], "memo_url": f"/v1/memos/{memo['memo_id']}",
        "decision": memo["verdict"]["decision"], "probability": memo["verdict"]["probability"],
        "distributions": memo["distributions"], "facets": memo["facets"],
        "filtered_out": bool(memo["verdict"]["filters_failed"]),
        "unknown_count": len(memo["unknowns"]), "conflict_count": len(memo["conflicts"]), "error": None,
    }


def counts(items: list[dict]) -> dict:
    out = {"advance": 0, "escalate": 0, "pass": 0, "filtered_out": 0}
    for it in items:
        if it["status"] == "complete":
            out["filtered_out" if it["filtered_out"] else it["decision"]] += 1
    return out
