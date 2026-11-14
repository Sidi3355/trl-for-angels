"""Web push: tell the investor's phone when a screening or a batch finishes (MASTER_PLAN 8, step 8).

Keys: VAPID_PRIVATE_KEY if set (its public key is derived from it); otherwise a key pair generated at
startup. Subscriptions live in memory with the job they're for and are dropped once used (nothing is
stored after the session), so a per-process key is enough: a restart loses jobs and subscriptions together.
The notification states the verdict at the investor's bar, sent with the subscription.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

from . import policy

log = logging.getLogger("screener.push")

# The words the app shows for each decision (owner's choice for angel investors; internal values unchanged).
WORDS = {"advance": "Meet", "escalate": "Look closer", "pass": "Pass"}
TARGET = {"$50M": "$50M+", "$500M": "$500M+", "$1B": "$1B+"}

Sender = Callable[[dict, str], int]  # (subscription, json payload) -> HTTP status from the push service


class Pusher:
    def __init__(self, *, private_key: str | None = None, subject: str = "mailto:push@example.com", sender: Sender | None = None):
        from cryptography.hazmat.primitives import serialization
        from py_vapid import Vapid01, b64urlencode

        vapid = None
        if private_key:
            try:
                vapid = Vapid01.from_string(private_key)
            except Exception as e:  # noqa: BLE001 - a bad key shouldn't stop the service
                log.error("VAPID_PRIVATE_KEY unreadable (%s); using a key generated for this process", type(e).__name__)
        if vapid is None:
            vapid = Vapid01()
            vapid.generate_keys()
        self.vapid = vapid
        raw = vapid.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.public_key = b64urlencode(raw)
        self.subject = subject
        self._sender = sender or self._webpush

    def _webpush(self, subscription: dict, payload: str) -> int:
        from pywebpush import WebPushException, webpush

        try:
            resp = webpush(subscription_info=subscription, data=payload, vapid_private_key=self.vapid,
                           vapid_claims={"sub": self.subject}, ttl=3600, timeout=10)
            return getattr(resp, "status_code", 201)
        except WebPushException as e:
            return getattr(e.response, "status_code", 0) or 0

    async def send(self, subscription: dict, payload: dict) -> bool:
        """Send one notification. False if the push service refused it (an expired subscription, say)."""
        try:
            status = await asyncio.to_thread(self._sender, subscription, json.dumps(payload))
        except Exception as e:  # noqa: BLE001 - a failed push never breaks a screening
            log.warning("push failed: %s", type(e).__name__)
            return False
        if status >= 300 or status == 0:
            log.info("push service answered %s", status)
            return False
        return True


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def screening_payload(memo: dict | None, thresholds: dict, pol: dict | None, error: dict | None = None) -> dict:
    if memo is None:
        return {"title": "Screening couldn't finish", "body": (error or {}).get("message", "Open the app to try again.")[:180], "url": "/"}
    fields = {k: f["value"] for k, f in memo["fields"].items()}
    v = policy.verdict(memo["distributions"], thresholds, pol, fields)
    p = v["policy"]
    horizon = f" within {p['timeline_years']} years" if p["timeline_years"] else ""
    approx = "≈" if v["probability_is_estimate"] else ""
    name = memo["founder"]["display_name"]
    return {
        "title": f"{WORDS[v['decision']]}: {name}",
        "body": f"{approx}{_pct(v['probability'])} chance of {TARGET[p['target']]}{horizon}. Tap to open the memo.",
        "url": f"/memos/{memo['memo_id']}",
        "tag": memo["memo_id"],
    }


def batch_payload(batch_id: str, items: list[dict], thresholds: dict, pol: dict | None) -> dict:
    r = policy.resolve(thresholds, pol)["policy"]
    counts = {"advance": 0, "escalate": 0, "pass": 0}
    done = failed = 0
    for it in items:
        if it["status"] == "failed":
            failed += 1
        if not it.get("distributions"):
            continue
        done += 1
        prob = policy.score(it["distributions"], r["target"], r["timeline_years"])
        counts[policy.decide(prob, r["advance_threshold"], r["pass_threshold"])] += 1
    body = f"{counts['advance']} to meet, {counts['escalate']} to look closer at, {counts['pass']} to pass."
    if failed:
        body += f" {failed} couldn't be screened."
    return {"title": f"Your list is screened ({done} founder{'s' if done != 1 else ''})", "body": body,
            "url": f"/batch?id={batch_id}", "tag": batch_id}
