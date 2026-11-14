"""Three FICTIONAL demo founders and what the mock research agent 'finds' for them.

The mock agent (pipeline/research.py) serves these findings when an investor screens one of these
names, and build_mocks.py generates app/contract/mocks/mock_memo.json from them. Every URL is on
example.com. For any other founder the mock agent finds nothing, because mock mode runs no research.
"""

from __future__ import annotations

import re

VERSION = "0.1.0"


def _src(sid, url, title, published, before, used_for):
    return {"id": sid, "url": url, "title": title, "publisher": "example.com", "published_date": published,
            "before_founding": before, "used_for": used_for}


DEMO_FOUNDERS = [
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
        "findings": {
            "founding_date": ("2024-03", ["s2"]),
            "fields": {
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
                _src("s1", "https://example.com/mock/ada-moreno/linkedin", "Ada Moreno - professional profile (mock)", None, True,
                     ["background", "work_experience", "industry_experience", "education", "jobs"]),
                _src("s2", "https://example.com/mock/tallyframe/about", "About Tallyframe (mock)", "2024-03", True,
                     ["industry", "industry_experience", "founding_date"]),
                _src("s3", "https://example.com/mock/news/ledgerkit-acquired", "Payments API startup Ledgerkit acquired (mock news)", "2021-06", True,
                     ["prior_startups", "prior_exits"]),
                _src("s4", "https://example.com/mock/news/tallyframe-seed", "Tallyframe raises a seed round (mock news)", "2024-09", False,
                     ["notes"]),
            ],
            "searches": ["Ada Moreno Tallyframe founder background", "Ledgerkit acquisition", "Tallyframe founded"],
            "post_founding": [{"text": "Raised a seed round about six months after founding.", "source_ids": ["s4"]}],
        },
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
        "findings": {
            "founding_date": ("2025-01", ["s3"]),
            "fields": {
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
                _src("s1", "https://example.com/mock/samir-haddad/profile", "Dr Samir Haddad - professional profile (mock)", None, True,
                     ["industry", "background", "work_experience", "industry_experience", "education", "jobs", "prior_startups", "prior_exits"]),
                _src("s2", "https://example.com/mock/university/health-informatics-alumni", "Health informatics alumni list (mock)", "2019", True,
                     ["education"]),
                _src("s3", "https://example.com/mock/clearpath/team", "Clearpath Clinical - team page (mock)", "2025-01", True,
                     ["cofounders", "founding_date"]),
                _src("s4", "https://example.com/mock/news/clearpath-pilots", "Clearpath Clinical announces hospital pilots (mock news)", "2025-05", False,
                     ["notes"]),
            ],
            "searches": ["Samir Haddad physician Clearpath Clinical", "Clearpath Clinical team"],
            "post_founding": [{"text": "Announced pilots with hospital partners about four months after founding.", "source_ids": ["s4"]}],
        },
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
        "findings": {
            "founding_date": ("2025-06", ["s2"]),
            "fields": {
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
                _src("s1", "https://example.com/mock/jordan-pike/profile", "Jordan Pike - professional profile (mock)", None, True,
                     ["background", "work_experience", "industry_experience", "education", "jobs"]),
                _src("s2", "https://example.com/mock/loopcart", "Loopcart - home page (mock)", "2025-06", True,
                     ["industry", "founding_date"]),
                _src("s3", "https://example.com/mock/news/loopcart-preseed", "Loopcart raises a pre-seed round (mock news)", "2025-10", False,
                     ["notes"]),
            ],
            "searches": ["Jordan Pike Loopcart", "Loopcart founded"],
            "post_founding": [{"text": "Raised a pre-seed round about four months after founding.", "source_ids": ["s3"]}],
        },
    },
]


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def find_demo_founder(founder: dict) -> dict | None:
    """The demo founder matching an identifier by name, LinkedIn URL or website, if any."""
    keys = {_norm(founder.get("name")), _norm(founder.get("linkedin_url")), _norm(founder.get("website_url"))} - {""}
    for spec in DEMO_FOUNDERS:
        f = spec["input"]["founder"]
        if keys & ({_norm(f.get("name")), _norm(f.get("linkedin_url")), _norm(f.get("website_url"))} - {""}):
            return spec
    return None
