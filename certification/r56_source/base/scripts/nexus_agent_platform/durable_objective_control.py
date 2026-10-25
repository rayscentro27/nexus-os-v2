"""Durable master-objective identity and terminal-condition guard.

The active V5 campaign record is the existing V5 checkpoint.  This module
enriches that record atomically and makes it the authority used when workers
resume after process loss or context compaction.
"""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_CAMPAIGN_PATH = Path(os.environ.get(
    "NEXUS_ACTIVE_CAMPAIGN_PATH",
    ROOT / "reports/certification/NEXUS_FULL_OWNER_REAL_WORLD_V5_STATE_20261010.json",
)).expanduser()
MASTER_OBJECTIVE = "NEXUS FULL OWNER-REQUEST REAL-WORLD CERTIFICATION V5"
TERMINAL_CONDITION = "COMPLETE_OWNER_EXPERIENCE"
OBJECTIVE_STOP_CLASSES = {
    "NEW_INCREMENTAL_CASH_REQUIRED", "TRUE_TECHNICAL_BLOCKER", "RAY_ACTION_REQUIRED"
}


def objective_stop_class(*, new_incremental_cash_required: bool = False,
                         technical_impossibility_confirmed: bool = False,
                         repair_retry_reroute_exhausted: bool = False,
                         ray_action_required: bool = False) -> str:
    """Classify a genuine owner-objective stop; ordinary failures continue."""
    if ray_action_required:
        return "RAY_ACTION_REQUIRED"
    if new_incremental_cash_required:
        return "NEW_INCREMENTAL_CASH_REQUIRED"
    if technical_impossibility_confirmed and repair_retry_reroute_exhausted:
        return "TRUE_TECHNICAL_BLOCKER"
    return "CONTINUE"
OBJECTIVE_VERSION = "V5"
V5_CAMPAIGN_ID = "NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9"
V5_OBJECTIVE_ID = "ownerobj_nexus_full_owner_real_world_v5_6fb82fd9"
REPAIR_JOB_ID = "job_v5_objective_control_repair_20261010"
NEXT_JOB_ID = "job_v5_research_source_review_20261010"


class ObjectiveControlError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    """Serialize checkpoint updates across workers on the canonical Mac host."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    handle = lock_path.open("a+")
    try:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - Windows fallback
            pass
        yield
    finally:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ImportError:  # pragma: no cover
            pass
        handle.close()


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(dict(value), stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _read(path: Path = ACTIVE_CAMPAIGN_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ObjectiveControlError("ACTIVE_CAMPAIGN_RECORD_INVALID")
    return value


def ensure_v5_record(path: Path = ACTIVE_CAMPAIGN_PATH, *, current_job_id: str | None = None,
                     current_job_type: str = "CONTROL_PLANE_REPAIR",
                     assigned_department: str = "SYSTEMS", assigned_worker: str = "codex",
                     worker_role: str = "CODING_AND_SYSTEM_REPAIR_ONLY") -> dict[str, Any]:
    """Promote the extant V5 checkpoint to the canonical campaign record."""
    with _lock(path):
        state = _read(path)
        cert_id = str(state.get("CERTIFICATION_ID") or V5_CAMPAIGN_ID)
        if cert_id != V5_CAMPAIGN_ID:
            raise ObjectiveControlError("ACTIVE_CAMPAIGN_ID_MISMATCH")
        previous_phase = state.get("CURRENT_PHASE")
        already_canonical = (state.get("CAMPAIGN_ID") == V5_CAMPAIGN_ID
                             and state.get("OWNER_OBJECTIVE_ID") == V5_OBJECTIVE_ID
                             and bool(state.get("CURRENT_JOB_ID")))
        selected_job_id = current_job_id or (state.get("CURRENT_JOB_ID") if already_canonical else REPAIR_JOB_ID)
        completed = list(state.get("JOB_IDS") or [])
        completed = [job for job in completed if job == "job_e33989d3e27e4dc89b1c976aabd9d5da"]
        state.update({
            "DURABLE_OBJECTIVE_SCHEMA": "nexus.durable-owner-objective.v1",
            "CAMPAIGN_ID": V5_CAMPAIGN_ID,
            "OWNER_OBJECTIVE_ID": V5_OBJECTIVE_ID,
            "MASTER_OBJECTIVE": MASTER_OBJECTIVE,
            "OBJECTIVE_VERSION": OBJECTIVE_VERSION,
            "OWNER": "RAY",
            "CAMPAIGN_STATUS": state.get("CAMPAIGN_STATUS", "ACTIVE") if already_canonical else "ACTIVE",
            "CURRENT_PHASE": state.get("CURRENT_PHASE") if already_canonical else "CONTROL_PLANE_REPAIR",
            "CURRENT_JOB_ID": selected_job_id,
            "CURRENT_JOB_TYPE": state.get("CURRENT_JOB_TYPE", current_job_type) if already_canonical else current_job_type,
            "ASSIGNED_DEPARTMENT": state.get("ASSIGNED_DEPARTMENT", assigned_department) if already_canonical else assigned_department,
            "ASSIGNED_WORKER": state.get("ASSIGNED_WORKER", assigned_worker) if already_canonical else assigned_worker,
            "WORKER_ROLE": state.get("WORKER_ROLE", worker_role) if already_canonical else worker_role,
            "CHECKPOINT": state.get("CHECKPOINT") if already_canonical else {
                "checkpoint_ref": "reports/certification/NEXUS_FULL_OWNER_REAL_WORLD_V5_STATE_20261010.json",
                "previous_phase": previous_phase,
                "last_completed_phase": state.get("LAST_COMPLETED_PHASE"),
                "next_phase": "PHASE_3_GLOBAL_ONLINE_BUSINESS_RESEARCH",
                "next_action": "RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
                "v1_preserved": True,
            },
            "COMPLETED_JOBS": completed,
            "REMAINING_JOBS": state.get("REMAINING_JOBS", ["RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY", "ALL_REMAINING_V5_OWNER_DELIVERABLES"]) if already_canonical else ["RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY", "ALL_REMAINING_V5_OWNER_DELIVERABLES"],
            "NEXT_REQUIRED_JOB": state.get("NEXT_REQUIRED_JOB") if already_canonical else {
                "job_id": NEXT_JOB_ID,
                "job_type": "RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
                "department": "RESEARCH",
                "status": "NOT_CREATED_PENDING_OWNER_RESUME",
            },
            "TERMINAL_CONDITION": TERMINAL_CONDITION,
            "TERMINAL_CONDITION_SATISFIED": state.get("TERMINAL_CONDITION_SATISFIED", "NO") if already_canonical else "NO",
            "LAST_VALID_TRANSITION": state.get("LAST_VALID_TRANSITION") if already_canonical else {
                "from": previous_phase,
                "to": "CONTROL_PLANE_REPAIR",
                "job_id": selected_job_id,
                "at": utc_now(),
                "reason": "V5 master-objective persistence defect repair",
            },
            "LAST_HEARTBEAT": utc_now(),
            "UPDATED_AT": utc_now(),
        })
        _atomic_write(path, state)
        return state


def load_active_campaign(path: Path = ACTIVE_CAMPAIGN_PATH) -> dict[str, Any]:
    state = _read(path)
    required = ("CAMPAIGN_ID", "OWNER_OBJECTIVE_ID", "MASTER_OBJECTIVE", "OBJECTIVE_VERSION",
                "CURRENT_JOB_ID", "WORKER_ROLE", "TERMINAL_CONDITION", "TERMINAL_CONDITION_SATISFIED")
    missing = [key for key in required if not state.get(key)]
    if missing:
        raise ObjectiveControlError("ACTIVE_CAMPAIGN_FIELDS_MISSING:" + ",".join(missing))
    if state.get("CAMPAIGN_STATUS") in {"COMPLETE", "PASS", "COMPLETED"} and state.get("TERMINAL_CONDITION_SATISFIED") != "YES":
        raise ObjectiveControlError("FALSE_CAMPAIGN_TERMINATION_REJECTED")
    return state


def recover_worker_context(*, worker_id: str, job_id: str, campaign_id: str | None,
                           objective_id: str | None, objective_version: str | None,
                           worker_role: str, path: Path = ACTIVE_CAMPAIGN_PATH) -> dict[str, Any]:
    """Resolve worker context from durable state; supplied chat/context is never authoritative."""
    state = load_active_campaign(path)
    if state.get("CAMPAIGN_STATUS") not in {"ACTIVE", "IN_PROGRESS"}:
        raise ObjectiveControlError("NO_ACTIVE_DURABLE_CAMPAIGN")
    if campaign_id != state["CAMPAIGN_ID"] or objective_id != state["OWNER_OBJECTIVE_ID"]:
        raise ObjectiveControlError("WORKER_CAMPAIGN_OR_OBJECTIVE_MISMATCH")
    if objective_version != state["OBJECTIVE_VERSION"]:
        raise ObjectiveControlError("WORKER_OBJECTIVE_VERSION_MISMATCH")
    if job_id != state["CURRENT_JOB_ID"]:
        raise ObjectiveControlError("WORKER_JOB_NOT_CURRENT")
    allowed_role = state.get("WORKER_ROLE")
    if worker_role != allowed_role:
        raise ObjectiveControlError("WORKER_ROLE_MISMATCH")
    return {
        "campaign_id": state["CAMPAIGN_ID"], "objective_id": state["OWNER_OBJECTIVE_ID"],
        "master_objective": state["MASTER_OBJECTIVE"], "objective_version": state["OBJECTIVE_VERSION"],
        "job_id": state["CURRENT_JOB_ID"], "worker_role": allowed_role,
        "checkpoint": state.get("CHECKPOINT"), "next_required_job": state.get("NEXT_REQUIRED_JOB"),
        "ignore_stale_task": True, "worker_id": worker_id,
    }


def recover_after_context_compaction(stale_context: Mapping[str, Any] | None = None,
                                    path: Path = ACTIVE_CAMPAIGN_PATH) -> dict[str, Any]:
    """Resume solely from the active record; prior chat/task labels are hints only."""
    state = load_active_campaign(path)
    old = dict(stale_context or {})
    stale = bool(old) and (old.get("campaign_id") != state.get("CAMPAIGN_ID")
                           or old.get("objective_id") != state.get("OWNER_OBJECTIVE_ID")
                           or old.get("objective_version") != state.get("OBJECTIVE_VERSION"))
    return {"campaign_id": state["CAMPAIGN_ID"], "objective_id": state["OWNER_OBJECTIVE_ID"],
            "master_objective": state["MASTER_OBJECTIVE"], "objective_version": state["OBJECTIVE_VERSION"],
            "current_job_id": state["CURRENT_JOB_ID"], "current_job_type": state["CURRENT_JOB_TYPE"],
            "worker_role": state["WORKER_ROLE"], "checkpoint": state["CHECKPOINT"],
            "next_required_job": state["NEXT_REQUIRED_JOB"], "stale_context_ignored": stale,
            "ignore_stale_task": True}


def complete_intermediate_job(state: Mapping[str, Any], *, job_id: str,
                              next_job: Mapping[str, Any]) -> dict[str, Any]:
    """An intermediate completion creates the next job and cannot end the campaign."""
    result = dict(state)
    if job_id != result.get("CURRENT_JOB_ID"):
        raise ObjectiveControlError("ONLY_CURRENT_JOB_MAY_COMPLETE")
    result["COMPLETED_JOBS"] = list(dict.fromkeys([*(result.get("COMPLETED_JOBS") or []), job_id]))
    result["CURRENT_JOB_ID"] = str(next_job["job_id"])
    result["CURRENT_JOB_TYPE"] = str(next_job["job_type"])
    result["ASSIGNED_DEPARTMENT"] = str(next_job["department"])
    result["ASSIGNED_WORKER"] = str(next_job.get("worker", "Nexus"))
    result["WORKER_ROLE"] = str(next_job.get("worker_role", "DEPARTMENT_EXECUTION"))
    result["NEXT_REQUIRED_JOB"] = dict(next_job)
    result["CAMPAIGN_STATUS"] = "ACTIVE"
    result["TERMINAL_CONDITION_SATISFIED"] = "NO"
    result["CONTINUATION_DECISION"] = "CONTINUE_BY_DEFAULT"
    result["ALLOWED_OBJECTIVE_STOP_CLASSES"] = sorted(OBJECTIVE_STOP_CLASSES)
    result["LAST_VALID_TRANSITION"] = {"from_job": job_id, "to_job": result["CURRENT_JOB_ID"], "at": utc_now()}
    result["UPDATED_AT"] = utc_now()
    return result


def finish_campaign(state: Mapping[str, Any], *, all_required_jobs_complete: bool,
                    complete_owner_experience: bool) -> dict[str, Any]:
    result = dict(state)
    terminal = bool(all_required_jobs_complete and complete_owner_experience)
    result["TERMINAL_CONDITION_SATISFIED"] = "YES" if terminal else "NO"
    if terminal:
        result["CAMPAIGN_STATUS"] = "COMPLETE"
        result["CONTINUATION_DECISION"] = "TERMINAL_OBJECTIVE_SATISFIED"
    else:
        result["CAMPAIGN_STATUS"] = "ACTIVE"
        result["CREATE_NEXT_JOB"] = "YES"
        result["CONTINUE_CAMPAIGN"] = "YES"
        result["CONTINUATION_DECISION"] = "CONTINUE_BY_DEFAULT"
        result["ALLOWED_OBJECTIVE_STOP_CLASSES"] = sorted(OBJECTIVE_STOP_CLASSES)
    result["UPDATED_AT"] = utc_now()
    return result


def complete_current_and_create_next(state: Mapping[str, Any], *, job_id: str,
                                     next_job: Mapping[str, Any] | None,
                                     enqueue: Any,
                                     all_required_jobs_complete: bool = False,
                                     complete_owner_experience: bool = False) -> dict[str, Any]:
    """Controller-owned transition; durable enqueue is idempotent by event key."""
    if job_id != state.get("CURRENT_JOB_ID"):
        raise ObjectiveControlError("ONLY_CURRENT_JOB_MAY_COMPLETE")
    if all_required_jobs_complete and complete_owner_experience:
        return finish_campaign(state, all_required_jobs_complete=True, complete_owner_experience=True)
    if not next_job:
        raise ObjectiveControlError("NEXT_JOB_REQUIRED_WHILE_TERMINAL_FALSE")
    context = {"campaign_id": state["CAMPAIGN_ID"],
               "owner_objective_id": state["OWNER_OBJECTIVE_ID"],
               "objective_version": state["OBJECTIVE_VERSION"],
               "master_objective": state["MASTER_OBJECTIVE"]}
    key = f"objective-next:{state['CAMPAIGN_ID']}:{job_id}:{next_job['job_type']}"
    created = enqueue(department=next_job["department"], job_type=next_job["job_type"],
                      payload_ref=next_job.get("payload_ref"), parent_job_id=job_id,
                      correlation_id=state.get("CORRELATION_IDS", [None])[0],
                      idempotency_key=key, governance_context=context)
    next_record = {**dict(next_job), "job_id": getattr(created, "job_id", None) or created["job_id"],
                   "status": "READY", "idempotency_key": key}
    return complete_intermediate_job(state, job_id=job_id, next_job=next_record)


def persist_campaign(state: Mapping[str, Any], path: Path = ACTIVE_CAMPAIGN_PATH) -> None:
    if state.get("CAMPAIGN_STATUS") in {"COMPLETE", "PASS", "COMPLETED"} and state.get("TERMINAL_CONDITION_SATISFIED") != "YES":
        raise ObjectiveControlError("FALSE_CAMPAIGN_TERMINATION_REJECTED")
    with _lock(path):
        _atomic_write(path, state)


def _is_bounded_runtime_canary_descendant(job: Any, store: Any,
                                          state: Mapping[str, Any]) -> bool:
    """Validate the one bounded Research→Needle canary lineage and its repair."""
    job_type=getattr(job,"job_type",None)
    context=getattr(job,"governance_context",None) or {}
    if job_type not in {"NEEDLE_RESEARCH_READINESS_VERIFY","NEEDLE_RESEARCH_TARGETED_REPAIR"}:
        return False
    if (getattr(job,"department",None)!="RESEARCH"
            or context.get("source")!="NOTEBOOK_COMPLETION_CONTRACT_NEEDLE"
            or context.get("runtime_restoration_canary") is not True
            or context.get("independent_job") is not True
            or context.get("no_new_owner_objective") is not True
            or context.get("spend_allowed") is not False
            or context.get("paid_provider_authorized") is not False
            or context.get("external_actions_allowed") is not False
            or not context.get("research_case_id")
            or not context.get("contract_completion_receipt_id")
            or context.get("campaign_id")!=state.get("CAMPAIGN_ID")
            or context.get("owner_objective_id")!=state.get("OWNER_OBJECTIVE_ID")
            or context.get("objective_version")!=state.get("OBJECTIVE_VERSION")):
        return False
    repair=int(context.get("repair_attempt",-1))
    if job_type=="NEEDLE_RESEARCH_READINESS_VERIFY":
        if context.get("resource_dependencies") != ["OPENAI_CODEX"] or repair not in {0,1}:
            return False
        expected_parent=("NEXUS_NOTEBOOKLM_RUNTIME_CANARY" if repair==0
                         else "NEEDLE_RESEARCH_TARGETED_REPAIR")
    else:
        if repair!=1 or context.get("resource_dependencies") != ["NOTEBOOKLM"]:
            return False
        expected_parent="NEEDLE_RESEARCH_READINESS_VERIFY"
    parent_id=getattr(job,"parent_job_id",None)
    parent=store.get(parent_id) if parent_id else None
    if not parent or getattr(parent,"state",None)!="COMPLETED" or getattr(parent,"job_type",None)!=expected_parent:
        return False
    if getattr(parent,"department",None)!="RESEARCH":
        return False
    parent_context=getattr(parent,"governance_context",None) or {}
    if expected_parent=="NEXUS_NOTEBOOKLM_RUNTIME_CANARY":
        return bool(
            getattr(parent,"parent_job_id",None)==state.get("CURRENT_JOB_ID")
            and parent_context.get("source")=="NOVA_MCP_NOTEBOOKLM_CANARY"
            and parent_context.get("runtime_restoration_canary") is True
            and parent_context.get("spend_allowed") is False
            and parent_context.get("paid_provider_authorized") is False
            and parent_context.get("external_actions_allowed") is False
            and parent_context.get("resource_dependencies")==["NOTEBOOKLM"]
            and parent_context.get("campaign_id")==state.get("CAMPAIGN_ID")
            and parent_context.get("owner_objective_id")==state.get("OWNER_OBJECTIVE_ID")
            and parent_context.get("objective_version")==state.get("OBJECTIVE_VERSION"))
    parent_repair=int(parent_context.get("repair_attempt",-1))
    if (parent_context.get("source")!="NOTEBOOK_COMPLETION_CONTRACT_NEEDLE"
            or parent_context.get("research_case_id")!=context.get("research_case_id")
            or parent_context.get("contract_completion_receipt_id")!=context.get("contract_completion_receipt_id")
            or parent_context.get("campaign_id")!=state.get("CAMPAIGN_ID")
            or parent_context.get("owner_objective_id")!=state.get("OWNER_OBJECTIVE_ID")
            or parent_context.get("objective_version")!=state.get("OBJECTIVE_VERSION")
            or parent_context.get("spend_allowed") is not False
            or parent_context.get("paid_provider_authorized") is not False
            or parent_context.get("external_actions_allowed") is not False):
        return False
    if expected_parent=="NEEDLE_RESEARCH_TARGETED_REPAIR":
        return parent_repair==1 and parent_context.get("resource_dependencies")==["NOTEBOOKLM"]
    return (parent_repair==0 and parent_context.get("resource_dependencies")==["OPENAI_CODEX"])


def authorize_job_start(job: Any, *, path: Path = ACTIVE_CAMPAIGN_PATH,
                        store: Any | None = None) -> dict[str, Any] | None:
    """Reject stale/unbound jobs while V5 owns the active objective lane."""
    if not path.exists():
        return None
    state = load_active_campaign(path)
    if state.get("CAMPAIGN_STATUS") not in {"ACTIVE", "IN_PROGRESS"}:
        return None
    context = getattr(job, "governance_context", None) or {}
    identity_matches=(context.get("campaign_id") == state.get("CAMPAIGN_ID")
            and context.get("owner_objective_id") == state.get("OWNER_OBJECTIVE_ID")
            and context.get("objective_version") == state.get("OBJECTIVE_VERSION"))
    current_job_matches=getattr(job,"job_id",None)==state.get("CURRENT_JOB_ID")
    bounded_research_notice=(
        getattr(job,"job_type",None)=="NOVA_RESEARCH_RESULT_NOTICE"
        and getattr(job,"parent_job_id",None)==state.get("CURRENT_JOB_ID")
        and context.get("campaign_id")==state.get("CAMPAIGN_ID")
        and context.get("owner_objective_id")==state.get("OWNER_OBJECTIVE_ID")
        and context.get("objective_version")==state.get("OBJECTIVE_VERSION")
        and context.get("source")=="NEXUS_RESEARCH_COMPLETION_NOTICE"
        and bool(context.get("completed_research_job_id"))
        and bool(context.get("completed_research_receipt_id"))
        and context.get("spend_allowed") is False
        and context.get("paid_provider_authorized") is False
        and context.get("external_actions_allowed") is True)
    bounded_systems_notice=(
        getattr(job,"job_type",None)=="NOVA_SYSTEMS_RESULT_NOTICE"
        and getattr(job,"parent_job_id",None)==state.get("CURRENT_JOB_ID")
        and context.get("campaign_id")==state.get("CAMPAIGN_ID")
        and context.get("owner_objective_id")==state.get("OWNER_OBJECTIVE_ID")
        and context.get("objective_version")==state.get("OBJECTIVE_VERSION")
        and context.get("source")=="NEXUS_SYSTEMS_COMPLETION_NOTICE"
        and bool(context.get("completed_systems_job_id"))
        and bool(context.get("completed_systems_receipt_id"))
        and context.get("spend_allowed") is False
        and context.get("paid_provider_authorized") is False
        and context.get("external_actions_allowed") is True)
    bounded_alpha_notice=(
        getattr(job,"job_type",None) in {"NOVA_ALPHA_ASSIGNMENT_NOTICE","NOVA_ALPHA_RESULT_NOTICE"}
        and getattr(job,"parent_job_id",None)==state.get("CURRENT_JOB_ID")
        and context.get("campaign_id")==state.get("CAMPAIGN_ID")
        and context.get("owner_objective_id")==state.get("OWNER_OBJECTIVE_ID")
        and context.get("objective_version")==state.get("OBJECTIVE_VERSION")
        and context.get("alpha_job_id")
        and context.get("source")==("NOVA_ALPHA_ASSIGNMENT_NOTICE" if getattr(job,"job_type",None)=="NOVA_ALPHA_ASSIGNMENT_NOTICE" else "NEXUS_ALPHA_COMPLETION_NOTICE")
        and context.get("spend_allowed") is False
        and context.get("paid_provider_authorized") is False
        and context.get("external_actions_allowed") is True)
    # A direct, bounded Research assignment explicitly requested through the
    # live Nova action is a separate owner task. It may run alongside the
    # active campaign only when the MCP action marked it non-spend and
    # non-external; it cannot mutate or advance that campaign.
    nova_research_assignment=(
        getattr(job,"department",None)=="RESEARCH"
        and getattr(job,"job_type",None) in {"RESEARCH_GAP_VERIFY", "RESEARCH_RUNTIME_INSPECT", "NOTEBOOKLM_RESEARCH"}
        and context.get("source")=="NOVA_MCP_RESEARCH_ASSIGNMENT"
        and bool(context.get("objective_id"))
        and (context.get("spend_allowed") is False
             or "spend_allowed" not in context and context.get("external_actions_authorized") is False)
        and (context.get("external_actions_allowed") is False
             or "external_actions_allowed" not in context and context.get("external_actions_authorized") is False)
        and context.get("paid_provider_authorized") is False
    )
    independent_parallel=False
    bounded_runtime_canary_child=bool(identity_matches and store is not None
        and _is_bounded_runtime_canary_descendant(job,store,state))
    if identity_matches and not current_job_matches and context.get("independent_job") is True:
        waiting=state.get("WAITING_RESOURCE_JOBS") or []
        paused={str(row.get("resource") or "").upper() for row in waiting
                if isinstance(row,dict) and row.get("status")=="WAITING_RESOURCE_WINDOW"}
        required={str(item).upper() for item in (context.get("resource_dependencies") or [])}
        bounded_nova_notice=(getattr(job,"job_type",None)=="NOVA_RESOURCE_ALERT_RETRY"
            and context.get("retained_event_id") is not None
            and context.get("external_actions_allowed") is True)
        bounded_runtime_canary=(getattr(job,"job_type",None)=="NEXUS_NOTEBOOKLM_RUNTIME_CANARY"
            and context.get("source")=="NOVA_MCP_NOTEBOOKLM_CANARY"
            and context.get("runtime_restoration_canary") is True
            and context.get("spend_allowed") is False
            and context.get("external_actions_allowed") is False
            and context.get("resource_dependencies")==["NOTEBOOKLM"])
        independent_parallel=(getattr(job,"parent_job_id",None)==state.get("CURRENT_JOB_ID")
            and bool(paused) and not (paused & required)
            and context.get("spend_allowed") is False
            and (context.get("external_actions_allowed") is False or bounded_nova_notice)
            or getattr(job,"parent_job_id",None)==state.get("CURRENT_JOB_ID")
            and bounded_runtime_canary
            or bounded_research_notice or bounded_systems_notice or bounded_alpha_notice
            or bounded_runtime_canary_child)
    if not (identity_matches or nova_research_assignment or bounded_research_notice or bounded_systems_notice or bounded_alpha_notice) or not (
            current_job_matches or independent_parallel or nova_research_assignment or bounded_research_notice or bounded_systems_notice or bounded_alpha_notice):
        raise ObjectiveControlError("JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN")
    return {"campaign_id": state["CAMPAIGN_ID"], "objective_id": state["OWNER_OBJECTIVE_ID"],
            "master_objective": state["MASTER_OBJECTIVE"], "job_id": state["CURRENT_JOB_ID"],
            "checkpoint": state.get("CHECKPOINT"), "worker_role": state.get("WORKER_ROLE"),
            "independent_parallel_job":independent_parallel,
            "bounded_runtime_canary_child":bounded_runtime_canary_child,
            "nova_research_assignment":nova_research_assignment,
            "ignore_stale_task": True}


def authorize_coding_action(*, campaign_id: str | None, objective_id: str | None, job_id: str | None,
                            objective_version: str | None, worker_role: str, action_summary: str,
                            path: Path = ACTIVE_CAMPAIGN_PATH) -> dict[str, Any]:
    try:
        context = recover_worker_context(worker_id=worker_role.lower(), job_id=str(job_id or ""),
                                         campaign_id=campaign_id, objective_id=objective_id,
                                         objective_version=objective_version, worker_role=worker_role, path=path)
    except ObjectiveControlError:
        # A repair-only coding task may run as an independent V5 DAG job when
        # the durable job is bound to this objective and has no external side
        # effects. The ordinary current-job rule remains the default.
        from nexus_agent_platform.durable_jobs import default_store
        job=default_store().get(str(job_id or ""))
        if not job or job.job_type!="V5_OPENCODE_MODEL_BENCHMARK":
            raise
        state=load_active_campaign(path)
        identity=(campaign_id==state.get("CAMPAIGN_ID")
            and objective_id==state.get("OWNER_OBJECTIVE_ID")
            and objective_version==state.get("OBJECTIVE_VERSION"))
        if not identity or worker_role!="CODING_AND_SYSTEM_REPAIR_ONLY":
            raise ObjectiveControlError("INDEPENDENT_CODING_JOB_IDENTITY_MISMATCH")
        authorized=authorize_job_start(job,path=path)
        if not authorized or not authorized.get("independent_parallel_job"):
            raise ObjectiveControlError("INDEPENDENT_CODING_JOB_NOT_AUTHORIZED")
        context={**authorized,"job_id":job.job_id,"worker_role":worker_role,
            "independent_parallel_job":True,"ignore_stale_task":True}
    lower = action_summary.lower()
    prohibited = ("business plan", "marketing campaign", "finance output", "funding output",
                  "creative asset", "nova answer", "trading analysis", "notebooklm research",
                  "social post", "publish campaign", "send campaign email")
    if any(term in lower for term in prohibited):
        raise ObjectiveControlError("CODEX_DEPARTMENT_SUBSTITUTION_BLOCKED")
    if worker_role != "CODING_AND_SYSTEM_REPAIR_ONLY":
        raise ObjectiveControlError("CODEX_ROLE_NOT_REPAIR_ONLY")
    return context


__all__ = ["ACTIVE_CAMPAIGN_PATH", "ObjectiveControlError", "ensure_v5_record", "load_active_campaign",
           "recover_worker_context", "recover_after_context_compaction", "complete_intermediate_job", "finish_campaign", "persist_campaign",
           "authorize_job_start", "authorize_coding_action", "complete_current_and_create_next"]
