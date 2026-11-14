"""The research artefacts the app runs on: rules.json, thresholds.json, model.json.

Loaded once from ARTIFACTS_DIR (mocks by default, shared/artifacts when the research is done) and
validated against the contract, so a malformed artefact fails at startup, not mid-screening.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .contract import REPO_ROOT, Contract, ContractError

NAMES = ("rules", "thresholds", "model")


@dataclass(frozen=True)
class Artifacts:
    dir: Path
    rules: dict
    thresholds: dict
    model: dict

    @property
    def rule_ids(self) -> list[str]:
        return [r["id"] for r in self.rules["rules"]]

    @property
    def decider_input(self) -> str:
        return self.model["decider_input"]

    @property
    def any_mock(self) -> bool:
        return any(self.is_mock(n) for n in NAMES)

    def is_mock(self, name: str) -> bool:
        return bool(getattr(self, name).get("mock", False))

    def get(self, name: str) -> dict:
        if name not in NAMES:
            raise KeyError(name)
        return getattr(self, name)

    def summary(self) -> dict:
        return {
            "dir": _display(self.dir),
            "rules": {"mock": self.is_mock("rules"), "count": len(self.rules["rules"])},
            "thresholds": {"mock": self.is_mock("thresholds"), "val_n": self.thresholds["source"]["n"]},
            "model": {"mock": self.is_mock("model"), "model_id": self.model["model_id"],
                      "decider_input": self.decider_input},
        }


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path.name


def load_artifacts(directory: Path, contract: Contract) -> Artifacts:
    if not directory.is_dir():
        raise FileNotFoundError(f"ARTIFACTS_DIR not found: {directory}")
    docs = {}
    for name in NAMES:
        path = directory / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"missing artefact: {path}")
        docs[name] = json.loads(path.read_text())
        try:
            contract.check(name, docs[name])
        except ContractError as e:
            raise ContractError(f"{path}", e.errors) from None
    return Artifacts(dir=directory, **docs)
