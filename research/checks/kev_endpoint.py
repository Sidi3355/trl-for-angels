"""One call to a Kev System One endpoint through TRL's real LLMSession.

Usage:
    KEV_BASE_URL=http://127.0.0.1:8009 python research/checks/kev_endpoint.py

KEV_BASE_URL is the server's root; /v1/systemone is added if missing. Prints the
answers and exits 1 if the call fails. Uses a throwaway cache, so it always calls.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from think_reason_learn.llm import LLM, LLMSession, YesNoQuestion, set_config
from think_reason_learn.llm._spec import resolve

SAMPLE = (
    "This founder leads a startup in the logistics industry, founded with 1 co-founder(s).\n"
    "Prior startups: none.\n"
    "Prior exits: none."
)
QUESTIONS = {
    "exit": YesNoQuestion("Does the founder have a prior exit?"),
    "logistics": YesNoQuestion("Is the startup in the logistics industry?"),
}


def kev_llm(base_url: str, name: str = "kev") -> LLM:
    """The TRL spec for a Kev endpoint (see MASTER_PLAN section 0)."""
    url = base_url.rstrip("/")
    if not url.endswith("/v1/systemone"):
        url += "/v1/systemone"
    key = os.environ.get("KEV_API_KEY") or "local"
    return LLM(name, base_url=url, kind="decision", api_key=key)


async def _call(endpoint) -> list:
    return await LLMSession().answer([endpoint], [SAMPLE], QUESTIONS, role="answerer")


def main() -> int:
    base = os.environ.get("KEV_BASE_URL", "http://127.0.0.1:8009")
    endpoint = resolve(kev_llm(base))
    print(f"endpoint: {endpoint.base_url} protocol={endpoint.protocol} kind={endpoint.kind}")
    with tempfile.TemporaryDirectory() as tmp:
        set_config(cache_dir=Path(tmp))
        try:
            answers = asyncio.run(_call(endpoint))
        except Exception as exc:  # report any failure plainly
            print(f"FAILED: {type(exc).__name__}: {exc}")
            return 1
    for qid, answer in answers[0].items():
        print(f"{qid}: {answer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
