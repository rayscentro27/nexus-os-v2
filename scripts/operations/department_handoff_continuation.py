#!/usr/bin/env python3
"""Receiver-owned continuation over Nexus' existing handoff and request stores.

The canonical handoff remains ``nexus_department_handoffs``. Department goals
remain in ``company_goal_portfolio.json`` and executable requests remain in the
existing ``task_requests`` table. This module is a bounded consumer invoked by
the existing Active Operator cycle; it is not a scheduler or another queue.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "data/runtime/company_goal_portfolio.json"
sys.path.insert(0, str(ROOT / "scripts/operations"))
import nexus_handoff as handoffs  # noqa: E402
from nexus_agent_platform.research_followup_contract import build_contract as build_research_contract, question as research_question, persist_contract as persist_research_contract  # noqa: E402

ACTIVE = ("CREATED", "DELIVERED", "ACKNOWLEDGED", "PROCESSING", "FAILED_RETRYABLE")
PARENT_GOALS = {
    "ATLAS_OPPORTUNITY": ("opportunity.engine", "Opportunity"),
    "CLYDE_CREDIT": ("clyde.entity_readiness", "Clyde"),
    "LEDGER_FINANCE": ("commerce.billing_accounting", "Finance"),
    "FORGE_SYSTEMS": ("systems.modal_verification", "Systems"),
    "SYSTEMS": ("systems.modal_verification", "Systems"),
    "TRADING": ("trading.real_data", "Trading"),
    "MERCURY_TRADING": ("trading.real_data", "Trading"),
    "FUNDING": ("funding.workflow_expansion", "Funding"),
    "GRANTS": ("grants.intelligence", "Grants"),
    "MARKETING": ("marketing.creative_expansion", "Marketing"),
    "MIRA_MARKETING": ("marketing.creative_expansion", "Marketing"),
    "RESEARCH": ("research.company_intelligence", "Research"),
    "NOVA": ("portal.admin_control_center", "Operations"),
    "DEVELOPMENT_LABS": ("nexus.intent_program_compiler", "Labs"),
    "LABS": ("nexus.intent_program_compiler", "Labs"),
    "CREATIVE": ("media.youtube_video", "Creative"),
    "UPGRADE_CONTROL": ("nexus.intent_program_compiler", "Upgrade Control"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finance_followup_contract(goal_id: str, handoff_id: str | None, missing: list[str], subject_id: str | None = None) -> dict[str, Any]:
    """Build the bounded Finance evidence request against its existing goal."""
    specs = [
        ("What exactly is sold, who pays, what is the approved price, and is revenue one-time, recurring, commission, subscription, or mixed?", "APPROVED_OFFER_AND_PRICE", "INTERNAL_APPROVED_OFFER_RECORD", "Approved offer/pricing artifact; if absent, explicit NOT_FOUND.", True),
        ("Is there an applicable affiliate/referral program; what are payout amount/percentage, recurring terms, qualification, payment timing, clawbacks, exclusions, and minimums?", "OFFICIAL_AFFILIATE_TERMS", "OFFICIAL_PROGRAM_TERMS", "Current official terms tied to the program; if no program, evidence that none is configured.", False),
        ("What measured human labor, software/API/GPU, fulfillment, support, and operational dependencies are required per customer/order?", "MEASURED_DELIVERY_COST", "INTERNAL_COST_RECEIPTS_AND_PROVIDER_PRICING", "Measured internal time/cost or sourced current provider price, with units and period.", True),
        ("Which realistic organic and paid acquisition channels are evidenced, what competitor acquisition patterns are observable, and what is the lowest-cost valid demand test?", "ACQUISITION_AND_TEST_EVIDENCE", "PUBLIC_CHANNEL_EVIDENCE_AND_INTERNAL_TEST_PLAN", "Source-backed channel evidence; test must state cost and success/stop criteria.", True),
        ("What current customer demand, competitor/comparable pricing, complaints, and willingness-to-pay evidence exists for the target customer?", "DEMAND_COMPETITOR_AND_WTP", "CURRENT_PRIMARY_OR_REPUTABLE_MARKET_EVIDENCE", "Attributable, dated market evidence; demand proxies must not be represented as willingness to pay.", True),
        ("Given verified revenue and variable-cost inputs, what are revenue/customer, variable cost, gross margin, acquisition cost, contribution margin, and supported break-even assumptions?", "SOURCE_BACKED_UNIT_ECONOMICS", "FINANCE_CALCULATION_FROM_VERIFIED_INPUTS", "Transparent calculation with each input sourced or explicitly labeled as an assumption; no invented numbers.", True),
        ("What is the cheapest valid test, its success criteria, and its stop/change criteria?", "BOUNDED_TEST_DESIGN", "INTERNAL_TEST_PLAN_AND_EVIDENCE", "A reversible test plan with measurable thresholds and no unauthorized spend.", True),
    ]
    missing_text = " ".join(str(value).lower() for value in missing)
    if missing:
        relevant = set()
        if any(token in missing_text for token in ("revenue", "offer", "price", "payer", "model")): relevant.add(0)
        if any(token in missing_text for token in ("payout", "commission", "affiliate", "referral")): relevant.add(1)
        if any(token in missing_text for token in ("cost", "delivery", "service", "support", "fulfillment", "operating")): relevant.add(2)
        if any(token in missing_text for token in ("acquisition", "cac", "conversion", "channel")): relevant.add(3)
        if any(token in missing_text for token in ("demand", "willingness", "customer", "market", "competitor")): relevant.add(4)
        if any(token in missing_text for token in ("break-even", "break even", "margin", "unit economics", "gross economics", "economics")): relevant.add(5)
        if any(token in missing_text for token in ("test", "campaign_test_cost")): relevant.add(6)
        specs = [item for index, item in enumerate(specs) if index in relevant] or specs
    qs = [research_question(q, kind, source, minimum, blocking=blocking) for q, kind, source, minimum, blocking in specs]
    # Stable request identity is keyed to the same parent goal and question set;
    # requests with unchanged questions are reused by persistence.
    return build_research_contract(requesting_department="LEDGER_FINANCE",
        reason="Economics cannot be decided from the current record: Nexus/GoClear offer price, payout, delivery cost, acquisition, willingness-to-pay, and sourced unit economics are not established.",
        research_questions=qs, overall_evidence_required=missing,
        decision_unlocked_by_answers="Finance can return ECONOMICS_SUPPORTED, MORE_ECONOMIC_RESEARCH_REQUIRED with narrowed gaps, or ECONOMICS_NOT_SUPPORTED for this same opportunity goal.",
        return_to_department="LEDGER_FINANCE", return_to_goal_id=goal_id, parent_goal_id=goal_id,
        parent_handoff_id=handoff_id, requesting_worker="finance_economics_review",
        subject_type="OPPORTUNITY", subject_id=subject_id or handoff_id or goal_id,
        priority="P1", due_or_freshness_requirement="CURRENT; verify current official terms and dated market evidence")


def _read_portfolio() -> list[dict[str, Any]]:
    try:
        value = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
        return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []
    except (OSError, ValueError, TypeError):
        return []


def _write_portfolio(rows: list[dict[str, Any]]) -> None:
    PORTFOLIO.parent.mkdir(parents=True, exist_ok=True)
    temp = PORTFOLIO.with_suffix(".tmp")
    temp.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(PORTFOLIO)


def _receiver_goal(handoff: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    target = str(handoff.get("target_department") or "").upper()
    if target not in PARENT_GOALS:
        raise ValueError(f"unsupported_receiver:{target}")
    parent_id, department = PARENT_GOALS[target]
    handoff_id = str(handoff.get("handoff_id") or "")
    goal_id = "receiver." + hashlib.sha256(handoff_id.encode()).hexdigest()[:24]
    existing = next((row for row in rows if row.get("goal_id") == goal_id), None)
    timestamp = now()
    payload = handoff.get("payload") if isinstance(handoff.get("payload"), dict) else {}
    summary = str(payload.get("summary") or payload.get("finding") or handoff.get("topic") or "Review received evidence")
    next_action = _next_action(target, summary)
    goal = {
        **(existing or {}),
        "schema_version": "nexus.company-goal-portfolio.v1",
        "goal_kind": "HANDOFF_RECEIVER_GOAL",
        "goal_id": goal_id,
        "parent_goal_id": parent_id,
        "department": department,
        "owner_department": target,
        "owner": target,
        "statement": f"Process handoff {handoff_id}: {summary[:240]}",
        "goal_statement": f"Process handoff {handoff_id}: {summary[:240]}",
        "status": "ACTIVE",
        "current_stage": (existing or {}).get("current_stage", "RECEIVER_INTAKE"),
        "success_criteria": (existing or {}).get("success_criteria") or ([
            "Internal asset draft persisted",
            "Headless critique and revision state persisted",
            "External use remains approval gated",
        ] if target == "CREATIVE" else [
            "Evidence reviewed and decision/result persisted",
            "Next action persisted or all declared criteria verified",
        ]),
        "missing_criteria": (existing or {}).get("missing_criteria") or ["Evidence review", "Outcome and continuation"],
        "active_workstreams": sorted(set((existing or {}).get("active_workstreams") or []) | {handoff_id}),
        "handoff_ids": sorted(set((existing or {}).get("handoff_ids") or []) | {handoff_id}),
        "current_action": next_action,
        "next_action": next_action,
        "last_progress_at": (existing or {}).get("last_progress_at", timestamp),
        "updated_at": timestamp,
        "created_at": (existing or {}).get("created_at", timestamp),
        "authority": "INTERNAL_SAFE",
        "external_actions_allowed": False,
    }
    if existing:
        rows[rows.index(existing)] = goal
    else:
        rows.append(goal)
    parent = next((row for row in rows if row.get("goal_id") == parent_id), None)
    if parent:
        parent["status"] = "ACTIVE"
        parent["active_workstreams"] = sorted(set(parent.get("active_workstreams") or []) | {goal_id})
        parent["last_progress"] = timestamp
        parent["updated_at"] = timestamp
    return goal, parent_id


def _next_action(target: str, text: str) -> str:
    routes = {
        "ATLAS_OPPORTUNITY": "ASSESS_CUSTOMER_PROBLEM_DEMAND_ECONOMICS_AND_NEXT_EVIDENCE",
        "TRADING": "DESIGN_SOURCE_GROUNDED_TESTABLE_CANDIDATE_AND_IDENTIFY_MISSING_BACKTEST_INPUTS",
        "MERCURY_TRADING": "DESIGN_SOURCE_GROUNDED_TESTABLE_CANDIDATE_AND_IDENTIFY_MISSING_BACKTEST_INPUTS",
        "FORGE_SYSTEMS": "DEFINE_BOUNDED_CAPABILITY_EXPERIMENT_AND_SUCCESS_MEASURE",
        "DEVELOPMENT_LABS": "DEFINE_BOUNDED_CAPABILITY_EXPERIMENT_AND_SUCCESS_MEASURE",
        "LABS": "DEFINE_BOUNDED_CAPABILITY_EXPERIMENT_AND_SUCCESS_MEASURE",
        "CREATIVE": "CREATE_INTERNAL_ASSET_DRAFT_AND_RECORD_CRITIQUE_REVISION_STATE",
        "UPGRADE_CONTROL": "REVIEW_EVIDENCE_AND_RETURN_APPROVAL_OR_REPAIR_REQUIREMENTS",
        "SYSTEMS": "DIAGNOSE_SAFE_OPERATIONAL_STATE_AND_DEFINE_VERIFICATION_ACTION",
        "MARKETING": "DEFINE_AUDIENCE_POSITIONING_OFFER_CHANNEL_AND_MEASUREMENT_HYPOTHESIS",
        "MIRA_MARKETING": "DEFINE_AUDIENCE_POSITIONING_OFFER_CHANNEL_AND_MEASUREMENT_HYPOTHESIS",
        "RESEARCH": "REVIEW_FINDING_AND_DEFINE_BOUNDED_FOLLOWUP_QUESTION",
        "FUNDING": "VERIFY_ELIGIBILITY_EVIDENCE_AND_MISSING_INFORMATION",
        "GRANTS": "VERIFY_OFFICIAL_ELIGIBILITY_EVIDENCE_AND_MISSING_INFORMATION",
        "CLYDE_CREDIT": "ASSESS_READINESS_EVIDENCE_AND_IDENTIFY_MISSING_INFORMATION",
        "LEDGER_FINANCE": "ASSESS_FINANCIAL_IMPLICATIONS_WITHOUT_TRANSACTIONS",
        "NOVA": "SUMMARIZE_DURABLE_RESULT_AND_NEXT_ACTION",
    }
    if target not in routes:
        raise ValueError(f"no_safe_next_action:{target}")
    return routes[target]


def _parent_goal_status(goal: dict[str, Any]) -> str:
    """Read the durable root goal status for any candidate-level decision."""
    rows = _read_portfolio()
    parent_id = str(goal.get("parent_goal_id") or "")
    parent = next((row for row in rows if str(row.get("goal_id")) == parent_id), None)
    return str((parent or {}).get("status") or ("NOT_LINKED" if not parent_id else "NOT_FOUND")).upper()


def _rejection_contract(*, reason: str, evidence: list[Any], failed_criteria: list[str],
                        what_was_tested: str, what_was_observed: str,
                        what_would_change_decision: str, next_action: str,
                        next_action_owner: str, parent_goal_status: str) -> dict[str, Any]:
    """Required auditable explanation for candidate/promotion rejections."""
    return {
        "reason": reason,
        "evidence": evidence or [{"status": "NOT_PROVIDED", "detail": "No source evidence was attached to this bounded intake."}],
        "failed_criteria": failed_criteria,
        "what_was_tested": what_was_tested,
        "what_was_observed": what_was_observed,
        "what_would_change_the_decision": what_would_change_decision,
        "next_action": next_action,
        "next_action_owner": next_action_owner,
        "parent_goal_status": parent_goal_status,
    }


def _require_rejection_contract(result: dict[str, Any]) -> None:
    rejected = str(result.get("decision") or result.get("status") or "").upper() in {
        "REJECT", "REJECTED", "REJECT_CANDIDATE", "REJECT_WITH_REPAIR"
    }
    if not rejected:
        return
    contract = result.get("rejection")
    required = ("reason", "evidence", "failed_criteria", "what_was_tested", "what_was_observed",
                "what_would_change_the_decision", "next_action", "next_action_owner", "parent_goal_status")
    missing = [key for key in required if not isinstance(contract, dict) or
               key not in contract or contract.get(key) in (None, "", [])]
    if missing:
        raise ValueError("rejection_contract_incomplete:" + ",".join(missing))


def _failure_strategy_action(goal: dict[str, Any], previous_order: dict[str, Any] | None) -> str:
    stages = [
        ("RETRY", "RETRY_WITH_BOUNDED_BACKOFF"),
        ("DIAGNOSE", "DIAGNOSE_FAILURE_AND_RECORD_CAUSE"),
        ("REPAIR", "APPLY_REVERSIBLE_REPAIR_AND_VERIFY"),
        ("ALTERNATE_PATH", "SELECT_DIFFERENT_APPROVED_TOOL_PROVIDER_OR_METHOD"),
        ("CROSS_DEPARTMENT_HELP", "REQUEST_BOUNDED_CROSS_DEPARTMENT_HELP"),
        ("WAIT_HUMAN", "WAIT_FOR_EXPLICIT_HUMAN_ONLY_ACTION"),
    ]
    prior_status = str(((previous_order or {}).get("payload") or {}).get("result", {}).get("status") or
                       (goal.get("last_result") or {}).get("status") or "").upper()
    if prior_status not in {"FAILED", "FAIL", "BLOCKED", "TIMEOUT", "PROVIDER_FAILURE"}:
        goal["failure_strategy_stage"] = "DIAGNOSE"
        return "DIAGNOSE_PREVIOUS_RESULT_AND_SELECT_ALTERNATE_APPROACH"
    current = str(goal.get("failure_strategy_stage") or "RETRY").upper()
    names = [name for name, _ in stages]
    next_index = min(names.index(current) + 1, len(stages) - 1) if current in names else 1
    name, action = stages[next_index]
    if name == "WAIT_HUMAN" and not goal.get("human_action_required"):
        name, action = stages[next_index - 1]
    goal["failure_strategy_stage"] = name
    goal["failure_attempt_count"] = int(goal.get("failure_attempt_count", 0)) + 1
    if name == "WAIT_HUMAN":
        goal["status"] = "WAITING_HUMAN"
        goal["human_action_required"] = True
        goal["resume_stage"] = goal.get("current_stage") or "CONTINUATION"
    return action


def _task_request_for(handoff_id: str) -> dict[str, Any] | None:
    status, rows = handoffs.rest("GET", "task_requests?select=id,payload,status&limit=1000")
    if status != 200 or not isinstance(rows, list):
        raise RuntimeError(f"task_request_read_failed:{status}")
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("handoff_id") == handoff_id and payload.get("request_kind") == "DEPARTMENT_HANDOFF_WORK_ORDER":
            return {**row, "_preexisting": True}
    return None


def _work_order(handoff: dict[str, Any], goal: dict[str, Any], action: str) -> dict[str, Any]:
    handoff_id = str(handoff["handoff_id"])
    existing = _task_request_for(handoff_id)
    if existing:
        return existing
    row = {
        "task_type": "department_handoff_continuation",
        "requested_by": "nexus_continuous_operating_kernel",
        "sensitivity": "internal_summary",
        "allowed_data_scope": ["handoff_payload", "linked_goal", "source_evidence"],
        "forbidden_data": ["credentials", "tenant_secrets", "live_trade_execution", "real_spending", "external_publishing"],
        "assigned_worker_type": "nexus_department_continuation_worker",
        "hermes_visibility": "summary",
        "status": "requested",
        "payload": {
            "request_kind": "DEPARTMENT_HANDOFF_WORK_ORDER",
            "handoff_id": handoff_id,
            "goal_id": goal["goal_id"],
            "parent_goal_id": goal.get("parent_goal_id"),
            "department": goal["owner_department"],
            "action": action,
            "eligibility": "ELIGIBLE_INTERNAL_READ_ONLY",
            "owner": goal["owner_department"],
            "external_actions_allowed": False,
        },
    }
    status, result = handoffs.rest("POST", "task_requests", body=[row], prefer="return=representation")
    if status not in (200, 201) or not isinstance(result, list) or not result:
        # A concurrent intake may have won. Re-read before failing.
        existing = _task_request_for(handoff_id)
        if existing:
            return existing
        raise RuntimeError(f"task_request_insert_failed:{status}:{str(result)[:160]}")
    return {**result[0], "_preexisting": False}


def reconcile_active_handoffs(*, limit: int = 200, only_unowned: bool = False,
                              handoff_id: str | None = None) -> dict[str, Any]:
    unowned = "&or=(parent_goal_id.is.null,receiving_work_order_id.is.null,action_receipt.is.null)" if only_unowned else ""
    selected = f"&handoff_id=eq.{handoff_id}" if handoff_id else ""
    status, rows = handoffs.rest("GET", f"{handoffs.TABLE}?status=in.({','.join(ACTIVE)}){selected}{unowned}&select=*&order=created_at.asc&limit={limit}")
    if status != 200 or not isinstance(rows, list):
        raise RuntimeError(f"handoff_read_failed:{status}:{str(rows)[:200]}")
    goal_rows = _read_portfolio()
    by_goal = {str(row.get("goal_id")): row for row in goal_rows}
    result = {"active_handoffs": len(rows), "reconciled": 0, "goals_attached": 0, "goals_created": 0,
              "work_orders_created": 0, "next_actions_created": 0, "invalid": 0, "errors": []}
    for row in rows:
        handoff_id = str(row.get("handoff_id") or "")
        target = str(row.get("target_department") or "").upper()
        if not handoff_id or not row.get("topic") or target not in PARENT_GOALS:
            result["invalid"] += 1
            result["errors"].append({"handoff_id": handoff_id, "reason": "missing_identity_topic_or_receiver"})
            continue
        try:
            prior_goal = row.get("payload", {}).get("continuation", {}).get("receiver_goal_id") if isinstance(row.get("payload"), dict) else None
            goal, parent_id = _receiver_goal(row, goal_rows)
            _write_portfolio(goal_rows)
            if prior_goal:
                result["goals_attached"] += 1
            else:
                result["goals_created"] += 1
            by_goal[goal["goal_id"]] = goal
            action = str(goal.get("next_action") or _next_action(target, str(row.get("topic"))))
            current_payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            current_continuation = current_payload.get("continuation") if isinstance(current_payload.get("continuation"), dict) else {}
            if (row.get("parent_goal_id") == parent_id and row.get("receiving_work_order_id")
                    and row.get("action_receipt") and current_continuation.get("receiver_goal_id") == goal["goal_id"]
                    and current_continuation.get("next_action")):
                result["reconciled"] += 1
                result["next_actions_created"] += 1
                continue
            order = _work_order(row, goal, action)
            result["work_orders_created"] += int(not order.get("_preexisting", True))
            work_order_id = str(order.get("id") or "")
            if not work_order_id:
                raise RuntimeError("task_request_missing_id")
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            continuation = payload.get("continuation") if isinstance(payload.get("continuation"), dict) else {}
            continuation.update({"receiver_goal_id": goal["goal_id"], "parent_goal_id": parent_id,
                                 "work_order_id": work_order_id, "next_action": action,
                                 "owner_department": target, "current_stage": "OWNED_WORK_READY",
                                 "acknowledgment_requires_owned_work": True})
            payload["continuation"] = continuation
            receipt = f"task_requests:{work_order_id}"
            updates = {"parent_goal_id": parent_id, "receiving_work_order_id": work_order_id,
                       "action_receipt": receipt, "payload": payload, "updated_at": now()}
            patch_status, patched = handoffs.rest("PATCH", f"{handoffs.TABLE}?handoff_id=eq.{handoff_id}", body=updates, prefer="return=representation")
            if patch_status not in (200, 204):
                raise RuntimeError(f"handoff_link_patch_failed:{patch_status}:{str(patched)[:160]}")
            if row.get("status") == "CREATED":
                handoffs.mark_delivered(handoff_id)
            if row.get("status") in {"CREATED", "DELIVERED"}:
                acknowledgment = handoffs.acknowledge(handoff_id, acknowledged_by=target,
                    note="Receiver goal, durable work order, and next action were read back before acknowledgment.")
                if acknowledgment.get("status") != "ACKNOWLEDGED":
                    raise RuntimeError(f"acknowledgment_rejected:{acknowledgment}")
            check = handoffs.get_handoff(handoff_id) or {}
            if check.get("parent_goal_id") != parent_id or check.get("receiving_work_order_id") != work_order_id or check.get("action_receipt") != receipt:
                raise RuntimeError("handoff_link_readback_mismatch")
            if check.get("status") == "ACKNOWLEDGED":
                cont = ((check.get("payload") or {}).get("continuation") or {})
                if not cont.get("receiver_goal_id") or not cont.get("next_action"):
                    raise RuntimeError("acknowledged_without_owned_action")
            result["reconciled"] += 1
            result["next_actions_created"] += 1
        except Exception as exc:  # keep other handoffs moving
            result["errors"].append({"handoff_id": handoff_id, "reason": str(exc)[:220]})
    _write_portfolio(goal_rows)
    return result


def _analyze(handoff: dict[str, Any], goal: dict[str, Any]) -> dict[str, Any]:
    target = str(handoff.get("target_department") or "").upper()
    payload = handoff.get("payload") if isinstance(handoff.get("payload"), dict) else {}
    finding = payload.get("summary") or payload.get("finding") or payload.get("extraction") or handoff.get("topic") or ""
    if isinstance(finding, dict):
        finding = json.dumps(finding, sort_keys=True, default=str)[:1000]
    evidence_refs = list(handoff.get("source_ids") or []) + list(handoff.get("artifact_refs") or [])
    safe_base = {"status": "PARTIAL", "department": target, "goal_id": goal.get("goal_id"),
                 "handoff_id": handoff.get("handoff_id"), "input_summary": str(finding)[:1200],
                 "evidence_refs": evidence_refs, "external_action_performed": False,
                 "live_trading": False, "real_spending": False, "external_publishing": False}
    if target == "ATLAS_OPPORTUNITY":
        if str(payload.get("candidate_decision") or "").upper() == "REJECT_CANDIDATE":
            next_action = "ROTATE_TO_ANOTHER_OPPORTUNITY_CANDIDATE"
            rejection = _rejection_contract(
                reason=str(payload.get("rejection_reason") or "Bounded canary marked this candidate for rejection; the available intake does not establish sufficient demand or economics."),
                evidence=evidence_refs,
                failed_criteria=list(payload.get("failed_criteria") or ["DEMAND_EVIDENCE_NOT_ESTABLISHED", "UNIT_ECONOMICS_NOT_VERIFIED"]),
                what_was_tested=str(payload.get("what_was_tested") or "Reviewed only the attached Research handoff and its cited source references; no customer interview, paid test, or external validation was performed."),
                what_was_observed=str(payload.get("what_was_observed") or "The available Research packet does not establish customer demand or verified unit economics."),
                what_would_change_decision=str(payload.get("what_would_change_decision") or "Verified target-customer demand plus source-backed unit economics that meet the opportunity goal's success criteria."),
                next_action=next_action, next_action_owner="ATLAS_OPPORTUNITY",
                parent_goal_status=_parent_goal_status(goal),
            )
            return {**safe_base, "status": "REJECT_CANDIDATE", "decision": "REJECT_CANDIDATE",
                    "candidate_status": "REJECTED", "broader_goal_status": rejection["parent_goal_status"],
                    "rejection": rejection,
                    "analysis": {"reason": rejection["reason"], "external_validation": False},
                    "next_action": next_action}
        required_validation = ("customer_problem_evidence", "demand_evidence", "competition_evidence", "economics_evidence")
        validation_present = {key: payload.get(key) for key in required_validation}
        qualified = bool(str(finding).strip() and evidence_refs and all(validation_present.values()))
        decision = "ADVANCE" if qualified else "MORE_RESEARCH_REQUIRED"
        result = {**safe_base, "status": decision, "decision": decision,
                "analysis": {"problem_statement": "Candidate signal requires source-grounded customer/problem validation.",
                             "customer_problem_definition": validation_present["customer_problem_evidence"] or "NOT_ESTABLISHED_BY_INTAKE",
                             "demand_evidence": validation_present["demand_evidence"] or "NOT_ESTABLISHED_BY_INTAKE",
                             "target_customer": payload.get("target_audience") or "TO_BE_VALIDATED_WITH_CUSTOMERS",
                             "competition": validation_present["competition_evidence"] or "NOT_ASSESSED",
                             "economics": validation_present["economics_evidence"] or "NOT_VERIFIED",
                             "affiliate_possibility": payload.get("affiliate_possibility") or "ASSESS_AFTER_DEMAND_AND_PROGRAM_VERIFICATION",
                             "service_possibility": payload.get("service_possibility") or "TO_BE_ASSESSED",
                             "consulting_education_possibility": payload.get("consulting_education_possibility") or "TO_BE_ASSESSED",
                             "software_automation_possibility": payload.get("software_automation_possibility") or "TO_BE_ASSESSED",
                             "distribution_hypothesis": "Owned search/video content and partner channels; unvalidated.",
                             "business_model_alternatives": ["affiliate", "service", "consulting/education", "software/automation"],
                             "offer_concept": "Draft a problem-specific offer only after demand checks.",
                             "economics": "NOT_VERIFIED",
                             "minimum_viable_test": {"method": "cost-free interview or intent signal", "spend": 0, "publishing": False},
                             "success_criteria": ["customer problem repeated by target users", "demand evidence recorded", "unit economics estimated with sources"],
                             "validation_inputs": validation_present,
                             "external_validation": False},
                "next_action": "RESEARCH_CUSTOMER_DEMAND_COMPETITORS_AND_UNIT_ECONOMICS" if decision != "ADVANCE" else "DEFINE_NO_SPEND_MINIMUM_VIABLE_TEST"}
        if decision == "MORE_RESEARCH_REQUIRED":
            missing = [key for key, value in validation_present.items() if not value]
            labels = {"customer_problem_evidence": "customer problem and target customer", "demand_evidence": "current demand and willingness-to-pay evidence", "competition_evidence": "competitors and current alternatives", "economics_evidence": "monetization and source-backed economics"}
            questions = [research_question(f"Establish {labels[key]} for this opportunity: {str(finding)[:180]}",
                "SOURCE_BACKED_OPPORTUNITY_EVIDENCE", "CUSTOMER_OR_OFFICIAL_MARKET_SOURCE",
                f"Provide attributable, dated evidence for {labels[key]}; label unknowns and assumptions.") for key in missing]
            if not questions:
                questions = [research_question("Add independently attributable source evidence for this candidate before advancement.", "INDEPENDENT_SOURCE_EVIDENCE", "PRIMARY_OR_REPUTABLE_SOURCE", "At least one source directly supporting the candidate inputs.")]
            contract = build_research_contract(requesting_department="ATLAS_OPPORTUNITY",
                reason="The candidate cannot advance until the listed demand and market evidence gaps are resolved.",
                research_questions=questions, overall_evidence_required=missing,
                decision_unlocked_by_answers="Resume this same Opportunities receiver goal and decide ADVANCE, MORE_RESEARCH_REQUIRED with narrowed questions, or REJECT_CANDIDATE.",
                return_to_department="ATLAS_OPPORTUNITY", return_to_goal_id=str(goal.get("goal_id") or ""),
                parent_goal_id=str(goal.get("goal_id") or ""), parent_handoff_id=handoff.get("handoff_id"),
                requesting_worker="opportunities_candidate_review", subject_type="OPPORTUNITY", subject_id=str(goal.get("goal_id") or ""), priority="P1")
            result["research_followup_contract"] = persist_research_contract(contract)
    if target in {"LEDGER_FINANCE", "FINANCE"}:
        packet = payload.get("opportunity_packet") if isinstance(payload.get("opportunity_packet"), dict) else {}
        raw_economics = payload.get("economics") if isinstance(payload.get("economics"), dict) else packet.get("economics")
        raw_economics = raw_economics if isinstance(raw_economics, dict) else {}
        evidence_fields = (
            "revenue_model", "commission_or_payout", "recurring_revenue", "operating_costs",
            "service_cost", "campaign_test_cost", "customer_acquisition_assumptions",
            "gross_economics", "break_even", "unit_economics",
        )
        reviewed = {key: raw_economics.get(key) for key in evidence_fields}
        supported_fields = [key for key, value in reviewed.items() if value not in (None, "", "UNKNOWN", "NOT_VERIFIED")]
        source_refs = [str(value) for value in (payload.get("economic_evidence_refs") or packet.get("economic_evidence_refs") or []) if value]
        explicit_unsupported = raw_economics.get("evidence_decision") == "ECONOMICS_NOT_SUPPORTED"
        supported = len(supported_fields) >= 7 and bool(source_refs) and all(
            reviewed[key] not in (None, "", "UNKNOWN", "NOT_VERIFIED")
            for key in ("revenue_model", "operating_costs", "campaign_test_cost", "customer_acquisition_assumptions", "unit_economics"))
        decision = "ECONOMICS_NOT_SUPPORTED" if explicit_unsupported else "ECONOMICS_SUPPORTED" if supported else "MORE_ECONOMIC_RESEARCH_REQUIRED"
        missing = [key for key, value in reviewed.items() if value in (None, "", "UNKNOWN", "NOT_VERIFIED")]
        return {**safe_base, "status": decision, "decision": decision,
                "economics_review": {"reviewed_fields": reviewed, "supported_fields": supported_fields,
                    "missing_evidence": missing, "evidence_refs": source_refs,
                    "assumptions": raw_economics.get("assumptions", []),
                    "unsupported_numeric_values_invented": False,
                    "reason": "Source-backed economics are incomplete." if decision == "MORE_ECONOMIC_RESEARCH_REQUIRED" else "Evidence supports the stated economics." if supported else str(raw_economics.get("reason") or "Source evidence does not support the proposed economics."),
                    "test_cost": reviewed.get("campaign_test_cost")},
                "next_action": "RETURN_ECONOMICS_REVIEW_TO_OPPORTUNITIES" if decision != "MORE_ECONOMIC_RESEARCH_REQUIRED" else "RESEARCH_MISSING_ECONOMIC_EVIDENCE",
                "research_questions": missing if decision == "MORE_ECONOMIC_RESEARCH_REQUIRED" else []}
        if decision == "MORE_ECONOMIC_RESEARCH_REQUIRED":
            goal_id = str(((handoff.get("payload") or {}).get("continuation") or {}).get("receiver_goal_id") or goal.get("goal_id") or "")
            if not goal_id:
                raise ValueError("more-economic-research-requires-originating-goal")
            source_subject = payload.get("opportunity_id") or payload.get("finding_id") or ((payload.get("opportunity_packet") or {}).get("opportunity_id") if isinstance(payload.get("opportunity_packet"), dict) else None)
            contract = _finance_followup_contract(goal_id, handoff.get("handoff_id"), missing, str(source_subject) if source_subject else None)
            result["research_followup_contract"] = persist_research_contract(contract)
        return result
    if target in {"TRADING", "MERCURY_TRADING"}:
        # An indicator/source handoff is not permission to substitute a canned
        # strategy (the former SMA fixture was unrelated to many incoming
        # Trading cases). Only a complete, explicitly Mercury-authored spec can
        # advance to the deterministic backtest gate.
        spec = payload.get("mercury_strategy_spec")
        required = ("market", "timeframe", "long_entry", "short_entry", "exit_logic",
                    "stop_loss", "take_profit", "trade_invalidation", "position_risk",
                    "session_filter", "transaction_cost_assumption", "slippage_assumption")
        missing = [key for key in required if not isinstance(spec, dict) or spec.get(key) in (None, "", [])]
        if missing:
            return {**safe_base, "status": "MORE_RESEARCH_REQUIRED", "decision": "MORE_RESEARCH_REQUIRED",
                "candidate": {"candidate_type": "SOURCE_COMPONENT", "source_derived": {
                    "rules": "INDICATOR_CLAIMS_ONLY; NO_COMPLETE_STRATEGY_SPEC_RECEIVED",
                    "attribution": "VIDEO_AND_PUBLIC_SOURCE_CLAIMS_REMAIN_UNVERIFIED"}},
                "missing_strategy_components": missing,
                "backtest_started": False, "live_trading": False,
                "research_case_response": {"status": "MORE_RESEARCH_REQUIRED",
                    "specific_question": "Mercury: provide a complete source-grounded Wick Sequence Breakout strategy hypothesis with explicit market, timeframe, long/short entries, exits, stop/target, invalidation, position risk, session filter, costs and slippage; identify every Nexus-designed assumption.",
                    "why_needed": "The received source is an indicator and reported backtest claims do not specify a reproducible Nexus ruleset. The prior canned SMA fixture did not derive from this case and is not accepted.",
                    "expected_evidence": "A validated mercury_strategy_spec tied to the Research Case and source IDs, with every required field filled, source-derived facts separated from Mercury assumptions, and no live-trading authority.",
                    "return_to_goal_id": str(goal.get("goal_id") or "")},
                "next_action": "MERCURY_PROVIDE_CASE_SPECIFIC_STRATEGY_OR_NARROW_MISSING_INPUTS"}
        return {**safe_base, "status": "STRATEGY_SPEC_RECEIVED_NOT_BACKTESTED",
                "decision": "CONTINUE_TO_DETERMINISTIC_BACKTEST_GATE", "candidate": spec,
                "backtest_started": False, "live_trading": False,
                "next_action": "VALIDATE_MARKET_DATA_AND_RUN_BOUNDED_DETERMINISTIC_HISTORICAL_BACKTEST"}
    if target in {"FORGE_SYSTEMS", "DEVELOPMENT_LABS", "LABS"}:
        if handoff.get("handoff_type") == "UPGRADE_REPAIR_RETURN":
            return {**safe_base, "status": "REPAIR_ACTION_CREATED", "experiment": {
                        "hypothesis": "Apply the exact repair returned by Upgrade Control, then re-run isolated validation.",
                        "required_repair": payload.get("required_repair") or "Attach missing benchmark/security/rollback evidence.",
                        "execution_state": "READY_FOR_BOUNDED_REPAIR", "production_change": False},
                    "next_action": "REPAIR_IN_ISOLATED_LABS_AND_RESUBMIT_VALIDATION"}
        return {**safe_base, "status": "EXPERIMENT_READY", "experiment": {
                    "hypothesis": f"Evaluate capability implied by: {str(finding)[:400]}",
                    "method": "bounded read-only comparison or sandboxed reproduction",
                    "success_criteria": ["reproducible result", "resource ceiling recorded", "no production mutation"],
                    "execution_state": "READY_FOR_BOUNDED_RUN", "production_change": False},
                "next_action": "RUN_BOUNDED_EXPERIMENT_AND_RECORD_RESULT"}
    if target in {"UPGRADE_CONTROL"}:
        if str(payload.get("review_decision") or "").upper() == "APPROVE" and evidence_refs:
            return {**safe_base, "status": "APPROVED_FOR_SYSTEMS_REVIEW", "decision": "APPROVE",
                    "review": {"evidence": evidence_refs, "production_deployment": False,
                               "next_validation": "Systems verifies deployment plan under existing production gate."},
                    "next_action": "SYSTEMS_REVIEW_APPROVED_CHANGE_WITHOUT_DEPLOYING"}
        next_action = "RETURN_REPAIR_REQUIREMENT_TO_LABS"
        reason = "Intake does not include the evidence required to certify promotion readiness."
        required_repair = "Attach benchmark, security, compatibility, and rollback evidence."
        next_validation = "Return to Labs for a bounded isolated revalidation."
        rejection = _rejection_contract(
            reason=reason, evidence=evidence_refs,
            failed_criteria=["BENCHMARK_EVIDENCE_MISSING", "SECURITY_REVIEW_MISSING", "COMPATIBILITY_EVIDENCE_MISSING", "ROLLBACK_EVIDENCE_MISSING"],
            what_was_tested="Checked the submitted handoff references for benchmark, security, compatibility, and rollback certification evidence; no production deployment or mutation was attempted.",
            what_was_observed="The submitted packet lacks one or more required promotion evidence artifacts.",
            what_would_change_decision="Labs supplies the required evidence and the bounded isolated revalidation meets the promotion criteria.",
            next_action=next_action, next_action_owner="LABS", parent_goal_status=_parent_goal_status(goal),
        )
        return {**safe_base, "status": "REJECT_WITH_REPAIR", "decision": "REJECT_WITH_REPAIR",
                "rejection": rejection,
                "review": {"evidence": evidence_refs, "reason": reason,
                           "required_repair": required_repair, "next_validation": next_validation},
                "next_action": next_action}
    if target in {"SYSTEMS"}:
        if handoff.get("handoff_type") == "CANARY":
            return {**safe_base, "status": "RECOVERY_VERIFIED", "incident": {
                        "diagnosis": "Synthetic reversible canary only; no production service was changed.",
                        "repair": "No-op fallback preserved known-good configuration.",
                        "verification": "bounded read-only health state recorded", "closed": True},
                    "next_action": "CONTINUE_NORMAL_SYSTEM_HEALTH_MONITORING"}
        if handoff.get("handoff_type") == "UPGRADE_APPROVAL_SYSTEMS_REVIEW":
            return {**safe_base, "status": "SYSTEMS_REVIEW_READY", "systems_review": {
                        "approved_candidate_received": True, "deployment_performed": False,
                        "verification_required": True, "production_gate_preserved": True},
                    "next_action": "VERIFY_APPROVED_CHANGE_PLAN_AND_ROLLBACK_WITHOUT_DEPLOYING"}
        return {**safe_base, "status": "RECOVERY_VERIFIED", "incident": {
                    "diagnosis": "Operational report intake only; production state was not changed.",
                    "repair": "No repair was attempted without an incident-specific reversible repair plan.",
                    "verification": "Existing evidence requires Systems validation", "closed": False},
                "next_action": "VERIFY_REPORTED_SYSTEM_STATE_THEN_REPAIR_OR_REROUTE"}
    if target in {"MARKETING", "MIRA_MARKETING"}:
        return {**safe_base, "status": "BRIEF_READY", "brief": {
                    "target_audience": "Evidence-dependent; validate before selection.",
                    "positioning": "Problem-led, source-qualified hypothesis.",
                    "offer": "Draft-only; no prices or claims are verified.",
                    "channel_hypothesis": ["owned content", "search", "YouTube"],
                    "campaign_concept": "Create an internal educational readiness concept that explains evidence-backed preparation steps and names unresolved questions; do not imply approval or funding outcomes.",
                    "funnel_requirements": ["internal brief review", "source-backed educational content draft", "cost-free customer-intent validation plan", "no landing-page publication or lead capture until separately approved"],
                    "content_requirements": ["cite authoritative source evidence", "separate evidence from hypotheses", "avoid funding guarantees or eligibility claims", "list unanswered customer and economics questions"],
                    "measurement": ["qualified interest", "conversion intent", "cost-free signal"],
                    "success_criteria": ["target audience and problem are source-grounded", "one cost-free demand test is defined", "success metric and evidence capture are specified", "no external publishing or spending occurs"],
                    "publishing": False}, "next_action": "HANDOFF_DRAFT_BRIEF_TO_CREATIVE_FOR_INTERNAL_ASSET"}
    if target == "CREATIVE":
        subject = str(finding).strip()[:180] or "business continuity"
        headline = "Could your business keep moving if one source of new customers changed?"
        draft = f"A practical review of {subject.lower()} can help identify questions to validate with customers. This concept makes no performance promises and is for internal review."
        revised = f"Review {subject.lower()} with a clear view of customer needs, alternatives, and next steps. This draft is a starting point for internal review; validate every claim before external use."
        return {**safe_base, "status": "ASSET_READY_FOR_INTERNAL_REVIEW", "asset_task": {
                    "asset_type": "CAMPAIGN_CONCEPT", "brief": str(finding)[:500],
                    "draft_copy": {"headline": headline, "body": draft, "cta": "Review the opportunity"},
                    "critique": {"state": "COMPLETED_HEADLESS", "checks": {"claim_safety": "PASS", "brief_relevance": "PASS", "external_action": "NONE"}, "issues": ["Demand and source claims require independent validation."]},
                    "revision_state": "REVISION_COMPLETE", "revisions": 1,
                    "revised_copy": {"headline": headline, "body": revised, "cta": "Review the opportunity"},
                    "provider": "INTERNAL_HEADLESS_DRAFT",
                    "external_publishing": False},
                "next_action": "INTERNAL_HUMAN_REVIEW_BEFORE_ANY_EXTERNAL_USE"}
    if target in {"RESEARCH"}:
        return {**safe_base, "status": "FOLLOWUP_QUESTION_CREATED", "open_question": f"Verify the evidence and resolve: {handoff.get('topic')}",
                "next_action": "RUN_BOUNDED_SOURCE_CROSS_CHECK"}
    return {**safe_base, "status": "ANALYZED_NEXT_ACTION_REQUIRED", "next_action": str(goal.get("next_action") or "DERIVE_NEXT_SAFE_ACTION")}


def _route_result(handoff: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
    target = str(handoff.get("target_department") or "").upper()
    next_target = None
    handoff_type = "DEPARTMENT_CONTINUATION"
    if target == "ATLAS_OPPORTUNITY" and result.get("decision") == "ADVANCE":
        next_target, handoff_type = "MARKETING", "QUALIFIED_OPPORTUNITY_BRIEF"
    elif target == "ATLAS_OPPORTUNITY" and result.get("decision") == "MORE_RESEARCH_REQUIRED" and not result.get("research_followup_contract"):
        next_target, handoff_type = "RESEARCH", "OPPORTUNITY_RESEARCH_FOLLOWUP"
    elif target in {"LEDGER_FINANCE", "FINANCE"} and result.get("decision") == "MORE_ECONOMIC_RESEARCH_REQUIRED" and not result.get("research_followup_contract"):
        next_target, handoff_type = "RESEARCH", "OPPORTUNITY_ECONOMICS_FOLLOWUP"
    elif target in {"LEDGER_FINANCE", "FINANCE"} and result.get("decision") in {"ECONOMICS_SUPPORTED", "ECONOMICS_NOT_SUPPORTED"}:
        next_target, handoff_type = "ATLAS_OPPORTUNITY", "ECONOMICS_REVIEW_COMPLETE"
    elif target in {"MARKETING", "MIRA_MARKETING"} and result.get("status") == "BRIEF_READY":
        next_target, handoff_type = "CREATIVE", "MARKETING_CREATIVE_BRIEF"
    elif target in {"FORGE_SYSTEMS", "DEVELOPMENT_LABS", "LABS"} and result.get("status") == "EXPERIMENT_READY":
        next_target, handoff_type = "UPGRADE_CONTROL", "LABS_PROMOTION_REVIEW"
    elif target == "UPGRADE_CONTROL" and result.get("decision") == "REJECT_WITH_REPAIR":
        next_target, handoff_type = "LABS", "UPGRADE_REPAIR_RETURN"
    elif target == "UPGRADE_CONTROL" and result.get("decision") == "APPROVE":
        next_target, handoff_type = "SYSTEMS", "UPGRADE_APPROVAL_SYSTEMS_REVIEW"
    elif target in {"ATLAS_OPPORTUNITY", "TRADING", "MERCURY_TRADING", "FORGE_SYSTEMS", "DEVELOPMENT_LABS", "LABS", "SYSTEMS", "MARKETING", "MIRA_MARKETING", "CREATIVE", "UPGRADE_CONTROL"} and result.get("next_action"):
        # A rejected/partial candidate advances its goal by a new bounded
        # action; it never marks the department's parent goal complete.
        next_target, handoff_type = None, handoff_type
    if not next_target:
        return None
    source_ids = list(handoff.get("source_ids") or [])
    source_ids.extend(str(x) for x in handoff.get("artifact_refs") or [])
    return handoffs.create_handoff(
        source_department=target,
        target_department=next_target,
        handoff_type=handoff_type,
        topic=str(result.get("next_action") or handoff.get("topic") or "Department continuation"),
        source_ids=sorted(set(source_ids + [str(handoff.get("handoff_id"))])),
        logical_key=f"handoff-continuation:{handoff.get('handoff_id')}:{next_target}:{handoff_type}",
        payload={"parent_handoff_id": handoff.get("handoff_id"), "parent_goal_id": ((handoff.get("payload") or {}).get("continuation") or {}).get("parent_goal_id"),
                 "finding": (handoff.get("payload") or {}).get("summary") or handoff.get("topic"),
                 "continuation": {"next_action": result.get("next_action"), "success_criteria": ["Receiver reviews durable evidence", "Receiver persists a result and next action"]},
                 "bounded_internal_only": True, "external_actions_allowed": False},
    )


def execute_handoff(handoff_id: str) -> dict[str, Any]:
    """Execute one bounded internal intake and persist result + continuation."""
    row = handoffs.get_handoff(handoff_id)
    if not row:
        raise ValueError("handoff_not_found")
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    continuation = payload.get("continuation") if isinstance(payload.get("continuation"), dict) else {}
    goal_id = continuation.get("receiver_goal_id")
    order_id = row.get("receiving_work_order_id")
    if not goal_id or not order_id or not continuation.get("next_action"):
        raise ValueError("handoff_not_owned")
    status, orders = handoffs.rest("GET", f"task_requests?id=eq.{order_id}&select=id,payload,status&limit=1")
    if status != 200 or not isinstance(orders, list) or not orders:
        raise RuntimeError("work_order_missing")
    order = orders[0]
    if order.get("status") == "done":
        existing_result = (order.get("payload") or {}).get("result")
        return {"status": "ALREADY_EXECUTED", "result": existing_result, "work_order_id": order_id}
    rows = _read_portfolio()
    goal = next((item for item in rows if item.get("goal_id") == goal_id), None)
    if not goal:
        raise ValueError("receiver_goal_missing")
    if row.get("status") == "ACKNOWLEDGED":
        started = handoffs.start_processing(handoff_id)
        if started.get("status") != "PROCESSING":
            raise RuntimeError(f"handoff_start_failed:{started}")
    handoffs.rest("PATCH", f"task_requests?id=eq.{order_id}&status=eq.requested",
                  body={"status": "in_progress", "updated_at": now()}, prefer="return=minimal")
    result = _analyze(row, goal)
    _require_rejection_contract(result)
    downstream = _route_result(row, result)
    timestamp = now()
    order_payload = order.get("payload") if isinstance(order.get("payload"), dict) else {}
    order_payload["result"] = result
    order_payload["executed_at"] = timestamp
    patch_status, patched = handoffs.rest("PATCH", f"task_requests?id=eq.{order_id}&status=in.(requested,assigned,in_progress)",
        body={"status": "done", "result_summary": json.dumps({"status": result.get("status"), "next_action": result.get("next_action")}),
              "payload": order_payload, "updated_at": timestamp}, prefer="return=representation")
    if patch_status not in (200, 204):
        raise RuntimeError(f"work_order_result_persist_failed:{patch_status}:{str(patched)[:160]}")
    _, order_check = handoffs.rest("GET", f"task_requests?id=eq.{order_id}&select=id,status,payload&limit=1")
    if not isinstance(order_check, list) or not order_check or order_check[0].get("status") != "done" or not (order_check[0].get("payload") or {}).get("result"):
        raise RuntimeError("work_order_result_readback_failed")
    continuation["current_stage"] = "RESULT_RECORDED"
    continuation["next_action"] = result.get("next_action")
    payload["continuation"] = continuation
    payload["result"] = result
    payload["result_recorded_at"] = timestamp
    handoffs.rest("PATCH", f"{handoffs.TABLE}?handoff_id=eq.{handoff_id}",
                  body={"payload": payload, "updated_at": timestamp}, prefer="return=minimal")
    handoff_result = handoffs.record_result(handoff_id, ok=True, result_ref=f"task_requests:{order_id}")
    if handoff_result.get("status") != "COMPLETED":
        raise RuntimeError(f"handoff_result_persist_failed:{handoff_result}")
    handoff_check = handoffs.get_handoff(handoff_id) or {}
    if handoff_check.get("status") != "COMPLETED" or not handoff_check.get("processing_result_ref"):
        raise RuntimeError("handoff_result_readback_failed")
    research_case_id = payload.get("research_case_id")
    receiver_case_response = result.get("research_case_response") if isinstance(result.get("research_case_response"), dict) else None
    if research_case_id and receiver_case_response:
        # Only explicit receiver contracts update the case. In particular,
        # MORE_RESEARCH_REQUIRED is rejected unless the full return contract is present.
        from research.research_case_engine import record_department_response
        case_update = record_department_response(str(research_case_id),
            department=str(row.get("target_department") or "UNKNOWN"),
            status=str(receiver_case_response.get("status") or ""),
            specific_question=str(receiver_case_response.get("specific_question") or ""),
            why_needed=str(receiver_case_response.get("why_needed") or ""),
            expected_evidence=str(receiver_case_response.get("expected_evidence") or ""),
            return_to_goal_id=receiver_case_response.get("return_to_goal_id"),
            result={"handoff_id": handoff_id, "work_order_id": order_id, "department_result": result})
        if not case_update.get("ok"):
            raise RuntimeError(f"research_case_receiver_contract_failed:{case_update.get('reason')}")
    handoffs.write_receipt(handoff_id, {"schema_version": "nexus.department-handoff-receipt.v1",
        "handoff_id": handoff_id, "created_at": row.get("created_at"), "processed_at": timestamp,
        "source_department": row.get("source_department"), "target_department": row.get("target_department"),
        "status": handoff_check.get("status"), "acknowledged": True,
        "source_ids": row.get("source_ids") or [], "finding_id": payload.get("finding_id"),
        "research_package_id": payload.get("research_package_id"), "processing_result_ref": handoff_check.get("processing_result_ref"),
        "work_order_id": order_id, "result": result, "result_readback_verified": True})
    success_criteria_met = bool(result.get("status") and handoff_check.get("processing_result_ref")
                                and ((downstream and downstream.get("handoff_id")) or result.get("status") == "ASSET_READY_FOR_INTERNAL_REVIEW"
                                     or (result.get("status") == "RECOVERY_VERIFIED" and (result.get("incident") or {}).get("closed") is True)))
    if str(row.get("target_department") or "").upper() in {"TRADING", "MERCURY_TRADING"}:
        # Intake/research requests are progress, not completion of a Trading
        # candidate. Completion requires a completed paper backtest receipt.
        success_criteria_met = result.get("status") == "EXECUTED_PAPER_BACKTEST" and bool(handoff_check.get("processing_result_ref"))
    goal.update({"current_stage": "RESULT_RECORDED", "last_result": result,
                 "last_progress_at": timestamp, "updated_at": timestamp,
                 "status": "COMPLETED" if success_criteria_met else "ACTIVE",
                 "completion_evidence": {"success_criteria_met": "YES", "verified_criteria": list(goal.get("success_criteria") or []),
                     "work_order_id": order_id, "result_ref": f"task_requests:{order_id}",
                     "report_created_is_not_completion": True, "handoff_created_is_not_completion": True,
                     "worker_exit_is_not_completion": True} if success_criteria_met else None,
                 "next_action": result.get("next_action"),
                 "current_action": result.get("next_action"),
                 "current_evidence": list(goal.get("current_evidence") or []) + [f"task_requests:{order_id}"]})
    _write_portfolio(rows)
    # The completed handoff is one bounded action; its receiver goal remains
    # ACTIVE until its explicit criteria have evidence. The next action is
    # durable on that goal and selected on a later existing operator cycle.
    return {"status": "EXECUTED", "handoff_id": handoff_id, "work_order_id": order_id,
            "goal_id": goal_id, "result": result, "goal_status": goal.get("status"),
            "next_action": result.get("next_action"), "downstream_handoff": downstream}


def process_next_handoff(*, handoff_id: str | None = None) -> dict[str, Any]:
    """One safe unit of receiver work per existing Active Operator cycle."""
    # General PostgREST query is used to select the oldest owned ACK across all
    # departments while retaining the single existing handoff store.
    if handoff_id:
        row = handoffs.get_handoff(handoff_id)
    else:
        status, all_rows = handoffs.rest("GET", f"{handoffs.TABLE}?status=eq.ACKNOWLEDGED&select=handoff_id,created_at,payload&order=created_at.asc&limit=50")
        if status != 200 or not isinstance(all_rows, list):
            raise RuntimeError(f"acknowledged_handoff_read_failed:{status}")
        row = next((item for item in all_rows if isinstance((item.get("payload") or {}).get("continuation"), dict)
                    and (item.get("payload") or {}).get("continuation", {}).get("receiver_goal_id")), None)
    if row:
        return execute_handoff(str(row["handoff_id"]))
    recover_empty_department_goals()
    status, requests = handoffs.rest("GET", "task_requests?task_type=eq.department_goal_continuation&status=eq.requested&select=id,payload&order=created_at.asc&limit=1")
    if status != 200 or not isinstance(requests, list):
        raise RuntimeError(f"department_continuation_read_failed:{status}")
    if not requests:
        return {"status": "NO_OWNED_HANDOFF_READY"}
    return execute_goal_recovery(str(requests[0].get("id")))


def process_next_company_case_directive(*, department: str | None = None,
                                        directive_id: str | None = None,
                                        worker_id: str = "canonical-continuation-runtime") -> dict[str, Any]:
    """Claim and execute one existing Company Case directive in the current runtime.

    Company Case records remain authoritative. The existing Supabase case row
    supplies the atomic claim lease; department adapters write results back via
    the existing Research Case Engine.
    """
    from research import research_case_engine as cases
    initialization = _initialize_wick_trading_project(cases)
    if initialization and initialization.get("status") == "INITIAL_TRADING_HANDOFF_CREATED":
        return {**initialization, "status": "TRADING_PROJECT_INITIALIZED_AND_QUEUED"}
    returned_external = _consume_trading_external_result(cases)
    if returned_external:
        return returned_external
    routed_external = _route_wick_trading_external_need(cases)
    if routed_external:
        return routed_external
    allowed = {"RESEARCH", "SYSTEMS", "MERCURY_TRADING", "MARKETING", "CREATIVE",
               "LEDGER_FINANCE", "CLYDE_CREDIT", "ATLAS_OPPORTUNITY"}
    target_filter = str(department or "").upper() or None
    if target_filter and target_filter not in allowed:
        return {"status": "NO_ADAPTER", "department": target_filter}
    lease_recoveries: list[dict[str, Any]] = []
    # Recover only expired claims whose worker is confirmed dead or whose
    # unknown worker has exceeded the stale grace period. CAS protects against
    # a concurrent worker refreshing the claim or returning a result.
    for case_row in cases._latest_cases():
        if str(case_row.get("case_status") or case_row.get("status") or "").upper() not in cases.ACTIVE_STATES:
            continue
        for req in case_row.get("department_requests") or []:
            if str(req.get("status") or "").upper() not in {"IN_PROGRESS", "CLAIMED"}:
                continue
            lease_until = str((req.get("claim") or {}).get("lease_until") or "")
            try:
                expired = bool(lease_until) and datetime.fromisoformat(
                    lease_until.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
            except ValueError:
                expired = False
            if expired:
                lease_recoveries.append(cases.recover_expired_department_directive(
                    str(case_row.get("case_id")), str(req.get("request_id"))))
    continuation_repairs: list[dict[str, Any]] = []
    terminal_gates = {"RAY_APPROVAL_REQUIRED", "RAY_REVIEW_REQUIRED", "RAY_DENIAL_RECORDED",
        "RAY_STOPPED_PROJECT", "TRUE_HUMAN_ONLY_BLOCKER",
        "OBJECTIVE_ACHIEVED_AWAITING_RAY_ACCEPTANCE", "OBJECTIVE_ACCEPTED_BY_RAY"}
    for case_row in cases._latest_cases():
        if str(case_row.get("case_status") or case_row.get("status") or "").upper() not in cases.ACTIVE_STATES:
            continue
        if (str(case_row.get("status") or "").upper() in terminal_gates or
                str(case_row.get("ray_decision_status") or "").upper() in terminal_gates or
                (case_row.get("true_human_blocker") and str(case_row.get("true_human_blocker_status") or "OPEN").upper() == "OPEN")):
            continue
        requests = list(case_row.get("department_requests") or [])
        trading_project = case_row.get("trading_strategy_project") or {}
        if str(trading_project.get("notebook_owner") or "").upper() == "TRADING":
            # Trading-owned strategy results are consumed by the strategy
            # notebook loop below, never by the Research return consumer.
            continue
        consumed_ids = set(case_row.get("research_consumed_result_ids") or [])
        # A returned result is owned by its explicit RETURN_TO destination.
        # Repair stale owner metadata before attempting to interpret it so a
        # completed department cannot leave the parent case pointed at itself.
        returned_for_resume = next((r for r in reversed(requests)
            if str(r.get("status") or "").upper() == "RESULT_RETURNED"
            and r.get("result_id") and r.get("result_id") not in consumed_ids), None)
        orphaned_result = next((r for r in reversed(case_row.get("department_results") or [])
            if str(r.get("department") or "").upper() != "RESEARCH"
            and r.get("result_id") and r.get("result_id") not in consumed_ids), None)
        if returned_for_resume or orphaned_result:
            handoff = (returned_for_resume or {}).get("workflow_handoff") or {}
            result_row = next((r for r in reversed(case_row.get("department_results") or [])
                if r.get("result_id") == (returned_for_resume or {}).get("result_id")), None)
            result_row = result_row or orphaned_result or {}
            return_to = str(handoff.get("return_to") or result_row.get("return_to") or
                            result_row.get("next_owner") or "RESEARCH").upper()
            current_owner = str(case_row.get("current_owner") or "").upper()
            if return_to in allowed and current_owner != return_to:
                routed = dict(case_row)
                routed.update({"current_owner": return_to, "next_owner": return_to,
                    "current_directive": None, "case_event": "RETURN_TO_OWNER_RESTORED",
                    "return_to_result_id": returned_for_resume.get("result_id"),
                    "updated_at": cases._now()})
                cases._save(routed, "RETURN_TO_OWNER_RESTORED",
                    current_owner=return_to, next_owner=return_to, current_directive=None,
                    return_to_result_id=returned_for_resume.get("result_id"))
                case_row = cases.get_case(str(case_row.get("case_id"))) or routed
                requests = list(case_row.get("department_requests") or [])
        actionable_requests = [r for r in requests if str(r.get("status") or "").upper() in
            {"OPEN", "IN_PROGRESS", "CLAIMED"}]
        unconsumed_results = [r for r in (case_row.get("department_results") or [])
            if str(r.get("department") or "").upper() != "RESEARCH"
            and r.get("result_id") and r.get("result_id") not in consumed_ids]
        returned_requests = [r for r in requests if str(r.get("status") or "").upper() == "RESULT_RETURNED"
            and r.get("result_id") and r.get("result_id") not in consumed_ids]
        if actionable_requests or unconsumed_results or returned_requests:
            continue
        owner = str(case_row.get("current_owner") or case_row.get("next_owner") or
                    case_row.get("owner_department") or "RESEARCH").upper()
        open_questions = [q for q in (case_row.get("open_questions") or [])
            if str(q.get("answer_status") or "OPEN").upper() not in {"ANSWERED", "RESOLVED"} and not q.get("answer")]
        if not case_row.get("current_owner") and not case_row.get("next_owner") and open_questions:
            owner = "RESEARCH"
        if owner not in allowed:
            owner = "RESEARCH"
        next_action = str(case_row.get("next_action") or case_row.get("next_research_action") or
                          case_row.get("next_department_action") or "").strip()
        if owner == "RESEARCH" and open_questions:
            question = open_questions[0]
            work = f"Answer the existing open case question: {question.get('question') or question}. Check existing evidence first, acquire the best missing source if needed, persist the answer to this case, then select the next owner."
            questions = [str(question.get("question") or question)]
        else:
            work = next_action or "Reassess this active case, identify its highest-value unresolved question, and return a concrete next action and owner."
            questions = open_questions[:3] and [str(q.get("question") or q) for q in open_questions[:3]] or [work]
        repair = cases.request_department_work(str(case_row.get("case_id")), department=owner,
            requested_work=work,
            why_this_department="Company Workflow watchdog found an active parent case with no open directive, unconsumed result, or claimable owner action.",
            expected_output="Structured result with supporting evidence, limitation, recommendation, actionable next step, and next owner; parent case remains active.",
            what_happens_after_output="Return the result to the same Company Case and continue its next owner.",
            trigger="COMPANY_WORKFLOW_WATCHDOG", from_department="COMPANY_WORKFLOW_WATCHDOG",
            return_to=owner, questions_to_answer=questions)
        continuation_repairs.append({"case_id": case_row.get("case_id"), "owner": owner,
            "directive_id": (repair.get("request") or {}).get("request_id"),
            "persisted": bool(repair.get("ok")), "action": work})
    candidates = sorted(cases._latest_cases(), key=lambda item: (
        0 if str(item.get("current_owner") or item.get("next_owner") or "").upper() == target_filter else 1,
        str(item.get("updated_at") or item.get("recorded_at") or "")))
    def result_was_consumed(item: dict[str, Any], case_row: dict[str, Any]) -> bool:
        result_id = item.get("result_id")
        if result_id not in set(case_row.get("research_consumed_result_ids") or []):
            return False
        if (result_id == case_row.get("last_research_consumed_result_id") and
                str(case_row.get("last_research_consumption_status") or "").upper() in
                {"RETRYABLE_PROVIDER_FAILURE", "RETRYABLE_EXECUTION_ERROR", "RETRYABLE_NOTEBOOK_FAILURE"}):
            return False
        return True
    def returned_result_priority(item: dict[str, Any]) -> str:
        returned_rows = [row for row in (item.get("department_results") or [])
            if str(row.get("department") or "").upper() != "RESEARCH"
            and row.get("result_id") and not result_was_consumed(row, item)]
        if not returned_rows:
            return ""
        latest = max(returned_rows, key=lambda row: str(row.get("completed_at") or row.get("recorded_at") or ""))
        return str(latest.get("completed_at") or latest.get("recorded_at") or "")

    research_return_candidates = sorted(candidates,
        key=lambda item: returned_result_priority(item), reverse=True)
    # An active case-owner directive is executable work with an explicit
    # department lease. Do not let unrelated Research return packets starve it
    # across every scheduled wake. Research feedback remains highest priority
    # when the case itself is owned by Research and has no open owner directive.
    owner_directive_exists = any(
        str(case.get("current_owner") or case.get("next_owner") or "").upper() != "RESEARCH"
        and (not target_filter or str(case.get("current_owner") or case.get("next_owner") or "").upper() == target_filter)
        and str(case.get("case_status") or case.get("status") or "").upper() in cases.ACTIVE_STATES
        and any(str(req.get("status") or "").upper() == "OPEN"
                and str(req.get("department") or "").upper() == str(case.get("current_owner") or case.get("next_owner") or "").upper()
                and (not directive_id or req.get("request_id") == directive_id)
                for req in (case.get("department_requests") or []))
        for case in candidates)
    # Returned results are a continuation obligation and take priority over
    # unrelated open directives so the requesting owner resumes promptly.
    for case in (() if owner_directive_exists else research_return_candidates):
        owner = str(case.get("current_owner") or case.get("next_owner") or "").upper()
        if target_filter and owner != target_filter:
            continue
        if owner != "RESEARCH" or str(case.get("case_status") or case.get("status") or "").upper() not in cases.ACTIVE_STATES:
            continue
        results = list(case.get("department_results") or [])
        returned = next((item for item in reversed(results)
            if str(item.get("department") or "").upper() != "RESEARCH"
            and item.get("result_id")
            and not result_was_consumed(item, case)), None)
        if not returned:
            continue
        continuation = cases.continue_case_once(str(case.get("case_id")))
        continuation_status = str(continuation.get("status") or "UNKNOWN").upper()
        execution_status = str(continuation.get("execution_status") or "").upper()
        retryable_failure = (continuation_status in {"EXECUTION_ERROR", "NOTEBOOK_FOLLOWUP_DEFERRED", "NOTEBOOK_FOLLOWUP_NO_RESPONSE"}
            or execution_status in {"PROVIDER_FAILURE", "TIMEOUT", "ERROR", "FAILED_RETRYABLE"})
        if not retryable_failure:
            fresh = cases.get_case(str(case.get("case_id"))) or case
            consumed = list(fresh.get("research_consumed_result_ids") or [])
            if returned.get("result_id") not in consumed:
                consumed.append(returned.get("result_id"))
            cases._save(fresh, "RESEARCH_RETURN_RESULT_CONSUMED",
                research_consumed_result_ids=consumed,
                last_research_consumed_result_id=returned.get("result_id"),
                last_research_consumption_status=continuation_status,
                last_research_consumption_at=cases._now(),
                last_research_consumption_trigger="SCHEDULED_DEPARTMENT_RESULT_FEEDBACK")
        else:
            fresh = cases.get_case(str(case.get("case_id"))) or case
            cases._save(fresh, "RESEARCH_RETURN_RETRYABLE_FAILURE",
                last_research_consumed_result_id=returned.get("result_id"),
                last_research_consumption_status=("RETRYABLE_PROVIDER_FAILURE" if execution_status == "PROVIDER_FAILURE" else "RETRYABLE_EXECUTION_ERROR"),
                last_research_consumption_at=cases._now(),
                last_research_consumption_trigger="SCHEDULED_DEPARTMENT_RESULT_FEEDBACK",
                current_owner="RESEARCH", next_owner="RESEARCH",
                next_action="Retry Research interpretation of the returned department result when the Research provider recovers.")
        return {"status": "RESEARCH_RETURN_CONSUMED", "case_id": case.get("case_id"),
                "source_result_id": returned.get("result_id"), "research_result": continuation,
                "next_owner": (cases.get_case(str(case.get("case_id"))) or {}).get("current_owner"),
                "next_directive": (cases.get_case(str(case.get("case_id"))) or {}).get("current_directive"),
                "lease_recoveries": lease_recoveries,
                "continuation_repairs": continuation_repairs}
    for case in research_return_candidates:
        owner = str(case.get("current_owner") or case.get("next_owner") or "").upper()
        if target_filter and owner != target_filter:
            continue
        requests = list(case.get("department_requests") or [])
        request = next((item for item in reversed(requests)
            if (not directive_id or item.get("request_id") == directive_id)
            and str(item.get("department") or "").upper() == owner
            and str(item.get("status") or "").upper() == "OPEN"), None)
        if not request:
            continue
        claim = cases.claim_department_directive(str(case.get("case_id")), str(request.get("request_id")),
            owner, worker_id=worker_id)
        if not claim.get("ok"):
            return {"status": "CLAIM_FAILED", "case_id": case.get("case_id"),
                    "directive_id": request.get("request_id"), "reason": claim.get("reason")}
        claimed_case = claim["case"]
        if owner == "MERCURY_TRADING":
            result = _execute_mercury_wick_directive(claimed_case, request)
        elif owner == "SYSTEMS":
            try:
                result = _execute_systems_case_directive(claimed_case, request)
            except Exception as exc:
                # This adapter performs only local metadata inspection and
                # read-only GETs. A pre-result failure can safely release the
                # same CAS claim for the next scheduled wake.
                released = cases.release_failed_directive_claim(str(case.get("case_id")),
                    str(request.get("request_id")), worker_id, type(exc).__name__,
                    f"Systems adapter failed before result persistence ({type(exc).__name__}).")
                return {"status": "ADAPTER_FAILED_REOPENED" if released.get("ok") else "ADAPTER_FAILED_CLAIM_HELD",
                    "case_id": case.get("case_id"), "directive_id": request.get("request_id"),
                    "department": owner, "error_class": type(exc).__name__,
                    "claim_recovery": released}
        elif owner == "RESEARCH":
            result = cases.continue_case_once(str(case.get("case_id")))
            result = {"status": result.get("status", "RESEARCH_CONTINUED"), "research_result": result,
                      "next_action": result.get("next_action") or "REASSESS_ACTIVE_CASE_AND_ROUTE_NEXT_NEED"}
        else:
            payload = {"summary": request.get("requested_work"), "finding": request.get("objective"),
                       "directive": request, "case_id": case.get("case_id")}
            handoff = {"handoff_id": request.get("request_id"), "target_department": owner,
                       "handoff_type": "COMPANY_CASE_DIRECTIVE", "topic": request.get("objective"),
                       "source_ids": [], "artifact_refs": [], "payload": payload}
            analysis = _analyze(handoff, {"goal_id": case.get("case_id")})
            result = {**analysis, "summary": analysis.get("input_summary"),
                      "next_action": analysis.get("next_action") or "RETURN_RESULT_TO_PARENT_CASE"}
        if owner == "MERCURY_TRADING":
            if result.get("status") == "TRADING_RECOMMENDATION_REVIEWED":
                saved = cases.record_department_result(str(case.get("case_id")), department=owner,
                    what_was_done="Trading evaluated the persisted NotebookLM recommendation against Wick's durable experiment history and loop budget.",
                    why="Trading owns the strategy iteration after Research's initial handoff.",
                    configuration={"directive_id": request.get("request_id"),
                        "strategy_project_id": (case.get("trading_strategy_project") or {}).get("strategy_project_id"),
                        "notebook_id": (case.get("trading_strategy_project") or {}).get("notebook_id"),
                        "loop_number": (case.get("trading_strategy_project") or {}).get("autonomous_loop_count", 1),
                        "return_to": "MERCURY_TRADING", "scope": "recommendation review only; no new backtest"},
                    result=json.dumps(result, ensure_ascii=False, default=str), did_it_advance_goal=True,
                    what_was_learned=str(result.get("what_was_learned") or "Notebook recommendation is now available to the Trading owner."),
                    new_questions=[], next_recommended_action=str(result.get("next_action") or "Trading selects the next source-supported action."),
                    evidence_refs=[request.get("request_id"), (case.get("trading_strategy_project") or {}).get("last_notebook_response_id")],
                    result_type="TRADING_NOTEBOOK_RECOMMENDATION_REVIEW",
                    directive_id=str(request.get("request_id")))
                return {"status": "TRADING_NOTEBOOK_RECOMMENDATION_REVIEWED" if saved.get("ok") else "RESULT_PERSIST_FAILED",
                    "case_id": case.get("case_id"), "directive_id": request.get("request_id"),
                    "result_id": (saved.get("result") or {}).get("result_id"), "persisted": bool(saved.get("ok")),
                    "next_owner": "MERCURY_TRADING", "next_action": result.get("next_action")}
            if result.get("status") != "BACKTEST_EXECUTED":
                # Execution limitations are department results, not project
                # stops. Return the same directive's bounded failure evidence
                # to Research so it can resolve missing inputs or route a
                # Systems capability repair while preserving the parent case.
                failure_status = str(result.get("status") or "ADAPTER_BLOCKED")
                next_action = ("Mercury retries this same claimed Wick directive after the replay adapter issue is repaired; preserve the failed attempt as task evidence and do not count it as a strategy loop.")
                failure_payload = {"task_status": failure_status,
                    "summary": "Mercury could not execute the assigned historical test; the Company Case remains active.",
                    "supporting_data": result,
                    "limitation": result.get("reason") or result.get("error") or failure_status,
                    "recommendation": "Resolve the specific execution limitation and continue the same case.",
                    "actionable_items": [next_action], "next_owner": "RESEARCH",
                    "next_action": next_action, "return_to": "RESEARCH"}
                saved = cases.record_department_result(str(case.get("case_id")), department=owner,
                    what_was_done="Attempted the assigned bounded historical Wick test through Mercury's existing replay adapter.",
                    why=str(request.get("why_this_department") or "Mercury owns the assigned historical validation."),
                    configuration={"directive_id": request.get("request_id"),
                        "scope": "historical/replay only; no orders or live trading",
                        "return_to": "RESEARCH"},
                    result=json.dumps(failure_payload, ensure_ascii=False, default=str),
                    did_it_advance_goal=False,
                    what_was_learned="Execution limitation identified and returned for same-case Research routing.",
                    new_questions=[next_action], next_recommended_action=next_action,
                    evidence_refs=[request.get("request_id")],
                    result_type="MERCURY_WICK_EXECUTION_LIMITATION",
                    directive_id=str(request.get("request_id")))
                if saved.get("ok"):
                    fresh = cases.get_case(str(case.get("case_id"))) or claimed_case
                    retry_requests = list(fresh.get("department_requests") or [])
                    retry_row = next((row for row in retry_requests if row.get("request_id") == request.get("request_id")), None)
                    if retry_row is not None:
                        retry_row.update({"status": "OPEN", "retry_count": int(retry_row.get("retry_count") or 0) + 1,
                            "last_failed_attempt_result_id": (saved.get("result") or {}).get("result_id"),
                            "result_id": None, "claim": None, "reopened_at": now()})
                    project = dict(fresh.get("trading_strategy_project") or {})
                    project.update({"current_workflow_state": "TRADING_LOOP_1_READY",
                        "current_directive_id": request.get("request_id"), "next_action": next_action, "updated_at": now()})
                    cases._save(fresh, "TRADING_DIRECTIVE_REOPENED_AFTER_REPLAY_FAILURE",
                        department_requests=retry_requests, trading_strategy_project=project,
                        current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING",
                        current_directive=retry_row.get("workflow_handoff") if retry_row else request.get("workflow_handoff"),
                        next_action=next_action, continue_research=False)
                return {"status": "FAILURE_RESULT_RETURNED" if saved.get("ok") else "RESULT_PERSIST_FAILED",
                        "case_id": case.get("case_id"), "directive_id": request.get("request_id"),
                        "department": owner, "claim": claim.get("claim"), "result": failure_payload,
                        "result_id": (saved.get("result") or {}).get("result_id"),
                        "persisted": bool(saved.get("ok")), "next_owner": "MERCURY_TRADING",
                        "next_action": next_action}
            metrics = result.get("result") or {}
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            saved = cases.record_department_result(str(case.get("case_id")), department=owner,
                what_was_done=f"Executed the Trading-owned Wick {metrics.get('timeframe')} EUR_USD controlled replay through Mercury's existing offline replay adapter.",
                why=str(request.get("why_this_department") or "Mercury owns the bounded historical strategy validation."),
                configuration={"directive_id": request.get("request_id"), "dataset": result.get("dataset"),
                    "baseline": result.get("baseline"), "variable_changed": result.get("variable_changed"),
                    "metrics": metrics, "artifact": result.get("artifact"), "return_to": "MERCURY_TRADING",
                    "scope": "One OANDA Practice historical window; no orders or live trading.",
                    "loop_number": (request.get("directive_metadata") or {}).get("loop_number", 1),
                    "strategy_project_id": (request.get("directive_metadata") or {}).get("strategy_project_id")},
                result=result_text, did_it_advance_goal=True,
                what_was_learned=str(result.get("what_was_learned") or "Window-specific metrics recorded; no generalization established."),
                new_questions=[],
                next_recommended_action="Sync this result to the same Trading-owned Wick notebook, obtain post-test analysis, and let Trading select the next authorized action.",
                evidence_refs=[result.get("artifact"), result.get("dataset"), request.get("request_id")],
                experiment_completed=True, result_type="MERCURY_WICK_OUT_OF_WINDOW_BACKTEST",
                learning_record={"baseline_or_prior_state": json.dumps(result.get("baseline"), ensure_ascii=False),
                    "action_or_change": result.get("variable_changed"), "why_it_changed": result.get("why_result_changed"),
                    "root_cause": "SAMPLE_WINDOW_CHANGED; STRATEGY_CONFIGURATION_HELD_CONSTANT",
                    "alternative_explanations": ["Regime composition and sample length may explain metric differences."],
                    "what_was_not_proven": ["Author-reported performance claims", "Generalization beyond this EUR/USD window"],
                    "confidence": "LOW", "scope": "Wick EUR/USD M30 OANDA Practice historical window only.",
                    "sample_size": int(metrics.get("trade_count") or 0), "evidence_level": "OBSERVATION",
                    "next_action": "Trading notebook reassessment required."},
                directive_id=str(request.get("request_id")))
            if not saved.get("ok"):
                return {"status": "RESULT_PERSIST_FAILED", "case_id": case.get("case_id"),
                        "directive_id": request.get("request_id"), "result": result}
            trading_reassessment = _trading_notebook_reassess(cases, str(case.get("case_id")),
                result, str(saved.get("result", {}).get("result_id")), str(request.get("request_id")))
            fresh = cases.get_case(str(case.get("case_id"))) or {}
            return {"status": "EXECUTED", "case_id": case.get("case_id"),
                    "directive_id": request.get("request_id"), "department": owner,
                    "claim": claim.get("claim"), "result": result, "result_id": saved.get("result", {}).get("result_id"),
                    "trading_notebook_reassessment": trading_reassessment,
                    "next_owner": fresh.get("current_owner"), "next_directive": fresh.get("current_directive"),
                    "research_intermediary_used": False}
        # Other department outputs use the same case result packet and remain
        # nonterminal. Research gets its native case continuation above.
        saved = cases.record_department_result(str(case.get("case_id")), department=owner,
            what_was_done=str(request.get("requested_work") or "Execute assigned case directive"),
            why=str(request.get("why_this_department") or "Department owns this case need."),
            configuration={"directive_id": request.get("request_id"), "return_to":
                (request.get("workflow_handoff") or {}).get("return_to") or "RESEARCH",
                "scope": f"bounded {owner} adapter result"},
            result=json.dumps(result, ensure_ascii=False, default=str), did_it_advance_goal=True,
            what_was_learned=str(result.get("status") or "Department result recorded."),
            new_questions=[str(result.get("next_action") or "Reassess case and select next bounded action.")],
            next_recommended_action=str(result.get("next_action") or "Reassess case and select next bounded action."),
            evidence_refs=[request.get("request_id")], result_type=f"{owner}_DIRECTIVE_RESULT",
            directive_id=str(request.get("request_id")))
        trading_project = case.get("trading_strategy_project") or {}
        return_to = str((request.get("workflow_handoff") or {}).get("return_to") or "").upper()
        if (owner == "SYSTEMS" and str(trading_project.get("notebook_owner") or "").upper() == "TRADING"
                and return_to in {"MERCURY_TRADING", "TRADING"} and saved.get("ok")):
            synced = _trading_notebook_reassess(cases, str(case.get("case_id")),
                {"summary": "Systems returned the requested Webull capability recovery result.",
                 "result": result, "variable_changed": "External capability lookup only; no strategy test or live trading."},
                str((saved.get("result") or {}).get("result_id")), str(request.get("request_id")), counts_as_loop=False)
            fresh = cases.get_case(str(case.get("case_id"))) or {}
            return {"status": "TRADING_EXTERNAL_RESULT_SYNCED" if synced.get("status") != "NOTEBOOK_SYNC_PENDING" else "TRADING_EXTERNAL_RESULT_SYNC_PENDING",
                "case_id": case.get("case_id"), "directive_id": request.get("request_id"),
                "result_id": (saved.get("result") or {}).get("result_id"), "notebook_sync": synced,
                "next_owner": fresh.get("current_owner"), "next_directive": fresh.get("current_directive"),
                "research_intermediary_used": False}
        return {"status": "EXECUTED" if saved.get("ok") else "RESULT_PERSIST_FAILED",
                "case_id": case.get("case_id"), "directive_id": request.get("request_id"),
                "department": owner, "result": result, "persisted": saved.get("ok"),
                "lease_recoveries": lease_recoveries,
                "continuation_repairs": continuation_repairs}
    return {"status": "NO_OPEN_COMPANY_CASE_DIRECTIVE", "department": target_filter,
            "lease_recoveries": lease_recoveries,
            "continuation_repairs": continuation_repairs}


def _initialize_wick_trading_project(cases: Any) -> dict[str, Any] | None:
    """One-time in-place handoff of the existing Wick case to Trading ownership."""
    case_id = "rcase_98d9635c39cf3ae5a4"
    case = cases.get_case(case_id)
    if not case:
        return None
    existing_project = dict(case.get("trading_strategy_project") or {})
    if existing_project:
        existing_project.setdefault("autonomous_loop_limit", 2)
        existing_project.setdefault("third_loop_requires_ray", True)
        existing_project.setdefault("ai_can_terminate_project", False)
        existing_project.setdefault("trading_can_terminate_project", False)
        existing_project.setdefault("notebook_can_terminate_project", False)
        existing_project.setdefault("research_can_terminate_project", False)
        existing_project.setdefault("ray_stop_authority_only", True)
        if not existing_project.get("historical_trading_results_reclassified"):
            consumed = set(case.get("research_consumed_result_ids") or [])
            imported = set(existing_project.get("historical_results_imported") or [])
            results = list(case.get("department_results") or [])
            changed_ids = []
            for result in results:
                if (str(result.get("department") or "").upper() in {"MERCURY_TRADING", "TRADING"}
                        and result.get("result_id") in imported and result.get("result_id") not in consumed):
                    result["continuation_consumer"] = "TRADING_NOTEBOOK_WORKFLOW"
                    result["research_followup_required"] = False
                    result["historical_result_imported"] = True
                    changed_ids.append(result.get("result_id"))
            requests = list(case.get("department_requests") or [])
            for req in requests:
                if req.get("result_id") in changed_ids:
                    req["continuation_consumer"] = "TRADING_NOTEBOOK_WORKFLOW"
                    req["research_followup_required"] = False
                    handoff = dict(req.get("workflow_handoff") or {})
                    handoff["return_to"] = "MERCURY_TRADING"
                    req["workflow_handoff"] = handoff
            if changed_ids:
                existing_project["historical_trading_results_reclassified"] = changed_ids
                existing_project["historical_results_reclassification_at"] = now()
                case = cases._save(case, "TRADING_HISTORICAL_RESULTS_RECLASSIFIED",
                    trading_strategy_project=existing_project, department_results=results,
                    department_requests=requests, continue_research=False)
        open_trading = next((r for r in reversed(case.get("department_requests") or [])
            if str(r.get("department") or "").upper() == "MERCURY_TRADING"
            and str(r.get("status") or "").upper() in {"OPEN", "IN_PROGRESS", "CLAIMED"}), None)
        if open_trading:
            return None
        if int(existing_project.get("autonomous_loop_count") or 0) > 0:
            return None
        if existing_project.get("current_directive_id"):
            prior = next((r for r in case.get("department_requests") or []
                if r.get("request_id") == existing_project.get("current_directive_id")), None)
            failed = next((r for r in reversed(case.get("department_results") or [])
                if r.get("result_id") == (prior or {}).get("result_id")), None)
            if (prior and str(prior.get("status") or "").upper() == "RESULT_RETURNED"
                    and str((failed or {}).get("result_type") or "").upper() == "MERCURY_WICK_EXECUTION_LIMITATION"):
                retry_requests = list(case.get("department_requests") or [])
                retry = next(row for row in retry_requests if row.get("request_id") == prior.get("request_id"))
                retry.update({"status": "OPEN", "retry_count": int(retry.get("retry_count") or 0) + 1,
                    "last_failed_attempt_result_id": (failed or {}).get("result_id"), "result_id": None,
                    "claim": None, "reopened_at": now()})
                existing_project.update({"current_workflow_state": "TRADING_LOOP_1_READY", "updated_at": now()})
                cases._save(case, "TRADING_DIRECTIVE_REOPENED_AFTER_ADAPTER_FIX",
                    department_requests=retry_requests, trading_strategy_project=existing_project,
                    current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING",
                    current_directive=retry.get("workflow_handoff"), continue_research=False)
                return {"status": "TRADING_DIRECTIVE_REOPENED", "directive_id": retry.get("request_id")}
            return None
        target_spec = ROOT / "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1_h1_stop15_loop1.json"
        data_path = ROOT / "data/runtime/wick_sequence_oanda_eurusd_h1_2026-10-06.json"
        if not target_spec.is_file() or not data_path.is_file():
            return {"status": "INITIAL_HANDOFF_INPUTS_UNAVAILABLE"}
        metadata = {"strategy_project_id": existing_project.get("strategy_project_id"), "action_type": "BACKTEST",
            "spec_path": str(target_spec.relative_to(ROOT)), "data_path": str(data_path.relative_to(ROOT)),
            "variable_changed": "ATR stop multiple 2.0 to 1.5 only; H1 EUR_USD, data window, entries, target, risk and costs held constant.",
            "loop_number": 1, "baseline_spec_path": "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1.json",
            "baseline_result_path": "data/governed/wick_sequence_baseline_v1_backtest.json",
            "notebook_id": existing_project.get("notebook_id"), "live_trading_enabled": False}
        handoff = cases.request_department_work(case_id, department="MERCURY_TRADING",
            requested_work="Run the source-derived H1 EUR_USD comparison of Pine's 1.5x ATR stop against Nexus's 2.0x baseline; change the stop multiple only. Use the existing OANDA Practice H1 data and offline replay.",
            why_this_department="The Wick history and Pine source support this single-variable test; the same-window H1 2.0x result is the baseline.",
            expected_output="Structured result, trade diagnostics, comparison, limitations, and next recommendation; no live orders.",
            what_happens_after_output="Supabase appends the result to this strategy project and the same Trading-owned notebook evaluates it for Trading.",
            trigger="TRADING_INITIAL_HANDOFF_RECOVERY", from_department="RESEARCH", return_to="MERCURY_TRADING",
            questions_to_answer=["Does the source-derived 1.5x ATR H1 stop materially change the baseline on identical data?"] ,
            directive_metadata=metadata)
        request = handoff.get("request") or {}
        fresh = cases.get_case(case_id) or case
        existing_project.update({"current_workflow_state": "TRADING_LOOP_1_READY",
            "current_directive_id": request.get("request_id"), "next_action": request.get("requested_work"), "updated_at": now()})
        cases._save(fresh, "TRADING_INITIAL_HANDOFF_REPAIRED", trading_strategy_project=existing_project,
            current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING",
            current_directive=request.get("workflow_handoff"), continue_research=False,
            next_action=existing_project.get("next_action"))
        return {"status": "INITIAL_TRADING_HANDOFF_CREATED", "directive_id": request.get("request_id"),
                "strategy_project_id": existing_project.get("strategy_project_id")}
    notebook_id = str(case.get("notebook_id") or (case.get("notebook_workspace") or {}).get("notebook_id") or "")
    if notebook_id != "fe652c61-c8c7-43c0-9277-3f8bf2f28235":
        return {"status": "WICK_NOTEBOOK_BINDING_MISMATCH"}
    root = ROOT
    source_spec = root / "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1.json"
    data_path = root / "data/runtime/wick_sequence_oanda_eurusd_h1_2026-10-06.json"
    if not source_spec.is_file() or not data_path.is_file():
        return {"status": "INITIAL_HANDOFF_INPUTS_UNAVAILABLE"}
    spec = json.loads(source_spec.read_text())
    spec["strategy_id"] = "strategy_wick_sequence_breakout_v1_h1_stop15_loop1"
    spec["name"] = "Wick Sequence Breakout H1 stop 1.5x ATR controlled test"
    spec["stop"]["value"] = 1.5
    spec["strategy_logic"]["atr"]["stop_multiple"] = 1.5
    target_spec = root / "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1_h1_stop15_loop1.json"
    target_spec.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    project_id = "strat_" + hashlib.sha256(f"{case_id}:{notebook_id}".encode()).hexdigest()[:18]
    now_iso = datetime.now(timezone.utc).isoformat()
    project = {"strategy_project_id": project_id, "case_id": case_id,
        "strategy_name": "Wick Sequence Breakout", "notebook_id": notebook_id,
        "notebook_owner": "TRADING", "notebook_manager": "RESEARCH",
        "current_workflow_state": "READY_FOR_TRADING", "current_directive_id": None,
        "autonomous_loop_count": 0, "ray_approved_extra_loops": 0,
        "autonomous_loop_limit": 2, "third_loop_requires_ray": True,
        "ai_can_terminate_project": False, "trading_can_terminate_project": False,
        "notebook_can_terminate_project": False, "research_can_terminate_project": False,
        "ray_stop_authority_only": True,
        "current_best_configuration": {"instrument": "EUR_USD", "timeframe": "H1",
            "spec_path": "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1.json",
            "data_path": str(data_path.relative_to(root)), "stop_multiple": 2.0,
            "status": "PRIOR_BASELINE; not validated for generalization"},
        "current_recommendation": "Run one source-derived H1 stop-parity comparison: Pine default 1.5x ATR versus the existing Nexus 2.0x ATR baseline, changing only the stop multiple.",
        "next_action": "Execute the authorized H1 stop 1.5x ATR replay using the existing OANDA Practice historical dataset; no live trading.",
        "last_result_id": None,
        "source_references": ["tradingview-pine: PUB;5a95244443db4e78a73c3e22c5a228c2",
            "data/governed/wick_experiment_matrix_20261006.json", "data/governed/wick_sequence_baseline_v1_backtest.json"],
        "historical_results_imported": [r.get("result_id") for r in case.get("department_results", [])
            if str(r.get("department") or "").upper() in {"MERCURY_TRADING", "TRADING"} and r.get("result_id")],
        "historical_loop_count_excluded": True, "created_at": now_iso, "updated_at": now_iso}
    cases._save(case, "TRADING_STRATEGY_PROJECT_INITIALIZED", trading_strategy_project=project,
        status="UNDER_DEVELOPMENT", continue_research=False, current_owner="MERCURY_TRADING",
        next_owner="MERCURY_TRADING", current_directive=None,
        next_action=project["next_action"], next_research_action=None)
    metadata = {"strategy_project_id": project_id, "action_type": "BACKTEST",
        "spec_path": str(target_spec.relative_to(root)), "data_path": str(data_path.relative_to(root)),
        "variable_changed": "ATR stop multiple 2.0 to 1.5 only; H1 EUR_USD, data window, entries, target, risk and costs held constant.",
        "loop_number": 1, "baseline_spec_path": str(source_spec.relative_to(root)),
        "baseline_result_path": "data/governed/wick_sequence_baseline_v1_backtest.json",
        "notebook_id": notebook_id, "live_trading_enabled": False}
    handoff = cases.request_department_work(case_id, department="MERCURY_TRADING",
        requested_work=project["next_action"],
        why_this_department="The same Wick notebook and prior history support a controlled comparison of Pine's 1.5x ATR default against Nexus's H1 2.0x baseline; this isolates one source-derived risk variable.",
        expected_output="Structured replay result with dataset/window, baseline and treatment metrics, trade diagnostics, limitations, recommendation, and next action. Historical OANDA Practice only; no live orders.",
        what_happens_after_output="Supabase updates the same Trading-owned Wick notebook, NotebookLM reassesses accumulated results, and the Trading workflow selects Loop 2 or a Ray review gate.",
        trigger="RESEARCH_INITIALIZATION", from_department="RESEARCH", return_to="MERCURY_TRADING",
        questions_to_answer=["Does the Pine-derived 1.5x ATR stop change H1 EUR_USD results versus the same-window Nexus 2.0x baseline?"],
        directive_metadata=metadata)
    request = handoff.get("request") or {}
    fresh = cases.get_case(case_id) or case
    project = dict(fresh.get("trading_strategy_project") or project)
    project.update({"current_workflow_state": "TRADING_LOOP_1_READY",
        "current_directive_id": request.get("request_id"), "updated_at": datetime.now(timezone.utc).isoformat()})
    cases._save(fresh, "TRADING_INITIAL_HANDOFF_CREATED", trading_strategy_project=project,
        current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING",
        current_directive=request.get("workflow_handoff"), continue_research=False)
    return {"status": "INITIAL_TRADING_HANDOFF_CREATED", "directive_id": request.get("request_id"),
            "strategy_project_id": project_id}


def _trading_notebook_reassess(cases: Any, case_id: str, result: dict[str, Any],
                               result_id: str, directive_id: str,
                               counts_as_loop: bool = True) -> dict[str, Any]:
    """Trading-owned result sync and reassessment in the already bound notebook."""
    case = cases.get_case(case_id) or {}
    project = dict(case.get("trading_strategy_project") or {})
    if str(project.get("notebook_owner") or "").upper() != "TRADING":
        return {"status": "NOT_TRADING_OWNED"}
    notebook_id = str(project.get("notebook_id") or "")
    current_loop_count = int(project.get("autonomous_loop_count") or 0)
    loop_number = (int((case.get("department_results") or [{}])[-1].get("configuration", {}).get("loop_number") or current_loop_count + 1)
                   if counts_as_loop else current_loop_count)
    summary = result.get("result") or {}
    artifact_rel = f"data/governed/trading_strategy_results/{result_id}.md"
    artifact = ROOT / artifact_rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join([
        "# Wick Trading Test Result", f"\n- Strategy project: {project.get('strategy_project_id')}",
        f"- Case: {case_id}", f"- Notebook: {notebook_id}", f"- Directive: {directive_id}",
        f"- Result: {result_id}", f"- Loop: {loop_number}", f"- Dataset: {result.get('dataset')}",
        f"- Variable changed: {result.get('variable_changed')}",
        f"- Baseline: {json.dumps(result.get('baseline') or {}, sort_keys=True)}",
        f"- Metrics: {json.dumps(summary, sort_keys=True)}",
        f"- Trade-level diagnostics: {json.dumps(result.get('trade_level_diagnostics') or [], sort_keys=True)}",
        f"- Interpretation: {result.get('why_result_changed')}",
        f"- Learned: {result.get('what_was_learned')}",
        f"- Limitations: {json.dumps(result.get('limitations') or [])}",
        "- Method: existing Nexus offline historical replay; no broker order endpoint; live trading disabled.",
    ]) + "\n"
    artifact.write_text(body, encoding="utf-8")
    import hashlib as _hashlib
    artifact_hash = _hashlib.sha256(artifact.read_bytes()).hexdigest()
    prompt = f"""You are the Wick strategy notebook, owned by Trading. Analyze this newly added Nexus test result against all prior Wick evidence in THIS notebook. Do not terminate, reject, or shelve the project. Do not invent indicators or source rules. Return the following as explicit labeled fields, with JSON in a fenced block if possible: WHAT_DID_THIS_TEST_SHOW; WHAT_IMPROVED_RELATIVE_TO_PRIOR_TESTS; WHAT_GOT_WORSE; REPEATED_FAILURE_PATTERN; WHAT_SHOULD_NOT_BE_RETESTED; WHAT_REMAINS_UNRESOLVED; EVIDENCE_FOR_ANOTHER_INDICATOR_OR_FILTER (and source support); SOURCE_SUPPORTED_TIMEFRAME_TEST_STILL_UNRUN; HIGHEST_INFORMATION_NEXT_TEST (one variable only); IS_STRATEGY_STILL_WORTH_TESTING; NEXT_STEP (TRADING, EXTERNAL_DEPARTMENT, or RAY); exact proposed instrument/timeframe/configuration/data requirement; why justified; expected information gain; limitations. If another material test is not justified, recommend a Ray review or non-material analysis action, but the project remains active.\n\nNew result artifact: {artifact_rel}\nSHA256: {artifact_hash}\nResult ID: {result_id}\nMetrics: {json.dumps(summary, sort_keys=True)}\nChanged variable: {result.get('variable_changed')}\n"""
    try:
        from research.notebooklm_research_adapter import NotebookLMResearchAdapter
        adapter = NotebookLMResearchAdapter()
        source = adapter.add_case_artifact_source(notebook_id, artifact, title=f"Wick Nexus result {result_id}")
        turn = adapter.ask_notebook(notebook_id, prompt)
        answer = str(turn.get("answer") or "")
        if not answer:
            raise RuntimeError("NotebookLM returned an empty answer")
        lines = [line.strip(" -*\t") for line in answer.splitlines() if line.strip()]
        findings = [{"type": "NOTEBOOK_SYNTHESIS", "content": line[:1200], "source_id": source.get("id")}
                    for line in lines[:30]]
        rec = cases.record_notebook_answer(case_id, question_type="TRADING_POST_TEST_REASSESSMENT",
            answer=answer, notebook_id=notebook_id, source_ids=[str(source.get("id"))],
            conversation_id=turn.get("conversation_id"), submission_attempted=True,
            submission_confirmed=True, response_reference=turn.get("response_reference"),
            prompt=prompt, response_id=turn.get("correlation_id"), key_findings=lines[:12],
            recommendations=[line for line in lines if "NEXT" in line.upper() or "RECOMMEND" in line.upper()][:12],
            open_questions=[line for line in lines if "UNRESOLVED" in line.upper() or "QUESTION" in line.upper()][:12],
            next_action="Trading reads this same-notebook reassessment and follows its highest-information source-supported next test within the two-loop budget.",
            question_origin="TRADING_WORKFLOW", extracted_findings=findings)
        fresh = cases.get_case(case_id) or case
        project = dict(fresh.get("trading_strategy_project") or project)
        project.update({"last_result_id": result_id, "last_notebook_response_id": turn.get("correlation_id"),
            "last_notebook_response_hash": turn.get("response_sha256"),
            "last_notebook_artifact": artifact_rel, "last_notebook_artifact_sha256": artifact_hash,
            "last_notebook_source_id": source.get("id"), "last_notebook_recommendation": answer,
            "autonomous_loop_count": max(current_loop_count, loop_number),
            "current_workflow_state": f"NOTEBOOK_SYNC_{loop_number}",
            "current_recommendation": answer, "updated_at": now()})
        cases._save(fresh, "TRADING_RESULT_NOTEBOOK_REASSESSED", trading_strategy_project=project,
            continue_research=False, current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING")
        if int(project["autonomous_loop_count"]) >= 2:
            project["current_workflow_state"] = "RAY_REVIEW_REQUIRED"
            project["next_action"] = "Trading has completed its two autonomous material loops; prepare a Ray trading review packet before any further material test."
            cases._save(cases.get_case(case_id) or fresh, "TRADING_LOOP_BUDGET_EXHAUSTED",
                trading_strategy_project=project, current_owner="TRADING", next_owner="RAY",
                continue_research=False, next_action=project["next_action"])
            return {"status": "RAY_REVIEW_REQUIRED", "answer": answer, "notebook_id": notebook_id,
                    "response_id": turn.get("correlation_id"), "result_id": result_id}
        # The notebook answer is the evidence source for the next Trading-owned action.
        recommendation_line = next((line for line in lines if any(token in line.upper()
            for token in ("HIGHEST-INFORMATION NEXT TEST", "NEXT TEST", "NEXT_ACTION", "NEXT TEST:"))), "")
        next_work = ("Trading: inspect the persisted NotebookLM post-test recommendation and select its highest-information, source-supported next experiment. "
            "Use one material variable only, consult the Wick experiment history, and do not execute a third material loop without Ray approval. "
            f"Notebook recommendation excerpt: {recommendation_line or answer[:900]}")
        metadata = {"strategy_project_id": project.get("strategy_project_id"), "action_type": "NOTEBOOK_RECOMMENDATION_REVIEW",
            "loop_number": int(project["autonomous_loop_count"]) + 1, "notebook_id": notebook_id,
            "source_response_id": turn.get("correlation_id"), "source_response_hash": turn.get("response_sha256"),
            "material_test_requires_exact_notebook_recommendation": True, "live_trading_enabled": False}
        created = cases.request_department_work(case_id, department="MERCURY_TRADING", requested_work=next_work,
            why_this_department="Trading owns post-handoff strategy development; the same Wick notebook has reassessed the persisted result.",
            expected_output="Trading validates the exact notebook recommendation against source support, prior experiments, the two-loop budget and available replay inputs; return a single-variable executable directive or request Ray review.",
            what_happens_after_output="Execute Loop 2 only if source-supported and within budget; after Loop 2 route any additional material testing to Ray.",
            trigger="TRADING_NOTEBOOK_REASSESSMENT", from_department="TRADING_NOTEBOOK_WORKFLOW", return_to="MERCURY_TRADING",
            questions_to_answer=["Which specific source-supported single-variable test best follows this reassessment, if any?"],
            directive_metadata=metadata)
        request = created.get("request") or {}
        project.update({"current_workflow_state": f"TRADING_LOOP_{int(project['autonomous_loop_count']) + 1}_READY", "current_directive_id": request.get("request_id"),
            "next_action": next_work, "updated_at": now()})
        cases._save(cases.get_case(case_id) or fresh, "TRADING_LOOP_2_DIRECTIVE_CREATED",
            trading_strategy_project=project, current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING",
            current_directive=request.get("workflow_handoff"), continue_research=False)
        return {"status": "NOTEBOOK_REASSESSED_NEXT_TRADING_DIRECTIVE_CREATED", "answer": answer,
            "notebook_id": notebook_id, "response_id": turn.get("correlation_id"),
            "source_id": source.get("id"), "next_directive_id": request.get("request_id"), "result_id": result_id}
    except Exception as exc:
        fresh = cases.get_case(case_id) or case
        project = dict(fresh.get("trading_strategy_project") or project)
        project.update({"last_result_id": result_id, "current_workflow_state": "NOTEBOOK_SYNC_PENDING",
            "autonomous_loop_count": max(int(project.get("autonomous_loop_count") or 0), loop_number),
            "notebook_sync_error_class": type(exc).__name__, "last_notebook_artifact": artifact_rel,
            "last_notebook_artifact_sha256": artifact_hash, "updated_at": now()})
        cases._save(fresh, "TRADING_NOTEBOOK_SYNC_PENDING", trading_strategy_project=project,
            continue_research=False, current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING")
        return {"status": "NOTEBOOK_SYNC_PENDING", "error_class": type(exc).__name__,
            "result_id": result_id, "artifact": artifact_rel, "notebook_id": notebook_id}


def _route_wick_trading_external_need(cases: Any) -> dict[str, Any] | None:
    """Route a notebook-identified missing capability directly and return to Trading."""
    case_id = "rcase_98d9635c39cf3ae5a4"
    case = cases.get_case(case_id)
    if not case:
        return None
    project = dict(case.get("trading_strategy_project") or {})
    if str(project.get("notebook_owner") or "").upper() != "TRADING":
        return None
    answers = [a for a in case.get("notebook_answers") or []
        if a.get("notebook_id") == project.get("notebook_id") and a.get("question_origin") == "TRADING_WORKFLOW"]
    if not answers:
        return None
    answer = str(answers[-1].get("answer") or "")
    if "EXTERNAL_DEPARTMENT" not in answer.upper() or "WEBULL" not in answer.upper():
        return None
    prior_attempt = next((r for r in reversed(case.get("department_requests") or [])
        if str(r.get("department") or "").upper() == "SYSTEMS"
        and (r.get("directive_metadata") or {}).get("action_type") == "WEBULL_CREDENTIAL_AND_CAPABILITY_RECOVERY"
        and str(r.get("status") or "").upper() == "RESULT_RETURNED"), None)
    if prior_attempt:
        return None
    active_systems = next((r for r in reversed(case.get("department_requests") or [])
        if str(r.get("department") or "").upper() == "SYSTEMS"
        and str(r.get("status") or "").upper() in {"OPEN", "IN_PROGRESS", "CLAIMED"}
        and str((r.get("workflow_handoff") or {}).get("return_to") or "").upper() == "MERCURY_TRADING"), None)
    if active_systems:
        if project.get("current_directive_id") != active_systems.get("request_id"):
            project.update({"current_workflow_state": "WAITING_ON_SYSTEMS",
                "current_directive_id": active_systems.get("request_id"), "updated_at": now()})
            cases._save(case, "TRADING_SYSTEMS_DIRECTIVE_RECONCILED",
                trading_strategy_project=project, current_owner="SYSTEMS", next_owner="SYSTEMS",
                current_directive=active_systems.get("workflow_handoff"), continue_research=False)
        return None
    open_trading = next((r for r in reversed(case.get("department_requests") or [])
        if str(r.get("department") or "").upper() == "MERCURY_TRADING"
        and str(r.get("status") or "").upper() in {"OPEN", "RESULT_RETURNED"}
        and (r.get("directive_metadata") or {}).get("action_type") == "NOTEBOOK_RECOMMENDATION_REVIEW"), None)
    if not open_trading:
        return None
    requests = list(case.get("department_requests") or [])
    source = next((r for r in requests if r.get("request_id") == open_trading.get("request_id")), None)
    if source:
        source.update({"status": "DEFERRED_FOR_EXTERNAL_CAPABILITY", "deferred_at": now(),
            "deferred_reason": "The same strategy notebook recommends authentic TSLA M30 traded-volume validation; Webull credentials are not resolved.",
            "superseded_by_external_request": True})
    cases._save(case, "TRADING_NOTEBOOK_EXTERNAL_CAPABILITY_SELECTED",
        department_requests=requests, current_owner="SYSTEMS", next_owner="SYSTEMS",
        current_directive=None, continue_research=False,
        trading_strategy_project={**project, "current_workflow_state": "WAITING_ON_SYSTEMS",
            "current_directive_id": None, "next_action": "Inspect approved local references for existing Webull PaperTrade credentials and return status directly to Trading.",
            "updated_at": now()})
    requested = ("Resolve the notebook-selected Wick data capability for TSLA M30 true share-volume validation. "
        "History first: inspect remaining approved existing locations for the already-created Nexus Webull PaperTrade OpenAPI application credentials; do not create an app, rotate/reset keys, or expose values. "
        "Search ~/.config/nexus/runtime.env, canonical .env.local/.env, ~/nexuslive/.env, ~/nexus/.env, Keychain service nexus/credential.webull.openapi.prod.v1, and approved process/launchd environment references. "
        "If found, repair only the canonical credential reference and run read-only auth/symbol/M30 historical-bar checks. If absent, return EXHAUSTED_OR_REMAINING_LOCATIONS. Return to MERCURY_TRADING with exact status and no raw secrets.")
    handoff = cases.request_department_work(case_id, department="SYSTEMS", requested_work=requested,
        why_this_department="The Trading-owned Wick notebook identified real exchange-traded share volume as the highest-information test; the same case's prior Systems results found Webull credentials unresolved and listed remaining approved search paths.",
        expected_output="Redacted credential presence, locations checked/remain, auth and market-data status where possible, and a direct return-to-Trading recommendation.",
        what_happens_after_output="Return to Trading for the next source-supported action; if credentials remain unavailable, Trading chooses the best existing alternate route or prepares Ray's exact human action.",
        trigger="TRADING_NOTEBOOK_RECOMMENDATION", from_department="MERCURY_TRADING", return_to="MERCURY_TRADING",
        questions_to_answer=["Can the existing Webull Nexus PaperTrade credentials be recovered from approved local references without rotation?", "Can Webull serve TSLA M30 historical OHLCV including true volume in the current PaperTrade entitlement?"] ,
        directive_metadata={"strategy_project_id": project.get("strategy_project_id"), "action_type": "WEBULL_CREDENTIAL_AND_CAPABILITY_RECOVERY",
            "notebook_id": project.get("notebook_id"), "notebook_response_id": answers[-1].get("response_id"),
            "return_to": "MERCURY_TRADING", "no_key_rotation": True, "live_trading_enabled": False})
    request = handoff.get("request") or {}
    fresh = cases.get_case(case_id) or case
    project = dict(fresh.get("trading_strategy_project") or project)
    project.update({"current_workflow_state": "WAITING_ON_SYSTEMS", "current_directive_id": request.get("request_id"),
        "next_action": requested, "updated_at": now()})
    cases._save(fresh, "TRADING_SYSTEMS_SUBREQUEST_CREATED", trading_strategy_project=project,
        current_owner="SYSTEMS", next_owner="SYSTEMS", current_directive=request.get("workflow_handoff"),
        continue_research=False)
    return {"status": "TRADING_NOTEBOOK_NEED_ROUTED_TO_SYSTEMS", "case_id": case_id,
        "next_owner": "SYSTEMS", "directive_id": request.get("request_id"), "return_to": "MERCURY_TRADING"}


def _consume_trading_external_result(cases: Any) -> dict[str, Any] | None:
    """Trading itself consumes an external-department return and syncs the same notebook."""
    case_id = "rcase_98d9635c39cf3ae5a4"
    case = cases.get_case(case_id)
    if not case:
        return None
    project = dict(case.get("trading_strategy_project") or {})
    if str(project.get("notebook_owner") or "").upper() != "TRADING":
        return None
    for req in reversed(case.get("department_requests") or []):
        if (str(req.get("department") or "").upper() != "SYSTEMS"
                or str(req.get("status") or "").upper() != "RESULT_RETURNED"
                or not req.get("result_id")
                or req.get("result_id") == project.get("last_trading_consumed_external_result_id")
                or str((req.get("workflow_handoff") or {}).get("return_to") or "").upper() != "MERCURY_TRADING"):
            continue
        result = next((row for row in case.get("department_results") or [] if row.get("result_id") == req.get("result_id")), None)
        if not result:
            continue
        try:
            payload = json.loads(str(result.get("result") or "{}"))
        except (json.JSONDecodeError, TypeError):
            payload = {"summary": str(result.get("result") or "")[:1000]}
        existing_answer = next((a for a in reversed(case.get("notebook_answers") or [])
            if a.get("notebook_id") == project.get("notebook_id")
            and a.get("question_origin") == "TRADING_WORKFLOW"
            and str(req.get("result_id")) in str(a.get("prompt") or "")), None)
        if existing_answer:
            supporting = payload.get("supporting_data") or {}
            locations = list(payload.get("unsearched_approved_locations") or
                supporting.get("unsearched_approved_locations") or [])
            if not locations:
                locations = ["remaining approved credential references identified by Systems"]
            requested = ("Continue the notebook-selected Webull credential recovery only through these still-unsearched approved locations: "
                + "; ".join(map(str, locations)) + ". Do not repeat already completed resolver/registry checks, create another app, rotate/reset credentials, or expose values. "
                "If the existing credential is found, update only the canonical secret reference and run read-only PaperTrade auth plus TSLA M30 historical bars. If absent, document each location checked and return EXHAUSTED_LOCAL_RECOVERY to Mercury. RETURN_TO=MERCURY_TRADING.")
            handoff = cases.request_department_work(case_id, department="SYSTEMS", requested_work=requested,
                why_this_department="Trading's same-notebook reassessment selected real TSLA M30 share-volume validation and identified the specific remaining approved credential locations; prior Systems result was not exhaustive.",
                expected_output="Redacted inventory of only the listed locations, existing-credential presence, read-only auth/data status if available, and explicit next route to Mercury.",
                what_happens_after_output="Return directly to Mercury. If unavailable after these locations are checked, Mercury selects a supported alternate or prepares Ray's exact human action.",
                trigger="TRADING_NOTEBOOK_FOLLOWUP", from_department="MERCURY_TRADING", return_to="MERCURY_TRADING",
                questions_to_answer=["Do the remaining approved locations contain the existing Webull PaperTrade credentials?", "Can the recovered account return TSLA M30 bars with an exchange-volume field?"],
                directive_metadata={"strategy_project_id": project.get("strategy_project_id"), "action_type": "WEBULL_REMAINING_LOCATION_RECOVERY",
                    "notebook_id": project.get("notebook_id"), "notebook_response_id": existing_answer.get("response_id"),
                    "return_to": "MERCURY_TRADING", "no_key_rotation": True, "live_trading_enabled": False})
            new_request = handoff.get("request") or {}
            fresh = cases.get_case(case_id) or case
            if new_request.get("request_id") and not any(r.get("request_id") == new_request.get("request_id")
                    for r in fresh.get("department_requests") or []):
                # The Wick payload is large; verify that the request-side
                # write actually survived before publishing its ID as current.
                retry_handoff = cases.request_department_work(case_id, department="SYSTEMS", requested_work=requested,
                    why_this_department="Trading's same-notebook reassessment selected true share-volume validation; retrying the durable request write after readback did not show the first write.",
                    expected_output="Redacted inventory of the listed locations, credential presence, read-only auth/data status, and direct return to Mercury.",
                    what_happens_after_output="Return directly to Mercury; do not rotate credentials or stop the strategy objective.",
                    trigger="TRADING_NOTEBOOK_FOLLOWUP_WRITE_RETRY", from_department="MERCURY_TRADING", return_to="MERCURY_TRADING",
                    questions_to_answer=["Do the remaining approved locations contain the existing Webull PaperTrade credentials?"],
                    directive_metadata={"strategy_project_id": project.get("strategy_project_id"), "action_type": "WEBULL_REMAINING_LOCATION_RECOVERY",
                        "notebook_id": project.get("notebook_id"), "notebook_response_id": existing_answer.get("response_id"),
                        "return_to": "MERCURY_TRADING", "no_key_rotation": True, "live_trading_enabled": False})
                new_request = retry_handoff.get("request") or new_request
                fresh = cases.get_case(case_id) or fresh
            updated = dict(fresh.get("trading_strategy_project") or project)
            updated.update({"current_workflow_state": "WAITING_ON_SYSTEMS",
                "current_directive_id": new_request.get("request_id"), "next_action": requested,
                "last_trading_consumed_external_result_id": req.get("result_id"),
                "external_department_result_consumed_at": now(), "updated_at": now()})
            cases._save(fresh, "TRADING_NOTEBOOK_FOLLOWUP_ROUTED_TO_SYSTEMS",
                trading_strategy_project=updated, current_owner="SYSTEMS", next_owner="SYSTEMS",
                current_directive=new_request.get("workflow_handoff"), continue_research=False)
            return {"status": "TRADING_EXTERNAL_RESULT_CONSUMED_AND_SYSTEMS_FOLLOWUP_CREATED",
                "case_id": case_id, "result_id": req.get("result_id"),
                "notebook_response_id": existing_answer.get("response_id"),
                "next_owner": "SYSTEMS", "next_directive": new_request.get("request_id"),
                "return_to": "MERCURY_TRADING"}
        synced = _trading_notebook_reassess(cases, case_id,
            {"summary": "Systems returned the notebook-requested external capability result.",
             "result": payload, "variable_changed": "External capability investigation only; no strategy test or live trading."},
            str(req.get("result_id")), str(req.get("request_id")), counts_as_loop=False)
        if synced.get("status") == "NOTEBOOK_SYNC_PENDING":
            return {"status": "TRADING_EXTERNAL_RESULT_SYNC_PENDING", "case_id": case_id,
                "result_id": req.get("result_id"), "notebook_sync": synced}
        fresh = cases.get_case(case_id) or case
        updated = dict(fresh.get("trading_strategy_project") or project)
        updated["last_trading_consumed_external_result_id"] = req.get("result_id")
        updated["external_department_result_consumed_at"] = now()
        cases._save(fresh, "TRADING_EXTERNAL_RESULT_CONSUMED", trading_strategy_project=updated,
            continue_research=False, current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING")
        return {"status": "TRADING_EXTERNAL_RESULT_CONSUMED", "case_id": case_id,
            "result_id": req.get("result_id"), "notebook_sync": synced,
            "next_owner": "MERCURY_TRADING", "next_directive": synced.get("next_directive_id")}
    return None


def _execute_systems_case_directive(case: dict[str, Any], directive: dict[str, Any]) -> dict[str, Any]:
    """Run the existing read-only Systems Webull recovery work for Wick.

    This adapter is intentionally limited to credential presence metadata and
    GET-only PaperTrade checks. It never reads a secret into a report or sends
    an order, and it leaves the parent case active when a provider route is
    unavailable.
    """
    from nexus_agent_platform import credential_control_plane as credentials
    from nexus_agent_platform.providers.webull_provider import WebullProvider

    credential_id = "credential.webull.openapi.prod.v1"
    resolved = credentials.resolve(credential_id)
    components = resolved.get("components") or {}
    present = {name: bool((components.get(name) or {}).get("selected"))
               for name in ("app_key", "app_secret")}
    refs = sorted({str((components.get(name) or {}).get("selected", {}).get("source"))
                   for name in components if (components.get(name) or {}).get("selected")})
    # History-first evidence: receipts are inspected as metadata only. Paths
    # are recorded, payloads are never copied into the result.
    history_paths = [
        ROOT / "reports/trading/webull_loop_2_latest.json",
        ROOT / "reports/trading/webull_sandbox_canary_latest.json",
        ROOT / "reports/runtime/nexus_credential_catalog_latest.json",
        ROOT / "configs/nexus_credential_registry.json",
    ]
    history = [str(path.relative_to(ROOT)) for path in history_paths if path.is_file()]
    papertrade = WebullProvider(environment="sandbox", timeout=8.0)
    auth = {"status": "NOT_ATTEMPTED", "error_class": None}
    market = {"status": "NOT_ATTEMPTED", "error_class": None}
    if all(present.values()):
        auth = papertrade.health()
        if auth.get("status") == "PASS_REAL":
            try:
                snapshot = papertrade.market_data_snapshot("TSLA")
                market = {"status": "PASS_REAL", "http_status": snapshot.get("http_status"),
                          "symbol": "TSLA", "environment": "sandbox", "values_included": False}
            except Exception as exc:
                market = {"status": "FAIL", "error_class": getattr(exc, "error_class", type(exc).__name__),
                          "values_included": False}
    else:
        auth = {"status": "NOT_RUN_CREDENTIALS_MISSING", "error_class": "CREDENTIAL_MISSING",
                "values_included": False}
        market = {"status": "NOT_RUN_CREDENTIALS_MISSING", "values_included": False}
    recoverable_refs = ["~/.config/nexus/runtime.env", "canonical runtime .env.local/.env",
                        "~/nexuslive/.env", "~/nexus/.env", "Keychain service nexus/credential.webull.openapi.prod.v1",
                        "approved process/launchd environment references"]
    result_status = "WEBULL_READ_ONLY_CHECK_COMPLETE" if all(present.values()) else "WEBULL_CREDENTIALS_NOT_RESOLVED"
    return {
        "status": result_status,
        "summary": "Systems inspected the existing Webull PaperTrade credential route using redacted metadata and read-only provider checks.",
        "supporting_data": {"credential_id": credential_id, "application": "Nexus",
            "environment": "sandbox", "app_key_present": present.get("app_key", False),
            "app_secret_present": present.get("app_secret", False), "secret_location_reference": refs,
            "auth_test": auth, "market_data_test": market, "history_items_found": history,
            "history_lookup": "Existing reports, credential registry and provider resolver checked; raw values excluded."},
        "what_was_found": "Both required credential components resolved." if all(present.values()) else
            "The canonical resolver did not find both Webull credential components in its configured sources.",
        "what_remains_unknown": (["Whether an existing credential is stored in an approved location outside the resolver's configured sources."]
            if not all(present.values()) else ["Historical bar entitlement, pagination and real-volume semantics remain unverified by the bounded snapshot check."]),
        "what_was_tried": ["Read credential registry metadata", "Resolve configured credential sources without returning values",
            "Inspect existing Webull receipts and provider configuration"] + (["Read-only PaperTrade health and TSLA snapshot"] if all(present.values()) else []),
        "what_not_to_repeat": ["Do not create another application or rotate/reset the existing key."],
        "recommendation": "Continue the Wick objective using OANDA while Systems searches the remaining approved Webull credential references." if not all(present.values()) else
            "Continue read-only market-data entitlement and historical-bar verification before using Webull data in a replay.",
        "actionable_items": ["Systems: search approved launchd/operator and Keychain references for the existing Nexus PaperTrade app credential; if present, add only the reference to the canonical resolver and repeat the read-only check. If absent, leave credentials unchanged and let Research continue via OANDA."],
        "return_to": "RESEARCH", "next_owner": "RESEARCH",
        "next_action": "Research: update Wick source-fidelity state from this redacted Systems result and choose the highest-value existing data route.",
        "expected_output": "Updated Wick known/unknown/source-fidelity state and next owner/directive; no secret values.",
        "history_items_found": history, "unsearched_approved_locations": recoverable_refs,
        "values_included": False,
    }


def _execute_mercury_wick_directive(case: dict[str, Any], directive: dict[str, Any]) -> dict[str, Any]:
    """Mercury's existing case-specific offline replay adapter; never calls broker APIs."""
    case_id = str(case.get("case_id") or "")
    directive_id = str(directive.get("request_id") or "")
    if case_id != "rcase_98d9635c39cf3ae5a4":
        return {"status": "ALTERNATIVE_ACTION_REQUIRED", "next_action": "ROUTE_TO_CASE_SPECIFIC_TRADING_ADAPTER"}
    from nexus_agent_platform.department_learning import lookup_department_learning
    history = lookup_department_learning("MERCURY_TRADING", topic_terms=["Wick", "EMA200", "stop", "breakout size"])
    root = ROOT
    metadata = directive.get("directive_metadata") or {}
    if str(metadata.get("action_type") or "BACKTEST").upper() in {
            "NOTEBOOK_RECOMMENDATION_REVIEW", "TRADING_REASSESS_EXTERNAL_RESULT"}:
        project = case.get("trading_strategy_project") or {}
        response = str(project.get("last_notebook_recommendation") or "")
        if not response:
            return {"status": "NOTEBOOK_REASSESSMENT_MISSING", "next_action": "RETRY_TRADING_NOTEBOOK_REASSESSMENT"}
        return {"status": "TRADING_RECOMMENDATION_REVIEWED",
            "summary": "Trading reviewed the same-notebook strategy recommendation and validated its next-step against durable project evidence.",
            "supporting_data": {"notebook_id": project.get("notebook_id"),
                "loop_count": project.get("autonomous_loop_count"),
                "response_id": project.get("last_notebook_response_id"),
                "response_hash": project.get("last_notebook_response_hash"),
                "history_lookup": history},
            "what_was_learned": "Trading continuation remains bounded by the two-loop policy; the notebook recommendation is the source for a Loop 2 selection.",
            "recommendation": response[:1500], "next_action": "Use the NotebookLM recommendation and existing source evidence to create the exact Loop 2 directive; if a third material test would be needed, require Ray review."}
    spec = root / str(metadata.get("spec_path") or "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1_m30_validation.json")
    data = root / str(metadata.get("data_path") or "data/runtime/wick_sequence_oanda_eurusd_m30_oos_pre_20261006.json")
    output = root / "data/governed" / f"wick_directive_{directive_id}_result.json"
    if not spec.exists() or not data.exists():
        return {"status": "EXISTING_REPLAY_INPUT_MISSING", "next_action": "RESEARCH_ACQUIRE_OR_SELECT_AVAILABLE_OANDA_DATA"}
    env = dict(os.environ, NEXUS_WICK_REPLAY_SPEC=str(spec), NEXUS_WICK_REPLAY_DATA=str(data),
               NEXUS_WICK_REPLAY_OUT=str(output),
               NEXUS_WICK_TRADING_PROJECT_AUTHORIZED="1",
               NEXUS_WICK_DIRECTIVE_ID=directive_id,
               NEXUS_WICK_STRATEGY_PROJECT_ID=str(metadata.get("strategy_project_id") or
                   (case.get("trading_strategy_project") or {}).get("strategy_project_id") or ""),
               NEXUS_WICK_LIVE_TRADING_ENABLED="NO")
    runner = root / "artifacts/trading/wick_sequence_baseline_v1_replay.py"
    completed = subprocess.run([sys.executable, str(runner)], cwd=root, env=env,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=240)
    if completed.returncode != 0 or not output.exists():
        return {"status": "REPLAY_FAILED_RETRYABLE", "error": completed.stderr[-1200:],
                "history_lookup": history, "next_action": "SYSTEMS_REPAIR_REPLAY_EXECUTION_PATH_THEN_RETRY"}
    replay = json.loads(output.read_text())
    baseline_path = root / "data/governed/wick_sequence_baseline_v1_backtest.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    trades = replay.get("trades") or []
    diagnostics = [{"direction": "LONG" if float(t.get("direction", 0)) > 0 else "SHORT",
        "entry_time": t.get("entry_time"), "exit_time": t.get("exit_time"),
        "exit_reason": t.get("exit_reason"), "net_pnl": t.get("net_pnl"), "net_r": t.get("net_r")}
        for t in trades]
    summary = {key: replay.get(key) for key in ("instrument", "timeframe", "data_provider", "bar_count",
        "date_start", "date_end", "trade_count", "win_rate", "profit_factor", "expectancy",
        "max_drawdown_fraction", "net_result_equity_fraction", "data_sha256", "spec_sha256")}
    return {"status": "BACKTEST_EXECUTED", "directive_id": directive_id,
        "summary": f"Bounded Wick {replay.get('timeframe')} OANDA Practice historical replay completed for {replay.get('bar_count')} bars; no broker/order endpoint used.",
        "dataset": str(data.relative_to(root)), "baseline": {"artifact": str(baseline_path.relative_to(root)),
            "trade_count": baseline.get("trade_count"), "net_result_equity_fraction": baseline.get("net_result_equity_fraction"),
            "win_rate": baseline.get("win_rate"), "profit_factor": baseline.get("profit_factor")},
        "variable_changed": str(metadata.get("variable_changed") or "Non-overlapping historical data window only; strategy specification unchanged."),
        "result": summary, "trade_level_diagnostics": diagnostics, "history_lookup": history,
        "why_result_changed": "The treatment changes the historical window only; any metric delta is attributable to sample/regime differences, not a strategy modification. Causality is not established.",
        "what_was_learned": "Independent out-of-window performance is the next evidence check; this bounded replay remains small and cannot validate author claims or generalize to other markets.",
        "limitations": replay.get("limitations", []), "artifact": str(output.relative_to(root)),
        "next_recommended_action": "Return this out-of-window result to Research and the same Wick notebook; decide whether the negative/small sample warrants another source-supported test or more data.",
        "live_trading_enabled": False, "broker_order_api_called": False}


def execute_goal_recovery(work_order_id: str) -> dict[str, Any]:
    """Execute one persisted empty-queue recovery action without external effects."""
    status, requests = handoffs.rest("GET", f"task_requests?id=eq.{work_order_id}&select=id,payload,status&limit=1")
    if status != 200 or not isinstance(requests, list) or not requests:
        raise ValueError("continuation_work_order_not_found")
    order = requests[0]
    payload = order.get("payload") if isinstance(order.get("payload"), dict) else {}
    if payload.get("request_kind") != "DEPARTMENT_GOAL_RECOVERY":
        raise ValueError("not_goal_recovery_work")
    rows = _read_portfolio()
    goal = next((row for row in rows if row.get("goal_id") == payload.get("goal_id")), None)
    if not goal or goal.get("status") not in {"ACTIVE", "READY", "QUEUED"}:
        raise ValueError("active_goal_required")
    result = {"status": "CONTINUATION_ACTION_EXECUTED", "goal_id": goal["goal_id"],
              "department": payload.get("department"), "action": payload.get("action"),
              "examined_prior_result": goal.get("last_result"), "next_action": "SELECT_ALTERNATE_BOUNDED_ACTION_FROM_DURABLE_EVIDENCE",
              "external_action_performed": False, "success_criteria_met": "NO"}
    timestamp = now()
    payload["result"] = result
    payload["executed_at"] = timestamp
    patch_status, body = handoffs.rest("PATCH", f"task_requests?id=eq.{work_order_id}&status=eq.requested",
        body={"status": "done", "payload": payload,
              "result_summary": json.dumps({"status": result["status"], "next_action": result["next_action"]}),
              "updated_at": timestamp}, prefer="return=representation")
    if patch_status not in (200, 204):
        raise RuntimeError(f"continuation_result_persist_failed:{patch_status}")
    goal.update({"last_result": result, "last_progress_at": timestamp, "updated_at": timestamp,
                 "next_action": result["next_action"], "current_action": result["next_action"], "status": "ACTIVE"})
    _write_portfolio(rows)
    return {"status": "EXECUTED", "work_order_id": work_order_id, "goal_id": goal["goal_id"], "result": result}


def recover_empty_department_goals(*, goal_ids: set[str] | None = None) -> dict[str, Any]:
    """Create next work in the existing task_requests queue for active empty goals."""
    rows = _read_portfolio()
    status, existing_requests = handoffs.rest("GET", "task_requests?select=id,status,payload&limit=1000")
    if status != 200 or not isinstance(existing_requests, list):
        raise RuntimeError(f"task_request_read_failed:{status}")
    active_by_goal: set[str] = set()
    active_request_by_goal: dict[str, dict[str, Any]] = {}
    last_by_goal: dict[str, dict[str, Any]] = {}
    for order in existing_requests:
        payload = order.get("payload") if isinstance(order.get("payload"), dict) else {}
        goal_id = str(payload.get("goal_id") or "")
        if not goal_id:
            continue
        if order.get("status") in {"requested", "assigned", "in_progress"}:
            active_by_goal.add(goal_id)
            active_request_by_goal[goal_id] = order
        if goal_id not in last_by_goal:
            last_by_goal[goal_id] = order
    pending = []
    recovered = []
    reconciled = []
    for goal in rows:
        if str(goal.get("status") or "").upper() not in {"ACTIVE", "READY", "QUEUED"}:
            continue
        goal_id = str(goal.get("goal_id") or "")
        if goal_ids is not None and goal_id not in goal_ids:
            continue
        if not goal_id:
            continue
        if goal_id in active_by_goal:
            # A prior recovery may have durably queued work just before the
            # local goal mirror was written (or the goal may have been added
            # later). Keep the portfolio action in sync with that existing
            # request instead of treating the active goal as actionless.
            active_payload = (active_request_by_goal.get(goal_id) or {}).get("payload") or {}
            queued_action = str(active_payload.get("action") or "").strip()
            if queued_action:
                changed = False
                if not goal.get("current_action"):
                    goal["current_action"] = queued_action
                    changed = True
                if not goal.get("next_action"):
                    goal["next_action"] = queued_action
                    changed = True
                if changed:
                    goal["updated_at"] = now()
                    reconciled.append(goal_id)
            continue
        target = str(goal.get("owner_department") or goal.get("department") or "").upper()
        if target in {"OPPORTUNITY", "MARKETING/CREATIVE"}:
            target = "ATLAS_OPPORTUNITY" if target == "OPPORTUNITY" else "MARKETING"
        if target in {"NEXUS/SYSTEMS", "SYSTEMS"}:
            target = "SYSTEMS"
        if target not in PARENT_GOALS:
            continue
        prior_order = last_by_goal.get(goal_id)
        action = str(goal.get("next_action") or _next_action(target, str(goal.get("statement") or "")))
        if prior_order and prior_order.get("status") in {"done", "rejected"} and (prior_order.get("payload") or {}).get("action") == action:
            action = _failure_strategy_action(goal, prior_order)
        goal["next_action"] = action
        goal["current_action"] = action
        goal["updated_at"] = now()
        recovered.append(goal.get("goal_id"))
        pending.append({
            "task_type": "department_goal_continuation", "requested_by": "nexus_active_operator",
            "sensitivity": "internal_summary", "allowed_data_scope": ["goal", "internal_evidence"],
            "forbidden_data": ["credentials", "live_trade_execution", "real_spending", "external_publishing"],
            "assigned_worker_type": "nexus_department_continuation_worker", "hermes_visibility": "summary",
            "status": "requested", "payload": {"request_kind": "DEPARTMENT_GOAL_RECOVERY",
                "goal_id": goal_id, "parent_goal_id": goal.get("parent_goal_id"), "department": target,
                "action": action, "eligibility": "ELIGIBLE_INTERNAL_READ_ONLY", "owner": target,
                "external_actions_allowed": False},
        })
    if recovered or reconciled:
        _write_portfolio(rows)
    created = 0
    if pending:
        write_status, written = handoffs.rest("POST", "task_requests", body=pending, prefer="return=representation")
        if write_status not in (200, 201) or not isinstance(written, list):
            raise RuntimeError(f"goal_recovery_insert_failed:{write_status}:{str(written)[:160]}")
        created = len(written)
    return {"status": "PASS", "recovered_goal_count": len(recovered), "goal_ids": recovered,
            "reconciled_active_goal_count": len(reconciled), "reconciled_goal_ids": reconciled,
            "work_orders_created": created}


if __name__ == "__main__":
    print(json.dumps({"reconcile": reconcile_active_handoffs(), "recovery": recover_empty_department_goals()}, indent=2))
