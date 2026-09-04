"""General parent-goal continuation contracts for the Nexus Active Operator.

This is a pure decision layer. It does not execute providers, mutate external
systems, or create a scheduler. Existing runners supply evidence and perform
the bounded action selected by these contracts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TERMINAL_STATES = {"GOAL_COMPLETED", "GOAL_INVALIDATED_BY_EVIDENCE", "GOAL_SUPERSEDED", "GOAL_DEFERRED_BY_EXPLICIT_PRIORITY_DECISION", "TRUE_EXTERNAL_BLOCKER", "SAFETY_BLOCKED", "REQUIRES_RAY_APPROVAL", "REQUIRES_HUMAN_ORIGIN_EVENT", "TECHNICALLY_UNSOLVABLE_WITH_CURRENT_AUTHORITY"}
FAILURE_CLASSES = {"PROVIDER_UNAVAILABLE", "ENDPOINT_BLOCKED", "AUTH_RUNTIME_MISMATCH", "MISSING_CREDENTIAL", "RATE_LIMIT", "BAD_CONFIGURATION", "NETWORK_PATH_FAILURE", "DATA_NOT_AVAILABLE", "WEBSITE_INTERACTIVE_ONLY", "BROWSER_REQUIRED", "API_REQUIRED", "MCP_REQUIRED", "CLI_REQUIRED", "REMOTE_WORKER_REQUIRED", "CAPABILITY_GAP", "DEPENDENCY_MISSING", "FORMAT_CHANGED", "TEMPORARY_PROVIDER_ERROR", "PAID_SERVICE_REQUIRED", "LEGAL_TERMS_RESTRICTION", "SAFETY_BLOCKED"}
RESOLUTION_LADDER = ("REUSE_PREVIOUS_SUCCESSFUL_PATH", "CHECK_CONFIG_ENVIRONMENT", "EXISTING_CODE", "EXISTING_CREDENTIAL_CONTROL", "CLI", "API", "MCP", "PUBLIC_WEB", "ORACLE_BROWSER", "EXISTING_REMOTE_WORKER", "MODAL_CPU", "RESEARCH_ALTERNATIVE_PROVIDER", "GITHUB_OPEN_SOURCE_RESEARCH", "BUILD_OR_ADAPT_CONNECTOR", "REROUTE_OBJECTIVE", "RAY_ONLY_TRUE_BOUNDARY")
ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO_PATH = ROOT / "data/runtime/company_goal_portfolio.json"
ELIGIBLE_STATUSES = {"ACTIVE", "READY", "QUEUED"}
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


# This is the durable seed for the single runtime portfolio.  It contains
# definitions and success criteria only; progress/status are persisted in
# PORTFOLIO_PATH and are never inferred from a report existing.
ROADMAP_GOALS = (
    ("trading.real_data", "Trading", "Complete verified real market-data lanes and the research/backtest/OOS/paper pipeline.", "P1", (), ("real Forex/stock/options/crypto data lane proven or evidenced blocker", "real data-to-backtest-to-OOS-to-paper receipt", "failed paths produce next bounded work")),
    ("research.company_intelligence", "Research", "Operate a cross-department intelligence service with provenance and Alpha challenge.", "P1", (), ("department research contract proven", "fresh findings have source provenance", "Alpha review and department handoff recorded")),
    ("portal.client_beta", "Portal/Product", "Advance the GoClear client portal toward controlled human beta readiness.", "P2", (), ("capability audit recorded", "highest-value beta gap implemented or actively worked", "tenant and approval boundaries verified")),
    ("portal.admin_control_center", "Portal/Product", "Advance Ray Admin into a useful company control center.", "P2", (), ("current admin capability audit recorded", "highest-value control-center gap implemented or actively worked", "executive state is readable")),
    ("goclear.example_campaign", "Marketing/Creative", "Produce and internally review one complete GoClear campaign example.", "P2", (), ("Research and Marketing rationale recorded", "Creative campaign package exists", "publication remains approval-gated")),
    ("systems.modal_verification", "Systems", "Verify governed Modal CPU capability for bounded internal workloads.", "P2", (), ("health check proven", "bounded job result returned", "cost and authority boundaries recorded")),
    ("systems.oracle_browser", "Systems", "Verify the existing Oracle browser/computer-control capability.", "P2", (), ("Oracle path proven", "bounded read-only browser result returned", "stale-session recovery path documented")),
    ("clyde.entity_readiness", "Clyde", "Build governed entity and business-readiness intelligence for Funding handoff.", "P2", ("research.company_intelligence",), ("structured readiness model exists", "evidence linkage and handoff readiness proven", "legal/tax determinations remain out of scope")),
    ("business_plans.customer_goals", "Funding/Product", "Build canonical customer goals and business-plan capability used across GoClear.", "P2", ("portal.client_beta",), ("goals and milestones model exists", "use-of-funds and evidence linkage proven", "portal visibility proven")),
    ("funding.workflow_expansion", "Funding", "Complete governed Funding research, matching, readiness, and planning workflow.", "P2", ("clyde.entity_readiness", "business_plans.customer_goals"), ("readiness workflow exists", "offer and document planning is traceable", "applications remain approval-gated")),
    ("grants.intelligence", "Grants", "Build evidence-backed Grant Intelligence and review-ready draft packages.", "P3", ("business_plans.customer_goals",), ("source monitoring and eligibility model exists", "profile matching and missing information detected", "no autonomous submission")),
    ("goclear.economic_model", "Finance/Opportunity", "Determine evidence-grounded GoClear commercial economics and pricing hypotheses.", "P2", ("research.company_intelligence",), ("competing pricing hypotheses recorded", "value and economics evidence linked", "$97 remains unvalidated absent proof")),
    ("commerce.billing_accounting", "Finance", "Build governed Billing and Accounting capability and reconciliation visibility.", "P2", ("business_plans.customer_goals",), ("invoice lifecycle model tested", "receivables/expense views defined", "external invoices remain gated")),
    ("customer_service.communications", "Customer Service", "Build governed support, case, history, escalation, and drafting capability.", "P3", ("portal.client_beta",), ("case lifecycle exists", "customer context and handoff are traceable", "unsolicited communication is blocked")),
    ("documents.esign", "Documents", "Build governed Documents and e-sign workflows with auditability.", "P3", ("research.company_intelligence",), ("template/version workflow exists", "signature integration candidates audited", "consent and retention evidence defined")),
    ("research.notebook", "Research", "Build the Ray Admin Research Notebook and Source Manager over the existing Research plane.", "P2", ("research.company_intelligence",), ("notebook/source/question model exists", "claims and contradictions link to Alpha", "department handoff is readable")),
    ("opportunity.engine", "Opportunity", "Continue the evidence-backed business opportunity engine from research to measurement.", "P2", ("research.company_intelligence",), ("opportunity scoring is evidence-bound", "experiment design and routing exist", "hype and weak economics are rejected")),
    ("marketing.creative_expansion", "Marketing/Creative", "Expand internal Marketing and Creative campaign capability.", "P3", ("goclear.example_campaign",), ("campaign asset workflow exists", "landing/email/SEO/CTA artifacts are reviewable", "creative-first and external use gated")),
    ("media.youtube_video", "Creative", "Build reusable internal YouTube/video production workflow.", "P3", ("marketing.creative_expansion",), ("research-to-script workflow exists", "render/review loop proven", "publication and analytics remain future gated")),
    ("distribution.social", "Marketing", "Build governed social/content distribution planning and production.", "P3", ("marketing.creative_expansion",), ("calendar and channel plan exist", "assets and review states are traceable", "public posting remains gated")),
    ("finance.capital_management", "Finance", "Expand Finance into a capital-management intelligence layer.", "P3", ("commerce.billing_accounting",), ("cash/reserve/capital model defined", "scenario reasoning is evidence-bound", "no real transaction authority")),
    ("nexus.intent_program_compiler", "Nexus/Systems", "Build incrementally toward the future intent-to-program compiler.", "P3", ("research.notebook",), ("intent maps to parent-goal proposal", "dependencies and authority envelope included", "current goal system remains canonical")),
    ("nexus.productization", "Nexus/Product", "Prepare governed multi-tenant commercialization after core capability proof.", "P4", ("portal.client_beta", "commerce.billing_accounting", "nexus.intent_program_compiler"), ("productization options researched", "tenant/cost/governance model defined", "dependency-gated until proof is mature")),
)


def _portfolio_read() -> list[dict[str, Any]]:
    try:
        value = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        if isinstance(value, list):
            return value
    except (OSError, ValueError, TypeError):
        pass
    return []


def _portfolio_write(rows: list[dict[str, Any]]) -> None:
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PORTFOLIO_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(PORTFOLIO_PATH)


def ensure_company_goal_portfolio() -> list[dict[str, Any]]:
    """Materialize the one durable company portfolio without losing progress."""
    existing = {str(row.get("goal_id")): row for row in _portfolio_read() if isinstance(row, dict)}
    timestamp = _now()
    rows = []
    for goal_id, department, statement, priority, dependencies, criteria in ROADMAP_GOALS:
        prior = existing.get(goal_id, {})
        dependency_blocked = any(existing.get(dep, {}).get("status") == "PLANNED_DEPENDENCY" for dep in dependencies)
        default_status = "PLANNED_DEPENDENCY" if goal_id == "nexus.productization" or (dependencies and dependency_blocked) else ("ACTIVE" if priority in {"P1", "P2"} else "READY")
        row = {
            **prior, "schema_version": "nexus.company-goal-portfolio.v1", "goal_id": goal_id,
            "program_id": prior.get("program_id", goal_id.split(".", 1)[0]), "statement": statement,
            "domain": prior.get("domain", statement), "owner": prior.get("owner", "NEXUS"), "department": department, "priority": priority,
            "status": ("PLANNED_DEPENDENCY" if goal_id == "nexus.productization" and prior.get("status") in {None, "ACTIVE", "READY", "QUEUED"} else prior.get("status", default_status)), "authority": "INTERNAL_SAFE",
            "success_criteria": list(prior.get("success_criteria", criteria)),
            "dependencies": list(prior.get("dependencies", dependencies)),
            "active_workstreams": list(prior.get("active_workstreams", [])),
            "current_evidence": list(prior.get("current_evidence", [])),
            "missing_criteria": list(prior.get("missing_criteria", criteria)),
            "failed_paths": list(prior.get("failed_paths", [])),
            "candidate_next_paths": list(prior.get("candidate_next_paths", list(RESOLUTION_LADDER))),
            "last_progress": prior.get("last_progress"), "next_review": prior.get("next_review", timestamp),
            "last_selected_at": prior.get("last_selected_at"), "selection_count": int(prior.get("selection_count", 0)),
            "consecutive_selections": int(prior.get("consecutive_selections", 0)),
            "created_at": prior.get("created_at", timestamp), "updated_at": prior.get("updated_at", timestamp),
        }
        rows.append(row)
    if rows != _portfolio_read():
        _portfolio_write(rows)
    return rows


def operating_duty_preflight() -> dict[str, Any]:
    """Report always-on duties separately from discretionary goal selection."""
    heartbeat = _read_runtime_json(ROOT / "data/runtime/research_heartbeat.json")
    return {"control_plane": "HEALTHY", "supervisor": "RUNNING", "research_heartbeat": heartbeat.get("heartbeat", "UNKNOWN"),
            "research_execution_mode": heartbeat.get("execution_mode", "UNKNOWN"), "receipt_integrity": "HEALTHY",
            "ray_review": "EVALUATE", "safety_authority": "INTERNAL_SAFE", "duty_lane": "OPERATING_DUTY_PREFLIGHT"}


def _read_runtime_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]


@dataclass(frozen=True)
class ParentGoal:
    goal_id: str
    statement: str
    success_criteria: tuple[str, ...]
    owner: str = "NEXUS"
    priority: str = "P2"
    authority_envelope: str = "INTERNAL_SAFE"
    status: str = "ACTIVE"
    active_workstreams: tuple[str, ...] = ()
    current_evidence: tuple[str, ...] = ()
    missing_criteria: tuple[str, ...] = ()
    failed_paths: tuple[str, ...] = ()
    candidate_next_paths: tuple[str, ...] = ()
    last_progress: str | None = None
    next_review: str | None = None


def build_goal(goal_id: str, statement: str, success_criteria: Iterable[str], *, owner: str = "NEXUS", priority: str = "P2", authority_envelope: str = "INTERNAL_SAFE", active_workstreams: Iterable[str] = (), candidate_next_paths: Iterable[str] = ()) -> dict[str, Any]:
    goal = ParentGoal(goal_id, statement, tuple(success_criteria), owner, priority, authority_envelope, active_workstreams=tuple(active_workstreams), candidate_next_paths=tuple(candidate_next_paths), next_review=_now())
    return {**asdict(goal), "schema_version": "nexus.parent-goal.v1", "created_at": _now(), "updated_at": _now()}


def classify_path_failure(result: dict[str, Any]) -> dict[str, Any]:
    raw = " ".join(str(result.get(key, "")) for key in ("error", "reason", "status", "failure_class")).lower()
    if result.get("failure_class") in FAILURE_CLASSES:
        failure_class = result["failure_class"]
    elif any(term in raw for term in ("rate", "429", "throttle")):
        failure_class = "RATE_LIMIT"
    elif any(term in raw for term in ("credential", "401", "403", "auth")):
        failure_class = "AUTH_RUNTIME_MISMATCH"
    elif any(term in raw for term in ("timeout", "connection", "network")):
        failure_class = "NETWORK_PATH_FAILURE"
    elif any(term in raw for term in ("not found", "missing", "unavailable", "no data")):
        failure_class = "DATA_NOT_AVAILABLE"
    else:
        failure_class = "CAPABILITY_GAP"
    return {"failure_class": failure_class, "failed_path": result.get("path") or result.get("provider") or "UNKNOWN", "evidence": result.get("evidence", result.get("error", "UNKNOWN")), "retryability": "BOUNDED" if failure_class not in {"SAFETY_BLOCKED", "LEGAL_TERMS_RESTRICTION"} else "NONE", "known_alternatives": list(result.get("known_alternatives", [])), "classified_at": _now()}


def evaluate_parent_goal(goal: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = evidence or {}
    criteria = list(goal.get("success_criteria", []))
    satisfied = set(evidence.get("satisfied_criteria", []))
    missing = [criterion for criterion in criteria if criterion not in satisfied]
    existing_status = str(goal.get("status", "ACTIVE"))
    if existing_status in TERMINAL_STATES:
        status = existing_status
    elif not missing and criteria:
        status = "GOAL_COMPLETED"
    else:
        status = "ACTIVE"
    return {**goal, "status": status, "current_evidence": list(evidence.get("current_evidence", goal.get("current_evidence", []))), "missing_criteria": missing, "last_progress": evidence.get("last_progress", goal.get("last_progress")), "updated_at": _now()}


def select_next_safe_action(goal: dict[str, Any], *, failure: dict[str, Any] | None = None, attempted_paths: Iterable[str] = ()) -> dict[str, Any]:
    attempted = set(attempted_paths)
    if goal.get("status") in TERMINAL_STATES:
        return {"action": "VERIFY_TERMINAL_STATE", "owner": "NEXUS", "continue_parent": False}
    if failure:
        failure = classify_path_failure(failure) if "failure_class" not in failure else failure
        for path in goal.get("candidate_next_paths", RESOLUTION_LADDER):
            if path not in attempted and path != failure.get("failed_path"):
                return {"action": path, "owner": "NEXUS", "continue_parent": True, "failure": failure, "bounded": True}
        return {"action": "REROUTE_OBJECTIVE", "owner": "NEXUS", "continue_parent": True, "failure": failure, "bounded": True}
    return {"action": (goal.get("candidate_next_paths") or list(RESOLUTION_LADDER))[0], "owner": "NEXUS", "continue_parent": True, "bounded": True}


def should_continue(goal: dict[str, Any], *, evidence: dict[str, Any] | None = None, failure: dict[str, Any] | None = None, attempted_paths: Iterable[str] = ()) -> dict[str, Any]:
    evaluated = evaluate_parent_goal(goal, evidence)
    action = select_next_safe_action(evaluated, failure=failure, attempted_paths=attempted_paths)
    return {"goal": evaluated, "next_action": action, "parent_goal_complete": evaluated["status"] in TERMINAL_STATES, "report_complete_is_goal_complete": False}


def repetition_guard(attempts: Iterable[dict[str, Any]], *, max_identical: int = 2) -> dict[str, Any]:
    rows = list(attempts)
    fingerprints = [fingerprint({"path": row.get("path"), "arguments": row.get("arguments"), "result": row.get("result")}) for row in rows]
    repeated = len(fingerprints) - len(set(fingerprints))
    return {"repeated": repeated >= max_identical, "repeat_count": repeated, "action": "CHANGE_STRATEGY" if repeated >= max_identical else "CONTINUE_BOUNDED", "attempt_fingerprints": fingerprints}


def active_objective_portfolio() -> list[dict[str, Any]]:
    """Return the durable eligible portfolio, preserving all roadmap goals."""
    return [row for row in ensure_company_goal_portfolio() if row.get("status") in ELIGIBLE_STATUSES]


def select_portfolio_goal(goals: Iterable[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any] | None:
    """Select fairly from eligible goals after the operating-duty preflight.

    Priority remains dominant, while age and consecutive selection count prevent
    one open goal from monopolizing the discretionary lane.
    """
    rows = [row for row in goals if row.get("status") in ELIGIBLE_STATUSES]
    if not rows:
        return None
    now = now or datetime.now(timezone.utc)
    for row in rows:
        last = row.get("last_selected_at")
        try:
            age = max(0.0, (now - datetime.fromisoformat(str(last).replace("Z", "+00:00"))).total_seconds()) if last else 10**9
        except ValueError:
            age = 10**9
        row["_age_seconds"] = age
    # Once a goal has had two consecutive discretionary turns, prefer any
    # eligible peer that has materially older progress.
    fair = [row for row in rows if int(row.get("consecutive_selections", 0)) < 2]
    candidates = fair or rows
    selected = min(candidates, key=lambda row: (PRIORITY_RANK.get(str(row.get("priority", "P4")), 4), -float(row.get("_age_seconds", 0)), int(row.get("selection_count", 0)), str(row.get("goal_id"))))
    for row in rows:
        row.pop("_age_seconds", None)
    selected["last_selected_at"] = now.isoformat()
    selected["selection_count"] = int(selected.get("selection_count", 0)) + 1
    selected["consecutive_selections"] = int(selected.get("consecutive_selections", 0)) + 1
    all_rows = ensure_company_goal_portfolio()
    for row in all_rows:
        if row.get("goal_id") == selected.get("goal_id"):
            row.update({key: value for key, value in selected.items() if not key.startswith("_")})
            row["updated_at"] = now.isoformat()
        elif row.get("status") in ELIGIBLE_STATUSES:
            # A different eligible goal receiving consideration resets the
            # streak, which makes the fairness rule durable across cycles.
            row["consecutive_selections"] = 0
    _portfolio_write(all_rows)
    return selected


def next_work_for_active_goal(goal: dict[str, Any], *, work_item_id: str, question: str,
                              department: str | None = None, action: str | None = None) -> dict[str, Any]:
    """Materialize one bounded, idempotent child action for an open parent goal.

    This remains a planning contract: the canonical Active Operator owns queue
    persistence and execution.  Keeping the contract here makes empty-queue
    continuation reusable by departments instead of encoding a Trading-only
    exception in the supervisor.
    """
    if str(goal.get("status", "ACTIVE")) in TERMINAL_STATES:
        return {"dispatch": "SKIP_TERMINAL_GOAL", "continue_parent": False, "goal_id": goal.get("goal_id")}
    # Use the smallest already-authorized internal executor appropriate to the
    # goal.  Research remains the default when evidence is missing; bounded
    # internal reports let existing Portal/Systems/Marketing owners advance
    # without pretending that every department is a Research adapter.
    department = department or str(goal.get("department") or "RESEARCH")
    action = action or str(goal.get("next_action") or "research.refresh")
    if action == "research.refresh" and department != "RESEARCH":
        action = "generate_internal_report"
    return {
        "dispatch": "CREATE_OR_REUSE_WORK_ORDER",
        "goal_id": goal.get("goal_id"),
        "parent_goal": goal.get("statement") or goal.get("domain"),
        "department": department,
        "owner": goal.get("owner", "NEXUS"),
        "priority": goal.get("priority", "P2"),
        "action": action,
        "work_item_id": work_item_id,
        "question": question,
        "authority": goal.get("authority_envelope", "INTERNAL_SAFE"),
        "external_side_effects": False,
        "continue_parent": True,
    }


def record_goal_progress(goal_id: str, *, work_item_id: str, result: dict[str, Any],
                         action: str, receipt_ref: str | None = None) -> dict[str, Any] | None:
    """Persist bounded child-work evidence without declaring the parent done."""
    rows = ensure_company_goal_portfolio()
    for row in rows:
        if row.get("goal_id") != goal_id:
            continue
        evidence = list(row.get("current_evidence", []))
        marker = receipt_ref or f"work:{work_item_id}"
        if marker not in evidence:
            evidence.append(marker)
        workstreams = list(row.get("active_workstreams", []))
        if action not in workstreams:
            workstreams.append(action)
        row["current_evidence"] = evidence[-20:]
        row["active_workstreams"] = workstreams[-12:]
        row["last_progress"] = _now()
        row["updated_at"] = _now()
        # A child receipt is progress, not proof of every parent criterion.
        row["status"] = "ACTIVE" if row.get("status") in ELIGIBLE_STATUSES else row.get("status")
        _portfolio_write(rows)
        return row
    return None
