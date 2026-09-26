"""Canonical Finance foundation around the existing Finance engine.

This layer normalizes existing append-only records for read-only reporting. It
does not connect payment accounts, spend money, or turn estimates into facts.
"""
from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import persistence
from nexus_agent_platform.finance.engine import finance_preflight
from nexus_agent_platform.revenue_truth import build_revenue_snapshot

VALUE_CLASSES = frozenset({"ACTUAL", "ESTIMATED", "BUDGETED", "PROPOSED", "UNKNOWN"})
DIRECTIONS = frozenset({"REVENUE", "EXPENSE", "ASSET", "LIABILITY", "TRANSFER", "NON_CASH"})
REVENUE_STATES = frozenset({"VERIFIED_REALIZED", "INVOICED", "PENDING", "PROJECTED", "OPPORTUNITY_VALUE", "UNKNOWN"})
DEPARTMENTS = ("RESEARCH", "ALPHA", "MARKETING", "CREATIVE", "SYSTEMS", "LABS", "FINANCE", "CUSTOMER_SERVICE", "NOVA_HERMES", "CLYDE_FUNDING", "GRANTS", "TRADING", "GOCLEAR", "SHARED_INFRASTRUCTURE", "OTHER")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def financial_event(**fields: Any) -> dict[str, Any]:
    """Build and validate the canonical event shape; omitted fields stay null."""
    value_class = str(fields.get("value_class", "UNKNOWN")).upper()
    direction = str(fields.get("direction", "NON_CASH")).upper()
    if value_class not in VALUE_CLASSES:
        raise ValueError(f"invalid value_class: {value_class}")
    if direction not in DIRECTIONS:
        raise ValueError(f"invalid direction: {direction}")
    timestamp = fields.get("timestamp") or now()
    seed = json.dumps([timestamp, fields.get("event_type"), fields.get("source"), fields.get("source_receipt")], sort_keys=True, default=str)
    return {
        "financial_event_id": fields.get("financial_event_id") or "fev_" + hashlib.sha256(seed.encode()).hexdigest()[:24],
        "timestamp": timestamp, "event_type": fields.get("event_type", "UNKNOWN"),
        "department": fields.get("department", "OTHER"), "project_id": fields.get("project_id"),
        "campaign_id": fields.get("campaign_id"), "business_unit": fields.get("business_unit"),
        "provider": fields.get("provider"), "service": fields.get("service"), "model": fields.get("model"),
        "description": fields.get("description", ""), "vendor": fields.get("vendor"), "customer_id_if_allowed": fields.get("customer_id_if_allowed"), "amount": fields.get("amount"),
        "currency": fields.get("currency", "USD"), "value_class": value_class,
        "direction": direction, "source": fields.get("source", "UNKNOWN"),
        "cost_or_revenue": fields.get("cost_or_revenue", "UNKNOWN"), "actual_or_estimate": fields.get("actual_or_estimate", value_class),
        "fixed_or_variable": fields.get("fixed_or_variable", "UNKNOWN"), "one_time_or_recurring": fields.get("one_time_or_recurring", "UNKNOWN"),
        "reconciliation_status": fields.get("reconciliation_status", "UNRECONCILED"),
        "source_receipt": fields.get("source_receipt"), "confidence": fields.get("confidence", "UNKNOWN"),
        "verified": bool(fields.get("verified", False)), "notes": fields.get("notes"),
    }


def economic_request(*, requesting_department: str, business_reason: str,
                     current_limitation: str, proposed_spend: Any = "UNKNOWN",
                     expected_benefit: Any = "UNKNOWN", alternatives: list[str] | None = None,
                     labs_evidence: Any = "NOT_RUN", measurement_plan: Any = "UNKNOWN",
                     request_id: str | None = None) -> dict[str, Any]:
    """Create a Finance review request without granting spending authority."""
    department = str(requesting_department).upper()
    if department not in DEPARTMENTS:
        raise ValueError(f"invalid-requesting-department: {department}")
    row = {
        "schema_version": "nexus.finance-economic-request.v1",
        "request_id": request_id or f"fer_{hashlib.sha256((department + business_reason + current_limitation).encode()).hexdigest()[:20]}",
        "requesting_department": department, "business_reason": business_reason,
        "current_limitation": current_limitation, "proposed_spend": proposed_spend,
        "expected_benefit": expected_benefit, "alternatives": alternatives or [],
        "labs_evidence": labs_evidence, "measurement_plan": measurement_plan,
        "economic_analysis": "PENDING_FINANCE_REVIEW", "risk": "PENDING_FINANCE_REVIEW",
        "payback_if_estimable": "UNKNOWN", "recommended_test_budget": "UNKNOWN",
        "ray_approval_required": True, "approval_status": "NOT_AUTHORIZED",
        "created_at": now(), "production_mutation": False,
    }
    return persistence.append_record("finance_economic_requests", row)


def upgrade_proposal(*, upgrade_id: str, department: str, current_capability: str,
                     proposed_capability: str, current_cost: Any = "UNKNOWN",
                     proposed_cost: Any = "UNKNOWN", incremental_cost: Any = "UNKNOWN",
                     expected_benefit: Any = "UNKNOWN", expected_time_savings: Any = "UNKNOWN",
                     expected_revenue_impact: Any = "UNKNOWN", risk_reduction: Any = "UNKNOWN",
                     capacity_gain: Any = "UNKNOWN", alternatives: list[str] | None = None,
                     labs_evidence: Any = "REQUIRED", rollback: Any = "REQUIRED",
                     measurement_window: Any = "UNKNOWN") -> dict[str, Any]:
    department = str(department).upper()
    if department not in DEPARTMENTS:
        raise ValueError(f"invalid-department: {department}")
    return {
        "schema_version": "nexus.finance-upgrade-proposal.v1", "upgrade_id": upgrade_id,
        "department": department, "current_capability": current_capability,
        "proposed_capability": proposed_capability, "current_cost": current_cost,
        "proposed_cost": proposed_cost, "incremental_cost": incremental_cost,
        "expected_benefit": expected_benefit, "expected_time_savings": expected_time_savings,
        "expected_revenue_impact": expected_revenue_impact, "risk_reduction": risk_reduction,
        "capacity_gain": capacity_gain, "alternatives": alternatives or [],
        "labs_evidence": labs_evidence, "rollback": rollback,
        "measurement_window": measurement_window, "approval_status": "RAY_APPROVAL_REQUIRED",
        "created_at": now(), "purchase_authorized": False,
    }


def model_outcome_join(*, model_request_id: str | None = None, task_id: str | None = None,
                       department: str = "UNKNOWN", task_class: str = "UNKNOWN",
                       model: str = "UNKNOWN", provider: str = "UNKNOWN",
                       input_tokens: Any = "UNKNOWN", output_tokens: Any = "UNKNOWN",
                       estimated_cost: Any = "UNKNOWN", actual_cost: Any = "UNKNOWN",
                       retry_number: Any = "UNKNOWN", latency: Any = "UNKNOWN",
                       outcome_status: str = "UNKNOWN", output_valid: Any = "UNKNOWN",
                       success: Any = "UNKNOWN", failure_reason: Any = "UNKNOWN",
                       quality_signal: Any = "UNKNOWN", source: str = "UNKNOWN") -> dict[str, Any]:
    """Normalize one evidence-backed model-request/task/outcome relationship."""
    return {
        "schema_version": "nexus.finance-model-outcome-join.v1",
        "model_request_id": model_request_id, "task_id": task_id,
        "department": department, "task_class": task_class, "model": model,
        "provider": provider, "input_tokens": input_tokens, "output_tokens": output_tokens,
        "estimated_cost": estimated_cost, "actual_cost": actual_cost,
        "retry_number": retry_number, "latency": latency,
        "outcome_status": outcome_status, "output_valid": output_valid,
        "success": success, "failure_reason": failure_reason,
        "quality_signal": quality_signal, "source": source,
        "join_confidence": "HIGH" if model_request_id and task_id and success != "UNKNOWN" else "PARTIAL",
        "created_at": now(),
    }


def provider_invoice(**fields: Any) -> dict[str, Any]:
    """Normalize a future provider invoice; never creates an invoice fact."""
    return {
        "schema_version": "nexus.finance-provider-invoice.v1",
        "provider": fields.get("provider", "UNKNOWN"), "billing_period": fields.get("billing_period", "UNKNOWN"),
        "invoice_id": fields.get("invoice_id", "UNKNOWN"), "service": fields.get("service", "UNKNOWN"),
        "quantity": fields.get("quantity", "UNKNOWN"), "unit": fields.get("unit", "UNKNOWN"),
        "unit_price": fields.get("unit_price", "UNKNOWN"), "subtotal": fields.get("subtotal", "UNKNOWN"),
        "tax_if_present": fields.get("tax_if_present", "UNKNOWN"), "credits": fields.get("credits", "UNKNOWN"),
        "discounts": fields.get("discounts", "UNKNOWN"), "total": fields.get("total", "UNKNOWN"),
        "currency": fields.get("currency", "USD"), "source": fields.get("source", "UNKNOWN"),
        "actual_or_estimate": fields.get("actual_or_estimate", "ACTUAL"),
        "reconciliation_status": fields.get("reconciliation_status", "UNRECONCILED"),
        "created_at": now(),
    }


def transaction_reconciliation_record(**fields: Any) -> dict[str, Any]:
    """Normalize a future read-only bank/card transaction for review."""
    return {
        "schema_version": "nexus.finance-transaction-reconciliation.v1",
        "transaction_id": fields.get("transaction_id", "UNKNOWN"), "account_id": fields.get("account_id", "UNKNOWN"),
        "posted_date": fields.get("posted_date", "UNKNOWN"), "merchant": fields.get("merchant", "UNKNOWN"),
        "description": fields.get("description", "UNKNOWN"), "amount": fields.get("amount", "UNKNOWN"),
        "currency": fields.get("currency", "USD"), "pending": fields.get("pending", "UNKNOWN"),
        "category": fields.get("category", "UNKNOWN"), "provider_match": fields.get("provider_match", "UNKNOWN"),
        "invoice_match": fields.get("invoice_match", "UNKNOWN"), "department_match": fields.get("department_match", "UNKNOWN"),
        "campaign_match": fields.get("campaign_match", "UNKNOWN"), "confidence": fields.get("confidence", "UNKNOWN"),
        "review_required": fields.get("review_required", True),
        "classification": fields.get("classification", "UNKNOWN"),
        "created_at": now(),
    }


def reconcile_operational_invoice(*, estimated_cost: Any = "UNKNOWN", invoice_total: Any = "UNKNOWN",
                                 operational_usage: Any = "UNKNOWN", invoice_id: str = "UNKNOWN") -> dict[str, Any]:
    """Retain telemetry and invoice facts separately and calculate only safe variance."""
    variance = "UNKNOWN"
    if isinstance(estimated_cost, (int, float)) and isinstance(invoice_total, (int, float)):
        variance = invoice_total - estimated_cost
    return {
        "schema_version": "nexus.finance-operational-invoice-reconciliation.v1",
        "invoice_id": invoice_id, "estimated_operational_cost": estimated_cost,
        "actual_invoice_cost": invoice_total, "estimate_variance": variance,
        "unattributed_provider_cost": "UNKNOWN", "missing_operational_usage": "UNKNOWN",
        "duplicate_cost": "UNKNOWN", "credit_adjustment": "UNKNOWN",
        "actual_cash_source_of_truth": "PROVIDER_INVOICE_WHEN_VERIFIED",
        "operational_telemetry_role": "ATTRIBUTION_AND_DIAGNOSTICS",
        "reconciliation_status": "REVIEW_REQUIRED" if variance == "UNKNOWN" else "REQUIRES_REVIEW",
        "created_at": now(),
    }


def proposal_economics(*, proposal_id: str, owner: str, purpose: str,
                       one_time_cost: Any = "UNKNOWN", recurring_cost: Any = "UNKNOWN",
                       estimated_usage_cost: Any = "UNKNOWN", expected_value: Any = "UNKNOWN",
                       revenue_hypothesis: Any = "UNKNOWN", time_to_value: Any = "UNKNOWN",
                       alternatives: list[str] | None = None, free_option: Any = "UNKNOWN",
                       lower_cost_option: Any = "UNKNOWN", human_work_required: Any = "UNKNOWN",
                       recovery_burden: Any = "UNKNOWN", lock_in_risk: Any = "UNKNOWN",
                       evidence: Any = None, confidence: str = "UNKNOWN") -> dict[str, Any]:
    amounts = [one_time_cost, recurring_cost, estimated_usage_cost]
    if all(isinstance(value, (int, float)) and value == 0 for value in amounts):
        status = "ZERO_COST"
    elif any(value in ("UNKNOWN", None) for value in amounts):
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "REQUIRES_BUDGET_APPROVAL"
    return {"proposal_id": proposal_id, "owner": owner, "purpose": purpose,
            "one_time_cost": one_time_cost, "recurring_cost": recurring_cost,
            "estimated_usage_cost": estimated_usage_cost, "expected_value": expected_value,
            "revenue_hypothesis": revenue_hypothesis, "time_to_value": time_to_value,
            "alternatives": alternatives or [], "free_option": free_option,
            "lower_cost_option": lower_cost_option, "human_work_required": human_work_required,
            "recovery_burden": recovery_burden, "lock_in_risk": lock_in_risk,
            "evidence": evidence or [], "confidence": confidence,
            "economic_status": status, "purchase_authorized": False, "created_at": now()}


def _numeric(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _rollup_costs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actual_cash = sum(_numeric(row.get("money_spent_usd")) or 0 for row in rows if str(row.get("provenance", "")).upper() == "ACTUAL")
    department: dict[str, float] = {}
    for row in rows:
        amount = _numeric(row.get("money_spent_usd"))
        if amount is not None and str(row.get("provenance", "")).upper() == "ACTUAL":
            key = str(row.get("department") or "OTHER")
            department[key] = department.get(key, 0) + amount
    return {"actual_cash_expense_recorded_usd": actual_cash, "by_department_actual_usd": department,
            "row_count": len(rows), "unattributed_cost_rows": sum(1 for row in rows if not row.get("department") or row.get("department") == "UNKNOWN"),
            "scope": "recorded Finance receipts only; infrastructure provider bills are not inferred"}


def _model_evidence() -> dict[str, Any]:
    """Read existing token/cost receipts without treating estimates as actual."""
    # Keep the read-only certification bounded. These are the existing
    # receipt/report lanes that carry model usage; do not crawl every large
    # historical research artifact.
    files: list[Path] = []
    for lane in ("creative", "architecture", "finance", "hermes_model_cost_policy.json", "hermes_route_dominance_audit_latest.json"):
        target = ROOT / "reports" / lane
        if target.is_file(): files.append(target)
        elif target.is_dir(): files.extend(list(target.glob("**/*.json")) + list(target.glob("**/*.jsonl")))
    records = input_tokens = output_tokens = 0
    estimated_cost = 0.0
    actual_cost = 0.0
    for path in files:
        try:
            if path.stat().st_size > 8_000_000:
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.suffix == ".jsonl" else [path.read_text(encoding="utf-8", errors="ignore")]
            for line in lines:
                try: values = [json.loads(line)]
                except json.JSONDecodeError: continue
                stack = values
                while stack:
                    value = stack.pop()
                    if isinstance(value, dict):
                        if any(key in value for key in ("input_tokens", "output_tokens", "estimated_cost")):
                            records += 1
                            input_tokens += int(value.get("input_tokens") or 0) if isinstance(value.get("input_tokens"), (int, float)) else 0
                            output_tokens += int(value.get("output_tokens") or 0) if isinstance(value.get("output_tokens"), (int, float)) else 0
                            if isinstance(value.get("estimated_cost"), (int, float)): estimated_cost += float(value["estimated_cost"])
                        stack.extend(value.values())
                    elif isinstance(value, list): stack.extend(value)
        except OSError:
            continue
    return {"receipt_records_observed": records, "input_tokens_observed": input_tokens, "output_tokens_observed": output_tokens,
            "estimated_cost_usd_observed": estimated_cost, "actual_cost_usd_observed": actual_cost,
            "actual_cost_status": "NOT_REPORTED_BY_DISCOVERED_RECEIPTS", "estimate_status": "ESTIMATED_OR_ZERO_PROVIDER_CHARGE"}


def build_snapshot() -> dict[str, Any]:
    costs = persistence.read_records("finance_cost_receipts")
    resources = persistence.read_records("finance_resource_ledger")
    revenue = build_revenue_snapshot(period="30 DAYS")
    cost_rollup = _rollup_costs(costs)
    model = _model_evidence()
    actual_revenue = revenue["metrics"]["actual_revenue"]
    known_actual = cost_rollup["actual_cash_expense_recorded_usd"]
    return {
        "schema_version": "nexus.finance-snapshot.v1", "generated_at": now(), "currency": "USD",
        "verified_revenue": actual_revenue, "actual_expenses": {"value": known_actual, "value_class": "ACTUAL", "source": "finance_cost_receipts", "scope": "recorded receipts only"},
        "estimated_expenses": {"value": None, "value_class": "ESTIMATED", "status": "UNKNOWN", "source": "no authoritative monthly billing receipts"},
        "unknown_cost_items": ["Oracle billing", "Supabase billing", "Netlify billing", "OpenRouter/provider invoices", "software subscriptions", "storage/domains", "Meta production billing", "ad spend"],
        "operating_result": {"value": None, "status": "DATA_INCOMPLETE", "reason": "verified realized revenue and complete operating expenses are unavailable"},
        "department_costs": cost_rollup["by_department_actual_usd"], "project_campaign_costs": {}, "provider_costs": {},
        "model_cost_evidence": model, "resource_evidence_rows": len(resources),
        "reinvestment_capacity": {"status": "UNKNOWN", "verified_revenue_available": "UNKNOWN", "known_obligations": "UNKNOWN", "approved_budgets": "UNKNOWN", "authorization": "NONE"},
        "active_approved_budgets": [], "proposed_spend_awaiting_approval": [],
        "revenue_truth": {"actual": actual_revenue, "test_excluded": revenue.get("test_revenue"), "synthetic_excluded": revenue.get("synthetic_revenue"), "opportunity_value_excluded": revenue.get("opportunity_pipeline")},
        "authority": {"autonomous_purchases": False, "autonomous_subscriptions": False, "autonomous_ad_spend": False, "autonomous_financial_transfers": False},
        "data_quality": {"fake_financial_data_created": False, "projected_counted_as_actual": False, "unrealized_trading_counted_as_revenue": False, "unattributed_cost_allowed_visible": True},
    }


def run_canary() -> dict[str, Any]:
    proposal = proposal_economics(proposal_id="finance-foundation-canary", owner="Systems", purpose="read-only Finance foundation validation", one_time_cost=0, recurring_cost=0, estimated_usage_cost=0, expected_value="foundation certification", evidence=["existing Finance engine", "existing append-only ledgers"], confidence="HIGH")
    preflight = finance_preflight("finance-foundation-canary", department="FINANCE", initiative_id="finance-foundation", envelope={"MAX_CASH_COST_USD": 0}, estimated={"cash_cost_usd": 0}, authority="INTERNAL_ONLY", resource_state="UNKNOWN")
    return {"canary": "PASS_REAL_BOUNDED", "proposal": proposal, "preflight": preflight, "external_action_performed": False, "purchase_authorized": False}
