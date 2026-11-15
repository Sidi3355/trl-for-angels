"""Answers -> labels and Kev's input text, per model.json's answer_serialisation.

One line per rule, '<question> yes' or '<question> no' (yes when P(yes) >= 0.5), in rules.json order, and
'<question> unknown' where the answerer gave no answer (NaN). That is TRL's answers_text, which the real
decider (pipeline/kev.py) uses to build the text; state_text here must match it (tests/test_kev.py checks).
"""

from __future__ import annotations

import math

UNKNOWN = "unknown"

YES_LABELS = {"yes", "likely yes"}


def labels(p_yes: list[float], model: dict) -> list[str]:
    ser = model["answer_serialisation"]
    if ser["format"] == "binary":
        cut = ser.get("threshold", 0.5)
        return [UNKNOWN if _missing(p) else "yes" if p >= cut else "no" for p in p_yes]
    bands = sorted(ser["bands"].items(), key=lambda kv: kv[1])  # (label, lower bound), ascending
    return [([label for label, lo in bands if p >= lo] or [bands[0][0]])[-1] for p in p_yes]


def flip(label: str, model: dict) -> str | None:
    """The opposite answer, for drivers and what-ifs. None when there's no clear opposite ('unsure', 'unknown')."""
    if label == UNKNOWN:
        return None
    if model["answer_serialisation"]["format"] == "binary":
        return "no" if label == "yes" else "yes"
    return {"likely yes": "likely no", "likely no": "likely yes"}.get(label)


def state_text(rules: dict, answer_labels: list[str], model: dict) -> str:
    ser = model["answer_serialisation"]
    sep = ser.get("separator", "\n")
    return sep.join(ser["line_template"].format(question=r["question"], answer=a)
                    for r, a in zip(rules["rules"], answer_labels))


def _missing(p) -> bool:
    return p is None or (isinstance(p, float) and math.isnan(p))


def p_or_none(p: float) -> float | None:
    """P(yes) for the memo: null where the answerer gave none (JSON has no NaN)."""
    return None if _missing(p) else p


def binary_vector(answer_labels: list[str]) -> list[int]:
    return [1 if a in YES_LABELS else 0 for a in answer_labels]
