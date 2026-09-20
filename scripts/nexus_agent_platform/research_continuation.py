"""Goal-aware Research continuation above the canonical work queue.

This module owns purpose and bounded objective generation; the existing queue
continues to own scheduling, leases, routing, and settlement.  It deliberately
creates at most a small batch and deduplicates against current objective work.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CHARTER_PATH = ROOT / "data/governed/research_charter.json"
GENERATED_PATH = ROOT / "data/governed/research_generated_objectives.jsonl"
FEEDBACK_PATH = ROOT / "data/governed/research_goal_progress.jsonl"

CHARTER_ID = "research-charter-nexus-continuous-intelligence-v1"
ACTIVE_GOAL_STATES = {"ACTIVE", "READY", "QUEUED"}
TERMINAL_GOAL_STATES = {"COMPLETE", "GOAL_COMPLETED", "PAUSED", "CANCELLED", "GOAL_INVALIDATED_BY_EVIDENCE", "GOAL_SUPERSEDED"}

DEFAULT_CHARTER = {
    "schema_version": "nexus.research-charter.v1",
    "charter_id": CHARTER_ID,
    "status": "ACTIVE",
    "department": "RESEARCH",
    "mission": "Continuously reduce uncertainty around active Nexus company goals with sourced, challengeable intelligence.",
    "responsibilities": [
        "Find real customer needs, complaints, questions, frustrations, and unmet demand.",
        "Identify where customers discuss problems, desired outcomes, current alternatives, and missing solutions.",
        "Investigate service, affiliate, referral, lead generation, education, content, SEO, YouTube, white-label, and justified product-gap routes.",
        "Support GoClear funding, lender, underwriting, business-credit, documentation, and bankability intelligence.",
        "Continue approved monitored-source research and department evidence requests.",
        "Reduce uncertainty around active Nexus company goals without claiming revenue or business success from evidence alone.",
    ],
    "priority_order": ["ALPHA_FOLLOWUP", "DEPARTMENT_REQUEST", "ASSIGNED_OBJECTIVE", "MONITORED", "CUSTOMER_DEMAND", "GENERAL_DISCOVERY"],
    "created_at": None,
    "updated_at": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return default


def ensure_charter() -> dict[str, Any]:
    prior = _read_json(CHARTER_PATH, {})
    now = _now()
    charter = {**DEFAULT_CHARTER, **(prior if isinstance(prior, dict) else {})}
    charter["created_at"] = charter.get("created_at") or now
    charter["updated_at"] = charter.get("updated_at") or now
    CHARTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CHARTER_PATH.exists():
        CHARTER_PATH.write_text(json.dumps(charter, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return charter


def read_company_goals() -> list[dict[str, Any]]:
    from nexus_agent_platform.goal_completion import ensure_company_goal_portfolio
    rows = ensure_company_goal_portfolio()
    # Materialize the bounded certification goal in the existing canonical
    # portfolio store, not in a second continuation-specific goal database.
    if not any(row.get("goal_id") == "research.continuation_revenue" for row in rows):
        from nexus_agent_platform.goal_completion import _portfolio_read, _portfolio_write
        now = _now()
        rows = _portfolio_read()
        rows.append({
            "schema_version": "nexus.company-goal-portfolio.v1", "goal_id": "research.continuation_revenue",
            "program_id": "research", "statement": "Reduce uncertainty around a bounded path to $1,000/month in legitimate recurring or repeatable revenue; planning only, not revenue earned.",
            "domain": "Research", "owner": "NEXUS", "department": "Research", "priority": "P2", "status": "ACTIVE",
            "authority": "INTERNAL_SAFE", "success_criteria": ["current customer demand is evidenced", "at least one viable value path is investigated", "remaining uncertainty and next evidence are explicit"],
            "dependencies": [], "active_workstreams": [], "current_evidence": [], "missing_criteria": ["current customer demand is evidenced", "at least one viable value path is investigated", "remaining uncertainty and next evidence are explicit"],
            "created_at": now, "updated_at": now,
        })
        _portfolio_write(rows)
    goals = []
    for row in rows:
        status = str(row.get("status") or "").upper()
        if status in TERMINAL_GOAL_STATES or status not in ACTIVE_GOAL_STATES:
            continue
        goals.append({
            "goal_id": row.get("goal_id"),
            "title": row.get("title") or row.get("goal_id"),
            "description": row.get("statement") or row.get("domain"),
            "status": status,
            "priority": row.get("priority", "P3"),
            "success_condition": row.get("success_criteria", []),
            "time_horizon": row.get("time_horizon"),
            "owner": row.get("owner", "NEXUS"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "current_evidence": row.get("current_evidence", []),
            "missing_criteria": row.get("missing_criteria", []),
        })
    return goals


def _rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except ValueError:
                continue
    except OSError:
        pass
    return rows


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def dedup_key(goal_id: str, question: str, unknown: str) -> str:
    raw = "|".join((_norm(goal_id), _norm(question), _norm(unknown)))
    return "goalq_" + hashlib.sha256(raw.encode()).hexdigest()[:20]


def _source_candidates(capabilities: list[str], objective_id: str) -> list[dict[str, Any]]:
    """Attach only approved public candidates needed by the existing worker."""
    candidates = []
    caps = set(capabilities)
    if "SEO" in caps:
        candidates.append({"source_type": "SEO_RESEARCH", "source_id": "google-seo-starter", "source_url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "title": "Google SEO Starter Guide"})
    if "WEB_ACQUISITION" in caps or not candidates:
        candidates.append({"source_type": "WEB_PAGE", "source_id": f"goal-source-{objective_id}", "source_url": "https://www.sba.gov/business-guide", "title": "SBA business guide"})
    # Last30Days is an adapter-led path and intentionally receives no fake
    # source URL; the adapter acquires its own current public sources.
    return [] if "LAST30DAYS_DEMAND" in caps and len(caps) == 1 else candidates


def _queue_rows(queue) -> list[dict[str, Any]]:
    return queue.load().get("items", [])


def evaluate_goal_result(*, goal_id: str, objective_id: str, result: dict[str, Any], alpha: dict[str, Any] | None = None) -> dict[str, Any]:
    interpretation = result.get("ai_interpretation") or {}
    gain = interpretation.get("information_gain")
    remaining = interpretation.get("remaining_gaps") or "Additional evidence is required before the goal can be evaluated as complete."
    alpha_decision = str((alpha or {}).get("decision") or (alpha or {}).get("status") or "PENDING").upper()
    reduced = "YES" if gain and alpha_decision not in {"REJECT", "FAILED_REAL"} else "PARTIAL"
    feedback = {
        "schema_version": "nexus.research-goal-progress.v1", "feedback_id": "goal_feedback_" + hashlib.sha256(f"{goal_id}|{objective_id}|{_now()}".encode()).hexdigest()[:20],
        "goal_id": goal_id, "objective_id": objective_id, "created_at": _now(),
        "uncertainty_reduced": reduced, "information_gain": gain,
        "alpha_decision": alpha_decision, "next_knowledge_gap": remaining,
        "next_action": interpretation.get("recommended_followup") or "Compare the result with the company goal and select the next bounded question.",
        "goal_claimed_complete": False,
    }
    _append(FEEDBACK_PATH, feedback)
    generated = next((row for row in reversed(_rows(GENERATED_PATH)) if row.get("objective_id") == objective_id), None)
    if generated:
        _append(GENERATED_PATH, {**generated, "status": "FOLLOWUP_REQUIRED" if alpha_decision == "RESEARCH_MORE" else "COMPLETE", "completed_at": feedback["created_at"], "goal_feedback_id": feedback["feedback_id"]})
    try:
        from nexus_agent_platform.goal_completion import _portfolio_read, _portfolio_write
        rows = _portfolio_read()
        for row in rows:
            if row.get("goal_id") != goal_id:
                continue
            evidence = list(row.get("current_evidence") or [])
            evidence.append({"objective_id": objective_id, "information_gain": gain, "recorded_at": feedback["created_at"]})
            workstreams = list(row.get("active_workstreams") or [])
            if objective_id not in workstreams:
                workstreams.append(objective_id)
            row.update({"current_evidence": evidence[-20:], "active_workstreams": workstreams[-20:], "last_progress": reduced, "updated_at": feedback["created_at"]})
        _portfolio_write(rows)
    except Exception:
        feedback["portfolio_update"] = "DEGRADED"
    return feedback


def _existing_keys(queue) -> set[str]:
    keys = set()
    for row in _queue_rows(queue):
        key = str(row.get("dedup_key") or "").strip()
        if key and row.get("status") not in {"SUPERSEDED", "PARKED", "COMPLETE", "BLOCKED_EXTERNAL", "FAILED_FINAL"}:
            keys.add(key)
    for row in _rows(GENERATED_PATH):
        key = str(row.get("dedup_key") or "").strip()
        if key and row.get("status") not in {"SUPERSEDED", "COMPLETE", "BLOCKED_EXTERNAL", "FAILED_FINAL"}:
            keys.add(key)
    return keys


def _model_plan(goal: dict[str, Any], charter: dict[str, Any], context: dict[str, Any], count: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from nexus_agent_platform.research_ai_orchestrator import _call, _normalize_capability, certified_capabilities
    context = {**context, "certified_capabilities": certified_capabilities()}
    prompt = {
        "company_goal": goal,
        "research_charter": charter,
        "current_research_context": context,
        "requested_count": count,
        "required_json_schema": {"objectives": [{"question": "", "why_it_matters": "", "unknown_to_resolve": "", "required_evidence": [], "likely_capabilities": [], "priority": 20, "stop_condition": "", "dedup_key": ""}]},
    }
    result, meta = _call(prompt, "You are the Nexus Research purpose planner. Generate only bounded, evidence-seeking objectives that reduce uncertainty around the supplied active company goal. Do not claim the goal is achieved. Do not repeat current or completed questions. Return JSON only.")
    if not result:
        return [], {**meta, "planner_mode": "model_unavailable"}
    candidates = result.get("objectives") if isinstance(result.get("objectives"), list) else []
    normalized = []
    for candidate in candidates[:count]:
        if not isinstance(candidate, dict) or not candidate.get("question"):
            continue
        raw_caps = " ".join(str(value) for value in candidate.get("likely_capabilities", []))
        caps = [_normalize_capability(value) for value in candidate.get("likely_capabilities", []) if value]
        valid = {cap for row in certified_capabilities() for cap in row.get("capabilities", [])}
        # Alpha is a downstream evaluator, not a queue executor for a newly
        # generated Research objective.  Keep generated work on capabilities
        # that the Research dispatcher can actually invoke.
        valid.discard("ALPHA_REVIEW")
        caps = [cap for cap in caps if cap in valid]
        if not caps:
            lowered = raw_caps.lower() + " " + str(candidate.get("question", "")).lower()
            if any(term in lowered for term in ("demand", "customer", "pain", "need", "complaint")) and "LAST30DAYS_DEMAND" in valid:
                caps = ["LAST30DAYS_DEMAND"]
            else:
                caps = ["WEB_ACQUISITION"] if "WEB_ACQUISITION" in valid else sorted(valid)[:1]
        normalized.append({**candidate, "likely_capabilities": caps or ["WEB_ACQUISITION"]})
    return normalized, {**meta, "planner_mode": "model"}


def _fallback_plan(goal: dict[str, Any], context: dict[str, Any], count: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # A bounded safety fallback is purpose-derived, not a generic "find
    # something useful" prompt.  It is used only when the real planner cannot
    # be called and remains auditable as deterministic fallback evidence.
    description = str(goal.get("description") or "the active company goal")
    templates = [
        (f"What current customer problem most directly limits progress on {description}?", "customer demand evidence", ["LAST30DAYS_DEMAND", "WEB_ACQUISITION"]),
        (f"What public evidence would validate or challenge the strongest unresolved assumption in {description}?", "independent validation", ["WEB_ACQUISITION"]),
        (f"Which evidence-backed next step could reduce uncertainty around {description} without external spend or publication?", "safe next step", ["WEB_ACQUISITION"]),
    ]
    return ([{"question": q, "why_it_matters": why, "unknown_to_resolve": why, "required_evidence": ["current public evidence", "source provenance", "limitations"], "likely_capabilities": caps, "priority": 20, "stop_condition": "Stop after one bounded evidence package and explicit uncertainty assessment."} for q, why, caps in templates[:count]], {"planner_mode": "deterministic_fallback", "model_calls": 0, "model": None})


def generate_objectives(*, queue, goal: dict[str, Any] | None = None, count: int = 3, enqueue: bool = True) -> dict[str, Any]:
    charter = ensure_charter()
    goals = read_company_goals()
    goal = goal or (sorted(goals, key=lambda row: (str(row.get("priority", "P9")), str(row.get("goal_id"))))[0] if goals else None)
    if not goal:
        goal = {"goal_id": "research-charter-standing-mission", "title": "Standing Research Mission", "description": charter["mission"], "priority": "P3", "status": "CHARTER_ACTIVE"}
    rows = _queue_rows(queue)
    context = {
        "active_objectives": sorted({str(row.get("objective_id")) for row in rows if row.get("objective_id") and row.get("status") not in {"COMPLETE", "PARKED", "SUPERSEDED", "BLOCKED_EXTERNAL"}})[:40],
        "known_questions": [row.get("question") for row in rows if row.get("question")][:20],
        "known_evidence_gaps": [row.get("unknown_to_resolve") for row in rows if row.get("unknown_to_resolve")][:20],
        "completed_findings": [
            (row.get("last_result") or {}).get("ai_interpretation", {}).get("information_gain")
            for row in rows if row.get("status") == "COMPLETE" and isinstance(row.get("last_result"), dict)
        ][:10],
    }
    candidates, planner_meta = _model_plan(goal, charter, context, count)
    if not candidates:
        candidates, fallback_meta = _fallback_plan(goal, context, count)
        planner_meta = {**planner_meta, **fallback_meta}
    existing = _existing_keys(queue)
    generated = []
    skipped = []
    for candidate in candidates:
        question = str(candidate.get("question")).strip()
        unknown = str(candidate.get("unknown_to_resolve") or candidate.get("why_it_matters") or "").strip()
        key = dedup_key(str(goal["goal_id"]), question, unknown)
        if key in existing:
            skipped.append({"dedup_key": key, "question": question, "reason": "active_or_recent_duplicate"})
            continue
        objective_id = "goal-research-" + hashlib.sha256(key.encode()).hexdigest()[:20]
        record = {
            "schema_version": "nexus.research-generated-objective.v1",
            "objective_id": objective_id, "parent_goal_id": goal["goal_id"],
            "question": question, "why_it_matters": candidate.get("why_it_matters"),
            "unknown_to_resolve": unknown, "required_evidence": candidate.get("required_evidence", []),
            "likely_capabilities": candidate.get("likely_capabilities", ["WEB_ACQUISITION"]),
            "priority": int(candidate.get("priority", 20) or 20), "stop_condition": candidate.get("stop_condition"),
            "dedup_key": key, "planner_mode": planner_meta.get("planner_mode"),
            "planner_model": planner_meta.get("model"), "created_at": _now(), "status": "GENERATED",
        }
        source_candidates = _source_candidates(record["likely_capabilities"], objective_id)
        record["source_candidates"] = source_candidates
        generated.append(record)
        existing.add(key)
        if enqueue:
            from nexus_agent_platform.research_work_queue import default_queue
            queue.enqueue(
                work_id=f"goal-objective:{objective_id}", work_class="ASSIGNED", source_type="RESEARCH_OBJECTIVE",
                source_id=objective_id, title=question, question=question, objective_id=objective_id,
                parent_goal_id=goal["goal_id"], requested_by="research_continuation", priority=record["priority"],
                status="QUEUED", selection_reason="goal_generated", required_capabilities=record["likely_capabilities"],
                required_work=True, work_role="REQUIRED", dedup_key=key, why_it_matters=record["why_it_matters"],
                unknown_to_resolve=unknown, evidence_gaps=record["required_evidence"], stop_condition=record["stop_condition"],
                source_candidates=source_candidates,
            )
            _append(GENERATED_PATH, {**record, "status": "QUEUED", "work_id": f"goal-objective:{objective_id}"})
    return {"status": "GENERATED" if generated else "DEDUPLICATED", "goal": goal, "charter": charter, "generated": generated, "skipped": skipped, "planner": planner_meta}


def continue_when_empty(*, queue, force: bool = False) -> dict[str, Any]:
    rows = _queue_rows(queue)
    eligible = [row for row in rows if row.get("status") in {"QUEUED", "WAITING"}]
    if eligible and not force:
        return {"status": "NOT_EMPTY", "generated": [], "reason": "eligible_queue_work_exists"}
    result = generate_objectives(queue=queue, count=1, enqueue=True)
    result["trigger"] = "empty_queue_goal_continuation" if not eligible else "bounded_certification_force"
    result["reason"] = "Inspect active company goal and Research charter, then generate one bounded objective."
    return result


def continuation_snapshot(queue=None) -> dict[str, Any]:
    if queue is None:
        from nexus_agent_platform.research_work_queue import default_queue
        queue = default_queue()
    rows = _queue_rows(queue)
    goals = read_company_goals()
    charter = ensure_charter()
    generated = _rows(GENERATED_PATH)
    return {
        "status": "READY", "charter_id": charter["charter_id"], "charter_status": charter["status"],
        "active_goal_count": len(goals), "active_goals": goals[:12],
        "generated_objective_count": len(generated),
        "recent_goal_feedback": _rows(FEEDBACK_PATH)[-8:],
        "pending_goal_generated_work": [row.get("work_id") for row in rows if row.get("requested_by") == "research_continuation" and row.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"}],
        "empty_queue_rule": "QUEUE EMPTY -> READ GOALS/CHARTER -> GENERATE BOUNDED OBJECTIVE -> ENQUEUE",
        "source": "research_continuation",
    }
