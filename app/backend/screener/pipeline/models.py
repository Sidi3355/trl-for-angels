"""The answerer and the decider: the mocks here, the real Kev ones in kev.py.

ANSWERER=mock / DECIDER=mock (default): the toy model in mocks/model.py, clearly not the real thing.
ANSWERER=kev / DECIDER=kev: base Kev answers, the production Kev decides (pipeline/kev.py).
"""

from __future__ import annotations

from ..mocks.model import binary, mock_answer, mock_decide
from .context import Pipeline
from .kev import KevAnswerer, KevDecider  # noqa: F401 - re-exported for main.py
from .serialise import binary_vector


class MockAnswerer:
    name = "mock"

    async def answer(self, profile_text: str, fields: dict, ctx: Pipeline) -> list[float]:
        """P(yes) for every rule in rules.json, in order."""
        return mock_answer(fields, ctx.artifacts.rule_ids)


class MockDecider:
    name = "mock"

    async def decide(self, *, answer_labels: list[str] | None, profile_text: str, fields: dict, ctx: Pipeline) -> dict:
        """Outcome and years distributions. Answers mode reads the labels; profile mode reads the profile."""
        ids = ctx.artifacts.rule_ids
        if answer_labels is not None:
            return mock_decide(binary_vector(answer_labels), ids)
        return mock_decide(binary(mock_answer(fields, ids)), ids)

    async def decide_batch(self, inputs: list[dict], ctx: Pipeline) -> list[dict]:
        return [await self.decide(answer_labels=i.get("answer_labels"), profile_text=i.get("profile_text", ""),
                                  fields=i.get("fields", {}), ctx=ctx) for i in inputs]
