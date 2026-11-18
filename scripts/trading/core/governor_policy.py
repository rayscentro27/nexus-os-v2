#!/usr/bin/env python3
"""Owner-approved (2026-11-15) narrow governor policy for Trading Core R1.

OANDA / service * / job type TRADING_PAPER_CERTIFICATION only. Usage allowed,
spend NOT allowed (money caps 0), concurrency 1, bounded request rate. Insert
only if absent — never reopens a policy that later reached HARD_STOP. Any other
OANDA job type remains denied (no policy). Live OANDA is additionally blocked
by the adapter, transport, and risk policy, independent of this record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parents[3])]

from nexus_agent_platform.resource_spend_governor import default_store  # noqa: E402

PROVIDER, SERVICE, JOB_TYPE = "OANDA", "*", "TRADING_PAPER_CERTIFICATION"
LIMITS = {
    "rate": {"requests": 30, "operations": 30, "window_seconds": 60},
    "usage": {"requests": 400, "api_calls": 400, "bytes": 5_000_000, "cost": 0},
    "money": {"per_job": 0, "per_day": 0, "per_month": 0},
}


def _ensure_local_without_resolver(store) -> dict:
    """Older LocalGovernorStore (no resolve/ensure API): insert only if the exact scope is absent."""
    out = {}
    for period in ("DAILY", "MONTHLY"):
        with store.connect() as db:
            row = db.execute("SELECT state,autonomous_usage_allowed,autonomous_spend_allowed,concurrency_limit FROM policies "
                             "WHERE provider=? AND service=? AND job_type=? AND budget_period=?", (PROVIDER, SERVICE, JOB_TYPE, period)).fetchone()
        created = row is None
        if created:
            store.set_policy(PROVIDER, SERVICE, JOB_TYPE, period, autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                             soft_limits=LIMITS, hard_limits=LIMITS, concurrency_limit=1, resource_creation_limit=0,
                             state="NORMAL", approval_required=False)
            with store.connect() as db:
                row = db.execute("SELECT state,autonomous_usage_allowed,autonomous_spend_allowed,concurrency_limit FROM policies "
                                 "WHERE provider=? AND service=? AND job_type=? AND budget_period=?", (PROVIDER, SERVICE, JOB_TYPE, period)).fetchone()
        out[period] = {"created": created, "provider": PROVIDER, "service": SERVICE, "job_type": JOB_TYPE, **dict(row)}
    return out


def ensure() -> dict:
    store = default_store()
    if not hasattr(store, "resolve_policy") and hasattr(store, "connect"):
        return _ensure_local_without_resolver(store)
    out = {}
    for period in ("DAILY", "MONTHLY"):
        current = store.resolve_policy(PROVIDER, SERVICE, JOB_TYPE, period)
        created = False
        if not current or current.get("job_type") != JOB_TYPE:
            created = store.ensure_policy(PROVIDER, SERVICE, JOB_TYPE, period, autonomous_usage_allowed=True,
                                          autonomous_spend_allowed=False, soft_limits=LIMITS, hard_limits=LIMITS,
                                          concurrency_limit=1, resource_creation_limit=0, state="NORMAL", approval_required=False)
            current = store.resolve_policy(PROVIDER, SERVICE, JOB_TYPE, period)
        out[period] = {"created": created, **{k: (current or {}).get(k) for k in ("provider", "service", "job_type", "state", "autonomous_usage_allowed", "autonomous_spend_allowed", "concurrency_limit")}}
    return out


if __name__ == "__main__":
    print(json.dumps(ensure(), indent=2))
