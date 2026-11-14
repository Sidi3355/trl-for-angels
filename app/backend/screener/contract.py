"""Load the app contract's JSON Schemas (app/contract) and validate documents against them.

The schemas are the single source of truth: requests are validated against them at runtime, and
responses too when VALIDATE_RESPONSES is on (the default in dev and tests).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_DIR = REPO_ROOT / "app" / "contract"


class ContractError(ValueError):
    """A document that doesn't match its contract schema."""

    def __init__(self, schema: str, errors: list[str]):
        super().__init__(f"{schema}: {len(errors)} error(s): " + "; ".join(errors[:5]))
        self.schema = schema
        self.errors = errors


class Contract:
    def __init__(self, contract_dir: Path = DEFAULT_CONTRACT_DIR):
        self.dirs = [contract_dir / "schemas", contract_dir / "artifacts"]
        for d in self.dirs:
            if not d.is_dir():
                raise FileNotFoundError(f"contract schema folder not found: {d}")
        self.registry = Registry(retrieve=self._retrieve)
        self._validators: dict[str, Draft202012Validator] = {}

    def _path(self, name: str) -> Path:
        for d in self.dirs:
            if (d / name).exists():
                return d / name
        raise LookupError(f"no contract schema named {name}")

    def _retrieve(self, uri: str) -> Resource:
        return Resource.from_contents(json.loads(self._path(uri.rsplit("/", 1)[-1]).read_text()))

    def validator(self, schema: str) -> Draft202012Validator:
        """`schema` is a file stem, e.g. 'memo' or 'thresholds'."""
        if schema not in self._validators:
            doc = json.loads(self._path(f"{schema}.schema.json").read_text())
            Draft202012Validator.check_schema(doc)
            self._validators[schema] = Draft202012Validator(doc, registry=self.registry, format_checker=FormatChecker())
        return self._validators[schema]

    def errors_for_def(self, name: str, doc) -> list[str]:
        """Errors for a value against one common.schema.json definition (e.g. 'jobs')."""
        key = f"def:{name}"
        if key not in self._validators:
            self._validators[key] = Draft202012Validator(
                {"$ref": f"common.schema.json#/$defs/{name}"}, registry=self.registry, format_checker=FormatChecker())
        return [f"{'/'.join(str(p) for p in e.absolute_path) or '(value)'}: {e.message[:200]}"
                for e in leaf_errors(list(self._validators[key].iter_errors(doc)))]

    def errors(self, schema: str, doc) -> list[str]:
        errs = leaf_errors(list(self.validator(schema).iter_errors(doc)))
        out = []
        for err in sorted(errs, key=lambda e: [str(p) for p in e.absolute_path]):
            path = "/".join(str(p) for p in err.absolute_path) or "(root)"
            out.append(f"{path}: {err.message[:300]}")
        return out

    def check(self, schema: str, doc) -> None:
        errs = self.errors(schema, doc)
        if errs:
            raise ContractError(schema, errs)


def leaf_errors(errors):
    """Expand allOf errors and drop 'unevaluated properties' noise when a real error explains it."""
    out = []
    for err in errors:
        out += leaf_errors(err.context) if err.validator == "allOf" and err.context else [err]
    real = {tuple(e.absolute_path)[:-1] for e in out if e.validator != "unevaluatedProperties"}
    real |= {tuple(e.absolute_path) for e in out if e.validator != "unevaluatedProperties"}
    return [e for e in out if not (e.validator == "unevaluatedProperties" and tuple(e.absolute_path) in real)] or out


@lru_cache(maxsize=4)
def get_contract(contract_dir: Path = DEFAULT_CONTRACT_DIR) -> Contract:
    return Contract(contract_dir)
