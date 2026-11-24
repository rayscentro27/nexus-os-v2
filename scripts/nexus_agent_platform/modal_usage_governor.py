"""Monthly Modal included-credit guard used before governed Modal dispatch."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/modal_usage_governor.json"


@dataclass(frozen=True)
class ModalBudgetDecision:
    monthly_budget_usd: float
    status: str
    band: str
    confirmed_usage_usd: float
    estimated_usage_usd: float
    reserved_usage_usd: float
    proposed_job_usd: float
    remaining_included_usd: float
    projected_fraction: float

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "band": self.band,
                "monthly_included_budget_usd": self.monthly_budget_usd,
                "confirmed_usage_usd": round(self.confirmed_usage_usd, 6),
                "estimated_usage_usd": round(self.estimated_usage_usd, 6),
                "reserved_usage_usd": round(self.reserved_usage_usd, 6),
                "proposed_job_usd": round(self.proposed_job_usd, 6),
                "remaining_included_usd": round(self.remaining_included_usd, 6),
                "projected_fraction": round(self.projected_fraction, 6),
                "observed_at": datetime.now(timezone.utc).isoformat()}


def _config() -> dict[str, Any]:
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if value.get("monthly_included_budget_usd") != 30.0:
        raise ValueError("MODAL_MONTHLY_BUDGET_CONFIG_INVALID")
    return value


def parse_billing_summary(payload: Any) -> float:
    """Extract provider-reported metered spend; credits are not subtracted."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("MODAL_BILLING_USAGE_UNKNOWN")
    candidates = (payload.get("metered_cost"), payload.get("metered_cost_usd"),
                  (payload.get("summary") or {}).get("metered_cost"))
    for value in candidates:
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    raise ValueError("MODAL_BILLING_USAGE_UNKNOWN")


def read_confirmed_monthly_usage(*, modal_bin: str = "modal", profile: str = "goclearonline",
                                timeout: int = 12) -> float:
    """Query the authenticated Modal CLI; captured output is never logged."""
    result = subprocess.run([modal_bin, "billing", "summary", "--for", "this month", "--json"],
        capture_output=True, text=True, timeout=timeout, check=False,
        env={**__import__("os").environ, "MODAL_PROFILE": profile})
    if result.returncode:
        raise RuntimeError("MODAL_BILLING_USAGE_UNAVAILABLE")
    return parse_billing_summary(result.stdout)


def evaluate_monthly_budget(*, proposed_job_usd: float, confirmed_usage_usd: float,
                            estimated_usage_usd: float = 0.0, reserved_usage_usd: float = 0.0,
                            job_cost_known: bool = True, usage_known: bool = True) -> ModalBudgetDecision:
    if not usage_known or not job_cost_known:
        return ModalBudgetDecision(30.0, "WAITING_APPROVAL", "UNKNOWN", max(0, confirmed_usage_usd),
            max(0, estimated_usage_usd), max(0, reserved_usage_usd), max(0, proposed_job_usd),
            0.0, 1.0)
    cfg = _config()
    budget = float(cfg["monthly_included_budget_usd"])
    values = (proposed_job_usd, confirmed_usage_usd, estimated_usage_usd, reserved_usage_usd)
    if any(float(value) < 0 for value in values):
        raise ValueError("NEGATIVE_MODAL_USAGE")
    projected = sum(float(value) for value in values)
    fraction = projected / budget
    limits = cfg["thresholds"]
    if fraction > limits["approval_fraction"]:
        status, band = "WAITING_APPROVAL", "OVER_BUDGET"
    elif fraction >= limits["conserve_fraction"]:
        status, band = "AUTO_ALLOWED", "CONSERVE"
    elif fraction >= limits["warning_fraction"]:
        status, band = "AUTO_ALLOWED", "WARNING"
    else:
        status, band = "AUTO_ALLOWED", "NORMAL"
    ceiling = float(cfg["autonomous_job_cost_ceiling_usd"])
    if proposed_job_usd > ceiling:
        status, band = "WAITING_APPROVAL", "JOB_CEILING"
    return ModalBudgetDecision(budget, status, band, float(confirmed_usage_usd),
        float(estimated_usage_usd), float(reserved_usage_usd), float(proposed_job_usd),
        max(0.0, budget - (confirmed_usage_usd + estimated_usage_usd + reserved_usage_usd)), fraction)


def preflight_modal_job(*, proposed_job_usd: float | None, confirmed_usage_usd: float | None,
                        estimated_usage_usd: float = 0.0, reserved_usage_usd: float = 0.0) -> dict[str, Any]:
    """Fail closed on missing usage/cost; safe for policy and UI read paths."""
    known = proposed_job_usd is not None and confirmed_usage_usd is not None
    decision = evaluate_monthly_budget(proposed_job_usd=float(proposed_job_usd or 0),
        confirmed_usage_usd=float(confirmed_usage_usd or 0), estimated_usage_usd=estimated_usage_usd,
        reserved_usage_usd=reserved_usage_usd, job_cost_known=proposed_job_usd is not None,
        usage_known=confirmed_usage_usd is not None)
    result = decision.as_dict()
    result["reason"] = "MONTHLY_MODAL_INCLUDED_CREDIT_POLICY"
    result["status"] = decision.status if known else "WAITING_APPROVAL"
    return result
