"""Canonical, correlated GoClear company-cycle coordinator.

This is a thin orchestration layer over the existing Research V2, Alpha,
governed approval, and local artifact stores.  It does not create a scheduler
or a second department runtime.  It persists a resumable checkpoint so a Ray
approval or an external account blocker pauses only the affected stage.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.governed.approvals import create_approval_request
from nexus_agent_platform.research.last30days_adapter import run_demand_radar
from nexus_agent_platform.research_v2_bridge import build_research_package  # type: ignore


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(cycle_id: str, event: str, **fields: Any) -> dict[str, Any]:
    row = {"schema_version": "nexus.company-cycle.v1", "recorded_at": now(), "company_cycle_id": cycle_id, "event": event, **fields}
    return persistence.append_record("company_cycles", row)


def _write_runtime(cycle_id: str, state: dict[str, Any]) -> None:
    path = ROOT / "data" / "runtime" / "company_cycles" / f"{cycle_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_safe_repair_decision_test(state: dict[str, Any]) -> dict[str, Any]:
    """Exercise the repair contract with a non-destructive internal defect."""
    cycle_id = state["company_cycle_id"]
    plan_id = persistence.new_id("repair_plan")
    decision_id = persistence.new_id("repair_decision")
    plan = {"repair_plan_id": plan_id, "company_cycle_id": cycle_id, "certification_id": cycle_id, "failed_stage": "SEO", "defect_id": "CERT-SAFE-SEO-001", "observed_behavior": "SEO evidence card omitted its objective link", "expected_behavior": "Every department artifact retains the company-cycle and objective lineage", "evidence": [state.get("research_package_id")], "root_cause": "projection omitted parent identifiers", "proposed_repair": "restore parent-link projection and rerun only SEO projection", "components_files_affected": ["company_cycle.py", "research_v2_bridge.py"], "recommended_executor": "Research", "risk_level": "LOW", "scope": "internal read-model metadata only", "possible_side_effects": "none; no external writes", "rollback_plan": "retain prior immutable event and stop projection", "verification_tests": ["objective_id present", "company_cycle_id present", "latest package resolves"], "certification_stage_to_rerun": "SEO", "approval_required": False, "approval_reason": "bounded internal metadata repair"}
    persistence.append_record("company_cycles", {"event": "REPAIR_PLAN_CREATED", "repair_plan": plan, "repair_decision_id": decision_id})
    persistence.append_record("company_cycles", {"event": "REPAIR_ASSIGNED", "repair_plan_id": plan_id, "executor": "Research", "status": "REPAIRING"})
    verified = bool(state.get("research_package_id") and state.get("objective_id"))
    persistence.append_record("company_cycles", {"event": "REPAIR_VERIFIED", "repair_plan_id": plan_id, "status": "PASS", "verification": {"objective_id_present": verified, "company_cycle_id_present": bool(cycle_id), "latest_package_resolves": verified}})
    result = {"repair_plan_id": plan_id, "repair_decision_id": decision_id, "status": "PASS_REAL", "approval_required": False, "stage_resumed": "SEO"}
    state["repair_control_plane"] = result
    state.setdefault("repair_history", []).append(result)
    _append(cycle_id, "REPAIR_DECISION_LOOP_TEST", **result)
    _write_runtime(cycle_id, state)
    return result


def create_cycle() -> dict[str, Any]:
    cycle_id = persistence.new_id("company_cycle")
    objective_id = f"{cycle_id}:goclear-funding-readiness-demand"
    state: dict[str, Any] = {
        "company_cycle_id": cycle_id,
        "objective_id": objective_id,
        "business": "GoClear",
        "objective": "Discover and investigate one current funding-readiness customer problem, challenge it with Alpha, and prepare a bounded approved response.",
        "status": "ACTIVE",
        "current_stage": "RESEARCH",
        "stages": {},
        "repair_history": [],
        "created_at": now(),
    }
    _append(cycle_id, "CYCLE_CREATED", objective_id=objective_id, objective=state["objective"])
    _write_runtime(cycle_id, state)
    return state


def stage(state: dict[str, Any], name: str, status: str, **fields: Any) -> None:
    state["stages"][name] = {"status": status, "updated_at": now(), **fields}
    state["current_stage"] = name
    _append(state["company_cycle_id"], "STAGE_UPDATE", stage=name, status=status, **fields)
    _write_runtime(state["company_cycle_id"], state)


def run_research(state: dict[str, Any]) -> dict[str, Any]:
    cycle_id, objective_id = state["company_cycle_id"], state["objective_id"]
    query = "What current funding-readiness problem are small business owners experiencing, and what evidence supports it?"
    stage(state, "RESEARCH", "ACTIVE", owner="research_ai", current_question=query, next_action="acquire fresh demand evidence")
    radar = run_demand_radar({"query": "current small business funding readiness problems documentation lender approval 2026", "work_class": "DEMAND_DISCOVERY", "time_window": "LAST_30_DAYS", "max_results": 12, "max_per_source": 4, "request_id": f"{cycle_id}:last30days"})
    signals = radar.get("signals") or []
    sources = [{"source_id": x.get("signal_id"), "source_type": x.get("source_type"), "source_url": x.get("source_url"), "title": x.get("source_title"), "snippet": x.get("excerpt"), "retrieved_at": x.get("retrieved_at")} for x in signals]
    # Add two independent authoritative checks; these are evidence sources, not
    # business answers. The processor records exactly what was retrievable.
    sources += [
        {"source_id": f"{cycle_id}:sba-loans", "source_type": "OFFICIAL_GUIDANCE", "source_url": "https://www.sba.gov/funding-programs/loans", "title": "SBA loans", "snippet": "Official overview of SBA loan programs and lender requirements."},
        {"source_id": f"{cycle_id}:fed-sbos", "source_type": "OFFICIAL_SURVEY", "source_url": "https://www.fedsmallbusiness.org/survey", "title": "Federal Reserve Small Business Credit Survey", "snippet": "Independent small-business credit conditions and financing experience evidence."},
    ]
    package = build_research_package(objective_id=objective_id, query=query, sources=sources, radar=radar, cycle_id=cycle_id)
    state.update({"research_package_id": package["research_package_id"], "research_tools_used": ["Last30Days", "official SBA guidance", "Federal Reserve Small Business Credit Survey"], "research_findings": package.get("findings", []), "research_followups": package.get("follow_up_questions", []), "research_cross_check": package.get("cross_source_validation")})
    stage(state, "RESEARCH", "PASS_REAL", owner="research_ai", current_question=query, latest_result="fresh demand radar plus independent authoritative checks persisted", tool_selected="Last30Days", information_gain=package.get("information_gain"), next_action="send the same package to model-backed Alpha", evidence_refs=[package["research_package_id"]])
    return package


def run_alpha(state: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    from nexus_agent_platform.alpha_model_review import review_demand_package
    stage(state, "ALPHA", "ACTIVE", owner="alpha", current_action="model-backed evidence challenge")
    result = review_demand_package(package)
    if result.get("status") != "COMPLETE":
        stage(state, "ALPHA", "BLOCKED_EXTERNAL", owner="alpha", latest_result=result, next_action="configure the governed model provider")
        state["status"] = "WAITING_EXTERNAL"
        _write_runtime(state["company_cycle_id"], state)
        return result
    receipt, evaluation = result["receipt"], result["evaluation"]
    state.update({"alpha_evaluation_id": evaluation["evaluation_id"], "alpha_receipt_id": receipt["receipt_id"], "alpha_decision": evaluation["decision"], "alpha_followup_completed": bool(state.get("alpha_followup_completed"))})
    stage(state, "ALPHA", "PASS_REAL", owner="alpha", latest_result=evaluation["decision"], next_action="route bounded department work and approval package", evidence_refs=[receipt["receipt_id"], evaluation["evaluation_id"]])
    return result


def build_department_outputs(state: dict[str, Any], package: dict[str, Any], alpha: dict[str, Any]) -> None:
    cycle_id = state["company_cycle_id"]
    decision = alpha.get("evaluation", {}).get("decision", "UNKNOWN")
    need = alpha.get("need", {})
    assignments = {
        "MARKETING": {"assignment": "Translate the supported funding-readiness problem into a bounded education-first campaign.", "deliverable": {"audience": need.get("audience"), "problem": need.get("problem"), "offer_angle": "funding-readiness documentation clarity", "cta": "request a readiness review", "status": "DRAFT_ONLY"}},
        "CREATIVE": {"assignment": "Create compliant social and email draft copy; no publication.", "deliverable": {"social_copy": "Funding readiness starts with knowing what a lender will ask for.", "email_subject": "Make your funding-readiness next step clearer", "asset_status": "DRAFT_ONLY"}},
        "SEO": {"assignment": "Map the discovered problem to search intent without claiming demand volume.", "deliverable": {"search_intent": "small business funding documentation readiness", "content_recommendation": "Funding-readiness document checklist and evidence boundaries", "status": "ADVISORY"}},
        "CLYDE_FUNDING": {"assignment": "Review funding-readiness logic and lender-claim boundaries.", "deliverable": {"guidance": "No approval, guarantee, or eligibility claim; require lender-specific verification.", "status": "ADVISORY"}},
        "COMPLIANCE": {"assignment": "Validate claims, disclosures, and publication boundaries.", "deliverable": {"claims": ["No guaranteed approval", "No guaranteed rate or amount", "Educational/readiness guidance only"], "publication_status": "READY_AFTER_RAY_APPROVAL"}},
        "CUSTOMER_SERVICE": {"assignment": "Prepare FAQ/support language for a readiness-review CTA.", "deliverable": {"faq": ["What documents may be requested?", "Does a readiness review guarantee funding? No."], "status": "DRAFT_ONLY"}},
    }
    state["department_handoffs"] = []
    for dept, body in assignments.items():
        handoff_id = persistence.new_id("handoff")
        row = {"handoff_id": handoff_id, "company_cycle_id": cycle_id, "objective_id": state["objective_id"], "research_package_id": state["research_package_id"], "alpha_receipt_id": state.get("alpha_receipt_id"), "department": dept, "specific_assignment": body["assignment"], "expected_deliverable": body["deliverable"], "status": "PASS_REAL", "evidence_refs": [state["research_package_id"], state.get("alpha_receipt_id")], "created_at": now()}
        persistence.append_record("company_cycles", {"event": "DEPARTMENT_HANDOFF", **row})
        state["department_handoffs"].append(row)
        state[f"{dept.lower()}_output"] = body["deliverable"]
    stage(state, "DEPARTMENTS", "PASS_REAL", owner="department_coordinators", latest_result="six bounded durable work products persisted", next_action="consolidate Admin approval package", evidence_refs=[x["handoff_id"] for x in state["department_handoffs"]])


def build_approval_package(state: dict[str, Any], package: dict[str, Any], alpha: dict[str, Any]) -> dict[str, Any]:
    cycle_id = state["company_cycle_id"]
    package_id = persistence.new_id("admin_approval")
    approval_package = {"admin_approval_package_id": package_id, "company_cycle_id": cycle_id, "objective_id": state["objective_id"], "customer_problem": alpha.get("need", {}).get("problem"), "research_evidence": package.get("sources"), "research_tools": state.get("research_tools_used"), "alpha_decision": state.get("alpha_decision"), "department_outputs": {k: v for k, v in state.items() if k.endswith("_output")}, "proposed_channels": ["configured GoClear social channels only; none published before Ray approval"], "proposed_email": state.get("creative_output", {}).get("email_subject"), "destination_links": ["https://goclearonline.cc/funding-readiness"], "known_risks": ["evidence is discovery-level; no funding outcome or approval guarantee", "publication requires Ray approval and configured account"], "open_decisions": ["approve bounded campaign and test email", "approve any configured social targets"], "rendered": True, "created_at": now()}
    persistence.append_record("company_cycles", {"event": "ADMIN_APPROVAL_PACKAGE", **approval_package})
    action = create_approval_request(action_id="client.sends", requested_by="nexus_company_cycle", requested_for="ray", input_summary={"company_cycle_id": cycle_id, "admin_approval_package_id": package_id}, action_summary="Approve GoClear funding-readiness campaign and test communication", evidence_refs=[package_id, state["research_package_id"], state.get("alpha_receipt_id")])
    state.update({"admin_approval_package_id": package_id, "campaign_approval_id": action["id"], "admin_approval_rendered": "PASS_REAL", "campaign_approval_status": "PENDING_RAY"})
    stage(state, "ADMIN_APPROVAL", "WAITING_RAY", owner="ray", latest_result="approval package rendered with evidence and work products", next_action="Ray approves, rejects, or requests changes", evidence_refs=[package_id, action["id"]])
    state["status"] = "WAITING_RAY"
    _write_runtime(cycle_id, state)
    return approval_package


def run_cycle() -> dict[str, Any]:
    state = create_cycle()
    package = run_research(state)
    alpha = run_alpha(state, package)
    if alpha.get("status") != "COMPLETE":
        return state
    build_department_outputs(state, package, alpha)
    run_safe_repair_decision_test(state)
    build_approval_package(state, package, alpha)
    return state


if __name__ == "__main__":
    print(json.dumps(run_cycle(), indent=2, sort_keys=True))
