"""Controller-owned durable workflow primitives for Nexus."""
from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.nexus_agent_platform import agent_control_plane as ac
from scripts.nexus_agent_platform.durable_jobs import JobError

ROOT = Path(__file__).resolve().parents[2]
DEFINITION = ROOT / "configs/workflows/nexus_business_to_campaign_r1.json"
CRONBOTS = ROOT / "configs/nexus_workflow_cronbots.json"
WORKFLOW_STATUSES = {"QUEUED", "PLANNING", "RUNNING", "WAITING_DEPENDENCY", "WAITING_APPROVAL",
    "RETRY_SCHEDULED", "PARTIAL", "ESCALATED", "PAUSED", "COMPLETED", "CANCELLED_BY_OWNER", "FAILED_TERMINAL_SYSTEM"}
STEP_STATUSES = {"COMPLETE", "PARTIAL", "RETRY", "WAITING_DEPENDENCY", "WAITING_APPROVAL", "ESCALATE",
    "BLOCKED_EXTERNAL", "RESOURCE_BUDGET_EXCEEDED", "CAPABILITY_UNAVAILABLE", "VALIDATION_FAILED"}
WORKER_TERMINAL_STATUSES = {"FAILED_TERMINAL_SYSTEM", "COMPLETED", "CANCELLED_BY_OWNER"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def load_definition(workflow_type: str = "NEXUS_BUSINESS_TO_CAMPAIGN_R1") -> dict[str, Any]:
    value = json.loads(DEFINITION.read_text(encoding="utf-8"))
    if value.get("workflow_type") != workflow_type or value.get("ai_worker_can_terminate_workflow") is not False:
        raise ValueError("WORKFLOW_DEFINITION_INVALID")
    return value


def new_workflow(*, objective: str, owner: str, created_by: str,
                 workflow_type: str = "NEXUS_BUSINESS_TO_CAMPAIGN_R1",
                 priority: str = "NORMAL", success_criteria: list[str] | None = None,
                 campaign_id: str | None = None, research_room_id: str | None = None,
                 parent_workflow_id: str | None = None) -> dict[str, Any]:
    if not objective.strip() or owner not in {"NOVA", "RAY", "SYSTEM"}:
        raise ValueError("INVALID_WORKFLOW_REQUEST")
    definition = load_definition(workflow_type)
    now = utcnow()
    steps = [{**s, "status": "QUEUED", "attempt_count": 0, "result": None, "receipt_id": None, "last_error": None}
             for s in definition["steps"]]
    return {"workflow_id": "wf_" + uuid.uuid4().hex, "workflow_type": workflow_type, "objective": objective,
        "owner": owner, "created_by": created_by, "domain": "COMPANY", "status": "QUEUED",
        "current_step": steps[0]["step_id"], "current_domain_agent": steps[0]["owner"], "priority": priority,
        "created_at": now, "updated_at": now, "started_at": None, "completed_at": None,
        "success_criteria": success_criteria or [], "approval_state": "NOT_REQUIRED",
        "dependencies": {s["step_id"]: list(s.get("depends_on", [])) for s in steps}, "blockers": [],
        "retry_count": 0, "max_retries": max((s.get("max_retries", 0) for s in steps), default=0),
        "next_retry_at": None, "estimated_cost": 0.0, "actual_cost": 0.0,
        "token_usage": {"input": 0, "output": 0, "model_calls": 0}, "artifact_ids": [], "handoff_ids": [],
        "work_order_ids": [], "campaign_id": campaign_id, "research_room_id": research_room_id,
        "parent_workflow_id": parent_workflow_id, "child_workflow_ids": [], "last_certified_step": None,
        "next_action": "PLAN", "completion_receipt_id": None, "definition_version": definition["schema_version"],
        "definition_hash": _hash(definition), "revision": 1, "steps": steps, "receipts": [], "handoffs": [],
        "completion_receipt": None, "notification_outbox": [], "dependency_tasks": [],
        "ai_worker_cannot_terminate_workflow": True}


def context_packet(workflow: dict[str, Any], step: dict[str, Any], *, relevant_facts: list[Any] | None = None,
                   evidence: list[Any] | None = None, max_items: int = 12, max_chars: int = 12000) -> dict[str, Any]:
    """Construct a bounded handoff packet; never accepts or includes raw transcripts."""
    packet = {"workflow_id": workflow["workflow_id"], "objective": workflow["objective"],
        "current_step": step["step_id"], "current_domain_agent": step["owner"],
        "relevant_facts": (relevant_facts or [])[:max_items], "evidence": (evidence or [])[:max_items],
        "artifact_ids": list(workflow.get("artifact_ids", []))[:max_items],
        "constraints": load_definition(workflow["workflow_type"]).get("governance", {}),
        "approval_state": workflow.get("approval_state"), "recent_handoff": copy.deepcopy(workflow.get("handoffs", [])[-1:]),
        "success_criteria": workflow.get("success_criteria", [])[:max_items]}
    if len(json.dumps(packet, separators=(",", ":"), default=str)) > max_chars:
        packet.update(relevant_facts=[], evidence=[], recent_handoff=[], context_truncated=True)
    return packet


def create_handoff(workflow: dict[str, Any], *, source_step: str, source_bot: str,
                   source_domain_agent: str, target_domain_agent: str, objective: str, summary: str,
                   evidence: list[Any] | None = None, artifacts: list[str] | None = None,
                   decisions: list[Any] | None = None, constraints: list[str] | None = None,
                   open_questions: list[str] | None = None, recommended_next_action: str = "CONTINUE",
                   approval_required: bool = False) -> dict[str, Any]:
    handoff = {"handoff_id": "ho_" + uuid.uuid4().hex, "source_workflow": workflow["workflow_id"],
        "source_step": source_step, "source_bot": source_bot, "source_domain_agent": source_domain_agent,
        "target_workflow": workflow["workflow_id"], "target_step": None, "target_domain_agent": target_domain_agent,
        "objective": objective, "summary": summary[:4000], "evidence": (evidence or [])[:20],
        "artifacts": (artifacts or [])[:50], "decisions": (decisions or [])[:20], "constraints": (constraints or [])[:20],
        "open_questions": (open_questions or [])[:20], "recommended_next_action": recommended_next_action,
        "approval_required": bool(approval_required), "created_at": utcnow(), "accepted_at": None, "status": "READY_FOR_TARGET"}
    workflow["handoffs"].append(handoff)
    workflow["handoff_ids"].append(handoff["handoff_id"])
    return handoff


def continue_workflow(workflow: dict[str, Any], step: dict[str, Any], result: dict[str, Any], *,
                      retry_history: list[dict[str, Any]] | None = None, available_models: set[str] | None = None,
                      available_bots: set[str] | None = None, available_environments: set[str] | None = None,
                      dependencies_satisfied: bool = True, approval_granted: bool = False,
                      cost_allowed: bool = True) -> dict[str, Any]:
    """Pure deterministic policy: a worker result can never terminate its workflow."""
    outcome = str(result.get("status", "VALIDATION_FAILED"))
    if outcome in WORKER_TERMINAL_STATUSES or outcome not in STEP_STATUSES:
        outcome = "VALIDATION_FAILED"
    if not cost_allowed or outcome == "RESOURCE_BUDGET_EXCEEDED":
        return {"decision": "WAIT", "workflow_status": "PARTIAL", "reason": "RESOURCE_BUDGET_EXCEEDED"}
    if outcome == "WAITING_APPROVAL" or (step.get("approval_required") and not approval_granted):
        return {"decision": "WAIT_FOR_APPROVAL", "workflow_status": "WAITING_APPROVAL"}
    if outcome == "WAITING_DEPENDENCY" or not dependencies_satisfied:
        return {"decision": "WAIT_FOR_DEPENDENCY", "workflow_status": "WAITING_DEPENDENCY"}
    if outcome == "COMPLETE":
        return {"decision": "NEXT_STEP", "workflow_status": "RUNNING"}
    if outcome == "PARTIAL":
        return {"decision": "RETRY_SAME_WORKER", "workflow_status": "PARTIAL", "preserve_partial": True}
    attempt, limit = int(step.get("attempt_count", 0)), int(step.get("max_retries", 0))
    if outcome == "RETRY" and attempt < limit:
        return {"decision": "RETRY_SAME_WORKER", "workflow_status": "RETRY_SCHEDULED",
                "preserve_partial": bool(result.get("partial_output"))}
    fallback = step.get("fallback_model_profile")
    if fallback and fallback in (available_models or set()):
        return {"decision": "RETRY_ALTERNATE_MODEL_PROFILE", "workflow_status": "RETRY_SCHEDULED",
                "preserve_partial": bool(result.get("partial_output"))}
    if step.get("alternate_bot_id") in (available_bots or set()):
        return {"decision": "RETRY_ALTERNATE_WORKER", "workflow_status": "RETRY_SCHEDULED",
                "preserve_partial": bool(result.get("partial_output"))}
    if step.get("fallback_environment_id") in (available_environments or set()):
        return {"decision": "RETRY_ALTERNATE_ENVIRONMENT", "workflow_status": "RETRY_SCHEDULED",
                "preserve_partial": bool(result.get("partial_output"))}
    if step.get("independent_branches"):
        return {"decision": "CONTINUE_INDEPENDENT_BRANCH", "workflow_status": "PARTIAL", "preserve_partial": True}
    if attempt < limit:
        return {"decision": "SCHEDULE_RETRY", "workflow_status": "RETRY_SCHEDULED",
                "preserve_partial": bool(result.get("partial_output"))}
    return {"decision": "ESCALATE", "workflow_status": "ESCALATED", "preserve_partial": bool(result.get("partial_output")),
            "reason": outcome, "retry_history_count": len(retry_history or [])}


class WorkflowStateStore:
    """Workflow envelope persisted in the canonical nexus_durable_jobs row."""
    def __init__(self, jobs: Any):
        self.jobs = jobs

    @staticmethod
    def _envelope(job: Any) -> dict[str, Any]:
        return dict((job.governance_context or {}).get("workflow_fabric") or {})

    def create(self, workflow: dict[str, Any]) -> str:
        key = "workflow-fabric:" + workflow["workflow_id"]
        # Far-future schedule prevents generic workers from claiming this root.
        row = self.jobs.enqueue("SYSTEMS", "NEXUS_WORKFLOW_ROOT", scheduled_at="2099-01-01T00:00:00+00:00",
            max_attempts=1, idempotency_key=key,
            budget_envelope={"max_requests": 1, "max_response_bytes": 1000000, "max_tokens": 0, "max_gpu_seconds": 0,
                "max_runtime_seconds": 86400, "max_resource_creations": 0, "max_estimated_cost": 0.0, "max_retries": 1},
            governance_context={"workflow_fabric": workflow, "workflow_fabric_revision": workflow["revision"]})
        self.jobs.transition(row.job_id, "WAITING")
        workflow["durable_job_id"] = row.job_id
        context = dict(row.governance_context or {})
        context.update(workflow_fabric=workflow, workflow_fabric_revision=workflow["revision"])
        self.jobs.set_governance_context(row.job_id, context)
        return row.job_id

    def load(self, job_id: str) -> dict[str, Any]:
        row = self.jobs.get(job_id)
        if not row:
            raise JobError("WORKFLOW_NOT_FOUND")
        value = self._envelope(row)
        if not value:
            raise JobError("WORKFLOW_STATE_MISSING")
        return value

    def save(self, job_id: str, workflow: dict[str, Any]) -> None:
        row = self.jobs.get(job_id)
        if not row:
            raise JobError("WORKFLOW_NOT_FOUND")
        context = dict(row.governance_context or {})
        expected_revision = int(context.get("workflow_fabric_revision", 0))
        if int(workflow.get("revision", 0)) < expected_revision:
            raise JobError("WORKFLOW_REVISION_STALE")
        context["workflow_fabric"] = workflow
        context["workflow_fabric_revision"] = int(workflow.get("revision", 0))
        if hasattr(self.jobs, "_request") and not hasattr(self.jobs, "path"):
            from urllib.parse import quote
            path = (f"nexus_durable_jobs?job_id=eq.{quote(job_id, safe='')}"
                    f"&governance_context-%3E%3Eworkflow_fabric_revision=eq.{expected_revision}")
            rows = self.jobs._request(path, "PATCH", {"governance_context": context}, "return=representation")
            if not rows:
                raise JobError("WORKFLOW_REVISION_CONFLICT")
            return
        self.jobs.set_governance_context(job_id, context)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        if hasattr(self.jobs, "path"):
            jobs = self.jobs.list_workflow_roots(limit)
        else:
            from urllib.parse import quote
            rows = self.jobs._request(
                "nexus_durable_jobs?select=job_id,governance_context"
                "&governance_context->workflow_fabric->>workflow_id=not.is.null"
                f"&order=created_at.desc&limit={limit}")
            jobs = rows or []
        results = []
        for row in jobs:
            if isinstance(row, dict):
                value = (row.get("governance_context") or {}).get("workflow_fabric")
            else:
                value = self._envelope(row)
            if value:
                results.append(value)
        return results


class WorkflowController:
    def __init__(self, store: WorkflowStateStore, *, runtime_health: dict[str, str] | None = None,
                 handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
                 model_resolver: Callable[..., dict[str, Any]] | None = None):
        self.store, self.runtime_health, self.handlers = store, runtime_health or {}, handlers or {}
        self.model_resolver = model_resolver or ac.resolve_model_profile

    def create(self, **kwargs: Any) -> dict[str, Any]:
        workflow = new_workflow(**kwargs)
        job_id = self.store.create(workflow)
        workflow["durable_job_id"] = job_id
        self.store.save(job_id, workflow)
        return workflow

    @staticmethod
    def _connector_available(connector_id: str) -> bool:
        rows = {x.get("connector_id"): x for x in ac.public_registry_snapshot()["connectors"]}
        row = rows.get(connector_id)
        return bool(row and row.get("status") in {"ACTIVE", "AVAILABLE", "LIVE_CERTIFIED", "AVAILABLE_LIMITED", "PRACTICE_ONLY", "REGISTERED"})

    def authorize_step(self, workflow: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
        connectors = step.get("connector_ids", [])
        if any(not self._connector_available(c) for c in connectors):
            raise ac.AuthorizationDenied("CAPABILITY_UNAVAILABLE")
        choice = ac.route_bot_environment(agent_id=step["owner"], bot_id=step["bot_id"], runtime_health=self.runtime_health)
        if choice.get("status") != "SELECTED":
            raise ac.AuthorizationDenied("CAPABILITY_UNAVAILABLE")
        env = choice["environment_id"]
        for connector in connectors or [None]:
            ac.authorize(agent_id=step["owner"], bot_id=step["bot_id"], skill_id=step["skill_id"],
                connector_id=connector, environment_id=env, model_profile=step["model_profile"],
                runtime_health=self.runtime_health)
        profile = self.model_resolver(profile_id=step["model_profile"], agent_id=step["owner"], bot_id=step["bot_id"])
        if profile.get("status") not in {"AVAILABLE", "NO_MODEL"}:
            raise ac.AuthorizationDenied("CAPABILITY_UNAVAILABLE")
        return {"environment_id": env, "model_profile_status": profile["status"], "authorization": "AUTHORIZED"}

    def dispatch(self, workflow: dict[str, Any], step_id: str) -> dict[str, Any]:
        step = next((s for s in workflow["steps"] if s["step_id"] == step_id), None)
        if not step:
            raise ValueError("STEP_NOT_FOUND")
        completed = {s["step_id"] for s in workflow["steps"] if s["status"] == "COMPLETE"}
        if any(dep not in completed for dep in step.get("depends_on", [])):
            return self.record_result(workflow, step, {"status": "WAITING_DEPENDENCY",
                "error_code": "STEP_DEPENDENCY_NOT_COMPLETE", "worker_invoked": False})
        try:
            authorization = self.authorize_step(workflow, step)
        except ac.AuthorizationDenied as exc:
            state = "CAPABILITY_UNAVAILABLE" if "UNAVAILABLE" in str(exc) else "VALIDATION_FAILED"
            return self.record_result(workflow, step, {"status": state, "error_code": str(exc), "worker_invoked": False})
        handler = self.handlers.get(step["bot_id"])
        if handler is None:
            return self.record_result(workflow, step, {"status": "CAPABILITY_UNAVAILABLE",
                "error_code": "WORKER_HANDLER_NOT_REGISTERED", "worker_invoked": False, "authorization": authorization})
        try:
            result = handler(context_packet(workflow, step))
        except Exception as exc:
            result = {"status": "RETRY", "error_code": type(exc).__name__, "partial_output": None}
        return self.record_result(workflow, step, result)

    def record_result(self, workflow: dict[str, Any], step: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        status = str(result.get("status", "VALIDATION_FAILED"))
        if status in WORKER_TERMINAL_STATUSES or status not in STEP_STATUSES:
            status, result = "VALIDATION_FAILED", {"status": "VALIDATION_FAILED", "error_code": "WORKER_LIFECYCLE_MUTATION_REJECTED"}
        if step.get("approval_required") and status == "COMPLETE" and step.get("approval_state") != "APPROVED":
            status, result = "WAITING_APPROVAL", {"status": "WAITING_APPROVAL",
                "error_code": "APPROVAL_REQUIRED_BEFORE_STEP_COMPLETION", "partial_output": result.get("partial_output")}
        if step.get("bot_id") == "ASSET_PERSISTENCE" and status == "COMPLETE":
            required = ("canonical_asset_id", "r2_object_verified", "supabase_metadata_exists",
                        "campaign_link_exists", "generation_receipt_id")
            if not all(result.get(field) for field in required):
                status, result = "PARTIAL", {"status": "PARTIAL",
                    "error_code": "CANONICAL_ASSET_PERSISTENCE_INCOMPLETE",
                    "partial_output": result.get("partial_output")}
        step["status"] = status
        step["attempt_count"] = int(step.get("attempt_count", 0)) + (status != "COMPLETE")
        safe = {k: v for k, v in result.items() if k not in {"secret", "token", "credential_value", "api_key"}}
        step["result"] = safe
        step["last_error"] = result.get("error_code")
        step["receipt_id"] = "sr_" + _hash([workflow["workflow_id"], step["step_id"], step["attempt_count"], safe])[:24]
        workflow["receipts"].append({"receipt_id": step["receipt_id"], "step_id": step["step_id"], "status": status,
            "created_at": utcnow(), "error_code": step["last_error"], "partial_output": result.get("partial_output")})
        decision = continue_workflow(workflow, step, {**safe, "status": status})
        workflow["status"], workflow["next_action"] = decision["workflow_status"], decision["decision"]
        workflow["retry_count"] += decision["decision"] in {"RETRY_SAME_WORKER", "SCHEDULE_RETRY"}
        if status == "COMPLETE":
            workflow["last_certified_step"] = step["step_id"]
            next_step = next((s for s in workflow["steps"] if step["step_id"] in s.get("depends_on", []) and s["status"] == "QUEUED"), None)
            if next_step:
                workflow["current_step"], workflow["current_domain_agent"] = next_step["step_id"], next_step["owner"]
            elif all(s["status"] == "COMPLETE" for s in workflow["steps"]):
                workflow["status"], workflow["next_action"] = "PARTIAL", "COMPLETION_RECEIPT_REQUIRED"
        workflow["updated_at"], workflow["revision"] = utcnow(), int(workflow.get("revision", 0)) + 1
        return {"workflow_status": workflow["status"], "step_status": status, "continuation": decision, "receipt_id": step["receipt_id"]}

    def persist(self, workflow: dict[str, Any]) -> None:
        if not workflow.get("durable_job_id"):
            raise JobError("WORKFLOW_NOT_DURABLE")
        self.store.save(workflow["durable_job_id"], workflow)

    def pause(self, workflow: dict[str, Any]) -> None:
        workflow.update(status="PAUSED", updated_at=utcnow(), revision=workflow["revision"] + 1); self.persist(workflow)

    def park_for_dependency(self, workflow: dict[str, Any], *, dependency: str, reason: str) -> None:
        blocker = {"dependency": dependency, "reason": reason[:500], "created_at": utcnow()}
        if blocker not in workflow["blockers"]:
            workflow["blockers"].append(blocker)
        task = {"dependency_task_id": "dep_" + _hash([workflow["workflow_id"], dependency])[:24],
                "dependency": dependency, "status": "OPEN", "owner": "SYSTEMS_LEAD",
                "reason": reason[:500], "created_at": blocker["created_at"]}
        if not any(x.get("dependency_task_id") == task["dependency_task_id"] for x in workflow.get("dependency_tasks", [])):
            workflow.setdefault("dependency_tasks", []).append(task)
        workflow["status"] = "WAITING_DEPENDENCY"
        workflow["next_action"] = "WAIT_FOR_DEPENDENCY"
        workflow["updated_at"] = utcnow()
        workflow["revision"] = int(workflow["revision"]) + 1
        self.persist(workflow)

    @staticmethod
    def status_snapshot(workflow: dict[str, Any]) -> dict[str, Any]:
        current = next((s for s in workflow.get("steps", []) if s.get("step_id") == workflow.get("current_step")), {})
        return {"workflow_id": workflow["workflow_id"], "workflow_type": workflow["workflow_type"],
            "status": workflow["status"], "current_step": workflow.get("current_step"),
            "domain_owner": workflow.get("current_domain_agent"), "current_worker": current.get("bot_id"),
            "retry_state": {"count": workflow.get("retry_count", 0), "next_retry_at": workflow.get("next_retry_at")},
            "approval_state": workflow.get("approval_state"), "blockers": workflow.get("blockers", []),
            "artifacts": workflow.get("artifact_ids", []), "cost": workflow.get("actual_cost", 0),
            "token_usage": workflow.get("token_usage", {}), "environment": current.get("environment_id"),
            "next_action": workflow.get("next_action"), "completion_receipt_id": workflow.get("completion_receipt_id")}

    def resume(self, workflow: dict[str, Any]) -> None:
        if workflow["status"] not in {"PAUSED", "PARTIAL", "RETRY_SCHEDULED", "WAITING_DEPENDENCY", "ESCALATED"}:
            raise ValueError("WORKFLOW_NOT_RESUMABLE")
        workflow.update(status="RUNNING", updated_at=utcnow(), revision=workflow["revision"] + 1); self.persist(workflow)

    def resume_after_approval(self, workflow: dict[str, Any], approval_id: str) -> None:
        step = next((s for s in workflow["steps"] if s["step_id"] == workflow.get("current_step")), None)
        if workflow.get("status") != "WAITING_APPROVAL" or not step:
            raise ValueError("WORKFLOW_NOT_WAITING_FOR_APPROVAL")
        action_id = step.get("approval_action_id")
        if not action_id:
            raise ValueError("APPROVAL_ACTION_NOT_BOUND")
        from scripts.nexus_agent_platform.governed.approvals import (
            get_approval, is_approval_valid_for, mark_approval_consumed,
        )
        approval = get_approval(approval_id)
        if is_approval_valid_for(approval or {}, action_id, step.get("approval_inputs")):
            raise PermissionError("APPROVAL_INVALID")
        step["approval_state"], step["approval_id"] = "APPROVED", approval_id
        workflow["approval_state"], workflow["status"] = "APPROVED", "RUNNING"
        workflow["next_action"], workflow["updated_at"] = "RESUME_BLOCKED_STEP", utcnow()
        workflow["revision"] += 1
        self.persist(workflow)
        mark_approval_consumed(approval_id)

    def cancel_by_owner(self, workflow: dict[str, Any], actor: str) -> None:
        if actor not in {workflow.get("owner"), "RAY"}:
            raise PermissionError("OWNER_CANCEL_ONLY")
        workflow.update(status="CANCELLED_BY_OWNER", completed_at=utcnow(), revision=workflow["revision"] + 1); self.persist(workflow)

    def certify_completion(self, workflow: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        if any(s["status"] != "COMPLETE" for s in workflow["steps"]):
            raise ValueError("WORKFLOW_STEPS_INCOMPLETE")
        duration = None
        if workflow.get("started_at"):
            try:
                duration = max(0, int((datetime.fromisoformat(utcnow()) -
                                       datetime.fromisoformat(workflow["started_at"])).total_seconds()))
            except (TypeError, ValueError):
                duration = None
        receipt = {"completion_receipt_id": "cr_" + uuid.uuid4().hex, "workflow_id": workflow["workflow_id"],
            "objective": workflow["objective"], "result": result, "key_findings": result.get("key_findings", []),
            "artifacts": workflow["artifact_ids"], "handoffs": workflow["handoff_ids"], "cost": workflow["actual_cost"],
            "tokens": workflow["token_usage"], "duration": duration, "approvals_used": [
                s["approval_id"] for s in workflow["steps"] if s.get("approval_id")],
            "unresolved_items": result.get("unresolved_items", []),
            "next_recommended_action": result.get("next_recommended_action"), "created_at": utcnow()}
        workflow.update(completion_receipt=receipt, completion_receipt_id=receipt["completion_receipt_id"],
                        status="COMPLETED", completed_at=utcnow(), revision=workflow["revision"] + 1)
        workflow["notification_outbox"].append({"event_id": "evt_" + uuid.uuid4().hex,
            "event_type": "WORKFLOW_COMPLETED", "recipient": "NOVA",
            "completion_receipt_id": receipt["completion_receipt_id"], "status": "QUEUED",
            "created_at": utcnow()})
        self.persist(workflow)
        return receipt

    def fail_terminal_system(self, workflow: dict[str, Any], *, reason: str,
                             safe_continuation_exists: bool) -> None:
        if safe_continuation_exists or not reason.strip():
            raise ValueError("TERMINAL_FAILURE_REQUIRES_NO_SAFE_CONTINUATION")
        workflow["status"] = "FAILED_TERMINAL_SYSTEM"
        workflow["blockers"].append({"dependency": "NO_SAFE_CONTINUATION", "reason": reason[:500], "created_at": utcnow()})
        workflow["next_action"] = "OWNER_ESCALATION"
        workflow["updated_at"] = utcnow()
        workflow["revision"] += 1
        self.persist(workflow)

    def run_cronbot(self, cronbot_id: str, due_workflows: list[dict[str, Any]], *, dispatch: Callable | None = None) -> dict[str, Any]:
        bots = json.loads(CRONBOTS.read_text(encoding="utf-8"))["cronbots"]
        item = next((x for x in bots if x["cronbot_id"] == cronbot_id), None)
        if not item:
            raise ValueError("CRONBOT_NOT_REGISTERED")
        eligible = [w for w in due_workflows[:int(item["query_limit"])]
            if w.get("status") in {"RUNNING", "PARTIAL", "RETRY_SCHEDULED", "ESCALATED", "WAITING_DEPENDENCY"}
            and w.get("approval_state") != "WAITING_APPROVAL"]
        count = sum(bool(dispatch(w)) for w in eligible) if dispatch else 0
        return {"cronbot_id": cronbot_id, "examined": len(eligible), "dispatched": count, "model_calls": 0}

    def run_registered_cronbot(self, cronbot_id: str, *, dispatch: Callable | None = None) -> dict[str, Any]:
        bots = json.loads(CRONBOTS.read_text(encoding="utf-8"))["cronbots"]
        item = next((x for x in bots if x["cronbot_id"] == cronbot_id), None)
        if not item:
            raise ValueError("CRONBOT_NOT_REGISTERED")
        workflows = self.store.list(limit=int(item["query_limit"]))
        return self.run_cronbot(cronbot_id, workflows, dispatch=dispatch)


def default_state_store() -> WorkflowStateStore:
    """Select the existing durable-job persistence authority."""
    from scripts.nexus_agent_platform.durable_jobs import default_store
    return WorkflowStateStore(default_store())
