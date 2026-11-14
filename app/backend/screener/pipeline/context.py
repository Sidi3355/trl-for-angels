"""What a pipeline run needs: the artefacts, the three swappable components, a clock and pacing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

from ..artifacts import Artifacts


class Emitter(Protocol):
    async def __call__(self, type: str, message: str, *, stage: str | None = None, data: dict | None = None) -> None: ...


async def no_emit(type: str, message: str, *, stage: str | None = None, data: dict | None = None) -> None:
    return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class NotConfigured(RuntimeError):
    """A real component was selected but isn't available (not built yet, or a key is missing)."""


@dataclass
class Pipeline:
    artifacts: Artifacts
    agent: Any
    answerer: Any
    decider: Any
    clock: Callable[[], datetime] = utc_now
    pace: float = 1.0  # multiplies the mock agent's simulated delays; 0 in tests
    extra: dict = field(default_factory=dict)

    @property
    def any_mock(self) -> bool:
        return self.artifacts.any_mock or "mock" in (self.agent.name, self.answerer.name, self.decider.name)

    def now(self) -> str:
        return iso(self.clock())

    async def sleep(self, seconds: float) -> None:
        if self.pace > 0:
            await asyncio.sleep(seconds * self.pace)

    def components(self) -> dict:
        return {"agent": self.agent.name, "answerer": self.answerer.name, "decider": self.decider.name}


AsyncFn = Callable[..., Awaitable[Any]]
