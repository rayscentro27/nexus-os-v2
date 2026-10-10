"""Canonical, read-only executive status projection for Nova.

The projection is deliberately assembled from existing runtime contracts.  It
does not create work, select Research objectives, or maintain a second queue.
Missing or stale department evidence is reported as such instead of being
converted into a synthetic healthy state.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "nexus.executive-status.v1"
_EXECUTIVE_QUERY = re.compile(
    r"\b(?:what is nexus doing|what happened|what needs me|what is research doing|"
    r"what is alpha doing|what is systems doing|what is clyde waiting|"
    r"what is creative waiting|what happens next)\b",
    re.I,
)


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    except OSError:
        pass
    return rows


def _stamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value


def _age_hours(value: str | None, now: datetime) -> float | None:
    if not value:
        return None


def _fresh_next_action(value: Any, now: datetime) -> str | None:
    """Reject queue prose that embeds a next wake which is no longer future."""
    if value in (None, ""):
        return None
    text = str(value)
    stamps = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", text)
    for stamp in stamps:
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            continue
        if parsed <= now:
            return "Wait for the next deterministic execution slot."
    return text
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 3600)
    except (TypeError, ValueError):
        return None


def _ref(path: Path, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)}
    result.update({key: value for key, value in extra.items() if value is not None})
    return result


def _department(**values: Any) -> dict[str, Any]:
    return {
        "status": values.get("status", "UNKNOWN"),
        "current_objective": values.get("current_objective"),
        "current_task": values.get("current_task"),
        "last_useful_activity": values.get("last_useful_activity"),
        "completed_recently": values.get("completed_recently", []),
        "failed_recently": values.get("failed_recently", []),
        "blockers": values.get("blockers", []),
        "human_gate": values.get("human_gate"),
        "next_action": values.get("next_action"),
        "last_updated": values.get("last_updated"),
        "evidence_refs": values.get("evidence_refs", []),
    }


def _research_status(now: datetime) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    from nexus_agent_platform.research_operational_state import build_research_operational_state

    state = build_research_operational_state()
    queue = state.get("research_queue") or {}
    next_work = queue.get("next") or state.get("next_scheduled_work") or {}
    active = state.get("active_assigned_work") or []
    blocked = state.get("blocked_work_items") or queue.get("blocked") or []
    completed = state.get("recent_completed_work") or []
    current = active[0] if active else next_work if isinstance(next_work, dict) else {}
    ledger_path = ROOT / "data/runtime/research_execution_jobs.jsonl"
    ledger = _read_jsonl(ledger_path)
    failures = [row for row in ledger[-200:] if str(row.get("status", "")).upper() in {"FAILED", "RETRYABLE_FAILURE", "BLOCKED", "ERROR"}]
    useful = [row for row in ledger[-200:] if str(row.get("status", "")).upper() in {"COMPLETED", "EVIDENCE_READY", "AI_RESULT_INTERPRETATION"}]
    last_activity = state.get("last_successful_research_activity")
    blockers = [{"work_id": row.get("work_id"), "title": row.get("title"), "reason": row.get("blocker_type") or row.get("last_result", {}).get("reason")} for row in blocked[:8]]
    status = "WORKING" if active else "QUEUED" if queue.get("total_nonterminal", 0) else "BLOCKED" if blockers else "IDLE"
    evidence = [_ref(ROOT / "data/runtime/research_work_queue.json"), _ref(ROOT / "data/runtime/research_execution_jobs.jsonl")]
    details = _department(
        status=status,
        current_objective=current.get("objective_id") or current.get("title"),
        current_task=current.get("title") or current.get("question") or current.get("work_id"),
        last_useful_activity=last_activity,
        completed_recently=completed[:5],
        failed_recently=failures[-5:],
        blockers=blockers,
        next_action=_fresh_next_action(
            (state.get("current_work") or {}).get("next_action") or (next_work.get("title") if isinstance(next_work, dict) else None),
            now,
        ),
        last_updated=state.get("generated_at"),
        evidence_refs=evidence,
    )
    details.update({
        "active_objective_count": state.get("open_research_objectives", 0),
        "useful_executions_recently": len(useful),
        "failed_executions_recently": len(failures),
        "blocked_sources": blockers,
        "objective_coverage": (state.get("objective_progress") or {}).get("parent_objectives", []),
        "recent_findings": state.get("recent_findings", [])[:8],
        "next_deterministic_action": details["next_action"],
    })
    completed_events = [{"department": "Research", "summary": row.get("title") or row.get("work_id"), "at": row.get("completed_at")} for row in completed[:8]]
    failure_events = [{"department": "Research", "summary": row.get("title") or row.get("work_id"), "reason": row.get("blocker_type") or row.get("status")} for row in failures[-8:]]
    blocked_events = [{"department": "Research", **item} for item in blockers]
    return details, completed_events, failure_events, blocked_events


def _alpha_status(now: datetime, research: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / "data/runtime/alpha_telegram_status.json"
    value = _read(path, {})
    heartbeat = _stamp(value.get("heartbeat"))
    stale = _age_hours(heartbeat, now)
    status = str(value.get("state") or "UNKNOWN").upper()
    if stale is None:
        status = "UNKNOWN"
    elif stale > 24:
        status = "STALE"
    elif status in {"ALIVE", "RUNNING"}:
        status = "AVAILABLE"
    return _department(status=status, current_objective=None,
        current_task="Alpha validation and challenge" if research.get("recent_findings") else None,
        last_useful_activity=research.get("last_useful_activity"),
        completed_recently=(research.get("completed_recently") or [])[:3],
        failed_recently=(research.get("failed_recently") or [])[:3],
        blockers=[{"reason": "Alpha runtime status is stale."}] if status == "STALE" else [],
        next_action="Evaluate persisted Research evidence." if status == "AVAILABLE" else "Revalidate Alpha runtime before claiming fresh evaluation.",
        last_updated=heartbeat, evidence_refs=[_ref(path)])


def _systems_status() -> dict[str, Any]:
    kernel_path = ROOT / "reports/runtime/continuous_operating_kernel_latest.json"
    operator_path = ROOT / "reports/runtime/active_operator_latest.json"
    kernel = _read(kernel_path, {})
    operator = _read(operator_path, {})
    updated = kernel.get("completed_at") or kernel.get("heartbeat", {}).get("last_real_output")
    status = "UNKNOWN"
    if kernel.get("heartbeat", {}).get("heartbeat") == "ACTIVE":
        status = "RUNNING"
    elif operator:
        status = "DEGRADED"
    return _department(status=status, current_objective=operator.get("current_objective"),
        current_task=kernel.get("heartbeat", {}).get("next_action") or operator.get("next_action"),
        last_useful_activity=kernel.get("heartbeat", {}).get("last_real_output"),
        completed_recently=[], failed_recently=[], blockers=[],
        human_gate=operator.get("human_gate"), next_action=kernel.get("heartbeat", {}).get("next_action"),
        last_updated=updated, evidence_refs=[_ref(kernel_path), _ref(operator_path)])


def _creative_status() -> dict[str, Any]:
    path = ROOT / "data/runtime/creative_design_projects.json"
    projects = (_read(path, {}).get("projects") or [])
    pending = [project for project in projects if str(project.get("ray_approval_status", "")).upper() == "PENDING"]
    current = projects[0] if projects else {}
    status = "WAITING_HUMAN" if pending else "READY" if projects else "UNKNOWN"
    return _department(status=status, current_objective=current.get("business_objective"),
        current_task=current.get("title"), last_useful_activity=None,
        completed_recently=[], failed_recently=[], blockers=[],
        human_gate={"required": True, "items": len(pending)} if pending else None,
        next_action=current.get("next_action"), last_updated=None, evidence_refs=[_ref(path)])


def _clyde_status() -> dict[str, Any]:
    path = ROOT / "data/runtime/active_operator_work_orders.json"
    rows = _read(path, [])
    funding = [row for row in rows if any(token in json.dumps(row).lower() for token in ("clyde", "funding", "lender", "readiness")) and row.get("status") not in {"SUPERSEDED", "COMPLETED"}]
    waiting = [row for row in funding if row.get("status") == "WAITING_APPROVAL"]
    if not funding:
        status = "NO_CURRENT_WORK"
    elif waiting:
        status = "WAITING_HUMAN"
    else:
        status = "QUEUED"
    current = funding[0] if funding else {}
    return _department(status=status, current_objective=current.get("objective") or current.get("title"),
        current_task=current.get("title"), last_useful_activity=current.get("updated_at") or current.get("created_at"),
        completed_recently=[], failed_recently=[], blockers=[],
        human_gate={"required": True, "items": len(waiting)} if waiting else None,
        next_action=current.get("next_action") or current.get("recommended_action") or "No current structured Clyde work order.",
        last_updated=current.get("updated_at") or current.get("created_at"), evidence_refs=[_ref(path)])


def build_executive_status(*, now: datetime | None = None) -> dict[str, Any]:
    """Build the one canonical structured executive status object."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    research, completed, failures, blocked = _research_status(now)
    departments = {
        "research": research,
        "alpha": _alpha_status(now, research),
        "clyde": _clyde_status(),
        "systems": _systems_status(),
        "creative": _creative_status(),
    }
    human_gates = [{"department": name, **dept["human_gate"]} for name, dept in departments.items() if isinstance(dept.get("human_gate"), dict)]
    blockers = blocked + [{"department": name, **item} for name, dept in departments.items() for item in dept.get("blockers", [])]
    status_values = {str(dept.get("status")) for dept in departments.values()}
    overall = "BLOCKED" if any(value in {"BLOCKED", "STALE"} for value in status_values) else "ATTENTION_REQUIRED" if failures or human_gates else "WORKING"
    evidence_refs = [json.loads(ref) for ref in sorted({json.dumps(ref, sort_keys=True) for dept in departments.values() for ref in dept.get("evidence_refs", [])})]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "overall_status": overall,
        "departments": departments,
        "completed_since_last_brief": completed,
        "failures": failures,
        "blocked": blockers,
        "human_gates": human_gates,
        "current_work": [{"department": name, "objective": dept.get("current_objective"), "task": dept.get("current_task"), "status": dept.get("status")} for name, dept in departments.items() if dept.get("current_task") or dept.get("current_objective")],
        "next_actions": [{"department": name, "action": dept.get("next_action"), "owner": "RAY" if dept.get("human_gate") else "NEXUS"} for name, dept in departments.items() if dept.get("next_action")],
        "cost_or_provider_warnings": [],
        "evidence_refs": evidence_refs,
    }


def executive_status_delta(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Compare two projections without persisting a second status store."""
    changes: list[dict[str, Any]] = []
    previous_departments = previous.get("departments") or {}
    current_departments = current.get("departments") or {}
    for name in sorted(set(previous_departments) | set(current_departments)):
        before = previous_departments.get(name) or {}
        after = current_departments.get(name) or {}
        fields = {}
        for field in ("status", "current_objective", "current_task", "last_useful_activity", "next_action", "human_gate"):
            if before.get(field) != after.get(field):
                fields[field] = {"before": before.get(field), "after": after.get(field)}
        if fields:
            changes.append({"department": name, "changes": fields})
    return {
        "schema_version": "nexus.executive-status-delta.v1",
        "changed": bool(changes),
        "changed_departments": changes,
        "generated_at": current.get("generated_at"),
    }


def render_executive_status_answer(question: str, status: dict[str, Any] | None = None) -> str | None:
    """Render bounded operational answers directly from the canonical object.

    This is presentation of the existing status contract, not a second intent
    router or state source.  It prevents a remote model/tool read from
    contradicting the snapshot for simple executive-status questions.
    """
    if not _EXECUTIVE_QUERY.search(question or ""):
        return None
    value = status or build_executive_status()
    departments = value.get("departments") or {}
    def state_line(name: str) -> str:
        department = departments.get(name, {})
        state = department.get("status", "UNKNOWN")
        phrases = {
            "QUEUED": "has work queued and is waiting for its next deterministic execution slot",
            "STALE": "has not reported recent useful activity",
            "RUNNING": "is running",
            "WAITING_HUMAN": "is waiting for Ray to act",
            "UNKNOWN": "has no current verified status",
        }
        return f"{name.title()}: {phrases.get(state, f'is {str(state).lower()}')}"

    lowered = question.casefold()
    if "what needs me" in lowered:
        gates = value.get("human_gates") or []
        if not gates:
            return "Nothing currently requires a verified Ray action."
        lines = ["Ray action required:"]
        for gate in gates:
            department = departments.get(gate.get("department", ""), {})
            label = str(gate.get("department") or "Department").title()
            lines.append(f"- {label}: {department.get('next_action') or 'review the pending gate'}; this blocks {department.get('current_task') or 'the department next step'}.")
        return "\n".join(lines)
    if "what happens next" in lowered:
        lines = ["Next actions:"]
        for item in value.get("next_actions") or []:
            lines.append(f"- {item.get('owner', 'NEXUS')}: {item.get('department')}: {item.get('action')}")
        return "\n".join(lines)
    requested = next((name for name in ("research", "alpha", "systems", "clyde", "creative") if name in lowered), None)
    if requested:
        return state_line(requested) + ".\nNext: " + str((departments.get(requested) or {}).get("next_action") or "No verified next action.")
    if "what happened" in lowered:
        completed = value.get("completed_since_last_brief") or []
        failures = value.get("failures") or []
        return "Recently:\n" + ("- " + "\n- ".join(str(item.get("summary") or item.get("title") or item) for item in completed[:5]) if completed else "- No recent completed change is verified.") + ("\nFailures:\n- " + "\n- ".join(str(item.get("summary") or item.get("reason") or item) for item in failures[:5]) if failures else "\nNo recent failure is recorded in the executive snapshot.")
    return "Overall status: " + str(value.get("overall_status", "UNKNOWN")) + ".\n" + "\n".join(state_line(name) for name in ("research", "alpha", "clyde", "creative", "systems"))


def executive_status_for_prompt(status: dict[str, Any] | None = None) -> str:
    """Return a bounded JSON projection suitable for Hermes Nova context."""
    value = status or build_executive_status()
    def compact_items(items: Any, limit: int = 5) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in (items or [])[:limit]:
            if not isinstance(item, dict):
                continue
            selected = {
                key: item.get(key)
                for key in ("department", "summary", "title", "work_id", "objective_id", "status", "at", "reason", "blocker_type", "source")
                if item.get(key) is not None
            }
            result.append(selected or {"summary": json.dumps(item, ensure_ascii=False, default=str)[:300]})
        return result

    departments: dict[str, Any] = {}
    for name, department in (value.get("departments") or {}).items():
        departments[name] = {
            key: department.get(key)
            for key in (
                "status", "current_objective", "current_task", "last_useful_activity",
                "blockers", "human_gate",
                "next_action", "last_updated", "evidence_refs",
            )
            if key in department
        }
        departments[name]["completed_recently"] = compact_items(department.get("completed_recently"), 3)
        departments[name]["failed_recently"] = compact_items(department.get("failed_recently"), 3)
        departments[name]["evidence_refs"] = [
            {key: ref.get(key) for key in ("path", "id") if ref.get(key)}
            for ref in (department.get("evidence_refs") or [])[:5]
            if isinstance(ref, dict)
        ]
        if name == "research":
            departments[name]["recent_findings"] = compact_items(department.get("recent_findings"), 3)
            departments[name]["objective_coverage"] = compact_items(department.get("objective_coverage"), 3)
    compact = {
        "schema_version": value.get("schema_version"),
        "generated_at": value.get("generated_at"),
        "overall_status": value.get("overall_status"),
        "departments": departments,
        "completed_since_last_brief": compact_items(value.get("completed_since_last_brief"), 6),
        "failures": compact_items(value.get("failures"), 6),
        "blocked": compact_items(value.get("blocked"), 6),
        "human_gates": (value.get("human_gates") or [])[:8],
        "current_work": (value.get("current_work") or [])[:8],
        "next_actions": (value.get("next_actions") or [])[:8],
        "cost_or_provider_warnings": (value.get("cost_or_provider_warnings") or [])[:8],
        "evidence_refs": [
            {key: ref.get(key) for key in ("path", "id") if ref.get(key)}
            for ref in (value.get("evidence_refs") or [])[:12]
            if isinstance(ref, dict)
        ],
    }
    rendered = json.dumps(compact, ensure_ascii=False, sort_keys=True, default=str)
    if len(rendered) <= 18000:
        return rendered
    # Keep the contract valid JSON even if a source contains unusually large
    # free-form evidence.  The full object remains available to local callers.
    compact["departments"]["research"]["recent_findings"] = []
    compact["departments"]["research"]["objective_coverage"] = []
    compact["completed_since_last_brief"] = []
    compact["failures"] = []
    compact["blocked"] = []
    compact["evidence_refs"] = []
    return json.dumps(compact, ensure_ascii=False, sort_keys=True, default=str)
