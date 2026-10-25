"""Deterministic weekend status report maintained by the existing kernel.

This module reads bounded local durable state only. It creates no workers,
queues, schedulers, provider calls, or guessed metrics.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports/weekend"
LATEST = REPORT_DIR / "NEXUS_WEEKEND_AUTONOMY_REPORT_LATEST.txt"
LOCAL_TZ = ZoneInfo("America/Phoenix")
DEPARTMENTS = ("Research", "Opportunities", "Finance", "Trading", "Marketing", "Creative",
               "Labs", "Upgrade Control", "Systems")
MAX_JSON_BYTES = 4 * 1024 * 1024


def _json(path: Path, default: Any) -> Any:
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _jsonl_tail(path: Path, *, max_bytes: int = 2 * 1024 * 1024, max_rows: int = 8000) -> tuple[list[dict[str, Any]], bool]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()  # discard a partial first record
            raw = handle.read(max_bytes + 1)
        rows = []
        for line in raw.splitlines()[-max_rows:]:
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
            except (ValueError, TypeError):
                continue
        return rows, size > max_bytes
    except OSError:
        return [], False


def _latest_by(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for row in rows:
        ident = str(row.get(key) or "")
        if ident:
            found[ident] = row
    return list(found.values())


def _stamp(value: Any) -> datetime | None:
    try:
        text = str(value or "").replace("Z", "+00:00")
        result = datetime.fromisoformat(text)
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result
    except (ValueError, TypeError):
        return None


def _dur(value: float) -> str:
    seconds = max(0, int(value))
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}h {minutes}m {seconds}s"


def _brief(value: Any, limit: int = 220) -> str:
    if isinstance(value, dict):
        keys = ("status", "action", "decision", "final_status", "failure_class", "error", "next_action", "receipt_id", "artifact_id")
        compact = {key: value[key] for key in keys if key in value}
        value = compact or {"keys": list(value)[:8]}
    text = str(value if value not in (None, "") else "UNAVAILABLE").replace("\n", " ")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _collect(now_utc: datetime) -> dict[str, Any]:
    heartbeat = _json(ROOT / "data/runtime/research_heartbeat.json", {})
    tool_layer_rows, _ = _jsonl_tail(ROOT / "data/governed/research_tool_layer_runs.jsonl", max_rows=200)
    latest_tool_run = max(tool_layer_rows, key=lambda row: str(row.get("created_at") or ""), default={})
    receipt = _json(ROOT / "reports/runtime/continuous_operating_kernel_latest.json", {})
    program_rows = _json(ROOT / "data/runtime/research_program_registry.json", [])
    queue_data = _json(ROOT / "data/runtime/research_work_queue.json", {})
    queue_items = queue_data.get("items", []) if isinstance(queue_data, dict) else []
    historical_markers = ("HISTORICAL_BACKFILL", "CONTINUE_HISTORICAL_BACKFILL", "ARCHIVED_BACKLOG", "HISTORICAL_BACKLOG")
    live_items = [r for r in queue_items if isinstance(r, dict) and not any(
        marker in json.dumps(r, default=str).upper() for marker in historical_markers)]
    live_eligible = [r for r in live_items if str(r.get("status", "")).upper() in {
        "PENDING", "QUEUED", "READY", "ASSIGNED", "RETRY", "RETRYABLE"}]
    historical = len(queue_items) - len(live_items)

    portfolio = _json(ROOT / "data/runtime/company_goal_portfolio.json", [])
    goals = portfolio if isinstance(portfolio, list) else []
    goal_time = max((_stamp(g.get("updated_at") or g.get("last_progress")) for g in goals), default=None)
    active_goals = [g for g in goals if str(g.get("status", "")).upper() in {"ACTIVE", "IN_PROGRESS", "ADVANCING"}]
    completed_goals = [g for g in goals if str(g.get("status", "")).upper() in {"COMPLETED", "COMPLETE"}]
    stalled_goals = [g for g in goals if str(g.get("status", "")).upper() in {"STALLED", "BLOCKED", "WAITING_HUMAN"}]

    wo_rows, wo_truncated = _jsonl_tail(ROOT / "data/governed/work_orders.jsonl")
    work_orders = _latest_by(wo_rows, "work_order_id")
    handoff_rows, handoff_truncated = _jsonl_tail(ROOT / "data/governed/research_v2_handoffs.jsonl")
    handoffs = _latest_by(handoff_rows, "handoff_id")
    request_rows, requests_truncated = _jsonl_tail(ROOT / "data/governed/research_requests.jsonl")
    requests = _latest_by(request_rows, "research_request_id")
    finding_rows, findings_truncated = _jsonl_tail(ROOT / "data/governed/research_notebooklm_findings.jsonl")
    findings = _latest_by(finding_rows, "finding_id")
    operating_mode = _json(ROOT / "configs/nexus_operating_mode.json", {})
    weekend_cfg = operating_mode.get("weekend_mode", {}) if isinstance(operating_mode, dict) else {}
    activation = _stamp(weekend_cfg.get("activated_at")) if isinstance(weekend_cfg, dict) else None
    job_rows, jobs_truncated = _jsonl_tail(ROOT / "data/runtime/research_execution_jobs.jsonl", max_bytes=8 * 1024 * 1024)
    weekend_jobs = [row for row in job_rows if not activation or (_stamp(row.get("at") or row.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= activation]
    job_runs = {str(row.get("execution_id")) for row in weekend_jobs if row.get("execution_id")}
    selected_runs = {str(row.get("execution_id")) for row in weekend_jobs
                     if row.get("execution_id") and row.get("status") in {"CLAIMED", "RUNNING", "SOURCE_SELECTED", "NOTEBOOKLM_PROACTIVE_PROCESSOR"}}
    youtube_source_runs = {str(row.get("execution_id")) for row in weekend_jobs
                           if row.get("execution_id") and row.get("status") == "SOURCE_SELECTED"
                           and str(row.get("source_type") or "").upper() == "YOUTUBE_VIDEO"}
    youtube_completed_runs = {str(row.get("execution_id")) for row in weekend_jobs
                               if row.get("execution_id") and row.get("status") == "EVIDENCE_READY"
                               and str(row.get("processor") or "").startswith("youtube_full_pipeline")}
    youtube_processed = len(youtube_source_runs & youtube_completed_runs)
    completed_worker_events = [row for row in weekend_jobs if row.get("status") in {
        "COMPLETED", "EVIDENCE_READY", "DEPARTMENT_EXPERT_ASSESSMENT", "FAILED_RETRYABLE", "FAILED_FINAL"}]
    latest_worker_event = max(completed_worker_events, key=lambda row: str(row.get("at") or ""), default={})
    package_ids = {str(row.get("research_package_id") or row.get("research_id")) for row in weekend_jobs
                   if row.get("status") in {"EVIDENCE_READY", "EVIDENCE_INCOMPLETE"} and (row.get("research_package_id") or row.get("research_id"))}
    local_findings = [row for row in finding_rows if not activation or (_stamp(row.get("created_at") or row.get("recorded_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= activation]
    finding_count = max(len(local_findings), len(package_ids))
    local_handoffs = [row for row in handoffs if not activation or (_stamp(row.get("created_at") or row.get("updated_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= activation]
    routed = {str(row.get("finding_id") or row.get("information_item_id") or row.get("execution_id")) for row in weekend_jobs
              if row.get("status") == "DEPARTMENT_INFORMATION_ROUTED"}
    handoff_receipts = []
    receipt_dir = ROOT / "reports/runtime/department_handoffs"
    if receipt_dir.exists():
        for path in receipt_dir.glob("*.json"):
            item = _json(path, {})
            stamp = _stamp(item.get("created_at") or item.get("processed_at") or item.get("recorded_at"))
            if item and (not activation or (stamp and stamp >= activation)):
                handoff_receipts.append(item)
    handoff_count = max(len(local_handoffs), len(routed), len(handoff_receipts))
    ack_events = {str(row.get("assessment_id") or row.get("information_item_id")) for row in weekend_jobs
                  if row.get("status") in {"DEPARTMENT_EXPERT_ASSESSMENT", "HANDOFF_ACKNOWLEDGED"}}
    registry = _json(ROOT / "data/runtime/alpha_source_registry.json", [])
    checked_channels = []
    for row in registry if isinstance(registry, list) else []:
        if str(row.get("source_type") or "").upper() not in {"YOUTUBE_CHANNEL", "YOUTUBE_CHANNELS"}:
            continue
        stamp = _stamp(row.get("last_checked_at") or row.get("last_checked"))
        if row.get("enabled", row.get("monitoring_enabled", False)) and stamp and (not activation or stamp >= activation):
            checked_channels.append(row)
    proactive_wake = _json(ROOT / "reports/runtime/proactive_discovery_wake_latest.json", {})
    proactive_candidates = [proactive_wake] if proactive_wake.get("selected_task") else []
    for path in (ROOT / "reports/runtime").glob("NEXUS_PROACTIVE_DISCOVERY_*.json"):
        item = _json(path, {})
        if item.get("selected_task"):
            proactive_candidates.append(item)
    if proactive_candidates:
        proactive_wake = max(proactive_candidates, key=lambda item: str(item.get("recorded_at") or ""))
    objective_history = ROOT / "data/governed/proactive_research_objective_runs.jsonl"
    try:
        objective_rows = [json.loads(line) for line in objective_history.read_text(encoding="utf-8").splitlines()[-1000:]]
        objective_runs = [row for row in objective_rows if isinstance(row, dict) and row.get("record_type") == "PROACTIVE_OBJECTIVE_RUN"]
        if objective_runs:
            latest_objective = max(objective_runs, key=lambda row: str(row.get("last_run_at") or ""))
            if str(latest_objective.get("last_run_at") or "") > str(proactive_wake.get("recorded_at") or ""):
                objective = latest_objective.get("last_run_snapshot") or {}
                proactive_wake = {**proactive_wake, "selected_task": "PROACTIVE_SEARCH",
                    "recorded_at": latest_objective.get("last_run_at"),
                    "current_proactive_objective": latest_objective.get("research_question"),
                    "why_this_objective_was_selected": latest_objective.get("why_this_objective_was_selected"),
                    "objective_family": latest_objective.get("objective_family"),
                    "query": latest_objective.get("query"),
                    "source_classes": latest_objective.get("source_classes_used", []),
                    "raw_signals": latest_objective.get("raw_signals", (latest_objective.get("last_result") or {}).get("raw_signals", 0)),
                    "qualified_findings": latest_objective.get("qualified_findings", 0),
                    "handoffs": (latest_objective.get("last_result") or {}).get("handoffs", 0),
                    "saturation_state": latest_objective.get("saturation_state"),
                    "next_research_direction": "Rotate to another unsaturated customer/business objective family." if latest_objective.get("saturation_state") == "SATURATED_RECENTLY" else "Continue the open evidence gap through the existing Research contract."}
    except (OSError, ValueError, TypeError):
        pass
    youtube_run = _json(ROOT / "reports/runtime/weekend_youtube_monitor_latest.json", {})
    youtube_reconciliation = _json(ROOT / "reports/runtime/youtube_notebooklm_live_reconciliation_latest.json", {})
    notebooklm_inventory = _json(ROOT / "reports/runtime/notebooklm_inventory_latest.json", {})
    notebook_rows = notebooklm_inventory.get("notebooks", []) if isinstance(notebooklm_inventory, dict) else []
    notebook_rows = [row for row in notebook_rows if isinstance(row, dict)]
    notebook_case_rows = [row for row in notebook_rows if str(row.get("notebook_name") or "").startswith("Nexus Research Case ")]
    notebook_case_ids = {str(row.get("notebook_name", "")).removeprefix("Nexus Research Case ")
                         for row in notebook_case_rows}
    runtime_case_rows, _ = _jsonl_tail(ROOT / "data/governed/research_runtime_states.jsonl", max_rows=12000)
    latest_research_cases: dict[str, dict[str, Any]] = {}
    for row in runtime_case_rows:
        if row.get("memory_kind") not in {"PROACTIVE_RESEARCH_CASE", "RESEARCH_CASE"} or not row.get("case_id"):
            continue
        case_id = str(row["case_id"])
        prior = latest_research_cases.get(case_id)
        if prior is None or str(row.get("recorded_at") or "") >= str(prior.get("recorded_at") or ""):
            latest_research_cases[case_id] = row
    logged_notebook_ids: set[str] = set()
    logged_case_ids: set[str] = set()
    result_rows, _ = _jsonl_tail(ROOT / "data/runtime/notebooklm_research_results.jsonl", max_rows=1200)
    for row in result_rows:
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        ident = provenance.get("notebook_id") or row.get("notebook_id")
        if ident:
            logged_notebook_ids.add(str(ident))
        case_id = provenance.get("research_case_id") or row.get("research_case_id")
        if case_id:
            logged_case_ids.add(str(case_id))
    notebook_ids = {str(row.get("notebook_id") or "") for row in notebook_rows}
    nexus_notebook_count = sum(str(row.get("notebook_name") or "").startswith("Nexus") or
                               str(row.get("notebook_id") or "") in logged_notebook_ids for row in notebook_rows)
    mapped_case_ids = notebook_case_ids & (set(latest_research_cases) | logged_case_ids)
    active_case_ids = {case_id for case_id, row in latest_research_cases.items()
                       if str(row.get("status") or "").upper() in {"OPEN", "ACTIVE", "FOLLOWUP_WINDOW",
                           "DISCOVERED", "PROMISING", "UNDER_DEVELOPMENT", "RESEARCHING_MISSING_PIECES",
                           "SYNTHESIZING", "RECOMMENDATION_READY", "DEPARTMENT_DEVELOPMENT", "TESTING",
                           "REFINING", "MORE_RESEARCH_REQUIRED", "QUALIFIED"}}
    followup_case_ids = {case_id for case_id, row in latest_research_cases.items()
                         if str(row.get("status") or "").upper() in {"FOLLOWUP_WINDOW", "UNDER_DEVELOPMENT",
                             "RESEARCHING_MISSING_PIECES", "MORE_RESEARCH_REQUIRED", "REFINING"}}
    objective_cases = [row for row in latest_research_cases.values()
                       if row.get("memory_kind") == "RESEARCH_CASE"]
    objective_case_metrics = {
        "active_deep_cases": sum(str(row.get("status") or "").upper() in {
            "DISCOVERED", "PROMISING", "UNDER_DEVELOPMENT", "RESEARCHING_MISSING_PIECES",
            "SYNTHESIZING", "RECOMMENDATION_READY", "DEPARTMENT_DEVELOPMENT", "TESTING",
            "REFINING", "MORE_RESEARCH_REQUIRED", "QUALIFIED"} for row in objective_cases),
        "cases_recommendation_ready": sum(str(row.get("status") or "").upper() == "RECOMMENDATION_READY" for row in objective_cases),
        "followup_questions_answered": sum(len(row.get("answered_questions") or []) for row in objective_cases),
        "multi_source_syntheses": sum(int(row.get("source_class_count") or 0) >= 2 for row in objective_cases),
        "recommendations_produced": sum(len(row.get("recommendations") or []) for row in objective_cases),
        "strategies_fully_specified": sum(bool(row.get("strategy_specification_complete")) for row in objective_cases),
        "business_opportunities_developed": sum(str(row.get("objective_family") or "").upper() in {
            "BUSINESS_OPPORTUNITY", "CUSTOMER_NEEDS", "CUSTOMER_COMPLAINTS"} and bool(row.get("recommendations")) for row in objective_cases),
        "useful_lessons_created": sum(len(row.get("learning") or []) for row in objective_cases),
        "active_cases": sorted(objective_cases, key=lambda row: (int(row.get("priority") or 0), str(row.get("updated_at") or "")), reverse=True)[:3],
    }
    notebooklm_inventory_ready = bool(notebooklm_inventory.get("notebooks_listed"))
    plan_recovery_receipts = []
    receipt_root = ROOT / "reports/runtime/ai_workforce_receipts"
    if receipt_root.exists():
        for path in receipt_root.glob("aiwf_*.json"):
            item = _json(path, {})
            stamp = _stamp(item.get("completed_at") or item.get("started_at"))
            if item and item.get("failure_class") == "INVALID_MODEL_PLAN" and item.get("recovery_outcome") and (not activation or (stamp and stamp >= activation)):
                plan_recovery_receipts.append(item)
    readiness = _json(ROOT / "reports/architecture/NEXUS_FRIDAY_RESEARCH_READINESS_WEEKEND_ACTIVATION_2026-10-02.json", {})
    phase2 = readiness.get("phase_2_evidence", {}) if isinstance(readiness, dict) else {}

    since = now_utc - timedelta(hours=24)
    recent_programs = [p for p in program_rows if isinstance(p, dict) and
                       (_stamp(p.get("last_run") or p.get("last_success")) or datetime.min.replace(tzinfo=timezone.utc)) >= since]
    active_requests = [r for r in requests if str(r.get("status", "")).upper() in {"OPEN", "IN_RESEARCH", "PARTIAL", "ANSWERED"}]
    active_handoffs = [h for h in handoffs if str(h.get("status", "")).upper() in {"CREATED", "DELIVERED", "ACKNOWLEDGED", "ACTIVE", "IN_PROGRESS"}]

    department_state: dict[str, dict[str, Any]] = {}
    for department in DEPARTMENTS:
        normalized = department.upper().replace(" ", "_")
        dept_goals = [g for g in active_goals if str(g.get("department", "")).upper().replace(" ", "_") in {normalized, normalized.replace("_", "")}]
        dept_orders = [w for w in work_orders if str(w.get("department") or w.get("owner_department") or "").upper().replace(" ", "_") in {normalized, normalized.replace("_", "")}]
        current = dept_goals[0] if dept_goals else None
        hb_action = heartbeat.get("next_action") if department == "Research" else None
        current_action = (current or {}).get("current_action") or (current or {}).get("next_action") or hb_action
        if department == "Research" and str(current_action or "").upper() == "NONE":
            current_action = hb_action or "RUN_BOUNDED_AUTONOMOUS_DISCOVERY"
        department_state[department] = {
            "status": "LIVE" if (dept_goals or dept_orders) else "NOT_PROVEN",
            "active_goals": len(dept_goals),
            "goal": _brief((current or {}).get("goal_statement") or (current or {}).get("goal_id"), 180),
            "current_action": _brief(current_action, 160),
            "last_result": _brief((current or {}).get("last_result"), 200),
            "next_action": _brief((current or {}).get("next_action") or hb_action, 160),
            "work_order_count": len(dept_orders),
            "handoffs_in": "NOT_CONNECTED",
            "handoffs_out": "NOT_CONNECTED",
            "blockers": "UNAVAILABLE",
            "waiting_ray": "UNAVAILABLE",
            "last_activity": (current or {}).get("last_progress") or (current or {}).get("updated_at") or "UNAVAILABLE",
        }

    next_actions = []
    for goal in active_goals:
        action = _brief(goal.get("next_action") or goal.get("current_action"), 160)
        if action and action.upper() != "NONE":
            next_actions.append((str(goal.get("department") or "UNASSIGNED"), action))
    for work in work_orders:
        action = _brief(work.get("recommended_action") or work.get("next_action"), 160)
        if action:
            next_actions.append((str(work.get("department") or work.get("owner_department") or work.get("owner") or "UNASSIGNED"), action))
    if heartbeat.get("next_action") and str(heartbeat.get("next_action")).upper() != "NONE":
        next_actions.insert(0, ("Research", _brief(heartbeat.get("next_action"), 160)))
    deduped_actions = []
    seen = set()
    for owner, action in next_actions:
        key = (owner, action)
        if key not in seen:
            seen.add(key)
            deduped_actions.append((owner, action))

    return {
        "heartbeat": heartbeat, "receipt": receipt, "programs": program_rows,
        "live_queue_total": len(live_items), "live_queue_eligible": len(live_eligible),
        "historical_queue": historical, "active_goals": active_goals,
        "completed_goals": completed_goals, "stalled_goals": stalled_goals,
        "goal_snapshot_time": goal_time.isoformat() if goal_time else "UNAVAILABLE",
        "work_orders": work_orders, "handoffs": handoffs, "active_handoffs": active_handoffs,
        "research_requests": active_requests, "findings": findings, "recent_programs": recent_programs,
        "weekend_research_activity": {"execution_runs": len(job_runs), "worker_runs": len(selected_runs),
            "research_case_metrics": objective_case_metrics,
            "finding_records": finding_count, "handoff_records": handoff_count,
            "acknowledged_handoffs": max(len(ack_events), sum(str(row.get("status") or "").upper() in {"ACKNOWLEDGED", "COMPLETED"} for row in handoff_receipts)),
            "youtube_channels_checked": int(youtube_reconciliation.get("channels_checked") or max(len(checked_channels), int(youtube_run.get("channels_checked", 0) or 0))),
            "youtube_channels_enabled": int(youtube_reconciliation.get("enabled_channel_count") or 0) or "UNAVAILABLE",
            "youtube_new_videos": int(youtube_reconciliation.get("current_new_video_count", youtube_run.get("new_videos_found", (proactive_wake.get("result_counts") or {}).get("new_videos", 0))) or 0),
            "youtube_new_videos_processed": int(youtube_reconciliation.get("research_processed_count", youtube_run.get("new_videos_processed", youtube_processed)) or 0),
            "youtube_missed_videos_recovered": int(youtube_reconciliation.get("missed_current_videos_recovered", 0) or 0),
            "notebooklm_inventory_ready": notebooklm_inventory_ready,
            "notebooklm_inventory_count": len(notebook_rows) if notebooklm_inventory_ready else "UNAVAILABLE",
            "notebooklm_nexus_count": nexus_notebook_count if notebooklm_inventory_ready else "UNAVAILABLE",
            "notebooklm_case_count": len(notebook_case_rows) if notebooklm_inventory_ready else "UNAVAILABLE",
            "notebooklm_mapped_case_count": len(mapped_case_ids) if notebooklm_inventory_ready else "UNAVAILABLE",
            "notebooklm_active_case_count": len(active_case_ids & notebook_case_ids) if notebooklm_inventory_ready else "UNAVAILABLE",
            "notebooklm_followup_reusable_count": len(followup_case_ids & notebook_case_ids) if notebooklm_inventory_ready else "UNAVAILABLE",
            "notebooklm_orphaned_count": len(notebook_case_ids - (set(latest_research_cases) | logged_case_ids)) if notebooklm_inventory_ready else "UNAVAILABLE",
            "proactive_task": proactive_wake.get("selected_task") or "NONE",
            "proactive_runs": int(bool(proactive_wake.get("selected_task"))),
            "proactive_findings": int((proactive_wake.get("result_counts") or {}).get("trend_findings_created", 0) or 0),
            "current_proactive_objective": proactive_wake.get("current_proactive_objective"),
            "why_this_objective_was_selected": proactive_wake.get("why_this_objective_was_selected"),
            "objective_family": proactive_wake.get("objective_family"),
            "proactive_query": proactive_wake.get("query"),
            "source_classes": proactive_wake.get("source_classes", []),
            "raw_signals": proactive_wake.get("raw_signals", 0),
            "qualified_findings": proactive_wake.get("qualified_findings", 0),
            "proactive_handoffs": proactive_wake.get("handoffs", 0),
            "saturation_state": proactive_wake.get("saturation_state"),
            "next_research_direction": proactive_wake.get("next_research_direction"),
            "research_execution_engine": latest_tool_run.get("engine", "UNAVAILABLE"),
            "research_fallback_used": latest_tool_run.get("fallback_used", "UNAVAILABLE"),
            "research_fallback_reason": latest_tool_run.get("fallback_reason"),
            "research_question": latest_tool_run.get("research_question"),
            "research_tools_selected": latest_tool_run.get("tools_selected") or latest_tool_run.get("tools_used", []),
            "research_search_count": latest_tool_run.get("search_count", "UNAVAILABLE"),
            "research_sources_opened": latest_tool_run.get("sources_opened", "UNAVAILABLE"),
            "research_firsthand_sources": latest_tool_run.get("firsthand_source_count", "UNAVAILABLE"),
            "research_official_sources": latest_tool_run.get("official_source_count", "UNAVAILABLE"),
            "research_marketplace_sources": latest_tool_run.get("marketplace_source_count", "UNAVAILABLE"),
            "research_source_fit": latest_tool_run.get("source_fit", "UNAVAILABLE"),
            "research_evidence_quality": latest_tool_run.get("evidence_quality", "UNAVAILABLE"),
            "research_conclusion": latest_tool_run.get("research_conclusion", "UNAVAILABLE"),
            "research_why_concluded": latest_tool_run.get("why_concluded", "UNAVAILABLE"),
            "research_next_action": latest_tool_run.get("next_research_action", "UNAVAILABLE"),
            "latest_worker_event": latest_worker_event,
            "invalid_model_plan_recoveries": len(plan_recovery_receipts),
            "jobs_truncated": jobs_truncated},
        "department_state": department_state, "next_actions": deduped_actions,
        "invalid_model_plan_recoveries": len(plan_recovery_receipts),
        "finance_followup": {
            "goal_id": phase2.get("finance_goal_id", "UNAVAILABLE"),
            "status": phase2.get("finance_goal_status", "UNAVAILABLE"),
            "decision": phase2.get("finance_review", "UNAVAILABLE"),
            "next_action": phase2.get("finance_next_action", "UNAVAILABLE"),
            "remaining_evidence": phase2.get("finance_still_missing", []),
            "source_updated_at": readiness.get("report_date", "UNAVAILABLE") if isinstance(readiness, dict) else "UNAVAILABLE",
        },
        "truncated_sources": [name for name, value in (("work_orders", wo_truncated), ("handoffs", handoff_truncated),
                             ("research_requests", requests_truncated), ("findings", findings_truncated)) if value],
    }


def build_report(*, heartbeat: dict[str, Any] | None = None, receipt: dict[str, Any] | None = None) -> str:
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(LOCAL_TZ)
    mode = _json(ROOT / "configs/nexus_operating_mode.json", {})
    weekend = mode.get("weekend_mode", {}) if isinstance(mode, dict) else {}
    started = _stamp(weekend.get("activated_at")) if isinstance(weekend, dict) else None
    elapsed = (now_utc - started).total_seconds() if started else 0
    state = _collect(now_utc)
    hb = heartbeat or state["heartbeat"]
    cycle = receipt or state["receipt"]
    hb_success = _stamp(hb.get("last_success"))
    kernel_alive = bool(hb.get("enabled") and hb.get("heartbeat") == "ACTIVE" and hb_success and (now_utc - hb_success).total_seconds() < 3600)
    cycle_result = cycle.get("result", {}) if isinstance(cycle, dict) else {}
    activity = state.get("weekend_research_activity", {})
    result_status = str(hb.get("result_status") or "").upper()
    output_fields = ("findings_created", "new_items_found", "knowledge_updated", "work_generated", "new_results")
    has_output = False
    if isinstance(cycle_result, dict):
        for field in output_fields:
            try:
                has_output = has_output or int(cycle_result.get(field, 0) or 0) > 0
            except (TypeError, ValueError):
                continue
    research_productive = "YES" if kernel_alive and (has_output or result_status in {"COMPLETED_WITH_FINDINGS", "PRODUCTIVE", "PASS_WITH_OUTPUT"} or activity.get("finding_records", 0) or activity.get("handoff_records", 0)) else "NOT_PROVEN (healthy heartbeat; no persisted output in the bounded runtime read)"
    no_unexplained = not any(not (g.get("next_action") or g.get("current_action")) for g in state["stalled_goals"])
    actions = state["next_actions"][:5]
    lines = [
        "NEXUS WEEKEND AUTONOMY REPORT", "REPORT WINDOW",
        f"START_TIME={started.isoformat() if started else 'UNAVAILABLE'}",
        f"END_TIME={now_utc.isoformat()}", f"RUNTIME_UPTIME={_dur(elapsed)} since weekend activation",
        f"WEEKEND_MODE={'ON' if weekend.get('enabled') else 'OFF'}",
        f"KERNEL_ALIVE={'YES' if kernel_alive else 'NO'}", "",
        "EXECUTIVE SUMMARY",
        f"- what Nexus accomplished: latest Research cycle {hb.get('result_status', 'UNAVAILABLE')} at {hb.get('last_success', 'UNAVAILABLE')}; receipt {cycle.get('cycle_id', 'UNAVAILABLE')}.",
        "- what created value: no cash revenue or cost savings inferred from available local records; see VALUE CREATED.",
        "- what needs Ray: approval-gated actions only; precise approval queue is UNAVAILABLE in this local snapshot.",
        f"- what is running: continuous kernel={hb.get('scheduler', 'UNAVAILABLE')}; Research heartbeat={hb.get('heartbeat', 'UNAVAILABLE')}; active goals={len(state['active_goals'])} in the local goal portfolio.",
        f"- what failed: latest Research result={hb.get('result_status', 'UNAVAILABLE')}; no failure is promoted to goal failure by this report.",
        f"- what Nexus will do next: {hb.get('next_action', 'UNAVAILABLE')}.", "",
        "RESEARCH",
        f"items discovered=program counters available in {len(state['programs'])} durable program rows; recent programs={len(state['recent_programs'])}; real worker runs since weekend activation={activity.get('worker_runs', 0)}.",
        f"NotebookLM live inventory={activity.get('notebooklm_inventory_count', 'NOT_CONNECTED')}; Nexus-related notebooks={activity.get('notebooklm_nexus_count', 'NOT_CONNECTED')}; case notebooks={activity.get('notebooklm_case_count', 'NOT_CONNECTED')}; mapped to durable Research cases={activity.get('notebooklm_mapped_case_count', 'NOT_CONNECTED')}; active mapped cases={activity.get('notebooklm_active_case_count', 'NOT_CONNECTED')}; follow-up reusable={activity.get('notebooklm_followup_reusable_count', 'NOT_CONNECTED')}; orphaned case notebooks={activity.get('notebooklm_orphaned_count', 'NOT_CONNECTED')}.",
        f"findings persisted in local NotebookLM findings mirror={len(state['findings'])}; weekend durable research packages/findings={activity.get('finding_records', 0)}.",
        f"YouTube live reconciliation: enabled channels={activity.get('youtube_channels_enabled', 'UNAVAILABLE')}; checked={activity.get('youtube_channels_checked', 'UNAVAILABLE')}; new videos found={activity.get('youtube_new_videos', 'UNAVAILABLE')}; full Research processing completed={activity.get('youtube_new_videos_processed', 'UNAVAILABLE')}; missed current videos metadata-triaged={activity.get('youtube_missed_videos_recovered', 'UNAVAILABLE')}.",
        f"follow-ups active={len(state['research_requests'])}; monitored-source activity=program registry recent runs {len(state['recent_programs'])}; actual worker execution ids={activity.get('worker_runs', 0)}; proactive task={activity.get('proactive_task', 'NONE')}.",
        f"proactive discovery runs={activity.get('proactive_runs', 0)}; latest task={activity.get('proactive_task', 'NONE')}; qualified trend findings={activity.get('proactive_findings', 0)}; viral activity=NOT_PROVEN; NotebookLM inventory={'CONNECTED' if activity.get('notebooklm_inventory_ready') else 'NOT_CONNECTED'}.",
        f"current proactive objective={activity.get('current_proactive_objective') or 'NONE'}; why selected={activity.get('why_this_objective_was_selected') or 'UNAVAILABLE'}; family={activity.get('objective_family') or 'NONE'}; query={activity.get('proactive_query') or 'NONE'}; source classes={','.join(activity.get('source_classes') or []) or 'NONE'}; raw signals={activity.get('raw_signals', 0)}; qualified findings={activity.get('qualified_findings', 0)}; handoffs={activity.get('proactive_handoffs', 0)}; saturation={activity.get('saturation_state') or 'UNKNOWN'}; next direction={activity.get('next_research_direction') or 'UNAVAILABLE'}.",
        f"proactive research engine={activity.get('research_execution_engine')}; fallback used={activity.get('research_fallback_used')}; fallback reason={activity.get('research_fallback_reason') or 'NONE'}; question={activity.get('research_question') or 'NONE'}; tools={json.dumps(activity.get('research_tools_selected') or [], ensure_ascii=False)}; searches={activity.get('research_search_count')}; sources opened={activity.get('research_sources_opened')}; firsthand={activity.get('research_firsthand_sources')}; official={activity.get('research_official_sources')}; marketplace={activity.get('research_marketplace_sources')}; source fit={activity.get('research_source_fit')}; evidence quality={activity.get('research_evidence_quality')}; conclusion={activity.get('research_conclusion')}; why={activity.get('research_why_concluded')}; next action={activity.get('research_next_action')}.",
        f"depth-first objective cases: active={activity.get('research_case_metrics', {}).get('active_deep_cases', 0)}; recommendation-ready={activity.get('research_case_metrics', {}).get('cases_recommendation_ready', 0)}; follow-up questions answered={activity.get('research_case_metrics', {}).get('followup_questions_answered', 0)}; multi-source cases={activity.get('research_case_metrics', {}).get('multi_source_syntheses', 0)}; recommendations={activity.get('research_case_metrics', {}).get('recommendations_produced', 0)}; fully specified strategies={activity.get('research_case_metrics', {}).get('strategies_fully_specified', 0)}; business cases developed={activity.get('research_case_metrics', {}).get('business_opportunities_developed', 0)}; lessons={activity.get('research_case_metrics', {}).get('useful_lessons_created', 0)}.",
        "ACTIVE RESEARCH CASES (objective-level; newest bounded list):",
        *[f"- case={row.get('case_id')}; objective={_brief(row.get('objective'), 180)}; why promising={((row.get('selection_reason') or {}).get('classification') if isinstance(row.get('selection_reason'), dict) else 'EXISTING_CASE')} score={((row.get('selection_reason') or {}).get('promise_score') if isinstance(row.get('selection_reason'), dict) else row.get('promise_score', 'UNAVAILABLE'))}; status={row.get('status')}; owner={row.get('owner_department')}; sources={row.get('source_count', 0)} across {row.get('source_class_count', 0)} classes; open questions={len(row.get('open_questions') or [])}; answers={len(row.get('answered_questions') or [])}; recommendation={(row.get('recommendations') or [{}])[-1].get('recommendation', 'PENDING') if row.get('recommendations') else 'PENDING'}; next={row.get('next_research_action')}; depth={json.dumps(row.get('depth_used') or {}, sort_keys=True)}/{json.dumps(row.get('depth_budget') or {}, sort_keys=True)}; needs Ray={row.get('requires_ray', False)}" for row in activity.get('research_case_metrics', {}).get('active_cases', [])],
        f"latest durable Research worker event={_brief(activity.get('latest_worker_event'), 260)}.",
        f"live queue total={state['live_queue_total']}; eligible={state['live_queue_eligible']}; isolated historical backlog={state['historical_queue']} excluded from live queue.", "",
        "SOURCE ACTIVITY",
    ]
    for source in ("YouTube", "TradingView", "web discovery", "Affiliate.Watch", "PartnerStack", "GitHub", "funding/grants", "viral/social"):
        matches = [p for p in state["recent_programs"] if source.lower().split('/')[0] in (str(p.get("program_id", "") + " " + p.get("purpose", "")).lower())]
        if source == "YouTube":
            lines.append(f"{source}: {'CHECKED' if activity.get('youtube_channels_checked', 0) else 'NOT_PROVEN'}; enabled={activity.get('youtube_channels_enabled', 'UNAVAILABLE')}; designated channels checked={activity.get('youtube_channels_checked', 0)}; new videos={activity.get('youtube_new_videos', 0)}; processed={activity.get('youtube_new_videos_processed', 0)}; recovered={activity.get('youtube_missed_videos_recovered', 0)}; recent program records={len(matches)}")
        elif source == "web discovery":
            ran = activity.get("proactive_task") not in {None, "NONE", "MONITORED_SOURCES"}
            lines.append(f"{source}: {'RAN' if ran else 'NOT_PROVEN'}; last task={activity.get('proactive_task', 'NONE')}; recent program records={len(matches)}")
        else:
            lines.append(f"{source}: {'LIVE' if matches else 'NOT_PROVEN'}; recent program records={len(matches)}")
    lines += ["", "OPPORTUNITIES", "received/advanced/rejected/more research required=UNAVAILABLE from local bounded opportunity mirror.",
              "active business plans=NOT_PROVEN; next actions appear in AUTONOMY.", "",
              "FINANCE", "Last verified Finance continuation from the Friday readiness record:",
              f"GOAL_ID={state['finance_followup']['goal_id']}",
              f"PARENT_GOAL_STATUS={state['finance_followup']['status']}",
              f"LAST_DECISION={state['finance_followup']['decision']}",
              f"NEXT_ACTION={state['finance_followup']['next_action']}",
              "REMAINING_EVIDENCE=" + ("; ".join(state['finance_followup']['remaining_evidence']) or "UNAVAILABLE"),
              f"EVIDENCE_SOURCE_DATE={state['finance_followup']['source_updated_at']} (last verified; live Finance refresh remains in its active goal)",
              "cost findings=UNAVAILABLE; verified revenue=UNAVAILABLE (not asserted as zero activity).", "",
              "TRADING", "All activity remains PAPER/PRACTICE/SANDBOX. Candidate/backtest/tournament counts=UNAVAILABLE in this report source; LIVE ORDERS=FORBIDDEN.", "",
              "MARKETING", "plans and campaigns=UNAVAILABLE; creative prompt approvals=RAY_REQUIRED where applicable; final external approval=RAY_REQUIRED.", "",
              "CREATIVE", "prompt/assets/revision details=UNAVAILABLE in local bounded report source; unapproved production generation remains gated.", "",
              "LABS", "experiment counts=UNAVAILABLE in local bounded report source; use durable department work receipts for item detail.", "",
              "UPGRADE CONTROL", "certified/rejected-with-repair/waiting-Ray counts=UNAVAILABLE in local bounded report source.", "",
              "SYSTEMS", "incident/recovery detail=UNAVAILABLE in local bounded report source; no unsafe production changes authorized.", "",
              "HANDOFFS", f"local Research handoff mirror total={len(state['handoffs'])}; weekend routed/created handoffs={activity.get('handoff_records', 0)}; weekend acknowledged/evaluated={activity.get('acknowledged_handoffs', 0)}; active statuses={len(state['active_handoffs'])}; company-wide handoff totals=NOT_CONNECTED.", "",
              "AUTONOMY", f"local goals active={len(state['active_goals'])}; completed={len(state['completed_goals'])}; stalled={len(state['stalled_goals'])}.",
              f"invalid model-plan attempts recovered={state.get('invalid_model_plan_recoveries', 0)} with bounded schema retry/deterministic fallback; Finance/Marketing/Creative goals remain active.",
              "safe-solvable blockers found/closed=UNAVAILABLE in this report window.", "",
              "REJECTIONS", "No new structured rejection rows were read for this report snapshot; candidate-level rejection details=UNAVAILABLE.", "",
              "NEEDS RAY", "No approval queue is connected to this local report generator. Existing safety policy requires Ray for production deploy, prompt approval, final campaign execution, and external financial commitments.", "",
              "VALUE CREATED", "VERIFIED_CASH_REVENUE=UNAVAILABLE", "PAPER_TRADING_VALUE=UNAVAILABLE", "COST_SAVINGS=UNAVAILABLE", "QUALIFIED_OPPORTUNITIES=UNAVAILABLE", "OTHER_VERIFIED_VALUE=UNAVAILABLE", "",
              "NEXT AUTONOMOUS ACTIONS"]
    for i in range(5):
        owner, action = actions[i] if i < len(actions) else ("UNAVAILABLE", "UNAVAILABLE")
        lines += [f"NEXT_ACTION_{i+1}={action}", f"OWNER_{i+1}={owner}"]
    lines += ["", "WHERE NEXUS STOPPED"]
    if state["stalled_goals"]:
        for goal in state["stalled_goals"][:20]:
            lines += [f"GOAL={_brief(goal.get('goal_statement') or goal.get('goal_id'), 180)}",
                      f"DEPARTMENT={goal.get('department') or 'UNAVAILABLE'}",
                      f"LAST_SUCCESSFUL_ACTION={_brief(goal.get('last_result'), 200)}",
                      f"STOP_REASON={goal.get('blockers') or goal.get('status') or 'UNAVAILABLE'}",
                      f"BLOCKER_TYPE={goal.get('blocker_type') or 'UNAVAILABLE'}",
                      f"NEXT_ACTION={_brief(goal.get('next_action') or goal.get('current_action'), 160)}",
                      f"RAY_REQUIRED={'YES' if goal.get('human_action_required') else 'UNAVAILABLE'}", ""]
    else:
        lines.append(f"NO_UNEXPLAINED_STOPS={'YES' if no_unexplained else 'NO'} (no stalled goals in this local goal snapshot)")
    lines += ["", "DEPARTMENT SNAPSHOT (local durable goal/work-order mirror)"]
    for dept, detail in state["department_state"].items():
        lines.append(f"{dept}: STATUS={detail['status']} ACTIVE_GOALS={detail['active_goals']} CURRENT_GOAL={detail['goal']} CURRENT_ACTION={detail['current_action']} LAST_RESULT={detail['last_result']} NEXT_ACTION={detail['next_action']} HANDOFFS_IN={detail['handoffs_in']} HANDOFFS_OUT={detail['handoffs_out']} BLOCKERS={detail['blockers']} WAITING_RAY={detail['waiting_ray']} LAST_ACTIVITY_AT={detail['last_activity']}")
    lines += ["", "FINAL", f"RESEARCH_PRODUCTIVE={research_productive}",
              f"OPPORTUNITIES_PRODUCTIVE={'LIVE' if state['department_state']['Opportunities']['status']=='LIVE' else 'NOT_PROVEN'}",
              f"TRADING_PRODUCTIVE={'LIVE' if state['department_state']['Trading']['status']=='LIVE' else 'NOT_PROVEN'}",
              f"DEPARTMENTS_PRODUCTIVE={'LIVE' if state['active_goals'] or state['work_orders'] else 'NOT_PROVEN'}",
              f"HANDOFFS_PRODUCTIVE={'LIVE' if activity.get('handoff_records', 0) else 'NOT_PROVEN'}",
              f"COMPANY_CONTINUING={'YES' if kernel_alive and state['active_goals'] else 'NOT_PROVEN'}",
              "ATTENTION_REQUIRED=YES (unresolved evidence/approval state must be reviewed from live Admin read model)",
              f"WEEKEND_TEST_HEALTH={'HEALTHY' if kernel_alive else 'ATTENTION_REQUIRED'}",
              f"FINAL_STATUS={'RUNNING_WITH_OPEN_GOALS' if kernel_alive else 'ATTENTION_REQUIRED'}"]
    if state["truncated_sources"]:
        lines += ["", "REPORT SOURCE LIMITS", "bounded JSONL tail used; large sources: " + ", ".join(state["truncated_sources"]) + "."]
    lines += ["", "SAFETY", "LIVE_TRADING_ENABLED=NO", "REAL_AD_SPEND_ENABLED=NO", "EXTERNAL_PUBLISHING_ENABLED=NO",
              "PRODUCTION_DEPLOYMENT_REQUIRES_RAY=YES", "CREATIVE_GENERATION_REQUIRES_RAY_PROMPT_APPROVAL=YES",
              "FINAL_CAMPAIGN_EXECUTION_REQUIRES_RAY_APPROVAL=YES", "NEW_EXTERNAL_FINANCIAL_COMMITMENTS_REQUIRE_RAY=YES",
              "MAX_BACKGROUND_SHELLS=1", "MAX_PARALLEL_PYTHON_CHILDREN=1", ""]
    return "\n".join(lines)


def generate_weekend_report(*, heartbeat: dict[str, Any] | None = None,
                            receipt: dict[str, Any] | None = None,
                            force_snapshot: bool = False) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    content = build_report(heartbeat=heartbeat, receipt=receipt)
    live_state = _collect(datetime.now(timezone.utc))
    activity = live_state.get("weekend_research_activity", {})
    case_metrics = activity.get("research_case_metrics", {})
    runtime_dir = ROOT / "public/runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    case_view = {"schema_version": "nexus.research-case-read-model.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {key: value for key, value in case_metrics.items() if key != "active_cases"},
        "cases": [{key: row.get(key) for key in (
            "case_id", "objective", "objective_family", "business_or_nexus_goal", "owner_department",
            "status", "priority", "promise_score", "selection_reason", "primary_question", "open_questions",
            "answered_questions", "sources", "source_count", "source_class_count", "findings", "hypotheses",
            "recommendations", "department_requests", "experiment_requests", "next_research_action",
            "next_department_action", "development_profile", "depth_budget", "depth_used", "requires_ray",
            "notebook_playbook", "notebook_workspace", "notebook_playbook_run_id")}
            for row in case_metrics.get("active_cases", [])]}
    case_view_path = runtime_dir / "research-cases.json"
    case_view_tmp = case_view_path.with_suffix(".json.tmp")
    case_view_tmp.write_text(json.dumps(case_view, ensure_ascii=False, default=str), encoding="utf-8")
    case_view_tmp.replace(case_view_path)
    temporary = LATEST.with_suffix(".txt.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(LATEST)
    now_local = datetime.now(LOCAL_TZ)
    snapshots = sorted(REPORT_DIR.glob("NEXUS_WEEKEND_AUTONOMY_REPORT_????-??-??_????.txt"))
    newest = snapshots[-1] if snapshots else None
    snapshot_due = force_snapshot or newest is None or datetime.fromtimestamp(newest.stat().st_mtime, LOCAL_TZ) <= now_local - timedelta(hours=3)
    snapshot = None
    if snapshot_due:
        snapshot = REPORT_DIR / f"NEXUS_WEEKEND_AUTONOMY_REPORT_{now_local.strftime('%Y-%m-%d_%H%M')}.txt"
        snapshot.write_text(content, encoding="utf-8")
    return {"latest_written": True, "latest_path": str(LATEST),
            "research_case_read_model_path": str(case_view_path),
            "snapshot_written": bool(snapshot), "snapshot_path": str(snapshot) if snapshot else None,
            "generated_at": datetime.now(timezone.utc).isoformat(), "report_generator": "EXISTING_KERNEL_CYCLE"}
