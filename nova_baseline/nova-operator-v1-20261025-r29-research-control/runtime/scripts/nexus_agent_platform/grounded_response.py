"""Narrow grounding boundary for executive/current-state responses.

Hermes remains responsible for prose and recommendations.  This module owns
only facts whose truth must come from the executing runtime or a governed
read-only capability.  It is deliberately not a general response validator.
"""

from __future__ import annotations

import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _priority_request(request: str) -> bool:
    try:
        from nova.executive_intelligence import is_priority_request
    except ModuleNotFoundError:
        from executive_intelligence import is_priority_request
    return is_priority_request(request)


def _review_request(request: str) -> bool:
    try:
        from nova.executive_intelligence import is_executive_attention_request
    except ModuleNotFoundError:
        from executive_intelligence import is_executive_attention_request
    return is_executive_attention_request(request)


def _company_operating_request(request: str) -> bool:
    """Recognize the meaning class of broad company-state questions."""
    text = str(request or "").lower()
    scope = any(term in text for term in ("nexus", "company", "department", "departments", "everyone", "all teams")) or bool(re.search(r"\bwhat (?:are|is) we\b", text))
    state = any(term in text for term in ("working", "doing", "status", "update", "today", "completed", "queued", "next", "blocked", "broken", "currently", "right now", "happened"))
    return scope and state and not _review_request(text) and not _priority_request(text)


def requires_current_evidence(request: str) -> bool:
    """Detect requests that explicitly ask for current or runtime facts."""
    text = str(request or "").lower()
    try:
        from nexus_agent_platform.research_alpha_lineage import is_research_lineage_request
        if is_research_lineage_request(text):
            return True
    except Exception:
        pass
    # Priority is an executive recommendation, not a request to replace the
    # model's answer with the generic runtime-status composition.
    if _priority_request(text):
        return False
    if _review_request(text):
        return True
    if re.search(r"\bresearch\b", text) and re.search(
        r"\b(still|running|active|heartbeat|scheduler|processing|cycle|activity|status|enabled)\b", text
    ):
        return True
    return bool(
        re.search(r"\b(current|currently|right now|today|available|health|status|what happened|working|doing|queued|department|runtime|version|model|python|operating system|podman)\b", text)
        and re.search(r"\b(nexus|system|hermes|finance|alpha|research|model|python|operating|podman|runtime|health)\b", text)
    )


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def collect_verified_current_state(runtime: Dict[str, Any]) -> Dict[str, Any]:
    """Build a secret-free, read-only evidence object from canonical readers."""
    evidence: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "host": runtime.get("runtime_host", "UNKNOWN"),
            "hermes_version": runtime.get("hermes_version", "UNKNOWN"),
            "profile": runtime.get("profile", "UNKNOWN"),
            "provider": runtime.get("provider", "UNKNOWN"),
            "model": runtime.get("model", "UNKNOWN"),
            "source": "oracle_bridge_runtime_envelope",
            "provenance": "CURRENT",
        },
        "health": {"status": "UNKNOWN", "raw": {}, "source": "UNKNOWN", "provenance": "UNKNOWN"},
        "specialists": {},
        "priority": {"classification": "UNKNOWN", "summary": "Current priority was not verified.", "source": "UNKNOWN"},
        "research": {},
    }
    # Read the canonical bounded artifact directly.  Calling the full health
    # capability here can include telemetry/database work; the Telegram
    # response contract must not turn that into an unbounded nested request.
    try:
        path = Path(__file__).resolve().parents[2] / "reports/hermes_modernization/live_runtime_status.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        contract = raw.get("contract", {})
        degraded = sum(1 for row in contract.values() if isinstance(row, dict) and row.get("status") in {"DEGRADED", "STALE"})
        failed = len(raw.get("evidence", {}).get("failures", []))
        worker_status = Path(__file__).resolve().parents[2] / "data/runtime/nova_telegram_status.json"
        worker_running = False
        if worker_status.exists():
            try:
                worker_running = json.loads(worker_status.read_text(encoding="utf-8")).get("state") == "RUNNING"
            except (OSError, ValueError):
                pass
        evidence["health"] = {
            "status": "FAILED" if failed else ("OPERATIONAL_WITH_TELEMETRY_DEGRADED" if degraded else ("HEALTHY" if worker_running or raw.get("nexus_running") == "YES" else "UNKNOWN")),
            "raw": {"overall_status": raw.get("nexus_running", "UNKNOWN"), "worker_running": worker_running, "active_services": None, "degraded_services": degraded, "failed_services": failed},
            "source": "reports/hermes_modernization/live_runtime_status.json",
            "provenance": "CURRENT",
            "interpretation": "Nexus runtime evidence is available; individual degraded sources are reported separately from the Telegram-to-Oracle path.",
        }
    except Exception:
        pass

    # Read-only composition over the existing kernel and Research readers.
    # This is not a second state store: each dimension retains its canonical
    # owner so liveness is never mistaken for active task processing.
    try:
        from nexus_agent_platform.continuous_operating_kernel import current_kernel_contract
        from nexus_agent_platform.research_operational_state import build_research_operational_state
        kernel = current_kernel_contract()
        operational = build_research_operational_state()
        root = Path(__file__).resolve().parents[2]
        activity_path = root / "reports/runtime/alpha_research_activity_latest.json"
        activity = json.loads(activity_path.read_text(encoding="utf-8")) if activity_path.exists() else {}
        heartbeat_path = root / "data/runtime/research_heartbeat.json"
        heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8")) if heartbeat_path.exists() else {}
        process_path = root / "data/operations/nexus_process_registry.json"
        process_rows = json.loads(process_path.read_text(encoding="utf-8")) if process_path.exists() else []
        research_process = next(
            (row for row in (process_rows if isinstance(process_rows, list) else [])
             if row.get("process_id") == "research_intelligence"),
            {},
        )
        worker = str(heartbeat.get("worker_state") or kernel.get("research_worker_state") or "UNKNOWN").upper()
        if worker in {"RUNNING", "PROCESSING", "BUSY"} or operational.get("research_work_state") == "WORKING":
            task_processing = "ACTIVE"
        elif worker in {"IDLE", "IDLE_BETWEEN_CYCLES", "WAITING"}:
            task_processing = "IDLE_BETWEEN_CYCLES"
        else:
            task_processing = "UNKNOWN"
        scheduler = str(kernel.get("research_scheduler") or "UNKNOWN").upper()
        evidence["research"] = {
            "heartbeat": str(kernel.get("research_heartbeat") or heartbeat.get("heartbeat") or "UNKNOWN").upper(),
            "supervisor": scheduler,
            "scheduler_enabled": scheduler not in {"INACTIVE", "UNKNOWN"},
            "process_configured": bool(research_process),
            "process_enabled": research_process.get("enabled") if research_process else None,
            # The legacy registry row is a configuration snapshot (and may
            # retain an old simulated/manual status).  A current kernel
            # heartbeat is authoritative for the continuous executor.
            "execution_mode": str(heartbeat.get("execution_mode") or ("REAL" if heartbeat.get("heartbeat") == "ACTIVE" and heartbeat.get("result_status") == "PASS" else "UNKNOWN")).upper(),
            "dry_run": heartbeat.get("dry_run") if "dry_run" in heartbeat else False if heartbeat.get("heartbeat") == "ACTIVE" and heartbeat.get("result_status") == "PASS" else None,
            "process_last_status": str(heartbeat.get("result_status") or research_process.get("last_status") or "UNKNOWN").upper(),
            "task_processing": task_processing,
            "worker_state": worker,
            "queue_state": str(operational.get("research_work_state") or "UNKNOWN").upper(),
            "queued_jobs": operational.get("queued_research_jobs"),
            "active_jobs": operational.get("active_research_jobs"),
            "last_cycle": heartbeat.get("last_success") or activity.get("generated_at") or "UNKNOWN",
            "last_successful_output": heartbeat.get("last_real_output") or heartbeat.get("last_success") or "UNKNOWN",
            "recent_activity": {
                "sources_checked": activity.get("sources_checked"),
                "items_processed": activity.get("items_processed"),
                "new_items_discovered": activity.get("new_items_discovered"),
            },
            "source": "continuous_operating_kernel+research_operational_state+alpha_research_activity",
            "provenance": "CURRENT_READ_MODEL",
        }
    except Exception as exc:
        evidence["research"] = {"heartbeat": "UNKNOWN", "source": type(exc).__name__, "provenance": "UNKNOWN"}

    # Capability registry status is the canonical availability check for the
    # bounded Alpha lane.  Finance is a governed capability path rather than a
    # standalone agent registry entry, so verify its read-only rollup path.
    try:
        path = Path(__file__).resolve().parents[2] / "data/runtime/alpha_telegram_status.json"
        alpha = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        evidence["specialists"]["alpha"] = {
            "availability": "AVAILABLE" if path.exists() else "UNKNOWN",
            "source": "data/runtime/alpha_telegram_status.json",
            "provenance": "CURRENT",
        }
    except Exception as exc:
        evidence["specialists"]["alpha"] = {"availability": "UNKNOWN", "source": type(exc).__name__, "provenance": "UNKNOWN"}

    try:
        root = Path(__file__).resolve().parents[2]
        finance_path = root / "scripts/nexus_agent_platform/finance/engine.py"
        ledger = root / "data/governed/finance_resource_ledger.jsonl"
        if not finance_path.exists() or not ledger.exists():
            raise RuntimeError("governed_finance_path_unavailable")
        evidence["specialists"]["finance"] = {
            "availability": "AVAILABLE",
            "source": "GOVERNED_FINANCE_ROLLUP",
            "provenance": "CURRENT",
        }
    except Exception as exc:
        evidence["specialists"]["finance"] = {"availability": "UNKNOWN", "source": type(exc).__name__, "provenance": "UNKNOWN"}

    try:
        from nexus_agent_platform.capabilities.operational_reads import read_operational_capability
        approvals = read_operational_capability("APPROVAL_QUEUE")
        items = (approvals.get("data") or {}).get("items", []) if approvals.get("status") in {"OK", "success"} else []
        if not items:
            from nexus_agent_platform.governed.approvals import get_pending_approvals
            items = get_pending_approvals(requested_for="ray", include_self=False)
        ray_items = [item for item in items if item.get("approval_required") is True]
        if ray_items:
            top = ray_items[0]
            evidence["priority"] = {
                "classification": "REQUIRES_RAY",
                "summary": str(top.get("title") or top.get("action_summary") or top.get("exact_action_requested") or "A governed approval is pending."),
                "risk_level": str(top.get("risk_level") or "UNKNOWN").upper(),
                "status": str(top.get("status") or "PENDING").upper(),
                "expires_at": top.get("expires_at"),
                "source": approvals.get("source_path", "APPROVAL_QUEUE"),
                "provenance": "CURRENT",
            }
        else:
            evidence["priority"] = {"classification": "SOLVABLE_WITH_EXISTING_CAPABILITY", "summary": "No current governed approval requiring Ray was found.", "source": "APPROVAL_QUEUE", "provenance": "CURRENT"}
    except Exception:
        pass
    return evidence


_FACT_LABEL = re.compile(
    r"^(?:python(?:\s+version)?|operating\s+system(?:\s+version)?|os(?:\s+version)?|podman(?:\s+version)?|hermes(?:\s+runtime)?(?:\s+version)?|runtime(?:\s+host|\s+version)?|provider(?:\s*/\s*model)?|model|finance|alpha)\s*[:：-]",
    re.I,
)


def _normalized_line(line: str) -> str:
    value = re.sub(r"^\s*(?:[-*•]\s*|\d+[.)]\s*)", "", line)
    value = value.replace("**", "").replace("`", "").strip()
    return value


def _verified_lines(evidence: Dict[str, Any]) -> list[str]:
    runtime = evidence["runtime"]
    health = evidence["health"]
    specialists = evidence["specialists"]
    priority = evidence["priority"]
    lines = ["Nexus is operational, with telemetry currently degraded." if health.get("status") == "OPERATIONAL_WITH_TELEMETRY_DEGRADED" else f"Nexus health: {health.get('status', 'UNKNOWN')}."]
    if priority.get("classification") == "REQUIRES_RAY":
        lines.append(f"Ray action: {priority.get('summary', 'A governed approval is pending.')}")
    else:
        lines.append("Ray action: Nothing currently requires your action.")
        lines.append(f"Nexus working: {priority.get('summary', 'No internally actionable priority was verified.')}")
    lines.extend([
        f"Finance: {specialists.get('finance', {}).get('availability', 'UNKNOWN')}.",
        f"Alpha: {specialists.get('alpha', {}).get('availability', 'UNKNOWN')}.",
        f"Runtime: {runtime.get('host', 'UNKNOWN')} Hermes {runtime.get('hermes_version', 'UNKNOWN')}, profile {runtime.get('profile', 'UNKNOWN')}, {runtime.get('provider', 'UNKNOWN')} / {runtime.get('model', 'UNKNOWN')}.",
    ])
    return lines


def _research_verified_lines(evidence: Dict[str, Any]) -> list[str]:
    """Render Research liveness, scheduling, and work as separate facts."""
    state = evidence.get("research", {})
    activity = state.get("recent_activity", {})
    lines = [
        f"Research heartbeat: {state.get('heartbeat', 'UNKNOWN')}.",
        f"Research scheduler/supervisor: {state.get('supervisor', 'UNKNOWN')} (enabled={state.get('scheduler_enabled', 'UNKNOWN')}).",
        f"Research process: configured={state.get('process_configured', 'UNKNOWN')}, enabled={state.get('process_enabled', 'UNKNOWN')}, last status={state.get('process_last_status', 'UNKNOWN')}.",
        f"Execution mode: {state.get('execution_mode', 'UNKNOWN')}.",
        f"Task processing: {state.get('task_processing', 'UNKNOWN')}.",
        f"Queue/work state: {state.get('queue_state', 'UNKNOWN')} (active={state.get('active_jobs', 'UNKNOWN')}, queued={state.get('queued_jobs', 'UNKNOWN')}).",
        f"Last verified cycle/activity: {state.get('last_cycle', 'UNKNOWN')}.",
        "Recent monitored activity: "
        f"{activity.get('sources_checked', 'UNKNOWN')} sources checked, "
        f"{activity.get('items_processed', 'UNKNOWN')} items processed, "
        f"{activity.get('new_items_discovered', 'UNKNOWN')} new items.",
    ]
    if state.get("dry_run") is not None:
        lines.insert(3, f"Dry-run: {state.get('dry_run')}.")
    return lines


def _review_verified_lines(evidence: Dict[str, Any]) -> list[str]:
    """Turn the current approval read into an executive mobile decision."""
    priority = evidence.get("priority", {})
    if priority.get("classification") != "REQUIRES_RAY":
        return ["Nothing currently needs your review. Nexus can continue without you."]
    lines = [
        "One item currently needs your review.",
        f"What: {priority.get('summary', 'A governed approval is pending.')}",
        "Why you: Nexus needs your decision at the existing approval boundary before proceeding.",
        f"Risk: {str(priority.get('risk_level', 'UNKNOWN')).lower()}.",
        "Recommendation: review the bounded action and approve only if it matches your intent.",
        "If approved: Nexus can continue that action. If not: it remains pending and the parent work stays open.",
    ]
    if priority.get("expires_at"):
        lines.append(f"Expiry: {priority['expires_at']}.")
    return lines


def ground_response(response: str, request: str, runtime: Dict[str, Any], verified_current_state: Dict[str, Any] | None = None) -> tuple[str, Dict[str, Any]]:
    """Ground only current-state responses and return the evidence object."""
    if not requires_current_evidence(request):
        return str(response or "").strip(), {}
    evidence = verified_current_state or collect_verified_current_state(runtime)
    # Remove model-authored field claims only where deterministic evidence now
    # owns that field.  Narrative, analysis, and recommendations remain intact.
    kept = []
    owned_section = False
    for line in str(response or "").splitlines():
        heading = line.strip().lower()
        if re.search(r"highest[- ]priority|priority work item", heading):
            owned_section = True
            continue
        if re.search(r"(?:current )?(?:nexus )?system health|current nexus health|availability(?: of resources| of finance)|finance and alpha availability|actions required|hermes runtime", heading):
            owned_section = True
            continue
        if owned_section and re.search(r"availability|hermes runtime|runtime|let me know", heading):
            owned_section = False
        if owned_section or _FACT_LABEL.match(_normalized_line(line)):
            continue
        kept.append(line)
    # Current-state answers are a single authoritative composition.  Reusing
    # free-form model prose here would permit an unlabeled contradiction (for
    # example, a claim that a resource is unavailable) to survive the field
    # filter.  Hermes still performs the upstream reasoning; this boundary
    # owns the final machine-fact slots only for this narrow response surface.
    narrative = ""
    try:
        from nexus_agent_platform.research_alpha_lineage import is_research_lineage_request, query_lineage
    except Exception:
        is_research_lineage_request = lambda _request: False
        query_lineage = None
    if is_research_lineage_request(request) and query_lineage is not None:
        lineage = query_lineage()
        evidence["research_alpha_lineage"] = lineage
        composed = _research_lineage_lines(lineage)
    elif _company_operating_request(request):
        from nexus_agent_platform.company_operating_state import build_company_operating_state
        company = evidence.get("company_operating_state") or build_company_operating_state()
        evidence["company_operating_state"] = company
        composed = _company_verified_lines(company)
    elif _review_request(request):
        composed = "\n".join(_review_verified_lines(evidence))
    elif re.search(r"\bresearch\b", request, re.I):
        composed = "\n".join(_research_verified_lines(evidence))
    else:
        composed = "\n".join(_verified_lines(evidence))
    if re.search(r"\b(?:python|operating system|podman)\b", str(request), re.I):
        composed += "\nEnvironment versions: UNKNOWN unless separately verified."
    if narrative:
        composed = narrative + "\n\n" + composed
    return composed, evidence


def _research_lineage_lines(lineage: Dict[str, Any]) -> str:
    """Render only persisted Research outputs and explicit Alpha lineage."""
    outputs = lineage.get("research_outputs") or []
    lines = [f"Research produced {len(outputs)} persisted intelligence item(s) in the requested period."]
    if not outputs:
        lines.append("No persisted Research output records were found in that period. Heartbeat and monitored-source counters are not being substituted for output evidence.")
        lines.append("Alpha evaluations: 0.")
        return "\n".join(lines)
    for index, item in enumerate(outputs, 1):
        lines.append(f"\n{index}. {item.get('title', 'Untitled Research output')}")
        lines.append(f"Research finding: {item.get('finding', 'UNKNOWN')}")
        sources = item.get("sources") or []
        lines.append(f"Source: {', '.join(sources) if sources else 'UNKNOWN'}")
        lines.append(f"Artifact: {item.get('artifact_id', 'UNKNOWN')} (Research record: {item.get('research_id') or 'NONE'})")
        lines.append(f"Verification: {item.get('verification_status', 'UNKNOWN')}; confidence: {item.get('confidence', 'UNKNOWN')}")
        evaluation = item.get("alpha_evaluation") or {}
        if evaluation.get("evaluated"):
            lines.append(f"Alpha evaluation: score {evaluation.get('score', 'UNKNOWN')}; decision {evaluation.get('decision', 'UNKNOWN')}; reason {evaluation.get('reasoning') or 'not recorded'}.")
        else:
            intake = item.get("alpha_intake")
            lines.append("Alpha evaluation: not scored; no canonical Alpha evaluation record was found.")
            if intake:
                lines.append(f"Alpha intake: {intake.get('status', 'RECORDED')} (challenge/intake is not a score).")
        routing = item.get("routing") or {}
        lines.append(f"Routed to: {routing.get('destination') or 'NONE'}; current status: {item.get('current_status', 'UNKNOWN')}.")
    lines.append(f"Unscored Research items: {lineage.get('unscored_count', 0)}.")
    return "\n".join(lines)


def _company_verified_lines(state: Dict[str, Any]) -> str:
    health = state.get("system_health", {})
    research = state.get("research", {})
    lines = [f"Nexus is {str(health.get('state', 'UNKNOWN')).lower().replace('_', ' ')} and continuing internal work."]
    lines.append("\nWorking now:")
    work = state.get("current_work", [])
    if work:
        lines.extend(f"- {item.get('department', 'UNKNOWN')} — {item.get('action', 'bounded internal work')} ({item.get('status', 'UNKNOWN')})." for item in work[:4])
    else:
        lines.append(f"- No child task is active at this read. The supervisor is {health.get('supervisor', 'UNKNOWN')} and the next Research cycle is scheduled for {research.get('next_wake', 'UNKNOWN')}.")
    lines.append("\nCompleted recently:")
    completions = state.get("recent_completions", [])
    if completions:
        lines.extend(f"- {item.get('department', 'UNKNOWN')} — {item.get('goal_id', 'goal')} recorded progress at {item.get('at', 'UNKNOWN')}." for item in completions[:4])
    else:
        lines.append("- No fresh parent-goal completion was verified.")
    lines.append("\nResearch and Alpha:")
    lines.append(f"- Research — {research.get('state', 'UNKNOWN')}; execution mode {research.get('execution_mode', 'UNKNOWN')}; queue {research.get('queue_state', 'UNKNOWN')}.")
    lines.append(f"- Alpha — {state.get('alpha', {}).get('state', 'UNKNOWN')}; activity evidence {state.get('alpha', {}).get('activity', 'UNKNOWN')}.")
    lines.append("\nNext:")
    lines.append(f"- {state.get('queued_next', {}).get('action', 'UNKNOWN')} (next wake {state.get('queued_next', {}).get('next_wake', 'UNKNOWN')}).")
    lines.append("\nIssues:")
    blockers = state.get("blockers", [])
    lines.extend(f"- {item.get('summary')} Impact: {item.get('impact')}." for item in blockers[:3])
    if not blockers:
        lines.append("- No current blocker was evidenced.")
    lines.append(f"\nRay action: {state.get('ray_action', 'UNKNOWN')}.")
    return "\n".join(lines)


def response_completeness(response: str) -> Dict[str, bool]:
    """General multipart coverage check for the grounded executive surface."""
    text = str(response or "").lower()
    return {
        "system_health": "nexus is operational" in text or "nexus health:" in text,
        "ray_priority": "ray action:" in text,
        "finance": "finance:" in text,
        "alpha": "alpha:" in text,
        "runtime": "runtime:" in text,
    }
