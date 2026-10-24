"""Objective-first, depth-budgeted Research cases on governed Nexus memory.

Cases are durable objective records in the bounded Research State v2 store.
Source adapters, queue ownership, and provider routing remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import copy
import re
import os
import subprocess
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence
from research.proactive_research_memory import persist_state
from research import proactive_research_memory as research_memory
from research import research_state_v2 as state_v2

ROOT = Path(__file__).resolve().parents[2]

CASE_STATES = {
    "DISCOVERED", "PROMISING", "UNDER_DEVELOPMENT", "RESEARCHING_MISSING_PIECES",
    "SYNTHESIZING", "RECOMMENDATION_READY", "DEPARTMENT_DEVELOPMENT", "TESTING",
    "REFINING", "MORE_RESEARCH_REQUIRED", "QUALIFIED", "PARKED",
    "REJECTED_WITH_EVIDENCE", "COMPLETED",
    "INVESTIGATING", "RESEARCHING", "DEVELOPING_SOLUTION", "REPLANNING",
    "ALTERNATIVE_REQUIRED", "AWAITING_EVIDENCE", "AWAITING_RESOURCE",
    "AWAITING_EXTERNAL_ACTION", "AWAITING_RAY_DECISION", "READY_FOR_RAY",
    "APPROVED_FOR_NEXT_STAGE", "EXECUTING", "SCALING",
    "OBJECTIVE_ACHIEVED_AWAITING_RAY_ACCEPTANCE", "CHANGES_REQUESTED",
}
APPROACH_STATES = {"VIABLE", "VIABLE_WITH_CHANGES", "PROMISING", "INSUFFICIENT_EVIDENCE",
    "NOT_RECOMMENDED", "REPLACED_BY_BETTER_APPROACH", "TOO_EXPENSIVE_AT_CURRENT_SCALE",
    "REQUIRES_FUTURE_CAPABILITY", "INVALID_CLAIM", "SCAM_OR_MISREPRESENTED", "UNSAFE_APPROACH"}
ACTIVE_STATES = {"DISCOVERED", "PROMISING", "UNDER_DEVELOPMENT", "RESEARCHING_MISSING_PIECES",
                 "SYNTHESIZING", "RECOMMENDATION_READY", "DEPARTMENT_DEVELOPMENT", "TESTING",
                 "REFINING", "MORE_RESEARCH_REQUIRED", "QUALIFIED", "INVESTIGATING",
                 "RESEARCHING", "DEVELOPING_SOLUTION", "REPLANNING", "ALTERNATIVE_REQUIRED",
                 "AWAITING_EVIDENCE", "AWAITING_RESOURCE", "AWAITING_EXTERNAL_ACTION",
                 "APPROVED_FOR_NEXT_STAGE", "EXECUTING", "SCALING", "CHANGES_REQUESTED"}
MAX_ACTIVE_DEEP_CASES = 3
ACTIVE_DEEP_JOB_STATES = {"CLAIMED", "RUNNING"}
RAY_DECISION_STATES = {"READY_FOR_RAY_REVIEW", "AWAITING_RAY_INFORMATION", "APPROVED", "DENIED", "CHANGES_REQUESTED"}
DEFAULT_DEPTH_BUDGET = {
    "max_source_lookups": 20, "max_followup_questions": 10,
    "max_research_iterations": 5, "max_cross_department_requests": 5,
    "max_bounded_experiments": 3,
}
RECOMMENDATIONS = {"TEST", "BUILD", "INTEGRATE", "AFFILIATE", "PARTNER", "SERVICE",
                   "EDUCATION", "MONITOR", "GET_MORE_EVIDENCE", "PARK", "REJECT_WITH_EVIDENCE"}
DEVELOPMENT_PROFILES = {
    "TRADING_INTELLIGENCE": {"component_roles": ["ENTRY_SIGNAL", "CONFIRMATION", "TREND_FILTER", "REGIME_FILTER", "VOLATILITY_FILTER", "VOLUME_FILTER", "MARKET_STRUCTURE", "EXIT", "STOP", "TARGET", "POSITION_SIZING", "SESSION_FILTER", "CONTEXT_ONLY"],
        "required_before_independent_test": ["market", "timeframe", "entry", "exit", "stop", "target", "position sizing", "fees/slippage", "repainting/intrabar behavior"], "owner": "MERCURY_TRADING", "safety": "PAPER_PRACTICE_ONLY_NO_LIVE_TRADING"},
    "BUSINESS_OPPORTUNITIES": {"required_questions": ["customer segment and need", "frequency and pain", "current solutions and complaints", "willingness to pay", "competition", "delivery costs", "build vs affiliate vs service vs education vs partner", "monetization route"], "owner": "ATLAS_OPPORTUNITY", "economics_owner": "FINANCE"},
    "TECHNOLOGY_FOR_NEXUS": {"evaluation_fields": ["Nexus problem", "current alternative", "API/automation", "license/commercial rights", "price", "privacy", "latency", "quality", "reliability"], "route": ["RESEARCH", "LABS", "UPGRADE_CONTROL", "SYSTEMS"]},
    "CREATIVE": {"evaluation_fields": ["format/model/platform/audience signal", "fit to GoClear/Nexus", "evidence", "low-cost test", "owner"], "safety": "PROMPT_APPROVAL_AND_PUBLISHING_GATES_REMAIN"},
    "MARKETING_TRENDS": {"evaluation_fields": ["platform/funnel/audience signal", "customer language", "fit", "cheap test", "evidence and attribution"], "safety": "CAMPAIGN_EXECUTION_REQUIRES_APPROVAL"},
    "FUNDING_GRANTS": {"required_evidence": ["official program source", "eligibility", "deadline", "allowable use", "award amount", "application effort", "verification status"], "owner": "FUNDING"},
    "SYSTEMS": {"evaluation_fields": ["failure/problem statement", "affected service", "reliability evidence", "repair risk", "recovery test", "rollback"], "safety": "PRODUCTION_CHANGE_REQUIRES_GOVERNED_CONTROL"},
}


def _development_profile(family: str) -> dict[str, Any]:
    key = str(family or "").upper()
    return dict(DEVELOPMENT_PROFILES.get(key, {}))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _latest_cases(*, include_full_payload: bool = True) -> list[dict[str, Any]]:
    canonical: dict[str, dict[str, Any]] = {}
    legacy: dict[str, dict[str, Any]] = {}
    # Detailed case work explicitly hydrates bounded case payloads; ordinary
    # scheduling and proactive-memory reads use compact projections.
    for row in state_v2.list_current(kinds=("RESEARCH_CASE", "PROACTIVE_RESEARCH_CASE"),
                                     limit=100, include_payload=include_full_payload,
                                     fields=None if include_full_payload else (
                                         "memory_id", "memory_kind", "recorded_at",
                                         "case_id:payload->>case_id",
                                         "objective_key:payload->>objective_key",
                                         "status:payload->>status",
                                         "case_schema_version:payload->>case_schema_version")):
        kind = row.get("memory_kind")
        if kind not in {"RESEARCH_CASE", "PROACTIVE_RESEARCH_CASE"}:
            continue
        cid = str(row.get("case_id") or "")
        if not cid:
            continue
        target = canonical if kind == "RESEARCH_CASE" or row.get("case_schema_version") else legacy
        prior = target.get(cid)
        if prior is None or str(row.get("recorded_at") or "") >= str(prior.get("recorded_at") or ""):
            target[cid] = row

    # The legacy video worker writes PROACTIVE_RESEARCH_CASE bookkeeping for
    # the same case_id after its durable source/finding/handoff work. It is a
    # receipt, not a replacement for the objective case. Merge only evidence
    # projections into the objective record so late source-worker writes cannot
    # erase objective, owner, questions, depth budget, or recommendation state.
    merged: list[dict[str, Any]] = []
    for cid, case in canonical.items():
        old = legacy.get(cid)
        if old:
            value = dict(case)
            sources = list(value.get("sources") or [])
            if old.get("canonical_url") and not any(_source_identity(item) == _source_identity({"url": old.get("canonical_url")}) for item in sources):
                sources.append({"source_id": old.get("source_id") or old.get("canonical_url"),
                    "url": old.get("canonical_url"), "title": old.get("topic"),
                    "source_class": old.get("source_class") or "UNKNOWN",
                    "research_source_id": old.get("research_source_id"),
                    "extraction_status": "LEGACY_WORKER_RECEIPT"})
            value["sources"] = sources
            value["source_count"] = max(int(value.get("source_count") or 0), len(sources))
            value["source_ids"] = sorted(set(value.get("source_ids") or []) |
                {str(item.get("source_id")) for item in sources if item.get("source_id")})
            legacy_finding = old.get("finding_id")
            findings = list(value.get("findings") or [])
            if legacy_finding and not any(str(item.get("finding_id")) == str(legacy_finding) for item in findings):
                findings.append({"finding_id": str(legacy_finding), "source_id": old.get("research_source_id"),
                    "summary": old.get("topic"), "projection": "LEGACY_WORKER_RECEIPT"})
            value["findings"] = findings
            value["handoff_ids"] = sorted(set(value.get("handoff_ids") or []) |
                {str(item) for item in old.get("handoff_ids", []) if item})
            value.setdefault("notebook_id", old.get("notebook_id"))
            merged.append(value)
        else:
            merged.append(case)
    # Keep legacy-only records visible for backward-compatible read models;
    # they are still excluded from depth-first scheduling by schema version.
    merged.extend(row for cid, row in legacy.items() if cid not in canonical)
    return merged


def get_case(case_id: str, *, allow_bounded_local_recovery: bool = False) -> dict[str, Any] | None:
    """Hydrate one case by its durable identity instead of scanning full case bodies.

    ``_latest_cases`` is for bounded scheduling/read-model work.  Using it for a
    known case ID downloads up to 100 full payloads from Supabase and can exceed
    a durable job's egress envelope. Normal reads use exact indexed hydration
    only. The bounded local JSONL tail is available solely to an explicitly
    authorized recovery caller; it is never an implicit live lookup fallback.
    """
    if not case_id:
        return None
    remote = research_memory.hydrate_memory(str(case_id))
    if isinstance(remote, dict) and str(remote.get("case_id") or "") == str(case_id):
        return remote

    if not allow_bounded_local_recovery:
        try:
            _emit_current_state_lookup_unavailable(str(case_id))
        except Exception as exc:
            raise CurrentStateLookupUnavailable(
                f"CURRENT_STATE_LOOKUP_UNAVAILABLE; RECOVERY_EVENT_PERSIST_FAILED:{type(exc).__name__}") from exc
        raise CurrentStateLookupUnavailable(
            "CURRENT_STATE_LOOKUP_UNAVAILABLE; bounded local ledger access requires explicit recovery authorization")

    # Explicit recovery-only access, bounded by bytes and restricted to the tail.
    local_rows=[]
    path=persistence.collection_path("research_runtime_states")
    try:
        with path.open("rb") as handle:
            handle.seek(0,2); size=handle.tell(); handle.seek(max(0,size-8_000_000))
            raw=handle.read(8_000_000)
        lines=raw.splitlines()
        if size>8_000_000 and lines:
            lines=lines[1:]
        for line in lines:
            try:
                row=json.loads(line)
            except (ValueError,TypeError):
                continue
            if (isinstance(row,dict) and row.get("memory_kind") in {"RESEARCH_CASE","PROACTIVE_RESEARCH_CASE"}
                    and str(row.get("case_id") or "")==str(case_id)):
                local_rows.append(row)
    except OSError:
        pass
    if not local_rows:
        return None
    local_rows.sort(key=lambda row: str(row.get("recorded_at") or ""))
    return local_rows[-1]


def active_deep_execution_case_ids(jobs: list[Any] | None = None,
                                  cases: list[dict[str, Any]] | None = None) -> set[str]:
    """Return cases with a live durable Research execution lease.

    Persisted case status is objective/conversation state and does not imply a
    worker is currently using an execution slot. Slots are held by claimed or
    running durable Research jobs that carry an exact ``case_id`` in their
    governance context. Intake jobs without a case ID do not occupy a deep
    case slot; worker concurrency limits still bound those independently.
    """
    if jobs is None:
        from nexus_agent_platform.durable_jobs import default_store
        jobs = default_store().active()
    if cases is None:
        cases = _latest_cases()
    resumable_case_ids = {str(case.get("case_id")) for case in cases
        if case.get("case_schema_version") == "nexus.research-case.v1"
        and str(case.get("status") or "").upper() in ACTIVE_STATES
        and bool(case.get("continue_research", True))}
    result: set[str] = set()
    for job in jobs:
        get = job.get if isinstance(job, dict) else lambda key, default=None: getattr(job, key, default)
        state = str(get("state") or "").upper()
        department = str(get("department") or "").upper()
        if state not in ACTIVE_DEEP_JOB_STATES or department != "RESEARCH":
            continue
        context = get("governance_context", {}) or {}
        if isinstance(context, dict) and context.get("case_id"):
            case_id = str(context["case_id"])
            if case_id in resumable_case_ids:
                result.add(case_id)
    return result


class CurrentStateLookupUnavailable(RuntimeError):
    """Exact live case state could not be read without a history scan."""


def _emit_current_state_lookup_unavailable(case_id: str) -> dict[str, Any]:
    occurred = datetime.now(timezone.utc).isoformat()
    day = occurred[:10].replace("-", "")
    event_id = "sys_case_lookup_" + hashlib.sha256(f"{case_id}|{day}".encode()).hexdigest()[:20]
    event = {
        "schema_version": "nexus.recovery-event.v1", "event_id": event_id,
        "occurred_at": occurred, "objective_id": None, "project_id": None,
        "job_id": None, "case_id": str(case_id), "department": "RESEARCH",
        "job_type": "RESEARCH_STATE_LOOKUP", "failure_domain": "RESEARCH_STATE",
        "current_state": "CURRENT_STATE_UNAVAILABLE", "expected_state": "CASE_CONTROL_READABLE",
        "last_successful_transition": None, "failed_transition": "INDEXED_CASE_LOOKUP",
        "error_code": "CURRENT_STATE_LOOKUP_UNAVAILABLE",
        "error_summary": "Exact indexed Research case lookup unavailable; historical archive scan prohibited.",
        "attempt_count": 1, "recent_attempts": [],
        "available_capabilities": ["EXACT_INDEXED_CASE_LOOKUP", "STATE_REBUILD_FROM_ARCHIVE"],
        "authorized_actions": ["CREATE_SYSTEMS_RECOVERY_JOB", "ESCALATE_WITH_ACTIONABLE_DIAGNOSIS"],
        "prohibited_actions": ["FULL_ARCHIVE_SCAN_IN_LIVE_PATH", "TERMINATE_OBJECTIVE", "DELETE_HISTORY"],
        "cost_boundary": {"incremental_spend_authorized": False, "max_incremental_cost": 0},
        "evidence_references": ["research_case_id:" + str(case_id)],
        "relevant_self_knowledge": [], "objective_termination_authorized": False,
    }
    from nexus_agent_platform.stability_supervisor import route_recovery_event
    route_recovery_event(event)
    return event


def get_case_control(case_id: str) -> dict[str, Any] | None:
    """Read the compact fields needed for Systems case routing by exact ID."""
    if not case_id:
        return None
    try:
        return state_v2.lookup_case_control(str(case_id))
    except Exception as exc:
        failure_reason = type(exc).__name__
    try:
        event = _emit_current_state_lookup_unavailable(str(case_id))
    except Exception as exc:
        raise CurrentStateLookupUnavailable(
            f"CURRENT_STATE_LOOKUP_UNAVAILABLE; RECOVERY_EVENT_PERSIST_FAILED:{type(exc).__name__}") from exc
    raise CurrentStateLookupUnavailable(
        f"CURRENT_STATE_LOOKUP_UNAVAILABLE; reason={failure_reason}; event_id={event['event_id']}")


def claim_department_directive(case_id: str, directive_id: str, department: str, *,
                               worker_id: str, lease_seconds: int = 900) -> dict[str, Any]:
    """Atomically claim one OPEN case directive using its existing Supabase row."""
    import urllib.parse
    client = research_memory.supabase
    if client is None or not client.configured():
        return {"ok": False, "reason": "DURABLE_CASE_STORE_UNAVAILABLE"}
    case_key = urllib.parse.quote(case_id, safe="")
    status, rows = client.rest("GET", f"research_proactive_memory?memory_id=eq.{case_key}&select=memory_id,recorded_at,payload&limit=1")
    if status != 200 or not isinstance(rows, list) or not rows:
        return {"ok": False, "reason": "DURABLE_CASE_NOT_FOUND", "http_status": status}
    row = rows[0]
    case = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    request = next((item for item in case.get("department_requests", [])
                    if item.get("request_id") == directive_id), None)
    if not request:
        return {"ok": False, "reason": "DIRECTIVE_NOT_FOUND"}
    if str(request.get("department") or "").upper() != str(department).upper():
        return {"ok": False, "reason": "DEPARTMENT_OWNERSHIP_MISMATCH"}
    if str(request.get("status") or "").upper() != "OPEN":
        return {"ok": False, "reason": "DIRECTIVE_NOT_OPEN", "status": request.get("status")}
    now_dt = datetime.now(timezone.utc)
    lease_until = (now_dt + timedelta(seconds=max(60, min(int(lease_seconds), 3600)))).isoformat()
    claimed = copy.deepcopy(case)
    claimed_request = next(item for item in claimed["department_requests"] if item.get("request_id") == directive_id)
    claim = {"worker_id": worker_id, "claimed_at": now_dt.isoformat(), "lease_until": lease_until,
             "claim_method": "SUPABASE_RECORDED_AT_COMPARE_AND_SET"}
    claimed_request.update({"status": "IN_PROGRESS", "claim": claim, "claimed_at": now_dt.isoformat()})
    if isinstance(claimed_request.get("workflow_handoff"), dict):
        claimed_request["workflow_handoff"].update({"status": "IN_PROGRESS", "claim": claim})
    claimed.update({"current_owner": str(department).upper(), "current_directive": directive_id,
                    "directive_claim": {"directive_id": directive_id, **claim},
                    "case_event": "DEPARTMENT_DIRECTIVE_CLAIMED", "updated_at": now_dt.isoformat()})
    prior_recorded_at = str(row.get("recorded_at") or "")
    if not prior_recorded_at:
        return {"ok": False, "reason": "CASE_ROW_MISSING_CAS_VERSION"}
    query = (f"research_proactive_memory?memory_id=eq.{case_key}"
             f"&recorded_at=eq.{urllib.parse.quote(prior_recorded_at, safe='')}")
    durable_payload = {**claimed, "recorded_at": now_dt.isoformat(), "memory_id": case_id,
                       "memory_kind": "RESEARCH_CASE"}
    patch_status, echoed = client.rest("PATCH", query,
        body={"recorded_at": now_dt.isoformat(), "payload": durable_payload},
        prefer="return=representation")
    if patch_status not in {200, 204} or not isinstance(echoed, list) or len(echoed) != 1:
        return {"ok": False, "reason": "DIRECTIVE_CLAIM_RACE_OR_WRITE_FAILED", "http_status": patch_status}
    echoed_payload = echoed[0].get("payload") if isinstance(echoed[0], dict) else None
    echoed_request = next((item for item in (echoed_payload or {}).get("department_requests", [])
        if item.get("request_id") == directive_id), None) if isinstance(echoed_payload, dict) else None
    durable_claim_verified = bool(echoed_request
        and str(echoed_request.get("status") or "").upper() == "IN_PROGRESS"
        and str((echoed_request.get("claim") or {}).get("worker_id") or "") == worker_id)
    if not durable_claim_verified:
        return {"ok": False, "reason": "CLAIM_RESPONSE_DID_NOT_VERIFY_OWNER_AND_LEASE", "http_status": patch_status}
    saved = persist_state(durable_payload)
    # The existing Supabase CAS response is the durable write receipt. Local
    # mirror readback is useful observability, but cannot turn a confirmed
    # authoritative claim into a failed claim after the lease was written.
    return {"ok": True, "case": saved, "directive": claimed_request, "claim": claim,
            "durable_claim_verified": True,
            "local_mirror_verified": bool(saved.get("supabase_sync", {}).get("verified")),
            "reason": None}


def _directive_worker_liveness(worker_id: str) -> str:
    """Return ACTIVE only when a canonical kernel PID and command both match."""
    match = re.match(r"^continuous-kernel-(\d+)-cycle-", str(worker_id or ""))
    if not match:
        return "UNKNOWN"
    pid = int(match.group(1))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "DEAD"
    except PermissionError:
        return "UNKNOWN"
    try:
        proc = subprocess.run(["ps", "-p", str(pid), "-o", "command="], check=False,
            capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"
    command = (proc.stdout or "").strip()
    return "ACTIVE" if proc.returncode == 0 and "run_continuous_operating_kernel.py" in command else "UNKNOWN"


def recover_expired_department_directive(case_id: str, directive_id: str, *,
                                         now: datetime | None = None,
                                         unknown_worker_grace_seconds: int = 300) -> dict[str, Any]:
    """CAS-release a stale lease only after expiry and worker-death/stale proof.

    The same durable directive is reopened. Concurrent claim or result writes
    win through the recorded_at compare-and-set, preventing duplicate execution.
    """
    import urllib.parse
    client = research_memory.supabase
    if client is None or not client.configured():
        return {"ok": False, "reason": "DURABLE_CASE_STORE_UNAVAILABLE"}
    key = urllib.parse.quote(case_id, safe="")
    status, rows = client.rest("GET", f"research_proactive_memory?memory_id=eq.{key}&select=memory_id,recorded_at,payload&limit=1")
    if status != 200 or not isinstance(rows, list) or not rows:
        return {"ok": False, "reason": "DURABLE_CASE_NOT_FOUND", "http_status": status}
    stored = rows[0]
    case = stored.get("payload") if isinstance(stored.get("payload"), dict) else {}
    request = next((item for item in case.get("department_requests", [])
                    if item.get("request_id") == directive_id), None)
    if not request:
        return {"ok": False, "reason": "DIRECTIVE_NOT_FOUND"}
    current_status = str(request.get("status") or "").upper()
    if current_status not in {"IN_PROGRESS", "CLAIMED"}:
        return {"ok": False, "reason": "DIRECTIVE_NOT_LEASED", "status": current_status}
    claim = request.get("claim") or {}
    worker_id = str(claim.get("worker_id") or "")
    if not worker_id or request.get("result_id"):
        return {"ok": False, "reason": "CLAIM_MISSING_OR_RESULT_EXISTS"}
    try:
        lease_until = datetime.fromisoformat(str(claim.get("lease_until") or "").replace("Z", "+00:00"))
    except ValueError:
        return {"ok": False, "reason": "LEASE_TIMESTAMP_INVALID"}
    now_dt = now or datetime.now(timezone.utc)
    if lease_until.tzinfo is None:
        lease_until = lease_until.replace(tzinfo=timezone.utc)
    if lease_until > now_dt:
        return {"ok": False, "reason": "LEASE_NOT_EXPIRED", "lease_until": lease_until.isoformat()}
    liveness = _directive_worker_liveness(worker_id)
    expired_seconds = max(0.0, (now_dt - lease_until).total_seconds())
    if liveness == "ACTIVE":
        return {"ok": False, "reason": "WORKER_STILL_ACTIVE", "worker_id": worker_id}
    if liveness == "UNKNOWN" and expired_seconds < max(60, int(unknown_worker_grace_seconds)):
        return {"ok": False, "reason": "WORKER_STATUS_UNKNOWN_GRACE_PERIOD", "worker_id": worker_id}
    updated = copy.deepcopy(case)
    target = next(item for item in updated["department_requests"] if item.get("request_id") == directive_id)
    recovery = {"worker_id": worker_id, "worker_liveness": liveness,
        "old_lease_until": lease_until.isoformat(), "recovered_at": now_dt.isoformat(),
        "reason": "LEASE_EXPIRED_AND_WORKER_NOT_ACTIVE", "claim_recovery_method": "SUPABASE_RECORDED_AT_COMPARE_AND_SET"}
    target.update({"status": "OPEN", "claim": None, "claimed_at": None,
        "last_claim_recovery": recovery})
    if isinstance(target.get("workflow_handoff"), dict):
        target["workflow_handoff"].update({"status": "OPEN", "claim": None})
    if isinstance(updated.get("directive_claim"), dict) and updated["directive_claim"].get("directive_id") == directive_id:
        updated["directive_claim"] = None
    updated.update({"current_owner": str(request.get("department") or "RESEARCH").upper(),
        "current_directive": directive_id, "case_event": "EXPIRED_DIRECTIVE_LEASE_RECOVERED",
        "updated_at": now_dt.isoformat(), "status": "DEPARTMENT_DEVELOPMENT",
        "case_status": "DEPARTMENT_DEVELOPMENT", "continue_research": True,
        "next_action": str(request.get("requested_work") or "Resume the same expired Company Case directive.")})
    prior = str(stored.get("recorded_at") or "")
    if not prior:
        return {"ok": False, "reason": "CASE_ROW_MISSING_CAS_VERSION"}
    query = f"research_proactive_memory?memory_id=eq.{key}&recorded_at=eq.{urllib.parse.quote(prior, safe='')}"
    payload = {**updated, "recorded_at": now_dt.isoformat(), "memory_id": case_id,
        "memory_kind": "RESEARCH_CASE", "case_schema_version": "nexus.research-case.v1",
        "company_case_version": "nexus.company-case.v1"}
    patch_status, echoed = client.rest("PATCH", query, body={"recorded_at": payload["recorded_at"], "payload": payload},
        prefer="return=representation")
    if patch_status not in {200, 204} or not isinstance(echoed, list) or len(echoed) != 1:
        return {"ok": False, "reason": "LEASE_RECOVERY_CAS_RACE_OR_WRITE_FAILED", "http_status": patch_status}
    echo_case = echoed[0].get("payload") if isinstance(echoed[0], dict) else {}
    echo_request = next((item for item in (echo_case or {}).get("department_requests", [])
                         if item.get("request_id") == directive_id), None)
    if not echo_request or str(echo_request.get("status") or "").upper() != "OPEN":
        return {"ok": False, "reason": "LEASE_RECOVERY_DURABLE_ECHO_FAILED", "http_status": patch_status}
    persisted = persist_state(payload)
    return {"ok": True, "case_id": case_id, "directive_id": directive_id,
        "original_worker": worker_id, "worker_liveness": liveness,
        "lease_expired_at": lease_until.isoformat(), "status": "OPEN",
        "durable_cas_verified": True,
        "local_mirror_verified": bool(persisted.get("supabase_sync", {}).get("verified"))}


def release_failed_directive_claim(case_id: str, directive_id: str, worker_id: str,
                                   failure_class: str, failure_summary: str) -> dict[str, Any]:
    """Reopen the same directive after a verified pre-execution adapter failure.

    The owner, directive identity, and objective are preserved. This CAS repair
    is only allowed when the named worker owns an IN_PROGRESS claim and no
    result was returned, preventing duplicate execution after a completed task.
    """
    import urllib.parse
    client = research_memory.supabase
    if client is None or not client.configured():
        return {"ok": False, "reason": "DURABLE_CASE_STORE_UNAVAILABLE"}
    key = urllib.parse.quote(case_id, safe="")
    status, rows = client.rest("GET", f"research_proactive_memory?memory_id=eq.{key}&select=memory_id,recorded_at,payload&limit=1")
    if status != 200 or not isinstance(rows, list) or not rows:
        return {"ok": False, "reason": "DURABLE_CASE_NOT_FOUND", "http_status": status}
    stored = rows[0]
    case = stored.get("payload") if isinstance(stored.get("payload"), dict) else {}
    req = next((item for item in case.get("department_requests", [])
                if item.get("request_id") == directive_id), None)
    if not req or str(req.get("status") or "").upper() != "IN_PROGRESS":
        return {"ok": False, "reason": "DIRECTIVE_NOT_IN_PROGRESS"}
    claim = req.get("claim") or {}
    if str(claim.get("worker_id") or "") != str(worker_id) or req.get("result_id"):
        return {"ok": False, "reason": "CLAIM_OWNER_MISMATCH_OR_RESULT_EXISTS"}
    updated = copy.deepcopy(case)
    target = next(item for item in updated["department_requests"] if item.get("request_id") == directive_id)
    target.update({"status": "OPEN", "claim": None, "claimed_at": None,
        "last_claim_failure": {"worker_id": worker_id, "failure_class": failure_class,
            "summary": str(failure_summary)[:300], "recorded_at": _now()}})
    if isinstance(target.get("workflow_handoff"), dict):
        target["workflow_handoff"].update({"status": "OPEN", "claim": None})
    updated.update({"current_owner": str(req.get("department") or "SYSTEMS").upper(),
        "current_directive": directive_id, "case_event": "FAILED_CLAIM_RELEASED_FOR_RETRY",
        "updated_at": _now(), "status": "DEPARTMENT_DEVELOPMENT", "continue_research": True,
        "next_action": str(req.get("requested_work") or "Retry the same department directive after repairing its adapter.")})
    prior = str(stored.get("recorded_at") or "")
    query = f"research_proactive_memory?memory_id=eq.{key}&recorded_at=eq.{urllib.parse.quote(prior, safe='')}"
    payload = {**updated, "memory_id": case_id, "memory_kind": "RESEARCH_CASE",
        "case_schema_version": "nexus.research-case.v1", "company_case_version": "nexus.company-case.v1",
        "recorded_at": _now()}
    patch_status, echo = client.rest("PATCH", query, body={"recorded_at": payload["recorded_at"], "payload": payload},
        prefer="return=representation")
    if patch_status not in {200, 204} or not isinstance(echo, list) or len(echo) != 1:
        return {"ok": False, "reason": "CLAIM_RELEASE_CAS_FAILED", "http_status": patch_status}
    receipt = persist_state(payload)
    return {"ok": bool(receipt.get("supabase_sync", {}).get("verified")),
        "reason": None if receipt.get("supabase_sync", {}).get("verified") else "CLAIM_RELEASE_READBACK_UNVERIFIED",
        "case_id": case_id, "directive_id": directive_id, "status": "OPEN"}


def _save(case: dict[str, Any], event: str, **details: Any) -> dict[str, Any]:
    requested_status = str(details.get("status") or "").upper()
    if requested_status in {"COMPLETED", "PARKED", "FAILED", "FAILED_FINAL", "REJECTED",
            "REJECTED_WITH_EVIDENCE", "CANCELLED", "TERMINATED", "ABANDONED"}:
        from nexus_agent_platform.project_stop_policy import parent_stop_fallback, ray_stop_authorized
        actor = str(details.pop("actor", "NEXUS"))
        approval_id = details.pop("ray_approval_id", None)
        ray_decision = details.pop("ray_stop_decision", None)
        authorized = (requested_status not in {"COMPLETED", "PARKED", "FAILED"} and
            ray_stop_authorized(actor=actor, approval_id=approval_id, decision=ray_decision,
                                project_id=str(case.get("case_id") or "")))
        if not authorized:
            from nexus_agent_platform.company_workflow import _record_workflow_metric
            _record_workflow_metric("LEGACY_TERMINAL_INTERCEPTS", proposed_status=requested_status,
                                    case_id=str(case.get("case_id") or ""), actor=actor.upper())
            details.update(parent_stop_fallback(proposed_status=requested_status))
            details.update({"status": "REPLANNING",
                "next_research_action": "REASSESS_REJECTED_APPROACH_AND_ROUTE_NEXT_STEP",
                "next_department_action": "REASSESS_REJECTED_APPROACH_AND_ROUTE_NEXT_STEP",
                "next_action": f"Reassess the rejected {requested_status.lower()} approach, preserve the parent objective, and route the next evidence-backed action.",
                "continue_research": True})
    # Historical requests once embedded full copies of the prior request and
    # result arrays. Those snapshots recursively duplicated the authoritative
    # case history and made ordinary Supabase updates exceed the request
    # timeout. Keep canonical evidence once on the case and retain bounded,
    # traceable references in each request envelope.
    compacted_requests = []
    request_source = details.get("department_requests") or case.get("department_requests") or []
    for request in request_source:
        if not isinstance(request, dict):
            continue
        row = dict(request)
        snapshot = row.get("what_already_happened")
        if isinstance(snapshot, dict) and not snapshot.get("canonical_case_history_reference"):
            def refs(items: Any, fields: tuple[str, ...], limit: int = 80) -> dict[str, Any]:
                values = items if isinstance(items, list) else []
                compact = []
                for item in values[-limit:]:
                    if isinstance(item, dict):
                        compact.append({key: item.get(key) for key in fields if item.get(key) is not None})
                    else:
                        compact.append(str(item)[:240])
                return {"count": len(values), "items": compact}
            row["what_already_happened"] = {
                "canonical_case_history_reference": True,
                "sources": refs(snapshot.get("sources"), ("source_id", "id", "title", "url", "source_type")),
                "findings": refs(snapshot.get("findings"), ("finding_id", "summary", "claim", "evidence_level")),
                "syntheses": refs(snapshot.get("syntheses"), ("synthesis_id", "title", "summary", "recorded_at")),
                "hypotheses": refs(snapshot.get("hypotheses"), ("hypothesis_id", "statement", "status")),
                "notebook_answers": refs(snapshot.get("notebook_answers"), ("response_id", "question_type", "response_reference", "recorded_at")),
                "department_requests": refs(snapshot.get("department_requests"), ("request_id", "department", "status", "requested_work")),
                "department_results": refs(snapshot.get("department_results"), ("result_id", "department", "result_type", "completed_at")),
                "experiments": refs(snapshot.get("experiments"), ("experiment_id", "hypothesis", "status")),
            }
        compacted_requests.append(row)
    if compacted_requests:
        details["department_requests"] = compacted_requests
    updated_at = _now()
    updated = {**case, **details, "memory_kind": "RESEARCH_CASE", "case_event": event,
               "updated_at": updated_at, "case_schema_version": "nexus.research-case.v1"}
    # Backfill the compact notebook-reference contract on any case update so
    # a legacy full answer cannot be copied back into Supabase on the next save.
    compact_answers = []
    for answer_row in updated.get("notebook_answers") or []:
        if not isinstance(answer_row, dict):
            continue
        compact_answers.append({key: value for key, value in answer_row.items()
            if key not in {"answer", "prompt", "transcript", "full_transcript", "conversation"}})
    updated["notebook_answers"] = compact_answers
    updated.setdefault("company_case_version", "nexus.company-case.v1")
    updated.setdefault("case_type", updated.get("objective_family") or "OTHER")
    updated.setdefault("title", updated.get("objective") or updated.get("case_id"))
    updated.setdefault("parent_goal_id", updated.get("originating_goal_id"))
    updated.setdefault("case_selection_reason", updated.get("selection_reason"))
    updated.setdefault("originating_signal", None)
    updated.setdefault("expected_value", updated.get("expected_revenue_or_value"))
    updated.setdefault("why_now", None)
    updated.setdefault("success_criteria", ["Satisfy the objective-specific completion contract and create a decision-ready recommendation for Ray"])
    updated.setdefault("success_criteria_results", [])
    family = str(updated.get("objective_family") or "").upper()
    department_states = {"RESEARCH": "ACTIVE", "TRADING": "NOT_REQUIRED", "BUSINESS": "NOT_REQUIRED",
        "FINANCE": "NOT_REQUIRED", "SYSTEMS": "NOT_REQUIRED", "LABS": "NOT_REQUIRED",
        "MARKETING": "NOT_REQUIRED", "CREATIVE": "NOT_REQUIRED", "UPGRADE": "NOT_REQUIRED"}
    active_lane = {"TRADING_INTELLIGENCE": "TRADING", "BUSINESS_OPPORTUNITIES": "BUSINESS",
        "TECHNOLOGY_FOR_NEXUS": "UPGRADE", "SYSTEMS": "SYSTEMS"}.get(family)
    if active_lane:
        department_states[active_lane] = "ACTIVE"
    department_states.update(updated.get("department_states") or {})
    updated["department_states"] = department_states
    for field in ("department_results", "experiments", "experiment_results", "evidence", "department_requests"):
        updated.setdefault(field, [])
    updated.setdefault("ray_decision_status", "NOT_READY")
    updated.setdefault("last_owner_initiated_action", None)
    updated.setdefault("parent_objective", updated.get("objective"))
    updated.setdefault("current_approach_id", None)
    updated.setdefault("current_tool_or_provider", None)
    updated.setdefault("approaches", [])
    updated.setdefault("ray_question", None)
    updated.setdefault("business_plan", None)
    updated.setdefault("technical_plan", None)
    updated.setdefault("financial_analysis", None)
    updated.setdefault("marketing_plan", None)
    updated.setdefault("creative_plan", None)
    updated.setdefault("risk_analysis", [])
    updated.setdefault("expected_initial_cost", None)
    updated.setdefault("expected_operating_cost", None)
    updated.setdefault("expected_revenue_or_value", None)
    updated.setdefault("final_recommendation", None)
    updated.setdefault("recommendation_reason", None)
    updated.setdefault("recommendation_confidence", None)
    updated["research_state"] = department_states.get("RESEARCH", "NOT_REQUIRED")
    updated["trading_state"] = department_states.get("TRADING", "NOT_REQUIRED")
    updated["business_state"] = department_states.get("BUSINESS", "NOT_REQUIRED")
    updated["finance_state"] = department_states.get("FINANCE", "NOT_REQUIRED")
    updated["systems_state"] = department_states.get("SYSTEMS", "NOT_REQUIRED")
    updated["labs_state"] = department_states.get("LABS", "NOT_REQUIRED")
    updated["marketing_state"] = department_states.get("MARKETING", "NOT_REQUIRED")
    updated["creative_state"] = department_states.get("CREATIVE", "NOT_REQUIRED")
    updated["upgrade_state"] = department_states.get("UPGRADE", "NOT_REQUIRED")
    updated["case_status"] = updated.get("status")
    updated["current_phase"] = updated.get("status")
    updated["current_owner"] = updated.get("next_owner") or updated.get("owner_department")
    updated.setdefault("why_next", updated.get("next_action_reason"))
    try:
        from .company_case_contracts import CONTRACTS
        updated["completion_contract"] = CONTRACTS.get(family, CONTRACTS["OTHER"])
    except ImportError:
        pass
    if str(updated.get("status") or "").upper() in ACTIVE_STATES:
        next_action = (updated.get("next_research_action") or updated.get("next_department_action") or
                       updated.get("next_action") or "CONTINUE_CASE_RESEARCH")
        next_owner = updated.get("next_owner") or updated.get("owner_department") or "RESEARCH"
        next_action_id = updated.get("next_action_id") or "nxa_" + hashlib.sha256(
            f"{updated.get('case_id')}:{event}:{updated_at}:{next_action}".encode()).hexdigest()[:16]
        updated["next_research_action"] = next_action
        updated["next_action_id"] = next_action_id
        updated["next_owner"] = next_owner
        updated["continuation"] = {"current_objective": updated.get("objective"),
            "last_action": event, "last_result": details.get("result") or details.get("status") or event,
            "did_result_advance_objective": bool(details.get("advanced", event not in {"QUESTION_ADDED", "CASE_ENRICHED"})),
            "next_action": next_action, "next_owner": next_owner, "next_action_id": next_action_id}
    source_rows = updated.get("sources")
    if isinstance(source_rows, list):
        unique: dict[str, dict[str, Any]] = {}
        for source in source_rows:
            if not isinstance(source, dict):
                continue
            key = _source_identity(source) or str(source.get("source_id") or source.get("id") or "")
            if not key:
                continue
            prior = unique.get(key, {})
            # Keep the latest metadata while preserving non-empty extracted text.
            merged = {**prior, **source}
            for field in ("extracted_evidence", "extracted_text"):
                if not merged.get(field) and prior.get(field):
                    merged[field] = prior[field]
            unique[key] = merged
        updated["sources"] = list(unique.values())
        updated["source_count"] = len(unique)
        updated["source_class_count"] = len({str(row.get("source_class") or "UNKNOWN").upper()
            for row in unique.values() if str(row.get("source_class") or "UNKNOWN").upper()
            not in {"UNKNOWN", "UNCLASSIFIED"}})
    return persist_state(updated)


def promising_signal_gate(signal: dict[str, Any]) -> dict[str, Any]:
    """A transparent admission gate; incomplete evidence can still be promising."""
    factors = {
        "relevance": float(signal.get("relevance", 0) or 0),
        "novelty": float(signal.get("novelty", 0) or 0),
        "customer_problem_evidence": float(signal.get("customer_problem_evidence", 0) or 0),
        "strategic_fit": float(signal.get("strategic_fit", 0) or 0),
        "potential_value": float(signal.get("potential_value", 0) or 0),
        "testability": float(signal.get("testability", 0) or 0),
        "evidence_path_available": float(signal.get("evidence_path_available", 0) or 0),
    }
    score = round(sum(factors.values()) / len(factors), 3)
    if score >= .78:
        classification = "HIGH_PRIORITY"
    elif score >= .55:
        classification = "PROMISING"
    elif score >= .30:
        classification = "REFERENCE_ONLY"
    else:
        classification = "LOW_VALUE"
    return {"classification": classification, "promise_score": score, "factors": factors,
            "admit_case": classification in {"PROMISING", "HIGH_PRIORITY"},
            "incomplete_evidence_is_not_rejection": True}


def open_or_join_case(*, objective: str, objective_family: str, business_or_nexus_goal: str,
                      owner_department: str, primary_question: str, priority: int = 50,
                      signal: dict[str, Any] | None = None, case_id: str | None = None,
                      project_id: str | None = None, objective_id: str | None = None,
                      originating_goal_id: str | None = None, requires_ray: bool = False,
                      depth_budget: dict[str, int] | None = None, force_existing: bool = False) -> dict[str, Any]:
    try:
        from .notebook_playbooks import select_playbook
    except ImportError:
        from notebook_playbooks import select_playbook
    selected_playbook = select_playbook(objective_family=objective_family,
        owner_department=owner_department, current_goal=business_or_nexus_goal,
        case_context=objective + " " + primary_question)
    playbook_binding = {"playbook_id": selected_playbook["playbook_id"],
        "case_type": selected_playbook["case_type"], "version": selected_playbook["version"],
        "selection_reason": selected_playbook["selection_reason"], "selected_at": _now()}
    gate = promising_signal_gate(signal or {"relevance": 1, "novelty": 1, "strategic_fit": 1,
                                            "potential_value": 1, "testability": 1,
                                            "evidence_path_available": 1})
    if not gate["admit_case"] and not case_id and not force_existing:
        return {"opened": False, "gate": gate, "reason": "SIGNAL_BELOW_PROMISING_GATE"}
    objective_key = hashlib.sha256("|".join((_norm(objective_family), _norm(objective),
                                             _norm(business_or_nexus_goal))).encode()).hexdigest()[:24]
    if case_id:
        existing = get_case(case_id)
        cases = [existing] if existing else []
    else:
        cases = _latest_cases(include_full_payload=False)
        existing = next((row for row in cases if row.get("objective_key") == objective_key
                         and str(row.get("status") or "").upper() in ACTIVE_STATES), None)
    if existing:
        if not existing.get("primary_question") or not existing.get("case_schema_version"):
            existing = get_case(str(existing.get("case_id") or ""))
        if not existing:
            return {"opened": False, "joined": False, "gate": gate,
                    "reason": "EXACT_EXISTING_RESEARCH_CASE_UNAVAILABLE"}
        existing_project = str(existing.get("project_id") or "")
        if project_id and existing_project and existing_project != str(project_id):
            return {"opened": False, "joined": False, "gate": gate,
                "reason": "RESEARCH_CASE_PROJECT_LINEAGE_CONFLICT"}
        existing_objective = str(existing.get("objective_id") or existing.get("originating_goal_id") or "")
        requested_objective = str(objective_id or originating_goal_id or "")
        if requested_objective and existing_objective and existing_objective != requested_objective:
            return {"opened": False, "joined": False, "gate": gate,
                "reason": "RESEARCH_CASE_OBJECTIVE_LINEAGE_CONFLICT"}
        if case_id:
            used = {**{k: 0 for k in DEFAULT_DEPTH_BUDGET}, **(existing.get("depth_used") or {})}
            budget = {**DEFAULT_DEPTH_BUDGET, **(existing.get("depth_budget") or {}), **(depth_budget or {})}
            status = str(existing.get("status") or "PROMISING").upper()
            if status not in CASE_STATES:
                status = "DEPARTMENT_DEVELOPMENT" if existing.get("handoff_ids") else "PROMISING"
            normalized = _save(existing, "LEGACY_CASE_UPGRADED", status=status,
                           objective_key=objective_key,
                           objective_family=objective_family, business_or_nexus_goal=business_or_nexus_goal,
                           development_profile=existing.get("development_profile") or _development_profile(objective_family),
                           owner_department=owner_department, primary_question=primary_question,
                           open_questions=list(existing.get("open_questions") or []),
                           answered_questions=list(existing.get("answered_questions") or []),
                           findings=list(existing.get("findings") or []),
                           hypotheses=list(existing.get("hypotheses") or []),
                           recommendations=list(existing.get("recommendations") or []),
                           missing_information=list(existing.get("missing_information") or []),
                           department_requests=list(existing.get("department_requests") or []),
                           experiment_requests=list(existing.get("experiment_requests") or []),
                           depth_budget=budget, depth_used=used,
                           continue_research=bool(existing.get("continue_research", True)),
                           promise_score=max(float(existing.get("promise_score", 0) or 0), gate["promise_score"]),
                           requires_ray=requires_ray or bool(existing.get("requires_ray")),
                           project_id=project_id or existing_project or None,
                           objective_id=objective_id or existing_objective or None,
                           originating_goal_id=originating_goal_id or existing.get("originating_goal_id"),
                           notebook_playbook=existing.get("notebook_playbook") or playbook_binding)
            merged = _save(normalized, "CASE_ENRICHED", objective=objective,
                           primary_question=primary_question)
            return {"opened": False, "joined": True, "case": merged, "gate": gate}
        if (project_id and not existing_project) or (requested_objective and not existing_objective):
            existing = _save(existing, "CASE_LINEAGE_BOUND",
                project_id=project_id or None, objective_id=objective_id or originating_goal_id or None,
                originating_goal_id=originating_goal_id or existing.get("originating_goal_id"))
        if not existing.get("notebook_playbook"):
            existing = _save(existing, "NOTEBOOK_PLAYBOOK_SELECTED", notebook_playbook=playbook_binding)
        return {"opened": False, "joined": True, "case": existing, "gate": gate}
    # A persisted nonterminal objective is resumable work, not an execution
    # slot. Only a currently claimed/running durable Research job linked to an
    # exact case consumes bounded deep-execution capacity.
    try:
        active_case_ids = active_deep_execution_case_ids(cases=cases)
    except Exception:
        return {"opened": False, "gate": gate, "reason": "ACTIVE_EXECUTION_CAPACITY_UNAVAILABLE",
                "wait_for_capacity": True, "retryable": True, "objective_terminated": False}
    # An explicit Ray/user request to recover an existing durable NotebookLM
    # case may exceed ordinary proactive deep-case concurrency. This is a
    # bounded exception for requested work, not a selector-wide cap increase.
    if len(active_case_ids) >= MAX_ACTIVE_DEEP_CASES and not force_existing:
        return {"opened": False, "gate": gate, "reason": "MAX_ACTIVE_DEEP_CASES_REACHED",
                "active_case_ids": sorted(active_case_ids), "wait_for_capacity": True,
                "retryable": True, "objective_terminated": False}
    created = _now()
    cid = case_id or "rcase_" + objective_key[:18]
    question = {"question_id": "q_" + hashlib.sha256(f"{cid}:{primary_question}".encode()).hexdigest()[:16],
                "question": primary_question, "why_it_matters": "Primary question for resolving this objective.",
                "best_source_classes": [], "answer_status": "OPEN", "answer": None}
    case = {"case_id": cid, "case_schema_version": "nexus.company-case.v1",
            "case_type": selected_playbook.get("case_type") or objective_family,
            "objective_key": objective_key, "objective": objective,
            "success_criteria": [f"Resolve the primary objective question: {primary_question}",
                "Satisfy the case-type completion contract and produce a decision-ready recommendation for Ray"],
            "objective_family": objective_family, "business_or_nexus_goal": business_or_nexus_goal,
            "owner_department": owner_department, "status": "PROMISING", "priority": int(priority),
            "promise_score": gate["promise_score"], "created_at": created, "updated_at": created,
            "primary_question": primary_question, "open_questions": [question], "answered_questions": [],
            "source_ids": [], "sources": [], "source_count": 0, "source_class_count": 0,
            "findings": [], "hypotheses": [], "recommendations": [], "missing_information": [],
            "department_states": {"RESEARCH": "ACTIVE", "TRADING": "NOT_REQUIRED", "BUSINESS": "NOT_REQUIRED",
                "FINANCE": "NOT_REQUIRED", "SYSTEMS": "NOT_REQUIRED", "LABS": "NOT_REQUIRED",
                "MARKETING": "NOT_REQUIRED", "CREATIVE": "NOT_REQUIRED", "UPGRADE": "NOT_REQUIRED"},
            "department_results": [], "experiments": [], "experiment_results": [], "evidence": [],
            "ray_decision_status": "NOT_READY", "final_recommendation": None,
            "last_case_advancement_trigger": "CODEX", "last_owner_initiated_action": None,
            "department_requests": [], "experiment_requests": [], "next_research_action": "RESEARCH_PRIMARY_QUESTION",
            "development_profile": _development_profile(objective_family),
            "next_department_action": None, "continue_research": True, "requires_ray": bool(requires_ray),
            "originating_goal_id": originating_goal_id,
            "objective_id": objective_id or originating_goal_id,
            "project_id": project_id,
            "depth_budget": {**DEFAULT_DEPTH_BUDGET, **(depth_budget or {})},
            "depth_used": {k: 0 for k in DEFAULT_DEPTH_BUDGET}, "selection_reason": gate,
            "notebook_playbook": playbook_binding,
            "final_decision": None, "memory_kind": "RESEARCH_CASE",
            "case_schema_version": "nexus.research-case.v1", "company_case_version": "nexus.company-case.v1"}
    saved = persist_state(case)
    return {"opened": True, "joined": False, "case": saved, "gate": gate}


def _add_unique(rows: list[dict[str, Any]], row: dict[str, Any], identity: str) -> list[dict[str, Any]]:
    new = [x for x in rows if str(x.get("identity") or x.get(identity) or "") != str(row.get("identity") or row.get(identity) or "")]
    new.append(row)
    return new


def _source_identity(source: dict[str, Any]) -> str:
    url = str(source.get("url") or source.get("source_url") or "").strip()
    if url:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().removeprefix("www.")
        path = parts.path.rstrip("/")
        query = ""
        if host in {"youtube.com", "m.youtube.com"}:
            from urllib.parse import parse_qs
            video = (parse_qs(parts.query).get("v") or [""])[0]
            if video:
                return "youtube:" + video
        return urlunsplit((parts.scheme.lower(), host, path, query, ""))
    return str(source.get("source_id") or source.get("id") or "")


def add_source(case_id: str, source: dict[str, Any]) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    url = str(source.get("url") or source.get("source_url") or "")
    sid = str(source.get("source_id") or source.get("id") or url)
    identity = str(source.get("identity") or _source_identity(source) or sid or url)
    item = {**source, "identity": identity, "source_id": sid or None,
            "added_at": source.get("added_at") or _now()}
    prior_sources = list(case.get("sources") or [])
    source_identity = _source_identity(item)
    sources = [row for row in prior_sources if _source_identity(row) != source_identity
               and str(row.get("source_id") or "") != sid]
    sources.append(item)
    classes = {str(row.get("source_class") or "UNKNOWN").upper() for row in sources
               if str(row.get("source_class") or "UNKNOWN").upper() not in {"UNKNOWN", "UNCLASSIFIED"}}
    saved = _save(case, "SOURCE_ATTACHED", sources=sources,
                  source_ids=sorted({str(row.get("source_id")) for row in sources if row.get("source_id")}),
                  source_count=len(sources), source_class_count=len(classes))
    return {"ok": True, "case": saved, "source": item, "is_new": len(sources) > len(case.get("sources") or [])}


def bind_notebook_workspace(case_id: str, notebook: dict[str, Any]) -> dict[str, Any]:
    """Attach one bounded NotebookLM workspace to the objective case."""
    case = get_case(case_id)
    if not case or not notebook.get("notebook_id"):
        return {"ok": False, "reason": "CASE_OR_NOTEBOOK_ID_MISSING"}
    return {"ok": True, "case": _save(case, "NOTEBOOK_WORKSPACE_BOUND",
        notebook_workspace={"notebook_id": str(notebook["notebook_id"]),
            "title": str(notebook.get("title") or ""), "max_sources": max(1, min(int(notebook.get("max_sources") or 5), 5)),
            "created": bool(notebook.get("created")), "bound_at": _now()})}


def record_notebook_answer(case_id: str, *, question_type: str, answer: str,
                           notebook_id: str, source_ids: list[str] | None = None,
                           conversation_id: str | None = None,
                           submission_attempted: bool = False,
                           submission_confirmed: bool = False,
                           response_reference: str | None = None,
                           prompt: str = "", response_id: str | None = None,
                           key_findings: list[str] | None = None,
                           recommendations: list[str] | None = None,
                           open_questions: list[str] | None = None,
                           next_source_classes: list[str] | None = None,
                           next_action: str = "",
                           question_origin: str | None = None,
                           extracted_findings: list[dict[str, Any]] | None = None,
                           downstream_directive_id: str | None = None) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    answers = list(case.get("notebook_answers") or [])
    # The notebook is the evidence corpus. Preserve the raw exchange in a
    # local artifact and sync only its compact reference into case/Supabase
    # state; never mirror complete NotebookLM prompts or answers there.
    response = str(answer or "")
    response_id = response_id or response_reference or "answer_" + hashlib.sha256(
        f"{case_id}:{notebook_id}:{question_type}:{_now()}".encode()).hexdigest()[:20]
    from nexus_agent_platform.runtime.paths import nexus_research_state_path
    artifact_dir = nexus_research_state_path("runtime", "notebook_answer_artifacts",
        re.sub(r"[^A-Za-z0-9_.-]", "_", case_id)[:100])
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', str(response_id))[:100]}.json"
    artifact_path.write_text(json.dumps({"case_id": case_id, "question_type": question_type,
        "notebook_id": notebook_id, "prompt": prompt, "answer": response,
        "response_hash": hashlib.sha256(response.encode()).hexdigest(),
        "recorded_at": _now()}, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    compact_findings = [{k: str(v)[:500] for k, v in row.items() if isinstance(v, (str, int, float, bool))}
                        for row in (extracted_findings or [])[:20] if isinstance(row, dict)]
    answers.append({"question_type": str(question_type)[:120],
        "notebook_id": notebook_id, "source_ids": source_ids or [],
        "conversation_id": conversation_id, "submission_attempted": bool(submission_attempted),
        "submission_confirmed": bool(submission_confirmed),
        "response_received": bool(answer), "response_persisted": True,
        "response_id": response_id,
        "response_reference": response_reference,
        "response_hash": hashlib.sha256(response.encode()).hexdigest(),
        "prompt_hash": hashlib.sha256(str(prompt).encode()).hexdigest(),
        "local_artifact_ref": str(artifact_path.relative_to(ROOT)),
        "response_character_count": len(response),
        "source_set": list(source_ids or []), "key_findings": list(key_findings or []),
        "recommendations": [str(x)[:500] for x in (recommendations or [])[:20]],
        "open_questions": [str(x)[:500] for x in (open_questions or [])[:40]],
        "next_source_classes": list(next_source_classes or [])[:30], "next_action": str(next_action)[:500],
        "question_origin": str(question_origin or "UNSPECIFIED").upper(),
        "extracted_findings": compact_findings,
        "downstream_directive_id": downstream_directive_id,
        "recorded_at": _now()})
    return {"ok": True, "case": _save(case, "NOTEBOOK_ANSWER_RECORDED", notebook_answers=answers)}


def _select_autonomous_notebook_followup(case: dict[str, Any]) -> dict[str, Any] | None:
    """Select consequential unanswered work from case evidence, without a caller-supplied question."""
    workspace = case.get("notebook_workspace") or {}
    notebook_id = str(workspace.get("notebook_id") or case.get("notebook_id") or "")
    if not notebook_id:
        return None
    budget = case.get("depth_budget") or DEFAULT_DEPTH_BUDGET
    used = case.get("depth_used") or {}
    if int(used.get("followup_questions", 0)) >= int(budget.get("max_followup_questions", 10)):
        return None
    answers = list(case.get("notebook_answers") or [])
    followups = list(case.get("notebook_followup_cycles") or [])
    latest_answer = answers[-1] if answers else {}
    latest_answer_text = str(latest_answer.get("answer") or "").casefold()
    prompts = [str(row.get("prompt") or "").casefold() for row in answers]
    candidates: list[dict[str, Any]] = []
    # Result-generated questions have priority because they reflect new Nexus
    # evidence. Search newest results first, then their listed order.
    for result in reversed(list(case.get("department_results") or [])):
        for question in result.get("new_questions") or []:
            text = " ".join(str(question or "").split()).strip()
            if text:
                candidates.append({"issue": text, "result_id": result.get("result_id"),
                                   "department": result.get("department"),
                                   "result_summary": str(result.get("result") or "")[:1600],
                                   "result_what_was_learned": str(result.get("what_was_learned") or "")[:1200]})
    seen: set[str] = set()
    for candidate in candidates:
        normalized = _norm(candidate["issue"])
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if any(row.get("issue_hash") == hashlib.sha256(normalized.encode()).hexdigest()
               for row in followups):
            continue
        # Avoid asking again when the same issue is already in an earlier
        # prompt, or the latest NotebookLM response explicitly resolved it.
        prompt_tokens = set(normalized.split())
        # A prior prompt can contain several questions that NotebookLM did not
        # answer. Suppress a repeat only when the response itself covered the
        # material issue; an unanswered embedded question remains eligible for
        # one bounded clarification, then its issue hash prevents a loop.
        stopwords = {"which", "what", "does", "this", "that", "with", "from", "into", "about",
                     "whether", "could", "would", "should", "using", "after", "before", "there", "their",
                     "they", "them", "been", "have", "were", "will", "your", "case", "result", "current"}
        decisive_terms = [token for token in prompt_tokens if len(token) > 3 and token not in stopwords]
        resolved = bool(decisive_terms) and sum(token in latest_answer_text for token in decisive_terms) / len(decisive_terms) >= 0.66
        if resolved:
            continue
        # Question relevance is already established by being a department's
        # returned open issue. Prefer issues that can change source, strategy,
        # or test selection; avoid asking when a currently executable test is
        # a more direct answer.
        issue = candidate["issue"].casefold()
        if any(term in issue for term in ("signal parity", "reconstructed", "reconstruct")):
            question_type = "DATA_FIDELITY"
            action_if_unresolved = "DATA_FIDELITY_CHECK"
        elif any(term in issue for term in ("contradict", "claim", "reported", "author")):
            question_type = "SOURCE_CLAIM_VERIFICATION"
            action_if_unresolved = "NEW_SOURCE_REQUEST"
        elif any(term in issue for term in ("instrument", "timeframe", "market")):
            question_type = "INSTRUMENT_SELECTION"
            action_if_unresolved = "TRADING_EXPERIMENT"
        elif any(term in issue for term in ("volume", "data", "oanda", "webull")):
            question_type = "DATA_FIDELITY"
            action_if_unresolved = "DATA_FIDELITY_CHECK"
        elif any(term in issue for term in ("exit", "target", "stop", "risk", "ema", "filter", "winner", "losing trade", "performance changed")):
            question_type = "STRATEGY_IMPROVEMENT"
            action_if_unresolved = "STRATEGY_MODIFICATION_TEST"
        else:
            question_type = "FAILURE_ANALYSIS"
            action_if_unresolved = "ANOTHER_NOTEBOOK_QUESTION"
        # A research question is not useful if the case already has a capable,
        # executable experiment for the same unresolved variable.
        plan_text = json.dumps(case.get("trading_development_plan") or [], sort_keys=True).casefold()
        issue_terms = [token for token in prompt_tokens if len(token) > 5]
        test_can_answer = bool(issue_terms) and sum(token in plan_text for token in issue_terms) / len(issue_terms) >= 0.7
        # A test cannot answer an interpretation question about evidence that
        # has already been collected. In particular, comparing an out-of-window
        # result with the prior window is a Research/Notebook synthesis task;
        # using plan keyword overlap here previously suppressed that follow-up
        # and sent the stale primary question to Hermes instead.
        if (candidate.get("department") == "MERCURY_TRADING"
                and any(term in normalized for term in ("compare", "comparison", "window", "sample size", "regimes"))):
            test_can_answer = False
        return {**candidate, "issue_hash": hashlib.sha256(normalized.encode()).hexdigest(),
                "question_type": question_type, "action_if_unresolved": action_if_unresolved,
                "decision_relevant": True, "answer_could_change_next_action": True,
                "information_already_present": False, "test_can_answer_more_effectively": test_can_answer,
                "expected_information_gain": (candidate.get("expected_information_gain") or
                    ("Explain the treatment's trade-level effect and determine whether source-supported filters address the observed failure mode before selecting another modification." if question_type == "STRATEGY_IMPROVEMENT" else
                     "Resolve whether source-code signal lifecycle can be reproduced from currently available case data before selecting another strategy/data experiment."))}
    return None


def _parse_followup_payload(answer: str) -> dict[str, Any]:
    text = str(answer or "").strip()
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.I)
    candidate = match.group(1) if match else text
    if not match:
        start = candidate.find("{")
        if start >= 0:
            try:
                payload, _ = json.JSONDecoder().raw_decode(candidate[start:])
                return payload if isinstance(payload, dict) else {}
            except (TypeError, ValueError):
                pass
    try:
        payload = json.loads(candidate)
        return payload if isinstance(payload, dict) else {}
    except (TypeError, ValueError):
        return {}


def _run_autonomous_notebook_followup(case: dict[str, Any]) -> dict[str, Any] | None:
    """Normal Research continuation: select, ask, extract, persist, and route one notebook follow-up."""
    selected = _select_autonomous_notebook_followup(case)
    if not selected:
        return None
    # Do not ask the NotebookLM question if a deterministic test already
    # answers the issue more directly. Leave it on the normal case queue.
    if selected.get("test_can_answer_more_effectively"):
        return None
    notebook_id = str((case.get("notebook_workspace") or {}).get("notebook_id") or case.get("notebook_id"))
    latest_result = selected
    # Research composes the exact question at runtime from the selected case
    # issue and newest result. Codex and callers do not supply question text.
    issue_context = (
        f"For the active Nexus Wick case {case.get('case_id')}, Research selected this unresolved, decision-relevant issue from "
        f"{latest_result.get('department') or 'case'} result {latest_result.get('result_id')}: {latest_result['issue']} "
        f"The result context is: {latest_result.get('result_summary') or latest_result.get('result_what_was_learned')}. "
    )
    if selected.get("question_type") == "STRATEGY_IMPROVEMENT":
        generated_question = issue_context + (
            "Using only evidence and recommendations already represented in this notebook, explain why the treatment changed results, "
            "which failure mode the treatment was intended to address, whether the trade-level evidence shows it addressed that mode, "
            "and what differentiates retained and filtered winning/losing trades. Identify source-supported context filters or indicators "
            "that match those observed failure characteristics, if any. Rank candidates by source support, fit to observed failure, "
            "expected information gain, cost, and overfitting risk. Separate source evidence from hypotheses; do not invent combinations. "
            "State what remains unproven and what evidence would most change the next action."
        )
    else:
        generated_question = issue_context + (
            "Using the source code, video, and documentation already in this notebook, determine what is established, what remains unverified, "
            "and whether this issue can be resolved from current notebook evidence. Give source references. If the source evidence is insufficient, "
            "name the exact evidence needed. Explain whether resolving it would change the next company-case action."
        )
    case_context = {
        "case_id": case.get("case_id"), "objective": case.get("objective"),
        "status": case.get("status"), "current_phase": case.get("current_phase"),
        "latest_experiment_result": latest_result.get("result_summary"),
        "latest_learning": latest_result.get("result_what_was_learned"),
        "question_type": selected["question_type"], "selected_issue": selected["issue"],
    }
    notebook_prompt = (
        "This is a Research-owner follow-up for a live company case. Do not restate the whole prior synthesis. "
        "Answer the generated case question, distinguish source facts from claims and Nexus assumptions, and return a concise JSON object "
        "with keys: material_findings (array of objects with item_type, content_summary, source_support, limitation), "
        "resolution (ANSWERED/PARTIALLY_ANSWERED/UNANSWERED/CONTRADICTORY), "
        "followup_result_action_type (NEW_SOURCE_REQUEST/TRADING_EXPERIMENT/DATA_FIDELITY_CHECK/STRATEGY_MODIFICATION_TEST/ROBUSTNESS_TEST/NO_ACTION_SUFFICIENTLY_RESOLVED/ANOTHER_NOTEBOOK_QUESTION/DEPARTMENT_REQUEST), "
        "what_to_do, why, inputs, existing_capabilities, configuration, expected_output, return_path, next_step_after_result, next_owner. "
        "Do not invent sources or strategy rules. If further work is not warranted, say NO_ACTION_SUFFICIENTLY_RESOLVED and explain.\n\n"
        f"RESEARCH_GENERATED_QUESTION:\n{generated_question}\n\nCASE_CONTEXT_JSON:\n{json.dumps(case_context, ensure_ascii=False)}"
    )
    try:
        try:
            from .notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter
        except ImportError:
            from notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter
        receipt = None
        source_rows = []
        provider_attempts = list(case.get("provider_attempts") or [])
        prior_nb_failures = sum(1 for row in provider_attempts
            if row.get("provider") == "NOTEBOOKLM_PYTHON_CLI"
            and row.get("selected_issue_hash") == selected["issue_hash"])
        for attempt_number in range(1, 3):
            adapter = NotebookLMResearchAdapter(AdapterConfig(profile="default"))
            try:
                with adapter._job_slot():
                    receipt = adapter.ask_notebook(notebook_id, notebook_prompt)
                    source_rows = adapter.sources(notebook_id)
                break
            except Exception as exc:
                failure = {"attempt_id": "npa_" + hashlib.sha256(
                        f"{case.get('case_id')}:{notebook_id}:{selected['issue_hash']}:{prior_nb_failures + attempt_number}".encode()).hexdigest()[:18],
                    "provider": "NOTEBOOKLM_PYTHON_CLI", "path": "NotebookLMResearchAdapter.ask_notebook",
                    "case_id": case.get("case_id"), "notebook_id": notebook_id,
                    "selected_issue_hash": selected["issue_hash"], "failure_class": type(exc).__name__,
                    "repair_used": "ONE_BOUNDED_RETRY_THROUGH_EXISTING_AUTHENTICATED_CLI" if attempt_number == 2 else "NONE",
                    "fallback_used": False, "result": "RETRYABLE_PROVIDER_FAILURE", "recorded_at": _now()}
                provider_attempts.append(failure)
                _save(get_case(case["case_id"]) or case, "NOTEBOOKLM_FOLLOWUP_PROVIDER_ATTEMPT",
                    provider_attempts=provider_attempts, last_provider_failure=failure,
                    current_owner="RESEARCH", next_owner="RESEARCH",
                    next_action="Retry the same NotebookLM interpretation through the normal Research runtime; keep the Company Case active.")
                if attempt_number < 2:
                    continue
                if prior_nb_failures + attempt_number >= 2:
                    try:
                        from nexus_agent_platform.governed import persistence as governed
                        incident_key = f"research-provider:{case.get('case_id')}:NOTEBOOKLM_CLI_UNAVAILABLE"
                        prior = next((row for row in reversed(governed.read_records("systems_incidents"))
                            if row.get("incident_key") == incident_key and str(row.get("status") or "OPEN").upper() == "OPEN"), None)
                        governed.append_record("systems_incidents", {**(prior or {}),
                            "incident_id": (prior or {}).get("incident_id") or governed.new_id("sysinc"),
                            "incident_key": incident_key, "incident_type": "RESEARCH_PROVIDER_FAILURE",
                            "status": "OPEN", "owner": "SYSTEMS", "affected_case": case.get("case_id"),
                            "affected_workflow": "SAME_CASE_NOTEBOOKLM_REASSESSMENT",
                            "last_known_good": "Authenticated local NotebookLM Python CLI was the configured production route; previous inventory succeeded.",
                            "failure_class": type(exc).__name__, "auto_repair_attempt": "ONE_BOUNDED_CLI_RETRY",
                            "result": "NotebookLM follow-up did not return; parent case preserved.",
                            "next_action": "Inspect authenticated CLI/session health and restore the existing NotebookLM route without changing the bound case notebook.",
                            "detected_by": "RESEARCH_CASE_ENGINE", "recorded_at": _now()})
                    except Exception:
                        pass
                    request_department_work(case["case_id"], department="SYSTEMS",
                        requested_work="Repair the existing local NotebookLM authenticated Python CLI/session path after two bounded failures; inspect lock/process/auth/session health without rotating credentials or changing the Wick notebook binding.",
                        why_this_department="Research selected a material Wick result follow-up for the bound notebook, but the existing NotebookLM CLI failed twice. The parent case remains active and needs a safe provider health/repair check.",
                        expected_output="Redacted CLI path/version/auth/session health, bounded repair attempted, retry result, and same-notebook response reference if restored.",
                        what_happens_after_output="Return to Research on the same Wick case; retry the selected NotebookLM interpretation once the existing path is healthy.",
                        trigger="PROVIDER_FAILURE", from_department="RESEARCH", return_to="RESEARCH",
                        questions_to_answer=["Why does the existing authenticated NotebookLM CLI fail or time out on this same bound notebook, and can its current session/lock path be safely restored?"],
                        cost_or_resource_implication={"cash_cost":0,"uses_existing_provider":True})
                return {"status": "NOTEBOOK_FOLLOWUP_DEFERRED", "case_id": case.get("case_id"),
                    "selected_issue": selected["issue"], "failure_mode": type(exc).__name__,
                    "retryable": True, "provider_attempt": failure}
    except Exception as exc:
        return {"status": "NOTEBOOK_FOLLOWUP_DEFERRED", "case_id": case.get("case_id"),
                "selected_issue": selected["issue"], "failure_mode": type(exc).__name__,
                "retryable": True, "normal_runtime_path": "research_case_engine.continue_case_once"}
    answer = str(receipt.get("answer") or "")
    if not answer:
        return {"status": "NOTEBOOK_FOLLOWUP_NO_RESPONSE", "case_id": case.get("case_id"),
                "selected_issue": selected["issue"]}
    recovery_receipt = {"attempt_id": "npa_" + hashlib.sha256(
            f"{case.get('case_id')}:{notebook_id}:{selected['issue_hash']}:recovered".encode()).hexdigest()[:18],
        "provider": "NOTEBOOKLM_PYTHON_CLI", "path": "NotebookLMResearchAdapter.ask_notebook",
        "case_id": case.get("case_id"), "notebook_id": notebook_id,
        "selected_issue_hash": selected["issue_hash"],
        "failure_class": "RECOVERED_AFTER_REMOTE_CONTEXT_LENGTH_EXCEEDED",
        "repair_used": "BOUNDED_CASE_CONTEXT_AND_EXISTING_NOTEBOOKLM_CLI_FALLBACK",
        "fallback_used": True, "final_provider": "NOTEBOOKLM_PYTHON_CLI",
        "result": "NOTEBOOK_RESPONSE_RECEIVED", "response_reference": receipt.get("response_reference"),
        "recorded_at": _now()}
    provider_attempts = list((get_case(case["case_id"]) or case).get("provider_attempts") or [])
    if not any(row.get("attempt_id") == recovery_receipt["attempt_id"] for row in provider_attempts):
        provider_attempts.append(recovery_receipt)
    parsed = _parse_followup_payload(answer)
    findings = parsed.get("material_findings") if isinstance(parsed.get("material_findings"), list) else []
    if not findings:
        findings = [{"item_type": "NOTEBOOK_SYNTHESIS", "content_summary": answer[:2400],
                     "source_support": "NotebookLM answer; references recorded with response", "limitation": "No structured JSON findings were returned."}]
    source_ids = [str(row.get("id")) for row in source_rows if row.get("id")]
    foreign_refs = [str(row.get("source_id")) for row in receipt.get("references") or []
                    if row.get("source_id") and str(row.get("source_id")) not in set(source_ids)]
    if foreign_refs:
        return {"status": "NOTEBOOK_FOLLOWUP_SOURCE_CONTAMINATION", "case_id": case.get("case_id"),
                "foreign_reference_count": len(foreign_refs)}
    response_hash = hashlib.sha256(answer.encode()).hexdigest()
    directive_id = "ndirective_" + hashlib.sha256(f"{case['case_id']}:{receipt.get('response_reference')}".encode()).hexdigest()[:18]
    action_type = str(parsed.get("followup_result_action_type") or selected["action_if_unresolved"]).upper()
    valid_actions = {"NEW_SOURCE_REQUEST", "TRADING_EXPERIMENT", "DATA_FIDELITY_CHECK",
        "STRATEGY_MODIFICATION_TEST", "ROBUSTNESS_TEST", "NO_ACTION_SUFFICIENTLY_RESOLVED",
        "ANOTHER_NOTEBOOK_QUESTION", "DEPARTMENT_REQUEST"}
    if action_type not in valid_actions:
        action_type = selected["action_if_unresolved"]
    what_to_do = str(parsed.get("what_to_do") or "Review the cited source mechanics and compare them with the existing Nexus replay implementation.").strip()
    why = str(parsed.get("why") or selected["expected_information_gain"]).strip()
    next_owner = str(parsed.get("next_owner") or ("MERCURY_TRADING" if action_type in {"TRADING_EXPERIMENT", "STRATEGY_MODIFICATION_TEST", "ROBUSTNESS_TEST"} else "RESEARCH")).upper()
    credential_work = any(term in what_to_do.casefold() for term in ("credential", "app key", "app secret", "secret", "authentication"))
    if credential_work:
        # Credential discovery/health belongs to Systems even when a notebook
        # answer names Trading as the eventual consumer of the data.
        next_owner = "SYSTEMS"
    history_by_department: dict[str, dict[str, Any]] = {}
    try:
        from nexus_agent_platform.department_learning import lookup_department_learning
        departments_to_check = {next_owner}
        if credential_work:
            # Systems resolves credentials; Mercury remains the evidence consumer.
            departments_to_check.add(str(parsed.get("next_owner") or "MERCURY_TRADING").upper())
        for department in departments_to_check:
            history_by_department[department] = lookup_department_learning(
                department, topic_terms=["Wick", "EMA200", "signal parity", "volume"])
    except Exception as exc:
        history_by_department.setdefault(next_owner, {"status": "UNAVAILABLE", "reason": type(exc).__name__, "records": []})
    prior_lessons = [row for result in history_by_department.values() for row in result.get("records", [])]
    history_used = [row for row in prior_lessons if any(term in json.dumps(row, ensure_ascii=False).casefold()
                    for term in ("wick", "ema200", "signal parity", "volume"))]
    directive = {
        "directive_id": directive_id, "case_id": case.get("case_id"), "notebook_id": notebook_id,
        "question_that_created_action": generated_question, "notebook_response_id": receipt.get("response_reference"),
        "notebook_response_hash": response_hash, "source_set": source_ids,
        "notebook_finding": findings, "result_action_type": action_type,
        "what_to_do": what_to_do, "why": why,
        "inputs": parsed.get("inputs") or ["Existing Wick case sources, current Pine source, and latest Nexus result"],
        "existing_capabilities": parsed.get("existing_capabilities") or ["Bound Wick NotebookLM", "case evidence", "Mercury replay if test warranted"],
        "configuration": (parsed.get("configuration") if isinstance(parsed.get("configuration"), dict) else
                          {"summary": parsed.get("configuration")} if parsed.get("configuration") else {}) |
                         {"case_id": case.get("case_id"), "live_trading_enabled": False},
        "expected_output": parsed.get("expected_output") or ["Source-cited finding", "remaining uncertainty", "recommended next action"],
        "return_path": "Return result to the same Company Case and same NotebookLM notebook.",
        "next_step_after_result": parsed.get("next_step_after_result") or "Research reassesses the same case and selects whether evidence gathering or a controlled test is next.",
        "if_blocked_behavior": "Keep the parent case active; record missing credential component or authorization precisely, do not rotate/reset the existing key, and state the minimum operator action only if local recovery is exhausted.",
        "why_deviating_from_research": ("Routing credential restoration to Systems because credential recovery/health is Systems-owned; Trading remains the downstream data consumer. No key rotation is authorized." if credential_work and next_owner != str(parsed.get("next_owner") or "").upper() else ""),
        "history_lookup_performed": bool(history_by_department) and all(row.get("status") == "OK" for row in history_by_department.values()),
        "history_lookup_by_department": history_by_department,
        "relevant_prior_lessons": prior_lessons,
        "lessons_used": history_used,
        "lessons_rejected_as_not_applicable": [],
        "how_history_changed_next_action": ("Applied scoped lessons to avoid repeating an already tested Wick configuration; selected the next route only where instrument/data scope differs." if history_used else "No applicable prior department lesson was present in the shared history at decision time."),
        "next_owner": next_owner, "question_origin": "RESEARCH_OWNER", "created_at": _now(),
    }
    actionable = action_type != "NO_ACTION_SUFFICIENTLY_RESOLVED"
    cycles = list(case.get("notebook_followup_cycles") or [])
    cycle = {"trigger": "NORMAL_CASE_CONTINUATION", "question_origin": "RESEARCH_OWNER",
        "question_type": selected["question_type"], "why_research_decided_followup_was_needed": selected["expected_information_gain"],
        "open_issue_selected": selected["issue"], "generated_notebook_question": generated_question,
        "why_question_selected": "Selected from the newest result's unresolved questions after checking prior prompts, latest answer coverage, decision relevance, and case follow-up budget.",
        "is_decision_relevant": selected["decision_relevant"],
        "could_answer_change_next_action": selected["answer_could_change_next_action"],
        "information_already_present": selected["information_already_present"],
        "test_can_answer_more_effectively": selected["test_can_answer_more_effectively"],
        "expected_information_gain": selected["expected_information_gain"],
        "notebook_id": notebook_id, "notebook_response_id": receipt.get("response_reference"),
        "notebook_response_hash": response_hash, "source_set": source_ids,
        "extracted_findings": findings, "result_action_type": action_type,
        "downstream_directive_id": directive_id if actionable else None, "recorded_at": _now()}
    cycles.append(cycle)
    answers_saved = record_notebook_answer(case["case_id"], question_type=f"AUTONOMOUS_FOLLOWUP:{selected['question_type']}",
        answer=answer, notebook_id=notebook_id, source_ids=source_ids,
        conversation_id=receipt.get("conversation_id"), submission_attempted=True,
        submission_confirmed=True, response_reference=receipt.get("response_reference"),
        prompt=notebook_prompt, response_id=receipt.get("response_reference"),
        key_findings=[str(row.get("content_summary") or "") for row in findings],
        recommendations=[what_to_do] if actionable else [],
        open_questions=[selected["issue"]] if action_type in {"ANOTHER_NOTEBOOK_QUESTION", "NEW_SOURCE_REQUEST"} else [],
        next_action=what_to_do, question_origin="RESEARCH_OWNER", extracted_findings=findings,
        downstream_directive_id=directive_id if actionable else None)
    fresh = get_case(case["case_id"]) or case
    directives = list(fresh.get("actionable_directives") or [])
    if actionable:
        directives = [row for row in directives if row.get("directive_id") != directive_id] + [directive]
    depth_used = dict(fresh.get("depth_used") or {})
    depth_used["followup_questions"] = int(depth_used.get("followup_questions", 0)) + 1
    material_items = list(fresh.get("notebook_material_intelligence") or [])
    for item in findings:
        item_row = {**item, "response_id": receipt.get("response_reference"),
            "response_hash": response_hash, "source_set": source_ids,
            "notebook_id": notebook_id, "question_origin": "RESEARCH_OWNER",
            "recorded_at": _now()}
        material_items.append(item_row)
    status = str(fresh.get("status") or "REFINING").upper()
    if status not in ACTIVE_STATES:
        status = "REFINING"
    updated = _save(fresh, "AUTONOMOUS_NOTEBOOK_FOLLOWUP_COMPLETED",
        notebook_followup_cycles=cycles, notebook_material_intelligence=material_items,
        provider_attempts=provider_attempts, last_provider_recovery=recovery_receipt,
        actionable_directives=directives, research_intelligence=list(fresh.get("research_intelligence") or []) + [
            {"response_id": receipt.get("response_reference"), "response_hash": response_hash,
             "question_origin": "RESEARCH_OWNER", "question_type": selected["question_type"],
             "findings": findings, "next_action": what_to_do, "source_set": source_ids}],
        depth_used=depth_used, status=status, continue_research=True,
        next_action=what_to_do, next_research_action=what_to_do,
        next_owner=next_owner, why_next=why,
        last_case_advancement_trigger="DEPARTMENT_OWNER",
        last_owner_initiated_action=directive_id if actionable else receipt.get("response_reference"))
    if actionable and credential_work and next_owner == "SYSTEMS":
        request_department_work(case["case_id"], department="SYSTEMS",
            requested_work="Continue read-only recovery and health verification for the existing Webull PaperTrade OpenAPI credentials. Search only approved Nexus credential/config/launchd/Keychain references; report whether App Key and App Secret references exist, environment/mode, safe authentication test outcome if both are available, and exact recovery boundary. Do not print values or rotate/reset the existing key.",
            why_this_department="NotebookLM follow-up selected real exchange volume as the highest-value evidence route; credential restoration is a Systems capability/secret-resolution task, while Mercury is the downstream consumer.",
            expected_output="Redacted credential-presence and reference report, safe PaperTrade authentication result if possible, market-data entitlement/capability result if authenticated, and minimum human action if local recovery is exhausted.",
            what_happens_after_output="Return status to the same case and notebook; if available, Mercury validates TSLA M30 bars. If unavailable, Research continues with an evidence-supported alternative.",
            why_deviating_from_case_research="The NotebookLM recommendation named Mercury as consumer, but requested credential restoration; Systems owns credential recovery. No key rotation is authorized.",
            trigger="DEPARTMENT_OWNER")
        updated = get_case(case["case_id"]) or updated
    return {"status": "NOTEBOOK_FOLLOWUP_COMPLETED", "case_id": case.get("case_id"),
        "question": generated_question, "question_origin": "RESEARCH_OWNER",
        "response_reference": receipt.get("response_reference"), "response_hash": response_hash,
        "answer_persisted": bool(answers_saved.get("ok")), "findings_extracted": len(findings),
        "case_updated": bool(updated), "action_type": action_type,
        "directive_id": directive_id if actionable else None, "next_owner": updated.get("next_owner"),
        "next_action": updated.get("next_action"), "normal_runtime_path": "research_case_engine.continue_case_once"}


def record_notebook_intelligence(case_id: str, *, response_reference: str,
                                 research_conclusions: list[str],
                                 established_for_current_stage: list[str],
                                 unverified_claims: list[str],
                                 contradictory_evidence: list[str],
                                 open_questions: list[str],
                                 source_supported_recommendations: list[dict[str, Any]],
                                 untested_recommendations: list[dict[str, Any]],
                                 failed_approaches: list[dict[str, Any]],
                                 promising_approaches: list[dict[str, Any]],
                                 highest_value_open_question: str,
                                 best_next_source_class: list[str],
                                 best_next_test: dict[str, Any],
                                 why_this_next_action: str,
                                 expected_information_gain: str,
                                 next_department: str,
                                 actionable_department_directive: dict[str, Any],
                                 source_ids: list[str]) -> dict[str, Any]:
    """Persist notebook meaning as structured case state without replacing the full answer."""
    case = get_case(case_id)
    if not case or not response_reference or not source_ids:
        return {"ok": False, "reason": "CASE_RESPONSE_OR_SOURCE_LINEAGE_MISSING"}
    known_ids = {str(row.get("source_id") or row.get("id") or row.get("url"))
                 for row in case.get("sources", []) if isinstance(row, dict)}
    if any(str(value) not in known_ids for value in source_ids):
        return {"ok": False, "reason": "INTELLIGENCE_SOURCE_NOT_ATTACHED_TO_CASE"}
    record = {"response_reference": response_reference,
        "research_conclusions": research_conclusions,
        "established_for_current_stage": established_for_current_stage,
        "unverified_claims": unverified_claims,
        "contradictory_evidence": contradictory_evidence,
        "open_questions": open_questions,
        "source_supported_recommendations": source_supported_recommendations,
        "untested_recommendations": untested_recommendations,
        "failed_approaches": failed_approaches,
        "promising_approaches": promising_approaches,
        "highest_value_open_question": highest_value_open_question,
        "best_next_source_class": best_next_source_class,
        "best_next_test": best_next_test,
        "why_this_next_action": why_this_next_action,
        "expected_information_gain": expected_information_gain,
        "next_department": next_department,
        "actionable_department_directive": actionable_department_directive,
        "source_ids": source_ids, "recorded_at": _now()}
    records = list(case.get("research_intelligence") or [])
    records = [x for x in records if x.get("response_reference") != response_reference]
    records.append(record)
    return {"ok": True, "record": record,
        "case": _save(case, "STRUCTURED_NOTEBOOK_INTELLIGENCE_RECORDED",
                       research_intelligence=records,
                       research_summary=research_conclusions,
                       current_approach_id=case.get("current_approach_id"))}


def add_question(case_id: str, question: str, *, why_it_matters: str,
                 best_source_classes: list[str] | None = None) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    qnorm = _norm(question)
    all_q = list(case.get("open_questions") or []) + list(case.get("answered_questions") or [])
    prior = next((q for q in all_q if _norm(q.get("question")) == qnorm), None)
    if prior:
        return {"ok": True, "created": False, "question": prior, "case": case}
    budget = dict(case.get("depth_used") or {})
    limits = dict(case.get("depth_budget") or DEFAULT_DEPTH_BUDGET)
    if budget.get("followup_questions", 0) >= limits.get("max_followup_questions", 10):
        return {"ok": False, "reason": "FOLLOWUP_QUESTION_BUDGET_EXHAUSTED"}
    item = {"question_id": "q_" + hashlib.sha256(f"{case_id}:{qnorm}".encode()).hexdigest()[:16],
            "question": question, "why_it_matters": why_it_matters,
            "best_source_classes": list(best_source_classes or []),
            "answer_status": "OPEN", "answer": None}
    budget["followup_questions"] = int(budget.get("followup_questions", 0)) + 1
    saved = _save(case, "FOLLOWUP_QUESTION_ADDED", open_questions=list(case.get("open_questions") or []) + [item],
                  missing_information=list(dict.fromkeys(list(case.get("missing_information") or []) + [question])),
                  depth_used=budget, next_research_action="ANSWER_OPEN_QUESTION")
    return {"ok": True, "created": True, "question": item, "case": saved}


def request_case_research(case_id: str, *, requesting_department: str, question: str,
                          why_it_matters: str, best_source_classes: list[str] | None = None,
                          expected_output: str = "Attributed evidence, limitations, and an updated case answer") -> dict[str, Any]:
    """Route a departmental question into the same case and notebook lineage."""
    created = add_question(case_id, question, why_it_matters=why_it_matters,
                           best_source_classes=best_source_classes)
    if not created.get("ok"):
        return created
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    request_id = "rreq_" + hashlib.sha256(f"{case_id}:{question}".encode()).hexdigest()[:16]
    request = {"request_id": request_id,
        "case_id": case_id, "requesting_department": requesting_department,
        "question_id": created["question"].get("question_id"), "question": question,
        "why_it_matters": why_it_matters, "expected_output": expected_output,
        "notebook_id": case.get("notebook_id") or (case.get("notebook_workspace") or {}).get("notebook_id"),
        "status": "OPEN", "created_at": _now()}
    try:
        from nexus_agent_platform.company_workflow import build_handoff
        request["workflow_handoff"] = build_handoff(case=case, request_id=request_id,
            from_department=str(requesting_department), to_department="RESEARCH",
            work=question, why=why_it_matters, return_to=str(requesting_department),
            questions=[question], expected_output=expected_output)
    except Exception:
        request["workflow_handoff"] = {"case_id": case_id, "from_department": str(requesting_department).upper(),
            "to_department": "RESEARCH", "directive_id": request_id,
            "return_to": str(requesting_department).upper(), "work_to_perform": question,
            "status": "OPEN"}
    requests = list(case.get("research_requests") or [])
    if not any(row.get("request_id") == request["request_id"] for row in requests):
        requests.append(request)
    saved = _save(case, "DEPARTMENT_RESEARCH_REQUESTED", research_requests=requests,
        next_action="ANSWER_DEPARTMENT_RESEARCH_REQUEST", next_research_action="ANSWER_DEPARTMENT_RESEARCH_REQUEST",
        next_owner="RESEARCH", last_case_advancement_trigger="DEPARTMENT_OWNER")
    return {"ok": True, "request": request, "case": saved, "question": created["question"]}


def answer_question(case_id: str, question_id: str, *, answer: str, evidence_ids: list[str],
                    confidence: float, limitations: list[str] | None = None) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    opened = list(case.get("open_questions") or [])
    target = next((q for q in opened if q.get("question_id") == question_id), None)
    if not target:
        return {"ok": False, "reason": "OPEN_QUESTION_NOT_FOUND"}
    answer_record = {**target, "answer_status": "ANSWERED", "answer": answer,
                     "evidence_ids": list(evidence_ids), "confidence": max(0.0, min(1.0, float(confidence))),
                     "limitations": list(limitations or []), "answered_at": _now()}
    remaining = [q for q in opened if q.get("question_id") != question_id]
    missing = [x for x in list(case.get("missing_information") or []) if _norm(x) != _norm(target.get("question"))]
    status = "SYNTHESIZING" if not remaining else "RESEARCHING_MISSING_PIECES"
    research_requests = list(case.get("research_requests") or [])
    resumed_departments = []
    for request in research_requests:
        if request.get("question_id") == question_id:
            request.update({"status": "EVIDENCE_RETURNED", "answer": answer,
                "evidence_ids": list(evidence_ids), "answered_at": _now()})
            resumed_departments.append(str(request.get("requesting_department") or ""))
    next_action = "RESUME_REQUESTING_DEPARTMENT" if resumed_departments else ("SYNTHESIZE_CASE" if not remaining else "ANSWER_OPEN_QUESTION")
    saved = _save(case, "QUESTION_ANSWERED", open_questions=remaining,
                  answered_questions=list(case.get("answered_questions") or []) + [answer_record],
                  research_requests=research_requests, missing_information=missing, status=status,
                  next_action=next_action, next_owner=resumed_departments[0] if resumed_departments else "RESEARCH",
                  current_owner=resumed_departments[0] if resumed_departments else "RESEARCH",
                  current_directive=next_action,
                  waiting_on=None,
                  next_expected_output="Department resumes with Research evidence attached." if resumed_departments else "Research synthesis or the next open case question.",
                  workflow_return={"returned_to": resumed_departments[0], "question_id": question_id,
                    "condition": "RESEARCH_QUESTION_ANSWERED", "restored_at": _now()} if resumed_departments else case.get("workflow_return"),
                  next_research_action="SYNTHESIZE_CASE" if not remaining else "ANSWER_OPEN_QUESTION",
                  last_case_advancement_trigger="RESEARCH_RESPONSE")
    return {"ok": True, "case": saved, "answer": answer_record}


def reopen_question(case_id: str, question_id: str, *, reason: str) -> dict[str, Any]:
    """Reopen a question if later validation shows its prior answer was not direct."""
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    answered = list(case.get("answered_questions") or [])
    target = next((q for q in answered if q.get("question_id") == question_id), None)
    if not target:
        return {"ok": False, "reason": "ANSWERED_QUESTION_NOT_FOUND"}
    audit = list(case.get("nonresponsive_outputs") or [])
    audit.append({"question": target, "reason": reason, "reopened_at": _now()})
    reopened = {**target, "answer_status": "OPEN", "answer": None,
                "evidence_ids": [], "reopened_reason": reason}
    retained = [q for q in answered if q.get("question_id") != question_id]
    findings = [f for f in (case.get("findings") or [])
                if not f.get("research_execution_id") or str(f.get("research_execution_id")) not in reason]
    saved = _save(case, "QUESTION_REOPENED_AFTER_DIRECTNESS_REVIEW",
        answered_questions=retained, open_questions=[reopened] + list(case.get("open_questions") or []),
        findings=findings, nonresponsive_outputs=audit, status="MORE_RESEARCH_REQUIRED",
        continue_research=True, next_research_action="GATHER_DIRECT_CASE_EVIDENCE")
    return {"ok": True, "case": saved}


def record_finding(case_id: str, finding: dict[str, Any]) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    ident = str(finding.get("finding_id") or finding.get("id") or hashlib.sha256(json.dumps(finding, sort_keys=True, default=str).encode()).hexdigest()[:18])
    row = {**finding, "finding_id": ident, "recorded_at": finding.get("recorded_at") or _now()}
    saved = _save(case, "FINDING_ADDED", findings=_add_unique(list(case.get("findings") or []), row, "finding_id"),
                  status="SYNTHESIZING", next_research_action="SYNTHESIZE_CASE")
    return {"ok": True, "case": saved, "finding": row}


def record_synthesis(case_id: str, *, claims: list[dict[str, Any]], agreements: list[str],
                     disagreements: list[str], uncertainties: list[str],
                     source_ids: list[str]) -> dict[str, Any]:
    """Persist an evidence-linked case synthesis; it cannot manufacture evidence."""
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    known = {str(row.get("source_id") or row.get("url") or row.get("source_url"))
             for row in case.get("sources", [])}
    if not source_ids or any(str(value) not in known for value in source_ids):
        return {"ok": False, "reason": "SYNTHESIS_SOURCE_NOT_ATTACHED_TO_CASE"}
    classes = sorted({str(row.get("source_class") or "UNKNOWN").upper() for row in case.get("sources", [])
                      if str(row.get("source_id") or row.get("url") or row.get("source_url")) in set(source_ids)
                      and str(row.get("source_class") or "UNKNOWN").upper() not in {"UNKNOWN", "UNCLASSIFIED"}})
    row = {"claims": claims, "agreements": agreements, "disagreements": disagreements,
           "uncertainties": uncertainties, "source_ids": source_ids, "source_classes": classes,
           "recorded_at": _now(), "multi_source": len(classes) >= 2}
    saved = _save(case, "CASE_SYNTHESIS_RECORDED", syntheses=list(case.get("syntheses") or []) + [row],
                  status="MORE_RESEARCH_REQUIRED" if uncertainties else "SYNTHESIZING",
                  continue_research=bool(uncertainties),
                  next_research_action="ANSWER_OPEN_QUESTION" if uncertainties else "DEVELOP_RECOMMENDATION")
    return {"ok": True, "case": saved, "synthesis": row}


def add_hypothesis(case_id: str, hypothesis: dict[str, Any]) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    ident = str(hypothesis.get("hypothesis_id") or "hyp_" + hashlib.sha256(f"{case_id}:{hypothesis.get('statement')}".encode()).hexdigest()[:16])
    row = {**hypothesis, "hypothesis_id": ident, "status": hypothesis.get("status") or "PROPOSED", "created_at": _now()}
    saved = _save(case, "HYPOTHESIS_ADDED", hypotheses=_add_unique(list(case.get("hypotheses") or []), row, "hypothesis_id"),
                  status="UNDER_DEVELOPMENT", next_research_action="TEST_OR_GATHER_COMPLEMENTARY_EVIDENCE")
    return {"ok": True, "case": saved, "hypothesis": row}


def recommendation(case_id: str, *, kind: str, reason: str, supporting_evidence: list[str],
                   contradictory_evidence: list[str], uncertainties: list[str], missing_evidence: list[str],
                   confidence: float, next_action: str) -> dict[str, Any]:
    case = get_case(case_id)
    klass = str(kind).upper()
    if not case or klass not in RECOMMENDATIONS:
        return {"ok": False, "reason": "CASE_NOT_FOUND_OR_INVALID_RECOMMENDATION"}
    complete = bool(reason.strip() and next_action.strip() and (supporting_evidence or missing_evidence))
    status = "MORE_RESEARCH_REQUIRED" if klass == "GET_MORE_EVIDENCE" else "RECOMMENDATION_READY" if complete else "SYNTHESIZING"
    row = {"recommendation": klass, "recommendation_reason": reason,
           "supporting_evidence": supporting_evidence, "contradictory_evidence": contradictory_evidence,
           "uncertainties": uncertainties, "missing_evidence": missing_evidence,
           "confidence": max(0.0, min(1.0, float(confidence))), "next_action": next_action,
           "created_at": _now()}
    saved = _save(case, "RECOMMENDATION_RECORDED", recommendations=list(case.get("recommendations") or []) + [row],
                  missing_information=list(dict.fromkeys(list(case.get("missing_information") or []) + missing_evidence)),
                  status=status, continue_research=klass == "GET_MORE_EVIDENCE" or bool(missing_evidence),
                  final_decision=None if status == "MORE_RESEARCH_REQUIRED" else klass,
                  next_research_action=next_action)
    return {"ok": True, "case": saved, "recommendation": row}


def consume_budget(case_id: str, *, dimension: str, amount: int = 1) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    keys = {"source_lookups": "max_source_lookups", "followup_questions": "max_followup_questions",
            "research_iterations": "max_research_iterations", "cross_department_requests": "max_cross_department_requests",
            "bounded_experiments": "max_bounded_experiments"}
    if dimension not in keys:
        return {"ok": False, "reason": "UNKNOWN_DEPTH_DIMENSION"}
    used, limit = dict(case.get("depth_used") or {}), dict(case.get("depth_budget") or DEFAULT_DEPTH_BUDGET)
    if int(used.get(dimension, 0)) + amount > int(limit.get(keys[dimension], 0)):
        return {"ok": False, "reason": "DEPTH_BUDGET_EXHAUSTED", "used": used.get(dimension, 0), "limit": limit.get(keys[dimension])}
    used[dimension] = int(used.get(dimension, 0)) + amount
    return {"ok": True, "case": _save(case, "DEPTH_BUDGET_CONSUMED", depth_used=used)}


def map_research_conclusion(case_id: str, conclusion: str, *, evidence_paths_exhausted: bool = False,
                            why: str = "") -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    value = str(conclusion).upper()
    if value == "RESEARCH_INCONCLUSIVE" and not evidence_paths_exhausted:
        status, nxt, keep = "MORE_RESEARCH_REQUIRED", "REFINE_QUESTION_OR_SOURCE_STRATEGY", True
    elif value == "HYPOTHESIS_NOT_SUPPORTED" and evidence_paths_exhausted:
        status, nxt, keep = "REJECTED_WITH_EVIDENCE", "PRESERVE_LESSON_AND_CLOSE", False
    elif value == "FINDING_SUPPORTED":
        status, nxt, keep = "SYNTHESIZING", "DEVELOP_RECOMMENDATION", True
    else:
        status, nxt, keep = "MORE_RESEARCH_REQUIRED", "GATHER_MISSING_EVIDENCE", True
    saved = _save(case, "RESEARCH_CONCLUSION_MAPPED", research_conclusion=value,
                  conclusion_reason=why, evidence_paths_exhausted=bool(evidence_paths_exhausted),
                  status=status, next_research_action=nxt, continue_research=keep)
    return {"ok": True, "case": saved, "status": status, "next_action": nxt}


def request_extension(case_id: str, *, reason: str, requested_budget: dict[str, int]) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    requests = list(case.get("depth_extension_requests") or []) + [{"reason": reason,
        "requested_budget": requested_budget, "status": "PENDING_RAY_OR_GOVERNANCE_REVIEW", "created_at": _now()}]
    return {"ok": True, "case": _save(case, "DEPTH_EXTENSION_REQUESTED", depth_extension_requests=requests,
                                          requires_ray=True, next_research_action="WAIT_FOR_DEPTH_EXTENSION_REVIEW")}


def record_department_response(case_id: str, *, department: str, status: str, specific_question: str = "",
                               why_needed: str = "", expected_evidence: str = "",
                               return_to_goal_id: str | None = None, result: dict[str, Any] | None = None) -> dict[str, Any]:
    # Department completion is a child-work result, never parent case completion.
    allowed = {"DEVELOPING", "TESTING", "MORE_RESEARCH_REQUIRED", "ADVANCED", "PARKED", "REJECTED_WITH_EVIDENCE", "COMPLETED"}
    state = str(status).upper()
    if state not in allowed:
        return {"ok": False, "reason": "INVALID_DEPARTMENT_CONTINUATION_STATUS"}
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    row = {"department": department, "status": state, "specific_question": specific_question,
           "why_needed": why_needed, "expected_evidence": expected_evidence,
           "return_to_goal_id": return_to_goal_id, "result": result or {}, "recorded_at": _now()}
    requests = list(case.get("department_requests") or []) + [row]
    if state == "MORE_RESEARCH_REQUIRED":
        if not (specific_question and why_needed and expected_evidence and return_to_goal_id):
            return {"ok": False, "reason": "MORE_RESEARCH_REQUIRED_NEEDS_COMPLETE_RETURN_CONTRACT"}
        status_value, action, cont = "MORE_RESEARCH_REQUIRED", "ANSWER_DEPARTMENT_QUESTION", True
    else:
        status_value = "DEPARTMENT_DEVELOPMENT" if state in {"DEVELOPING", "TESTING", "COMPLETED", "PARKED", "REJECTED_WITH_EVIDENCE"} else "UNDER_DEVELOPMENT"
        action = "EVALUATE_CASE_COMPLETION_CONTRACT" if state in {"COMPLETED", "PARKED", "REJECTED_WITH_EVIDENCE"} else f"CONTINUE_{state}"
        cont = True
    saved = _save(case, "DEPARTMENT_RESPONSE_RECORDED", department_requests=requests,
                  status=status_value, next_department_action=action,
                  next_research_action=action,
                  next_action=action, next_owner=department, continue_research=cont)
    return {"ok": True, "case": saved, "response": row}


def request_department_work(case_id: str, *, department: str, requested_work: str,
                            why_this_department: str, expected_output: str,
                            what_happens_after_output: str = "Return result to this case for parent-engine evaluation.",
                            why_deviating_from_case_research: str = "",
                            trigger: str = "CODEX", from_department: str = "COMPANY_CASE_ENGINE",
                            return_to: str | None = None, questions_to_answer: list[str] | None = None,
                            cost_or_resource_implication: Any = None,
                            ray_approval_required: bool = False,
                            directive_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a full-context request on the same objective case."""
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    requests = list(case.get("department_requests") or [])
    duplicate = next((item for item in reversed(requests)
        if item.get("department") == department and item.get("requested_work") == requested_work
        and str(item.get("status") or "OPEN").upper() == "OPEN"), None)
    if duplicate:
        if (not duplicate.get("workflow_handoff") or
                duplicate.get("workflow_handoff", {}).get("expected_output") != expected_output or
                duplicate.get("workflow_handoff", {}).get("return_to") != (return_to or from_department)):
            try:
                from nexus_agent_platform.company_workflow import build_handoff
                duplicate["workflow_handoff"] = build_handoff(case=case,
                    request_id=duplicate.get("request_id"), from_department=from_department,
                    to_department=department, work=requested_work, why=why_this_department,
                    return_to=return_to or from_department, questions=questions_to_answer,
                    expected_output=expected_output,
                    cost_implication=cost_or_resource_implication,
                    ray_approval_required=ray_approval_required)
                case = _save(case, "WORKFLOW_HANDOFF_ENVELOPE_ADDED",
                    department_requests=requests)
            except Exception:
                pass
        return {"ok": True, "created": False, "case": case, "request": duplicate}
    row = {"request_id": "dreq_" + hashlib.sha256(f"{case_id}:{department}:{requested_work}:{_now()}".encode()).hexdigest()[:16],
        "case_id": case_id, "department": department, "objective": case.get("objective"),
        "success_criteria": case.get("success_criteria") or [], "relevant_findings": case.get("findings") or [],
        "relevant_recommendations": case.get("recommendations") or [], "open_questions": case.get("open_questions") or [],
        "assumptions": case.get("assumptions") or case.get("nexus_assumptions") or [], "risks": case.get("risk_analysis") or [],
        "case_selection_reason": case.get("case_selection_reason") or case.get("selection_reason"),
        "what_already_happened": {"sources": case.get("sources") or [], "findings": case.get("findings") or [],
            "syntheses": case.get("syntheses") or [], "hypotheses": case.get("hypotheses") or [],
            "notebook_answers": case.get("notebook_answers") or [], "department_requests": copy.deepcopy(requests),
            "department_results": case.get("department_results") or [], "experiments": case.get("experiment_results") or []},
        "what_resulted": case.get("department_results") or [],
        "requested_work": requested_work, "why_this_department": why_this_department,
        "expected_output": expected_output, "what_happens_after_output": what_happens_after_output,
        "why_deviating_from_case_research": why_deviating_from_case_research,
        "status": "OPEN", "created_at": _now(),
        "directive_metadata": copy.deepcopy(directive_metadata or {})}
    try:
        from nexus_agent_platform.company_workflow import build_handoff
        row["workflow_handoff"] = build_handoff(case=case, request_id=row["request_id"],
            from_department=from_department, to_department=department, work=requested_work,
            why=why_this_department, return_to=return_to or from_department,
            questions=questions_to_answer, expected_output=expected_output,
            cost_implication=cost_or_resource_implication,
            ray_approval_required=ray_approval_required)
    except Exception:
        row["workflow_handoff"] = {"case_id": case_id, "from_department": from_department,
            "to_department": department, "directive_id": row["request_id"],
            "work_to_perform": requested_work, "return_to": return_to or from_department,
            "ray_approval_required": bool(ray_approval_required), "status": "OPEN"}
    requests.append(row)
    states = dict(case.get("department_states") or {})
    states[str(department).upper()] = "REQUESTED"
    saved = _save(case, "DEPARTMENT_WORK_REQUESTED", department_requests=requests,
        department_states=states,
        status="DEPARTMENT_DEVELOPMENT", next_department_action=requested_work,
        next_action=requested_work, next_owner=department, current_owner=department,
        current_directive=row["workflow_handoff"], last_case_advancement_trigger=trigger,
        last_owner_initiated_action=row["request_id"] if str(trigger).upper() == "DEPARTMENT_OWNER" else case.get("last_owner_initiated_action"))
    return {"ok": True, "case": saved, "request": row}


def record_department_result(case_id: str, *, department: str, what_was_done: str, why: str,
                             configuration: dict[str, Any], result: str, did_it_advance_goal: bool,
                             what_was_learned: str, new_questions: list[str],
                             next_recommended_action: str, evidence_refs: list[str] | None = None,
                             prototype_completed: bool = False,
                             experiment_completed: bool = False,
                             result_type: str = "DEPARTMENT_RESULT",
                             learning_record: dict[str, Any] | None = None,
                             directive_id: str | None = None) -> dict[str, Any]:
    """Append department output as case evidence and keep a concrete continuation."""
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    packet = {"result_id": "cres_" + hashlib.sha256(f"{case_id}:{department}:{_now()}".encode()).hexdigest()[:16],
        "case_id": case_id, "department": department, "what_was_done": what_was_done, "why": why,
        "configuration": configuration, "result": result, "did_it_advance_the_goal": bool(did_it_advance_goal),
        "what_was_learned": what_was_learned, "new_questions": list(new_questions),
        "next_recommended_action": next_recommended_action, "evidence_refs": list(evidence_refs or []),
        "notebook_id": case.get("notebook_id") or (case.get("notebook_workspace") or {}).get("notebook_id"),
        "research_followup_required": bool(new_questions) and str((case.get("trading_strategy_project") or {}).get("notebook_owner") or "").upper() != "TRADING",
        "prototype_completed": bool(prototype_completed), "experiment_completed": bool(experiment_completed),
        "result_type": str(result_type).upper(), "completed_at": _now(), "recorded_at": _now()}
    trading_project = case.get("trading_strategy_project") or {}
    trading_project_owned = str(trading_project.get("notebook_owner") or "").upper() == "TRADING"
    trading_owned = trading_project_owned and str(department).upper() in {"MERCURY_TRADING", "TRADING"}
    direct_trading_return = trading_project_owned and str(configuration.get("return_to") or "").upper() in {"MERCURY_TRADING", "TRADING"}
    next_owner = ("MERCURY_TRADING" if trading_owned or direct_trading_return else
                  ("RESEARCH" if new_questions else department))
    next_action = next_recommended_action or "Re-evaluate the active company case and select the next bounded action."
    try:
        from nexus_agent_platform.company_workflow import result_contract
        packet["workflow_result"] = result_contract(result=result,
            interpretation=what_was_learned or "Interpretation not supplied; Research review remains available.",
            what_changed=str(configuration.get("measured_change") or "Recorded in result/configuration."),
            why_changed=str((learning_record or {}).get("why_it_changed") or "Not assessed in result packet."),
            learned=what_was_learned, recommendation=next_action,
            recommended_changes=list(configuration.get("recommended_changes") or []),
            next_owner=next_owner, next_directive=next_action,
            return_to=str(configuration.get("return_to") or department),
            ray_required=bool(configuration.get("ray_decision_required", False)),
            case_status="UNDER_DEVELOPMENT", case_id=case_id)
    except Exception:
        packet["workflow_result"] = {"result": result, "what_was_learned": what_was_learned,
            "next_owner": next_owner, "next_directive": next_action,
            "return_to": str(configuration.get("return_to") or department),
            "ray_decision_required": False, "case_status": "UNDER_DEVELOPMENT"}
    results = list(case.get("department_results") or [])
    prior = next((row for row in results if row.get("department") == department and row.get("what_was_done") == what_was_done), None)
    if prior:
        packet["result_id"] = prior.get("result_id")
        results = [row for row in results if row is not prior]
    # RESULT != LEARNING: every result gets an explicit, scoped learning
    # contract. When no causal analysis is supplied, unknown explanation fields
    # remain explicitly unassessed and evidence cannot be promoted.
    default_learning = {
        "department": department, "case_id": case_id, "objective": case.get("objective") or case.get("parent_objective") or "",
        "date": _now(), "baseline_or_prior_state": str(configuration.get("baseline_or_prior_state") or "Not supplied in result packet."),
        "action_or_change": what_was_done, "result": result,
        "what_changed": str(configuration.get("measured_change") or "Outcome recorded; directional change not separately specified."),
        "why_it_changed": "NOT_ASSESSED_BY_RESULT_PACKET" if not learning_record else "Provided by the department learning analysis.",
        "root_cause": "UNDETERMINED" if not learning_record else str(learning_record.get("root_cause") or "UNDETERMINED"),
        "alternative_explanations": ["Not assessed in this result packet."] if not learning_record else list(learning_record.get("alternative_explanations") or []),
        "what_was_learned": what_was_learned,
        "what_was_not_proven": ["Generalization beyond this case/result was not established."] if not learning_record else list(learning_record.get("what_was_not_proven") or []),
        "what_should_be_done_differently_next_time": str(configuration.get("next_time_change") or "Research should review this scoped result before selecting the next action."),
        "reusable_lesson": what_was_learned,
        "confidence": "LOW" if not learning_record else str(learning_record.get("confidence") or "LOW"),
        "scope": str(configuration.get("scope") or f"{department} result for case {case_id}; do not generalize without replication."),
        "sample_size": int(configuration.get("sample_size") or 1), "replication_count": 0,
        "out_of_sample_validated": False, "contradictory_evidence": [],
        "evidence_references": list(evidence_refs or [packet["result_id"]]),
        "source_references": [], "nexus_evidence_references": list(evidence_refs or [packet["result_id"]]),
        "notebook_id": packet["notebook_id"], "next_hypothesis": "",
        "next_action": next_recommended_action, "success_failure": str(result_type).upper(),
        "evidence_level": "OBSERVATION",
    }
    if learning_record:
        default_learning.update(learning_record)
    try:
        from nexus_agent_platform.department_learning import persist_department_learning
        learning_receipt = persist_department_learning(default_learning)
    except Exception as exc:  # preserve result delivery if the shared history is unavailable
        learning_receipt = {"status": "UNAVAILABLE", "reason": type(exc).__name__}
    packet["learning_record"] = learning_receipt.get("record") or default_learning
    packet["learning_history_persist_status"] = learning_receipt.get("status")
    packet["learning_history_id"] = learning_receipt.get("learning_id")
    results.append(packet)
    requests = list(case.get("department_requests") or [])
    for request in reversed(requests):
        if (request.get("department") == department and
            str(request.get("status") or "OPEN").upper() in {"OPEN", "IN_PROGRESS"} and
            (not directive_id or request.get("request_id") == directive_id)):
            request.update({"status": "RESULT_RETURNED", "result_id": packet["result_id"], "completed_at": _now()})
            break
    department_states = dict(case.get("department_states") or {})
    department_states[str(department).upper()] = "RESULT_RETURNED"
    evidence = [row for row in list(case.get("evidence") or []) if row.get("result_id") != packet["result_id"]]
    evidence.append({"department": department, "result_id": packet["result_id"], "refs": packet["evidence_refs"], "summary": result})
    learning_rows = list(case.get("department_learning_history") or [])
    learning_id = packet.get("learning_history_id")
    if learning_id:
        learning_rows = [row for row in learning_rows if row.get("learning_id") != learning_id]
        learning_rows.append(packet["learning_record"])
    saved = _save(case, "DEPARTMENT_RESULT_RETURNED", department_requests=requests, department_results=results,
        department_states=department_states,
        evidence=evidence,
        department_learning_history=learning_rows,
        department_feedback=packet, status="UNDER_DEVELOPMENT", continue_research=not trading_project_owned,
        next_action=next_action, next_research_action=next_action,
        next_owner=next_owner, current_owner=next_owner,
        current_directive=next_action,
        workflow_return={"returned_to": next_owner, "result_id": packet["result_id"],
            "condition": "DEPARTMENT_RESULT_RETURNED", "restored_at": _now()},
        last_case_advancement_trigger="RESULT_FEEDBACK")
    return {"ok": True, "case": saved, "result": packet}


def resume_returned_department_result(case_id: str, result_id: str) -> dict[str, Any]:
    """Research return handler: interpret returned evidence and dispatch next work.

    This uses the existing case/result/request records. It does not create a
    separate workflow queue and is safe to rerun because the downstream request
    is idempotent.
    """
    case = get_case(case_id)
    if not case:
        return {"status": "CASE_NOT_FOUND", "case_id": case_id}
    result = next((row for row in case.get("department_results", []) if row.get("result_id") == result_id), None)
    if not result:
        return {"status": "RESULT_NOT_FOUND", "case_id": case_id, "result_id": result_id}
    if str(result.get("department") or "").upper() != "SYSTEMS":
        return {"status": "UNSUPPORTED_RETURN_DEPARTMENT", "department": result.get("department")}
    interpretation = ("Systems' read-only resolver found neither Webull App Key nor App Secret through the canonical configured sources. "
        "This blocks the TSLA/Webull data route, not the Wick objective. Existing OANDA Practice history and prior EUR/USD replays remain usable; "
        "the next useful owner is Mercury to select a bounded, evidence-supported OANDA test without inventing a filter.")
    research_result = record_department_result(case_id, department="RESEARCH",
        what_was_done="Research consumed the returned Systems result, reconciled it against the active Wick case and known OANDA route, and selected the next owner.",
        why="The Systems result answers the credential-route question. Since credentials were not resolved, Research preserves the objective and continues through an already available market-data path.",
        configuration={"systems_result_id": result_id, "webull_route": "UNAVAILABLE_CREDENTIALS_NOT_RESOLVED",
            "oanda_route": "EXISTING_CAPABILITY_RETAINED", "return_to": "RESEARCH",
            "scope": "Wick parent objective remains active; no live trading, funded trading, or provider purchase."},
        result=interpretation, did_it_advance_goal=True,
        what_was_learned="A provider authentication gap is route-specific and should trigger capability substitution rather than parent-case failure.",
        new_questions=[], next_recommended_action="Mercury: review existing OANDA Wick replay evidence and nominate/execute the next single-variable source-supported validation; return metrics and evidence to the same case and Research.",
        evidence_refs=[result_id, "credential.webull.openapi.prod.v1", "OANDA_PRACTICE_HISTORICAL_CAPABILITY"],
        result_type="RESEARCH_SYSTEMS_RETURN_INTERPRETATION",
        learning_record={"why_it_changed": "The System result established the current configured Webull resolver has no credential references; OANDA historical data is already an evidenced alternate.",
            "root_cause": "WEBULL_ROUTE_NOT_RESOLVED; OBJECTIVE_UNAFFECTED", "confidence": "HIGH",
            "scope": "Wick case data-route selection only.", "sample_size": 1,
            "alternative_explanations": ["A credential may exist outside approved Nexus resolver locations."],
            "what_was_not_proven": ["Webull application is invalid", "Wick strategy viability"],
            "reusable_lesson": "When one route is unavailable, compare existing approved alternatives and continue the parent objective."})
    if not research_result.get("ok"):
        return {"status": "RESEARCH_RESULT_WRITE_FAILED", "reason": research_result.get("reason")}
    followup = request_department_work(case_id, department="MERCURY_TRADING",
        requested_work="Review the same Wick case's existing OANDA replay artifacts and source-supported experiment history. Select and, only if the existing safe replay path supports it, execute one highest-information-value OANDA validation; change one meaningful variable, do not add unsupported indicators, and return the structured metrics/limitations to Research.",
        why_this_department="Research interpreted the Systems result: the Webull route is not credential-resolved, while OANDA historical forex remains available. Mercury owns replay selection and strategy test execution.",
        expected_output="A proposed or executed bounded OANDA test with experiment ID, baseline, variable changed, instrument/timeframe, data source, trade count, net return, win rate, profit factor, expectancy, drawdown, methodology limitations, and next Research question/action.",
        what_happens_after_output="Return to Research on this same case for notebook/case reassessment; continue until evidence supports a Ray stage review.",
        trigger="RESULT_FEEDBACK", from_department="RESEARCH", return_to="RESEARCH",
        questions_to_answer=["Which existing source-supported Wick validation should Mercury run next using OANDA, given the prior small-sample EUR/USD M30 outcome and unresolved Webull credential route?"],
        cost_or_resource_implication={"cash_cost": 0, "mode": "historical_replay_only", "live_trading": False})
    fresh = get_case(case_id) or case
    latest_research = next((row for row in reversed(fresh.get("department_results", []))
        if row.get("department") == "RESEARCH" and row.get("result_type") == "RESEARCH_SYSTEMS_RETURN_INTERPRETATION"), None)
    if latest_research:
        latest_research.update({"summary": interpretation,
            "supporting_data": {"systems_result_id": result_id, "credential_route": "MISSING", "oanda_alternative": "EXISTING"},
            "actionable_items": [followup.get("request", {}).get("requested_work", "")],
            "exact_instructions": followup.get("request", {}).get("requested_work", ""),
            "next_owner": "MERCURY_TRADING", "expected_output": followup.get("request", {}).get("expected_output"),
            "actionable_item_count": 1})
        fresh = _save(fresh, "RESEARCH_RETURN_ROUTED_TO_TRADING", department_results=fresh.get("department_results", []),
            current_owner="MERCURY_TRADING", next_owner="MERCURY_TRADING", status="UNDER_DEVELOPMENT",
            continue_research=True, next_action=followup.get("request", {}).get("requested_work"),
            current_directive=followup.get("request", {}).get("workflow_handoff"),
            workflow_return={"returned_from": "SYSTEMS", "returned_to": "RESEARCH", "next_owner": "MERCURY_TRADING",
                "source_result_id": result_id, "restored_at": _now()},
            last_case_advancement_trigger="RESULT_FEEDBACK")
    return {"status": "RETURN_CONSUMED", "case_id": case_id, "systems_result_id": result_id,
        "research_result_id": (latest_research or {}).get("result_id"), "downstream_request_id": followup.get("request", {}).get("request_id"),
        "next_owner": "MERCURY_TRADING", "case_status": fresh.get("status"), "supabase_sync_expected": True}


def record_success_criteria_result(case_id: str, *, criterion: str, status: str,
                                   evidence_refs: list[str], result: str) -> dict[str, Any]:
    """Record criterion evidence without letting the caller complete the parent case."""
    case = get_case(case_id)
    state = str(status or "").upper()
    if not case or state not in {"SATISFIED", "NOT_SATISFIED", "OPEN"}:
        return {"ok": False, "reason": "CASE_OR_SUCCESS_CRITERIA_STATUS_INVALID"}
    if criterion not in (case.get("success_criteria") or []):
        return {"ok": False, "reason": "SUCCESS_CRITERION_NOT_FOUND"}
    if state == "SATISFIED" and not evidence_refs:
        return {"ok": False, "reason": "SATISFIED_CRITERION_REQUIRES_EVIDENCE"}
    rows = [row for row in case.get("success_criteria_results") or [] if row.get("criterion") != criterion]
    rows.append({"criterion": criterion, "status": state, "evidence_refs": list(evidence_refs),
        "result": result, "recorded_at": _now()})
    return {"ok": True, "case": _save(case, "SUCCESS_CRITERION_EVALUATED",
        success_criteria_results=rows, status="UNDER_DEVELOPMENT", continue_research=True,
        next_action="EVALUATE_CASE_COMPLETION_CONTRACT", next_owner="CASE_ENGINE")}


def evaluate_case_readiness(case_id: str) -> dict[str, Any]:
    """Check explicit case criteria before creating a Ray review packet."""
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    from .company_case_contracts import CONTRACTS, completion_gaps, decision_packet
    family = str(case.get("objective_family") or "OTHER").upper()
    contract = CONTRACTS.get(family, CONTRACTS["OTHER"])
    missing = completion_gaps(case)
    ready = not missing
    packet = decision_packet(case)
    status = contract["ready_status"] if ready else "MORE_RESEARCH_REQUIRED"
    saved = _save(case, "CASE_READINESS_EVALUATED", completion_missing=sorted(set(missing)),
        case_status=status, ray_decision_packet=packet, status=status,
        next_action=None if ready else (case.get("next_action") or "SATISFY_CASE_COMPLETION_CRITERIA"),
        next_owner="RAY" if ready else (case.get("next_owner") or "RESEARCH"),
        ray_required=ready, ray_decision_status="READY_FOR_RAY_REVIEW" if ready else "NOT_READY",
        continue_research=not ready)
    return {"ok": True, "ready": ready, "missing": sorted(set(missing)), "case": saved}


def queue_case_for_ray(case_id: str) -> dict[str, Any]:
    """Persist a decision queue entry on the durable parent case memory."""
    evaluated = evaluate_case_readiness(case_id)
    if not evaluated.get("ok"):
        return evaluated
    if not evaluated.get("ready"):
        return {**evaluated, "queued": False, "reason": "CASE_COMPLETION_CONTRACT_NOT_SATISFIED"}
    case = evaluated["case"]
    queue = list(case.get("ray_decision_queue") or [])
    if not any(str(row.get("case_id")) == case_id and row.get("status") == "READY_FOR_RAY_REVIEW" for row in queue):
        queue.append({"case_id": case_id, "status": "READY_FOR_RAY_REVIEW",
            "decision_packet": case.get("ray_decision_packet"), "created_at": _now(),
            "choices": ["APPROVE", "DENY", "REQUEST_CHANGES"]})
    saved = _save(case, "RAY_DECISION_QUEUE_ENTRY_CREATED", ray_decision_queue=queue,
        ray_decision_status="READY_FOR_RAY_REVIEW", status=case.get("case_status"),
        next_action=None, next_owner="RAY", continue_research=False)
    return {"ok": True, "queued": True, "case": saved}


def record_ray_case_decision(case_id: str, *, decision: str, approval_id: str,
                             requested_changes: str = "") -> dict[str, Any]:
    """Apply a Ray decision only when the governed approval ledger binds it to this case."""
    case = get_case(case_id)
    value = str(decision or "").upper()
    if not case or value not in {"APPROVE", "DENY", "REQUEST_CHANGES"}:
        return {"ok": False, "reason": "CASE_OR_DECISION_INVALID"}
    from nexus_agent_platform.governed.approvals import get_approval
    approval = get_approval(approval_id)
    if not approval or str(approval.get("status") or "").lower() not in {"approved", "consumed", "rejected"}:
        return {"ok": False, "reason": "RAY_DECISION_NOT_IN_APPROVAL_LEDGER"}
    inputs = approval.get("input_summary") or {}
    expected_action = "project.stop" if value == "DENY" else "company_case.decision"
    expected_decision = "REJECT" if value == "DENY" else value
    if (str(approval.get("resolved_by") or "").upper() not in {"RAY", "RAY DAVIS", "RAYMOND DAVIS"} or
        str(approval.get("action_id") or "") != expected_action or
        str(inputs.get("case_id") or inputs.get("project_id") or "") != case_id or
        str(inputs.get("decision") or "").upper() != expected_decision):
        return {"ok": False, "reason": "RAY_DECISION_AUTHORITY_OR_CASE_BINDING_FAILED"}
    if value != "DENY" and str(approval.get("status") or "").lower() not in {"approved", "consumed"}:
        return {"ok": False, "reason": "DECISION_REQUIRES_RAY_APPROVED_RECEIPT"}
    if value == "REQUEST_CHANGES":
        return {"ok": True, "case": _save(case, "RAY_CHANGES_REQUESTED", ray_decision_status="CHANGES_REQUESTED",
            ray_requested_changes=requested_changes, status="UNDER_DEVELOPMENT", continue_research=True,
            next_action=requested_changes or "APPLY_RAY_REQUESTED_CHANGES", next_owner="CASE_OWNER",
            last_case_advancement_trigger="RAY_DECISION")}
    if value == "DENY":
        # Reuse the existing Ray-only parent stop authority and its project.stop receipt.
        from nexus_agent_platform.project_stop_policy import ray_stop_authorized
        if not ray_stop_authorized(actor="RAY", approval_id=approval_id, decision="REJECT", project_id=case_id):
            return {"ok": False, "reason": "RAY_PARENT_STOP_AUTHORITY_FAILED"}
        from nexus_agent_platform.company_workflow import _record_workflow_metric
        _record_workflow_metric("RAY_TERMINATIONS", case_id=case_id, approval_id=approval_id)
        return {"ok": True, "case": _save(case, "RAY_DENIED_CASE", status="RAY_DENIAL_RECORDED",
            actor="RAY", ray_approval_id=approval_id, ray_stop_decision="REJECT",
            ray_decision_status="DENIED", continue_research=False, last_case_advancement_trigger="RAY_DECISION")}
    readiness = evaluate_case_readiness(case_id)
    if not readiness.get("ready"):
        return {"ok": False, "reason": "CASE_COMPLETION_CONTRACT_NOT_SATISFIED", "missing": readiness.get("missing")}
    from nexus_agent_platform.company_workflow import _record_workflow_metric
    _record_workflow_metric("OBJECTIVES_ACCEPTED", case_id=case_id, approval_id=approval_id)
    return {"ok": True, "case": _save(get_case(case_id) or case, "RAY_APPROVED_CASE",
        ray_decision_status="APPROVED", approved_at=_now(), continue_research=False,
        last_case_advancement_trigger="RAY_DECISION")}


def prioritized_cases(limit: int = 3) -> list[dict[str, Any]]:
    """Depth-first ordering for current bounded work; no scheduler is created."""
    cases = [row for row in _latest_cases() if row.get("case_schema_version") == "nexus.research-case.v1"
             and str(row.get("status") or "").upper() in ACTIVE_STATES and row.get("continue_research", True)]
    def rank(case: dict[str, Any]) -> tuple[float, float, str]:
        request = bool(case.get("department_requests"))
        return (float(case.get("priority", 0)) + float(case.get("promise_score", 0))*100 + (200 if request else 0),
                float(case.get("depth_used", {}).get("research_iterations", 0)), str(case.get("created_at") or ""))
    return sorted(cases, key=rank, reverse=True)[:max(0, limit)]


def next_schedulable_case() -> dict[str, Any] | None:
    """Return one active case for the existing Research kernel to continue."""
    candidates = prioritized_cases(limit=3)
    for case in candidates:
        budget = case.get("depth_budget") or DEFAULT_DEPTH_BUDGET
        used = case.get("depth_used") or {}
        if int(used.get("research_iterations", 0)) >= int(budget.get("max_research_iterations", 5)):
            continue
        if case.get("requires_ray") and str(case.get("next_research_action") or "").startswith("WAIT_FOR"):
            continue
        if case.get("open_questions") or case.get("continue_research"):
            return case
    return None


def _select_continuation_question(case: dict[str, Any]) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """Choose the most specific pending Research work before old discovery questions."""
    department_request = next((row for row in reversed(case.get("department_requests") or [])
        if str(row.get("department") or "").upper() == "RESEARCH"
        and str(row.get("status") or "OPEN").upper() == "OPEN"
        and str(row.get("requested_work") or "").strip()), None)
    if department_request:
        return str(department_request["requested_work"]).strip(), department_request, None
    case_request = next((row for row in reversed(case.get("research_requests") or [])
        if str(row.get("status") or "OPEN").upper() == "OPEN"
        and str(row.get("question") or "").strip()), None)
    if case_request:
        return str(case_request["question"]).strip(), None, case_request
    questions = list(case.get("open_questions") or [])
    question = str((questions[0] if questions else {}).get("question")
                   or case.get("primary_question") or case.get("objective") or "")
    return question, None, None


def continue_case_once(case_id: str) -> dict[str, Any]:
    """One bounded continuation through the canonical Hermes Research tool layer."""
    case = get_case(case_id)
    if not case:
        return {"status": "NOT_FOUND", "case_id": case_id}
    # A bound NotebookLM workspace is part of the normal case continuation.
    # Research selects a consequential unanswered issue from returned case
    # evidence before falling back to external-source research.
    notebook_turn = _run_autonomous_notebook_followup(case)
    if notebook_turn:
        if notebook_turn.get("status") == "NOTEBOOK_FOLLOWUP_COMPLETED":
            return notebook_turn
        if notebook_turn.get("status") not in {"NOTEBOOK_FOLLOWUP_DEFERRED", "NOTEBOOK_FOLLOWUP_NO_RESPONSE"}:
            return notebook_turn
    # A Research department handoff is more specific than the case's original
    # discovery question. Honor it first so autonomous continuation does not
    # repeatedly answer an old primary question while an actionable company
    # request is waiting in the same parent case.
    question_rows = list(case.get("open_questions") or [])
    question, pending_research_request, pending_case_request = _select_continuation_question(case)
    if not question:
        return {"status": "NO_QUESTION", "case_id": case_id}
    family = str(case.get("objective_family") or "GENERAL_DISCOVERY")
    strategy = None
    try:
        from nexus_agent_platform.research_tool_layer import execute_research_question, plan_source_strategy
        strategy = plan_source_strategy(question, evidence_needed="Answer the active case question with extracted, attributed evidence; distinguish facts, conflicts, and remaining unknowns.")
        result = execute_research_question(question, objective_family=family, source_strategy=strategy,
            research_case_id=case_id, originating_goal_id=case.get("originating_goal_id"), mode="autonomous",
            timeout_seconds=220, max_searches=3, max_pages=4)
    except Exception as exc:
        return {"status": "EXECUTION_ERROR", "case_id": case_id, "error": type(exc).__name__}
    if str(result.get("execution_status") or "").upper() == "PROVIDER_FAILURE":
        error = str(result.get("provider_error") or "UNKNOWN_PROVIDER_FAILURE")
        failure_class = ("REMOTE_CONTEXT_LENGTH_EXCEEDED" if error == "ssh_exit_1" else
                         "ORACLE_HERMES_TIMEOUT" if error == "oracle_timeout" else error)
        failure = {"attempt_id": str(result.get("run_id") or ""),
            "provider": "HERMES_TOOL_LAYER", "path": "research_tool_layer.execute_research_question → OracleHermes SSH → Hermes/OpenRouter",
            "case_id": case_id, "notebook_id": (case.get("notebook_workspace") or {}).get("notebook_id") or case.get("notebook_id"),
            "failure_class": failure_class, "provider_error": error,
            "repair_used": "CASE_CONTEXT_BOUNDED_TO_36K_CHARS",
            "fallback_used": False, "result": "RETRYABLE_PROVIDER_FAILURE", "recorded_at": _now()}
        failures = list(case.get("provider_attempts") or []) + [failure]
        _save(case, "RESEARCH_PROVIDER_FAILURE_RECORDED", provider_attempts=failures,
            last_provider_failure=failure, current_owner="RESEARCH", next_owner="RESEARCH",
            next_action="Retry the same-case NotebookLM follow-up after one bounded provider recovery attempt; keep the Company Case active.")
        try:
            from nexus_agent_platform.governed import persistence as governed
            prior = next((row for row in reversed(governed.read_records("systems_incidents"))
                if row.get("incident_key") == f"research-provider:{case_id}:{failure_class}"
                and str(row.get("status") or "OPEN").upper() == "OPEN"), None)
            governed.append_record("systems_incidents", {**(prior or {}),
                "incident_id": (prior or {}).get("incident_id") or governed.new_id("sysinc"),
                "incident_key": f"research-provider:{case_id}:{failure_class}",
                "incident_type": "RESEARCH_PROVIDER_FAILURE", "status": "OPEN", "owner": "SYSTEMS",
                "affected_case": case_id, "affected_workflow": "RESEARCH_CASE_CONTINUATION",
                "last_known_good": "Oracle Hermes structured Research succeeded on 2026-10-06 01:45 UTC; SSH, container, and Hermes binary health checks pass.",
                "failure_class": failure_class,
                "safe_repair_attempt": "Bound case context before remote Hermes requests; prefer the same bound NotebookLM follow-up when eligible.",
                "result": "RETRYABLE; parent case remains active",
                "next_action": "Verify bounded Research prompt and NotebookLM CLI response; repair provider route if retry fails.",
                "detected_by": "RESEARCH_CASE_ENGINE", "recorded_at": _now()})
        except Exception:
            pass
    resolution = result.get("question_resolution") if isinstance(result.get("question_resolution"), dict) else {}
    evidence_urls = {str(x) for x in (resolution.get("evidence_urls") or [])}
    case_sources = list(case.get("sources") or [])
    family = str(case.get("objective_family") or "").upper()
    question_text = question.casefold()
    directness_ok = bool(resolution.get("directly_answers_current_question"))
    directness_reason = "ACCEPTED"
    if family in {"TRADING", "TRADING_INTELLIGENCE"} and any(term in question_text for term in ("indicator", "script", "phase", "reversal")):
        anchor_urls = {str(row.get("url") or row.get("source_url")) for row in case_sources
                       if str(row.get("source_class") or "").upper() == "TRADINGVIEW_PUBLIC_SCRIPTS"
                       and (row.get("url") or row.get("source_url"))}
        if anchor_urls and not (anchor_urls & evidence_urls):
            directness_ok = False
            directness_reason = "INDICATOR_SPECIFIC_QUESTION_REQUIRES_EVIDENCE_FROM_THE_CASE_INDICATOR_SOURCE"
    if family in {"BUSINESS_OPPORTUNITIES", "CUSTOMER_NEEDS", "CUSTOMER_COMPLAINTS"} and any(term in question_text for term in ("customer demand", "customer problem", "unmet", "complaint", "willingness to pay")):
        firsthand_urls = {str(row.get("url") or "") for row in result.get("records", [])
                          if str(row.get("firsthand_or_secondary") or "").upper() == "FIRSTHAND"
                          and str(row.get("source_class") or "").upper() in {"DISCUSSION", "FORUM", "REVIEW"}}
        if not (firsthand_urls & evidence_urls):
            directness_ok = False
            directness_reason = "CUSTOMER_DEMAND_QUESTION_REQUIRES_ACCEPTED_FIRSTHAND_DISCUSSION_OR_REVIEW_EVIDENCE"
    if pending_research_request and directness_ok:
        ids = list(resolution.get("evidence_urls") or [])
        record_department_result(case_id, department="RESEARCH",
            what_was_done="Answered a case-bound departmental research request with attributed evidence.",
            why=str(pending_research_request.get("why_this_department") or "A department requested evidence required to continue the parent case."),
            configuration={"request_id": pending_research_request.get("request_id"),
                           "source_strategy": strategy, "run_id": (result.get("tool_layer_receipt") or {}).get("run_id")},
            result=str(resolution.get("answer") or result.get("research_conclusion") or "Evidence returned."),
            did_it_advance_goal=True,
            what_was_learned=str(resolution.get("answer") or "Research returned evidence to the parent case."),
            new_questions=[str(row) for row in result.get("followup_questions") or []],
            next_recommended_action="REASSESS_CASE_WITH_RETURNED_RESEARCH_EVIDENCE",
            evidence_refs=ids, result_type="DEPARTMENT_RESEARCH_RESPONSE")
    elif pending_case_request and directness_ok and pending_case_request.get("question_id"):
        ids = list(resolution.get("evidence_urls") or [])
        answer_question(case_id, str(pending_case_request["question_id"]),
            answer=str(resolution.get("answer") or ""), evidence_ids=ids,
            confidence=float(resolution.get("confidence") or 0),
            limitations=[str(x) for x in resolution.get("unanswered_parts") or []])
    elif question_rows and directness_ok and _norm(question_rows[0].get("question")) == _norm(question):
        ids = list(resolution.get("evidence_urls") or [])
        answer_question(case_id, str(question_rows[0].get("question_id")),
            answer=str(resolution.get("answer") or ""), evidence_ids=ids,
            confidence=float(resolution.get("confidence") or 0),
            limitations=[str(x) for x in resolution.get("unanswered_parts") or []])
    fresh = get_case(case_id) or case
    if (result.get("research_conclusion") == "RESEARCH_INCONCLUSIVE" or
        (question_rows and not directness_ok)) and not (result.get("followup_questions") or []):
        add_question(case_id, f"Which alternate source class can directly answer: {question}",
                     why_it_matters="The current pass did not resolve this important case question; source strategy should change before closure.",
                     best_source_classes=(strategy or {}).get("source_classes_planned", []))
    result["case_question_resolution"] = {"accepted": directness_ok,
        "reason": directness_reason if not directness_ok else "ACCEPTED",
        "evidence_urls": sorted(evidence_urls)}
    return {"status": "CONTINUED", "case_id": case_id, "question": question,
            "execution_status": result.get("execution_status"),
            "research_conclusion": result.get("research_conclusion"),
            "sources_opened": len(result.get("records", [])),
            "next_action": (get_case(case_id) or fresh).get("next_research_action"),
            "run_id": (result.get("tool_layer_receipt") or {}).get("run_id"),
            "provider_error": result.get("provider_error")}


def metrics_snapshot() -> dict[str, Any]:
    cases = _latest_cases()
    active = [row for row in cases if str(row.get("status") or "").upper() in ACTIVE_STATES]
    all_sources = sum(int(row.get("source_count", 0) or 0) for row in cases)
    from nexus_agent_platform.runtime.paths import nexus_research_state_path
    receipts_path = nexus_research_state_path("governed", "notebook_playbook_runs.jsonl")
    notebook_receipts = []
    try:
        notebook_receipts = [json.loads(line) for line in receipts_path.read_text(encoding="utf-8").splitlines()
                             if line.strip()]
    except (OSError, ValueError):
        notebook_receipts = []
    confirmed_turns = [row for row in notebook_receipts
        if row.get("initial_prompt_submission_confirmed") or row.get("followup_submissions_confirmed")]
    active_ids = {str(row.get("case_id")) for row in active}
    expansion_answers = [answer for case in cases for answer in (case.get("notebook_answers") or [])
        if answer.get("history_verified") and str(answer.get("response_reference") or "").startswith("adapter_visible_history_verified:")]
    questions_actually_asked = sum(
        (int(row.get("questions_asked") or 0) if row.get("initial_prompt_submission_confirmed") else 0) +
        (int(row.get("followup_prompt_question_count") or len(row.get("followup_questions") or []))
         if row.get("followup_submissions_confirmed") else 0)
        for row in notebook_receipts) + len(expansion_answers)
    company_cases = [row for row in cases if row.get("company_case_version") or row.get("case_schema_version") == "nexus.company-case.v1"]
    ready_cases = [row for row in company_cases if str(row.get("ray_decision_status") or "").upper() == "READY_FOR_RAY_REVIEW"]
    department_requests = [request for row in company_cases for request in row.get("department_requests", [])
                           if request.get("request_id")]
    department_results = [result for row in company_cases for result in row.get("department_results", [])]
    from datetime import datetime, timezone
    active_company = [row for row in company_cases if str(row.get("status") or "").upper() in ACTIVE_STATES]
    ages = []
    for row in active_company:
        try:
            created_at = datetime.fromisoformat(str(row.get("created_at")))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            ages.append(max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 3600))
        except (ValueError, TypeError):
            pass
    metrics = {"ACTIVE_COMPANY_CASES": len(active_company),
        "CASES_ADVANCED": sum(bool(row.get("department_requests") or row.get("department_results") or row.get("depth_used", {}).get("research_iterations", 0)) for row in company_cases),
        "DEEP_RESEARCH_CASES": sum(bool(row.get("sources") or row.get("findings") or row.get("notebook_answers")) for row in company_cases),
        "CROSS_DEPARTMENT_REQUESTS_CREATED": len(department_requests),
        "CROSS_DEPARTMENT_REQUESTS_CLOSED": sum(str(x.get("status") or "").upper() in {"CLOSED", "COMPLETED", "RESULT_RETURNED"} for x in department_requests),
        "EXPERIMENTS_COMPLETED": sum(bool(x.get("experiment_completed")) for row in company_cases for x in row.get("department_results", [])) + sum(bool(x.get("completed_at") or str(x.get("status") or "").upper() == "COMPLETED") for row in company_cases for x in row.get("experiment_results", [])),
        "PROTOTYPES_COMPLETED": sum(bool(x.get("prototype_completed") and x.get("completed_at")) for row in company_cases for x in row.get("department_results", [])),
        "DECISION_READY_CASES": len(ready_cases),
        "RAY_APPROVAL_PACKETS_CREATED": sum(len(row.get("ray_decision_queue") or []) for row in company_cases),
        "APPROVED_CASES": sum(str(row.get("ray_decision_status") or "").upper() == "APPROVED" for row in company_cases),
        "CHANGES_REQUESTED_CASES": sum(str(row.get("ray_decision_status") or "").upper() == "CHANGES_REQUESTED" for row in company_cases),
        "DENIED_CASES": sum(str(row.get("ray_decision_status") or "").upper() == "DENIED" for row in company_cases),
        "AVERAGE_CASE_AGE_HOURS": round(sum(ages) / len(ages), 2) if ages else None,
        "CASES_WITHOUT_NEXT_ACTION": sum(str(row.get("status") or "").upper() in ACTIVE_STATES and not (row.get("next_action") or row.get("next_research_action") or row.get("next_department_action")) for row in company_cases),
        "OWNER_INITIATED_ACTIONS_PROVEN": sum(bool(row.get("last_owner_initiated_action")) for row in company_cases)}
    return {"company_productivity": metrics, "active_deep_cases": len(active), "cases_advanced": sum(bool(row.get("depth_used", {}).get("research_iterations", 0)) for row in cases),
            "questions_actually_asked": questions_actually_asked,
            "notebook_responses_received": sum(bool(row.get("initial_prompt_submission_confirmed"))+
                                                bool(row.get("followup_submissions_confirmed"))
                                                for row in notebook_receipts) + len(expansion_answers),
            "source_gaps_closed": sum(int(row.get("questions_answered") or 0) for row in confirmed_turns),
            "sources_added_to_active_cases": sum(int(row.get("sources_added") or 0) for row in notebook_receipts
                                                   if str(row.get("case_id")) in active_ids),
            "hypotheses_created": sum(len(row.get("hypotheses") or []) for row in cases),
            "experiments_triggered": sum(len(row.get("experiment_requests") or []) for row in cases),
            "builds_triggered": sum(bool(row.get("build_request")) for row in cases),
            "actionable_handoffs": sum(bool(row.get("next_action_id") and row.get("next_owner")) for row in cases
                                        for _ in row.get("department_requests", [])),
            "cases_returned_from_department_and_advanced": sum(bool(row.get("department_feedback")) and
                int((row.get("depth_used") or {}).get("research_iterations") or 0) > 0 for row in cases),
            "cases_recommendation_ready": sum(str(row.get("status") or "").upper() == "RECOMMENDATION_READY" for row in cases),
            "followup_questions_answered": sum(len(row.get("answered_questions") or []) for row in cases),
            "multi_source_syntheses": sum(bool(synthesis.get("multi_source"))
                for row in cases for synthesis in row.get("syntheses", [])),
            "recommendations_produced": sum(len(row.get("recommendations") or []) for row in cases),
            "strategies_fully_specified": sum(bool(h.get("complete_rules")) for row in cases for h in row.get("hypotheses", [])),
            "strategies_backtested": sum(bool(h.get("backtest_id")) for row in cases for h in row.get("hypotheses", [])),
            "business_opportunities_developed": sum(str(row.get("objective_family") or "").upper() == "BUSINESS_OPPORTUNITIES"
                and any(str(rec.get("recommendation") or "").upper() not in {"GET_MORE_EVIDENCE", "MONITOR", "PARK"}
                        for rec in row.get("recommendations", [])) for row in cases),
            "technology_experiments_triggered": sum(bool(row.get("experiment_requests")) for row in cases if str(row.get("objective_family") or "").upper() == "TECHNOLOGY_FOR_NEXUS"),
            "creative_marketing_cases": sum(str(row.get("objective_family") or "").upper() in {"CREATIVE", "MARKETING_TRENDS"} for row in cases),
            "cases_rejected_with_evidence": sum(str(row.get("status") or "").upper() == "REJECTED_WITH_EVIDENCE" for row in cases),
            "useful_lessons_created": sum(bool(row.get("learning")) for row in cases),
            "source_records_total": all_sources}


def attach_case_learning(case_id: str, *, what_worked: str, what_failed: str, why: str,
                         what_was_learned: str, what_changed: str, try_next: str) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    learning = list(case.get("learning") or []) + [{"what_worked": what_worked, "what_failed": what_failed,
        "why": why, "what_was_learned": what_was_learned, "what_changed": what_changed,
        "what_should_be_tried_next": try_next, "recorded_at": _now()}]
    return {"ok": True, "case": _save(case, "LEARNING_RECORDED", learning=learning)}


def record_approach(case_id: str, *, approach_id: str, description: str,
                    why_considered: str, status: str, evidence: list[str] | None = None,
                    cost_estimate: Any = None, time_estimate: Any = None,
                    resource_requirements: list[str] | None = None,
                    tests: list[dict[str, Any]] | None = None,
                    results: list[dict[str, Any]] | None = None,
                    risks: list[str] | None = None, limitations: list[str] | None = None,
                    what_was_learned: str = "", why_not_recommended: str = "",
                    alternative_created: str | None = None, selected: bool = False,
                    next_action: str = "") -> dict[str, Any]:
    """Record an approach outcome without changing the parent objective's terminal state."""
    case = get_case(case_id)
    state = str(status or "").upper()
    if not case or state not in APPROACH_STATES or not approach_id or not description:
        return {"ok": False, "reason": "CASE_OR_APPROACH_INVALID"}
    row = {"approach_id": approach_id, "description": description,
        "why_considered": why_considered, "evidence": list(evidence or []),
        "cost_estimate": cost_estimate, "time_estimate": time_estimate,
        "resource_requirements": list(resource_requirements or []),
        "tests": list(tests or []), "results": list(results or []),
        "risks": list(risks or []), "limitations": list(limitations or []),
        "status": state, "what_was_learned": what_was_learned,
        "why_not_recommended": why_not_recommended,
        "alternative_created": alternative_created, "recorded_at": _now()}
    approaches = [x for x in case.get("approaches") or [] if x.get("approach_id") != approach_id]
    approaches.append(row)
    active_status = str(case.get("status") or "").upper()
    if active_status in {"FAILED", "FAILED_FINAL", "REJECTED", "CANCELLED", "ABANDONED", "TERMINATED"}:
        active_status = "REPLANNING"
    action = next_action or (case.get("next_action") or case.get("next_research_action") or "REASSESS_PARENT_OBJECTIVE")
    saved = _save(case, "APPROACH_RECORDED", approaches=approaches,
        parent_objective=case.get("parent_objective") or case.get("objective"),
        current_approach_id=approach_id if selected else case.get("current_approach_id"),
        status=active_status, continue_research=True, next_action=action,
        next_research_action=action, next_owner=case.get("next_owner") or case.get("owner_department") or "RESEARCH",
        objective_preserved=True, approach_status=state)
    return {"ok": True, "case": saved, "approach": row, "objective_preserved": True}


def replan_case(case_id: str, *, next_action: str, next_owner: str,
                selected_approach_id: str, reason: str,
                trigger: str = "RESULT_FEEDBACK") -> dict[str, Any]:
    """Select a new evidence route while preserving the active parent objective."""
    case = get_case(case_id)
    if not case or not next_action.strip() or not selected_approach_id:
        return {"ok": False, "reason": "CASE_OR_REPLAN_ACTION_MISSING"}
    action = {"action_id": "nxa_" + hashlib.sha256(f"{case_id}:{selected_approach_id}:{_now()}".encode()).hexdigest()[:16],
        "approach_id": selected_approach_id, "action": next_action,
        "owner": next_owner, "why_next": reason, "created_at": _now()}
    saved = _save(case, "OBJECTIVE_REPLANNED", parent_objective=case.get("parent_objective") or case.get("objective"),
        current_approach_id=selected_approach_id, status="REFINING", continue_research=True,
        next_action=next_action, next_research_action=next_action, next_owner=next_owner,
        next_action_id=action["action_id"], why_next=reason,
        last_case_advancement_trigger=trigger, objective_preserved=True,
        replans=list(case.get("replans") or []) + [action])
    return {"ok": True, "case": saved, "replan": action, "objective_preserved": True}
