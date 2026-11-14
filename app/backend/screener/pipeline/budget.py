"""Spend caps for the research agent, from the API's own usage numbers.

Two caps, both in USD:
- per founder (AGENT_MAX_COST_PER_FOUNDER_USD): research stops once one founder's calls reach it;
- total (AGENT_BUDGET_USD): once this process has spent it, no further research runs.

The totals live in memory, so a restart resets them. The hard cap that survives everything is the
spend limit on the API key's workspace in the Claude Console.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# USD per million tokens: (input, output, cache write (5 min), cache read). Web search: $10 per 1,000.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 5.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 2.50, 0.10),
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.01),
    "claude-fable-5-2": (8.00, 40.00, 10.00, 0.20),
}
FALLBACK_PRICE = PRICES["claude-fable-5-2"]  # an unknown or fallback model is costed at the dearest rate
WEB_SEARCH_USD = 0.01


def _price(model: str | None) -> tuple[float, float, float, float]:
    for prefix, price in PRICES.items():
        if model and model.startswith(prefix):
            return price
    return FALLBACK_PRICE


def cost_of(usage, model: str | None) -> float:
    """USD for one response's usage object (cumulative across its server-side tool iterations)."""
    inp, out, cw, cr = _price(model)
    g = lambda name: getattr(usage, name, 0) or 0  # noqa: E731
    tokens = (g("input_tokens") * inp + g("output_tokens") * out
              + g("cache_creation_input_tokens") * cw + g("cache_read_input_tokens") * cr) / 1e6
    stu = getattr(usage, "server_tool_use", None)
    searches = (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
    return tokens + searches * WEB_SEARCH_USD


@dataclass
class Budget:
    """Process-wide spend tracker, shared by every research run."""
    total_usd: float
    per_founder_usd: float
    spent_usd: float = 0.0
    runs: int = 0
    searches: int = 0
    log: list = field(default_factory=list)

    @property
    def exhausted(self) -> bool:
        return self.spent_usd >= self.total_usd

    def charge(self, usage, model: str | None, label: str = "") -> float:
        usd = cost_of(usage, model)
        self.spent_usd += usd
        stu = getattr(usage, "server_tool_use", None)
        self.searches += (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
        self.log.append({"label": label, "model": model, "usd": round(usd, 4)})
        return usd

    def summary(self) -> dict:
        return {"spent_usd": round(self.spent_usd, 4), "total_cap_usd": self.total_usd,
                "per_founder_cap_usd": self.per_founder_usd, "runs": self.runs, "searches": self.searches}
