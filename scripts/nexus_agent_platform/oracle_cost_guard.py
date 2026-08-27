"""Non-mutating Oracle zero-cost policy and optional read-only evidence hook."""
from __future__ import annotations
from typing import Any

POLICY = {"target_monthly_cost_usd": 0.0, "autonomous_provisioning": False, "autonomous_resize": False, "autonomous_paid_resource_creation": False, "autonomous_billing_changes": False}

def evaluate(cost_usd: float | None, *, fresh: bool = True) -> dict[str, Any]:
    if not fresh or cost_usd is None: status = "ORACLE_COST_UNKNOWN"
    elif cost_usd > 0: status = "ORACLE_COST_ALERT"
    else: status = "ORACLE_COST_HEALTHY"
    return {"status": status, "cost_usd": cost_usd, "fresh": fresh, "policy": POLICY, "positive_cost_blocks_expansion": status == "ORACLE_COST_ALERT", "mutation_performed": False}
