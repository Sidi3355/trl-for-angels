"""The answerer (Jev) and the decider (production Kev), each with a mock and a real implementation.

ANSWERER=mock / DECIDER=mock (default): the toy model in mocks/model.py, clearly not the real thing.
ANSWERER=jev / DECIDER=kev: wired in once the keys and the real artefacts exist.
"""

from __future__ import annotations

from ..mocks.model import binary, mock_answer, mock_decide
from .context import NotConfigured, Pipeline
from .serialise import binary_vector


class MockAnswerer:
    name = "mock"

    async def answer(self, profile_text: str, fields: dict, ctx: Pipeline) -> list[float]:
        """P(yes) for every rule in rules.json, in order."""
        return mock_answer(fields, ctx.artifacts.rule_ids)


class JevAnswerer:
    """Jev through TRL's own pipeline (rrf.answers), per the TRL fidelity rule (MASTER_PLAN 4b)."""
    name = "jev"

    def __init__(self, api_key: str | None):
        if not api_key:
            raise NotConfigured("ANSWERER=jev needs TYPESAFE_API_KEY")
        raise NotConfigured("ANSWERER=jev arrives with the real rules.json and the research session's TRL hook")

    async def answer(self, profile_text: str, fields: dict, ctx: Pipeline) -> list[float]:  # pragma: no cover
        raise NotImplementedError


class MockDecider:
    name = "mock"

    async def decide(self, *, answer_labels: list[str] | None, profile_text: str, fields: dict, ctx: Pipeline) -> dict:
        """Outcome and years distributions. Answers mode reads the labels; profile mode reads the profile."""
        ids = ctx.artifacts.rule_ids
        if answer_labels is not None:
            return mock_decide(binary_vector(answer_labels), ids)
        return mock_decide(binary(mock_answer(fields, ids)), ids)


class KevDecider:
    """The production Kev at model.json's endpoint (kev.serve's /v1/systemone)."""
    name = "kev"

    def __init__(self, api_key: str | None, model: dict):
        auth = model["endpoint"]["auth"]
        if auth["type"] != "none" and not api_key:
            raise NotConfigured(f"DECIDER=kev: model.json says the endpoint needs a key in {auth.get('env_var', 'KEV_API_KEY')}")
        if model.get("mock"):
            raise NotConfigured("DECIDER=kev needs the real model.json (ARTIFACTS_DIR=shared/artifacts)")
        raise NotConfigured("DECIDER=kev arrives once the research session confirms kev.serve's response format")

    async def decide(self, *, answer_labels, profile_text, fields, ctx) -> dict:  # pragma: no cover
        raise NotImplementedError
