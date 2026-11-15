"""Kev through TRL: base Kev answers the rules, the production Kev decides (research docs/app_integration.md).

Both are System One endpoints served by research's kev_server on the owner's PC, behind a Cloudflare tunnel:
    <KEV_URL>/answerer/v1/systemone   base jaredpalmer/kev-0.6b, answers rules.json's yes/no questions
    <KEV_URL>/decider/v1/systemone    the production model, outcome and years distributions, served RAW
Every call goes through TRL's own LLM and LLMSession (MASTER_PLAN 4b), and the decider's input text comes
from TRL's answers_text, so the app sends exactly what Kev was trained on. The tunnel address changes each
time it starts, so KEV_URL (one Railway variable) overrides model.json's placeholder endpoint.

Nothing is stored: TRL's reply cache is turned off for this process.
"""

from __future__ import annotations

import logging
import math
import re
from urllib.parse import urlsplit

from .context import NotConfigured

log = logging.getLogger("screener.kev")

PLACEHOLDER = "replace-with-tunnel"
ANSWER_P = {"yes": 1.0, "no": 0.0}  # serialised answers back to a P(yes) that answers_text turns into the same word


class KevUnavailable(RuntimeError):
    """Kev didn't answer: the PC server or its tunnel is down, the key is wrong, or the reply was unusable."""


def kev_urls(model: dict, kev_url: str | None) -> tuple[str, str]:
    """(answerer URL, decider URL). KEV_URL, when set, wins over model.json for both."""
    if kev_url:
        base = kev_url.strip().rstrip("/")
        if not base.startswith(("http://", "https://")):
            raise NotConfigured(f"KEV_URL must start with https:// (got {base[:40]!r})")
        return f"{base}/answerer/v1/systemone", f"{base}/decider/v1/systemone"
    decider = model["endpoint"]["base_url"].rstrip("/") + model["endpoint"]["path"]
    m = re.search(r'base_url="([^"]+)"', model.get("answerer", {}).get("spec", ""))
    answerer = m.group(1) if m else ""
    if not answerer or PLACEHOLDER in answerer or PLACEHOLDER in decider:
        raise NotConfigured("set KEV_URL to the Kev server's tunnel address (https://<words>.trycloudflare.com): "
                            "model.json only has a placeholder")
    return answerer, decider


def host(url: str) -> str:
    return urlsplit(url).netloc or url


def configure_trl(timeout_s: float, max_retries: int) -> None:
    """Process-wide TRL settings. Only Kev goes through TRL in this app."""
    from think_reason_learn.llm import set_config
    set_config(cache=False, timeout=timeout_s, max_retries=max_retries)


def _endpoints(url: str, api_key: str | None, role: str):
    from think_reason_learn.llm import LLM, resolve_models
    return resolve_models([LLM("kev-0.6b", base_url=url, kind="decision", api_key=api_key or None)],
                          param=role, task="answer")


async def _ask(endpoints, url: str, states: list[str], questions: dict, role: str) -> list[dict]:
    from think_reason_learn.exceptions import TRLError
    from think_reason_learn.llm import LLMSession
    try:
        return await LLMSession().answer(endpoints, states, questions, role=role)
    except TRLError as e:
        # The message names the host, never the key. Shown to the investor on a failed screening.
        raise KevUnavailable(f"Kev's {role} at {host(url)} didn't answer ({type(e).__name__}). Is the Kev server on "
                             f"the PC and its tunnel running, with the same KEV_API_KEY?") from e


class KevAnswerer:
    """Base Kev answers every rule in rules.json for one profile: P(yes) per rule, NaN where it gave no answer."""
    name = "kev"

    def __init__(self, *, url: str, api_key: str | None, rules: dict, auth_required: bool, timeout_s: float,
                 max_retries: int):
        if rules.get("mock"):
            raise NotConfigured("ANSWERER=kev needs the real rules.json (ARTIFACTS_DIR=shared/artifacts)")
        if auth_required and not api_key:
            raise NotConfigured("ANSWERER=kev: the Kev server needs a key in KEV_API_KEY")
        from think_reason_learn.llm import YesNoQuestion
        configure_trl(timeout_s, max_retries)
        self.url = url
        self.endpoints = _endpoints(url, api_key, "answerer")
        self.ids = [r["id"] for r in rules["rules"]]
        self.questions = {r["id"]: YesNoQuestion(r["question"]) for r in rules["rules"]}

    async def answer(self, profile_text: str, fields: dict, ctx) -> list[float]:
        [row] = await _ask(self.endpoints, self.url, [profile_text], self.questions, "answerer")
        p_yes = [row[i].probability() if row.get(i) is not None else math.nan for i in self.ids]
        missing = sum(math.isnan(p) for p in p_yes)
        if missing:
            log.warning("Kev left %d of %d questions unanswered; they read 'unknown'", missing, len(p_yes))
        return p_yes


class KevDecider:
    """The production Kev: outcome and years distributions, with model.json's temperatures applied here."""
    name = "kev"
    slow = True  # seconds per decision on a CPU: the memo's drivers are filled in afterwards (memo.fill_drivers)

    def __init__(self, *, url: str, api_key: str | None, model: dict, rules: dict, timeout_s: float, max_retries: int):
        if model.get("mock"):
            raise NotConfigured("DECIDER=kev needs the real model.json (ARTIFACTS_DIR=shared/artifacts)")
        if model["endpoint"]["auth"]["type"] != "none" and not api_key:
            raise NotConfigured("DECIDER=kev: model.json says the Kev server needs a key in KEV_API_KEY")
        self.input = model["decider_input"]
        if self.input == "answers" and model["answer_serialisation"]["format"] != "binary":
            raise NotConfigured("DECIDER=kev reads binary answers only (TRL's answers_text)")
        from think_reason_learn.llm import ChoiceQuestion
        configure_trl(timeout_s, max_retries)
        self.url = url
        self.endpoints = _endpoints(url, api_key, "decider")
        # Word for word from model.json, option descriptions included: the model was trained with them.
        self.questions = {qid: ChoiceQuestion(q["instructions"], tuple(q["criteria"]), tuple(q["criteria"].values()))
                          for qid, q in model["request"]["questions"].items()}
        temp = model["temperature"]
        self.temperatures = ({qid: float(temp[qid]) for qid in self.questions if temp.get(qid)}
                             if temp.get("applied_by") == "client" else {})
        self.rule_questions = [r["question"] for r in rules["rules"]]

    def state(self, answer_labels: list[str] | None, profile_text: str) -> str:
        if self.input == "profile":
            return profile_text
        from think_reason_learn.rrf import answers_text
        if answer_labels is None or len(answer_labels) != len(self.rule_questions):
            raise ValueError("the answers decider needs one answer per rule")
        return answers_text(self.rule_questions, [ANSWER_P.get(a, math.nan) for a in answer_labels])

    async def decide(self, *, answer_labels: list[str] | None, profile_text: str, fields: dict, ctx) -> dict:
        [dist] = await self.decide_states([self.state(answer_labels, profile_text)])
        return dist

    async def decide_batch(self, inputs: list[dict], ctx) -> list[dict]:
        """Several decisions in one TRL session (a chunk of the memo's drivers)."""
        return await self.decide_states([self.state(i.get("answer_labels"), i.get("profile_text", "")) for i in inputs])

    async def decide_states(self, states: list[str]) -> list[dict]:
        rows = await _ask(self.endpoints, self.url, states, self.questions, "decider")
        return [self._distributions(row) for row in rows]

    def _distributions(self, row: dict) -> dict:
        out = {}
        for qid, q in self.questions.items():
            ans = row.get(qid)
            if ans is None:
                raise KevUnavailable(f"Kev's decider gave no usable answer for {qid}")
            probs = {label: float(ans.probabilities.get(label, 0.0)) for label in q.labels}
            out[qid] = rounded(temper(probs, self.temperatures.get(qid)))
        return out


def temper(probs: dict[str, float], t: float | None) -> dict[str, float]:
    """Apply a fitted temperature to a served (raw) distribution: p^(1/T), renormalised.

    The same as dividing the logits by T (research/common.apply_temperature)."""
    if not t or t == 1.0:
        total = sum(probs.values())
        return {k: v / total for k, v in probs.items()} if total > 0 else probs
    powered = {k: (v ** (1.0 / t) if v > 0 else 0.0) for k, v in probs.items()}
    total = sum(powered.values())
    if total <= 0:
        raise KevUnavailable("Kev's decider returned an empty distribution")
    return {k: v / total for k, v in powered.items()}


def rounded(probs: dict[str, float]) -> dict[str, float]:
    """4 decimals that sum to exactly 1 (the contract's distributions), fixing the rounding on the largest."""
    out = {k: round(v, 4) for k, v in probs.items()}
    err = round(1 - sum(out.values()), 4)
    if err:
        k = max(out, key=out.get)
        out[k] = round(out[k] + err, 4)
    return out


async def probe(kev_url: str | None, api_key: str | None, timeout_s: float = 4.0) -> dict | None:
    """The Kev server's own /health (both models loaded? decider still standing in?), for our /health."""
    if not kev_url:
        return None
    import httpx
    base = kev_url.strip().rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.get(f"{base}/health", headers=headers)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    except (httpx.HTTPError, ValueError) as e:
        return {"host": host(base), "reachable": False, "error": type(e).__name__}
    decider = body.get("decider") if isinstance(body.get("decider"), dict) else {}
    return {"host": host(base), "reachable": True, "ready": bool(body.get("ready")),
            "decider_stand_in": decider.get("stand_in")}
