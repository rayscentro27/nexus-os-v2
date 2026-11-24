"""Governed $0 clients for Printify (GET-only) and Stripe (TEST key only).

Every call goes through the provider spend governor (provider_enforcement.execute)
under job type COMMERCE_CONVERSION_R1 with a zero-cost, non-billable estimate.
The owner-approved scoped policies (see ensure_policies) allow usage but never
spend. Secrets come from the credential control plane and are removed from the
process environment immediately after resolution.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / "scripts", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

JOB_TYPE = "COMMERCE_CONVERSION_R1"
LIMITS = {"rate": {"requests": 20, "operations": 20, "window_seconds": 60},
          "usage": {"requests": 300, "api_calls": 300, "bytes": 20_000_000, "cost": 0},
          "money": {"per_job": 0, "per_day": 0, "per_month": 0}}


class CommerceGuard(RuntimeError):
    pass


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def job_context(stage: str) -> None:
    run = os.environ.setdefault("NEXUS_COMMERCE_RUN_ID", uuid.uuid4().hex[:10])
    os.environ.update({"NEXUS_DURABLE_JOB_ID": f"commerce-conv-r1-{run}-{stage}-{uuid.uuid4().hex[:6]}",
                       "NEXUS_CORRELATION_ID": f"commerce-conv-r1-{run}", "NEXUS_DEPARTMENT": "COMMERCE", "NEXUS_JOB_TYPE": JOB_TYPE})


def ensure_policies() -> dict:
    """Owner-approved 2026-11-15: PRINTIFY + STRIPE, job type COMMERCE_CONVERSION_R1, usage yes, spend no. Insert-only."""
    from nexus_agent_platform.resource_spend_governor import default_store
    store = default_store(); out = {}
    for provider in ("PRINTIFY", "STRIPE"):
        for period in ("DAILY", "MONTHLY"):
            cur = store.resolve_policy(provider, "*", JOB_TYPE, period)
            created = False
            if not cur or cur.get("job_type") != JOB_TYPE:
                created = store.ensure_policy(provider, "*", JOB_TYPE, period, autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                                              soft_limits=LIMITS, hard_limits=LIMITS, concurrency_limit=1, resource_creation_limit=0,
                                              state="NORMAL", approval_required=False)
                cur = store.resolve_policy(provider, "*", JOB_TYPE, period)
            out[f"{provider}:{period}"] = {"created": created, "state": (cur or {}).get("state"),
                                           "spend_allowed": (cur or {}).get("autonomous_spend_allowed")}
    return out


def _secret(credential_id: str, alias_key: str) -> str:
    from nexus_agent_platform import credential_control_plane as ccp
    entry = ccp.registry_entry(credential_id)
    names = [entry.get("canonical_aliases", {}).get(alias_key), *entry.get("legacy_aliases", {}).get(alias_key, [])]
    names = [n for n in names if n]
    before = {n: os.environ.get(n) for n in names}
    try:
        ccp.apply_to_process(credential_id)
        value = next((os.environ.get(n) for n in names if os.environ.get(n)), "")
    finally:
        for n, v in before.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
    if not value:
        raise CommerceGuard(f"credential_missing:{credential_id}")
    return value


def _governed(provider: str, method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, Any]:
    from nexus_agent_platform.provider_enforcement import execute

    def op():
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, context=_ctx(), timeout=40) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read() or b"{}")
            except ValueError:
                data = {}
            err = data.get("error") if isinstance(data.get("error"), dict) else {"message": data.get("error") or data.get("message")}
            return e.code, {"error": {"type": (err or {}).get("type"), "message": str((err or {}).get("message", ""))[:200]}}

    path = urllib.parse.urlsplit(url).path
    return execute(provider, path.strip("/").split("/")[1] if "/" in path.strip("/") else "api", "PROVIDER_HTTP_REQUEST",
                   {"requests": 1, "api_calls": 1, "billable": False, "cost": 0.0}, op,
                   job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"), job_type=JOB_TYPE,
                   correlation_id=os.environ.get("NEXUS_CORRELATION_ID"), purpose=f"{method}:{path}:{uuid.uuid4().hex[:8]}")


class PrintifyReader:
    BASE = "https://api.printify.com/v1"

    def __init__(self, token: str | None = None) -> None:
        self._token = token or _secret("credential.printify.prod.v1", "api_token")

    def get(self, path: str) -> tuple[int, Any]:
        if not path.startswith("/"):
            raise CommerceGuard("bad_path")
        return _governed("PRINTIFY", "GET", self.BASE + path,
                         {"Authorization": f"Bearer {self._token}", "User-Agent": "Nexus-Commerce/1.0", "Accept": "application/json"}, None)


class StripeTest:
    BASE = "https://api.stripe.com/v1"

    def __init__(self, key: str | None = None) -> None:
        key = key or _secret("credential.stripe.payments.test.v1", "secret_key")
        if not key.startswith(("sk_test_", "rk_test_")):
            raise CommerceGuard("stripe_key_not_test_mode_refused")
        self._key = key

    def _call(self, method: str, path: str, params: dict | None = None) -> tuple[int, Any]:
        body = urllib.parse.urlencode(params or {}, doseq=True).encode() if method == "POST" else None
        url = self.BASE + path + ("?" + urllib.parse.urlencode(params or {}, doseq=True) if method == "GET" and params else "")
        status, data = _governed("STRIPE", method, url, {"Authorization": f"Bearer {self._key}", "Content-Type": "application/x-www-form-urlencoded"}, body)
        if isinstance(data, dict) and data.get("livemode") is True:
            raise CommerceGuard("stripe_live_object_returned_refused")
        return status, data

    def get(self, path: str, params: dict | None = None):
        return self._call("GET", path, params)

    def post(self, path: str, params: dict):
        return self._call("POST", path, params)
