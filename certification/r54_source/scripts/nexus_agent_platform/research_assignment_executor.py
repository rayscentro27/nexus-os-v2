"""Bounded executors for Nova-originated Research assignments.

This module routes operational inspection, actual web search, missions, and
NotebookLM operations separately. Unsupported/missing context fails closed and
is never converted to a public search.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from nexus_agent_platform.research_assignment_intent import result_contract

ROOT = Path(__file__).resolve().parents[2]


def _module_function(module_name: str, function_name: str) -> bool:
    try:
        module = importlib.import_module(module_name)
        return callable(getattr(module, function_name, None))
    except Exception:
        return False


def inspect_research_runtime(*, doctor_runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Perform bounded read-only capability inspection; never invokes search."""
    cli = Path.home() / ".nexus/venvs/notebooklm-py/bin/notebooklm"
    if not cli.exists():
        cli_value = shutil.which("notebooklm")
        cli = Path(cli_value) if cli_value else cli
    auth = {"status": "NOT_CONFIGURED", "evidence": "CLI_NOT_FOUND"}
    if cli.exists():
        try:
            proc = doctor_runner([str(cli), "doctor"], capture_output=True, text=True,
                                 timeout=90, check=False)
            auth = {"status": "PASS" if proc.returncode == 0 else "FAILED",
                    "exit_code": int(proc.returncode), "evidence": "BOUNDED_NOTEBOOKLM_DOCTOR"}
        except subprocess.TimeoutExpired:
            auth = {"status": "TIMEOUT", "evidence": "BOUNDED_NOTEBOOKLM_DOCTOR"}
        except Exception as exc:
            auth = {"status": "ERROR", "error": type(exc).__name__}

    checks = {
        "NOTEBOOKLM_AUTH": auth,
        "NOTEBOOKLM_RESEARCH_INTEGRATION": _module_function(
            "research.notebooklm_research_adapter", "get_adapter"),
        "GROUPED_NOTEBOOKLM_WORKFLOW": _module_function(
            "research.notebook_playbook_runner", "run_case_playbook") and
            _module_function("research.notebook_completion_contracts", "question_groups"),
        "DEDICATED_NOTEBOOK_CREATE_REUSE": _module_function(
            "research.notebooklm_research_adapter", "get_adapter") and
            _module_function("research.research_notebook_ownership", "find_dedicated_notebook"),
        "ADAPTIVE_FOLLOWUP": _module_function(
            "nexus_agent_platform.business_opportunity_research_v2", "execute_research_director") and
            _module_function("research.notebook_playbook_runner", "_business_opportunity_director_review"),
        "NEEDLE": _module_function("nexus_agent_platform.needle_research_workflow", "handle_job"),
        "ALPHA_RESEARCH_DIRECTOR": _module_function(
            "nexus_agent_platform.business_opportunity_research_v2", "execute_research_director"),
        "RESEARCH_WORKER": (ROOT / "scripts/nexus_agent_platform/job_worker_once.py").is_file(),
        "RESEARCH_QUEUE": _module_function("nexus_agent_platform.research_work_queue", "default_queue"),
        "GOVERNOR": _module_function("nexus_agent_platform.resource_spend_governor", "default_store"),
    }
    # Live host services, worker processes, and exact governor hard-stop state
    # are Systems-owned operational checks. Do not imply static code presence
    # proves those live states.
    cross_department = [
        "durable dispatcher/service process and eligible-job claim state",
        "live Research worker process/lease state",
        "current daily governor resolution and exact HARD_STOP reason",
        "host resource/concurrency status",
        "deprecated continuous-loop and V6 service state",
    ]
    result = {
        "status": "PARTIAL_CROSS_DEPARTMENT_REQUIRED",
        "checks": checks,
        "systems_owned_scope": {"status": "CROSS_DEPARTMENT_REQUIRED", "missing_scope": cross_department},
        "public_search_performed": False,
        "credentials_exposed": False,
    }
    result["task_fulfillment"] = result_contract(
        requested_intent="RESEARCH_RUNTIME_INSPECTION",
        routed_intent="RESEARCH_RUNTIME_INSPECTION",
        execution_path="READ_ONLY_RESEARCH_RUNTIME_INSPECTOR",
        status="COMPLETED", result=checks,
        blocker="CROSS_DEPARTMENT_REQUIRED: live service/governor/host checks belong to Systems",
    )
    return result


def _blocked(intent: str, reason: str, *, path: str) -> dict[str, Any]:
    contract = result_contract(requested_intent=intent, routed_intent=intent,
        execution_path=path, status="BLOCKED", result=None, blocker=reason)
    return {"status": "BLOCKED", "reason": reason, "execution_path": path,
            "requested_intent": intent, "routed_intent": intent, "public_search_performed": False,
            "task_fulfillment": contract}


def select_intake_capabilities(work_item: dict[str, Any]) -> dict[str, Any]:
    """Choose source-processing aids after intake; NotebookLM is optional."""
    source_type = str(work_item.get("original_source_type") or work_item.get("source_type") or "").upper()
    text = " ".join(str(work_item.get(key) or "") for key in
                    ("original_objective", "objective", "title", "question", "research_scope")).casefold()
    notebooklm_useful = source_type in {"YOUTUBE", "YOUTUBE_VIDEO", "YOUTUBE_CHANNEL", "VIDEO", "PDF", "TRANSCRIPT", "DOCUMENT", "MULTI_SOURCE"}
    if any(token in text for token in ("latest five videos", "youtube channel", "multiple videos", "transcript")):
        notebooklm_useful = True
    return {"entry_path": "RESEARCH_INTAKE", "notebooklm_selected": notebooklm_useful,
            "classification_required_before_start": False,
            "original_objective": work_item.get("original_objective") or work_item.get("objective") or work_item.get("title"),
            "original_source_url": work_item.get("original_source_url") or work_item.get("source_url"),
            "source_type": source_type or "UNKNOWN",
            "current_research_context": work_item.get("current_research_context") or {}}


def execute_assignment(work_item: dict[str, Any], *, public_search: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Run one request using its classified execution path, or fail closed."""
    intent = str(work_item.get("requested_intent") or "UNKNOWN_RESEARCH_INTENT")
    objective = str(work_item.get("objective") or work_item.get("title") or "").strip()
    question = str(work_item.get("question") or objective).strip()

    if intent == "RESEARCH_RUNTIME_INSPECTION":
        value = inspect_research_runtime()
        value["requested_intent"] = intent
        value["routed_intent"] = intent
        value["execution_path"] = "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR"
        return value

    if intent == "RESEARCH_STATUS_QUERY":
        return _blocked(intent, "STATUS_QUERY_MUST_USE_EXISTING_JOB_READ; NO_NEW_RESEARCH_JOB", path="NO_NEW_MISSION")

    if intent == "NOTEBOOKLM_OPERATION":
        notebook_id = str(work_item.get("notebook_id") or work_item.get("notebook_reference") or "")
        operation = str(work_item.get("notebook_operation") or "").upper()
        source_url = str(work_item.get("source_url") or "")
        if not notebook_id:
            return _blocked(intent, "NOTEBOOK_ID_REQUIRED_FOR_GOVERNED_NOTEBOOK_OPERATION", path="NOTEBOOKLM_GOVERNED_ADAPTER")
        if operation not in {"ADD_SOURCE", "ASK"} or (operation == "ADD_SOURCE" and not source_url):
            return _blocked(intent, "SUPPORTED_NOTEBOOK_OPERATION_FIELDS_REQUIRED", path="NOTEBOOKLM_GOVERNED_ADAPTER")
        try:
            from research.notebooklm_research_adapter import get_adapter
            adapter = get_adapter()
            if operation == "ADD_SOURCE":
                before = adapter.sources(notebook_id)
                existing = adapter.find_existing_source(before, video_id=adapter.video_id_of(source_url), title="")
                source = existing or adapter.add_source(notebook_id, source_url, video_title=source_url)
                sid = str(source.get("id") or source.get("source_id") or "")
                if not sid:
                    return _blocked(intent, "NOTEBOOK_SOURCE_ADD_RETURNED_NO_SOURCE_ID", path="NOTEBOOKLM_GOVERNED_ADAPTER")
                adapter.wait_for_source(notebook_id, sid)
                after = adapter.sources(notebook_id)
                verified = any(str(row.get("id") or row.get("source_id") or "") == sid for row in after)
                status = "COMPLETED" if verified else "BLOCKED"
                output = {"notebook_id": notebook_id, "source_id": sid, "source_count_before": len(before),
                          "source_count_after": len(after), "source_verified": verified}
            else:
                prompt = str(work_item.get("notebook_prompt") or question).strip()[:1200]
                output = adapter.ask_notebook(notebook_id, prompt)
                status = "COMPLETED" if str(output.get("answer") or "").strip() else "BLOCKED"
            contract = result_contract(requested_intent=intent, routed_intent=intent,
                execution_path="NOTEBOOKLM_GOVERNED_ADAPTER", status=status, result=output,
                blocker=None if status == "COMPLETED" else "NOTEBOOKLM_OPERATION_NOT_VERIFIED")
            return {"status": status, "result": output, "execution_path": "NOTEBOOKLM_GOVERNED_ADAPTER",
                    "requested_intent": intent, "routed_intent": intent, "task_fulfillment": contract,
                    "public_search_performed": False}
        except Exception as exc:
            return _blocked(intent, f"NOTEBOOKLM_OPERATION_FAILED:{type(exc).__name__}", path="NOTEBOOKLM_GOVERNED_ADAPTER")

    if intent == "RESEARCH_MISSION":
        intake = select_intake_capabilities(work_item)
        case_id = str(work_item.get("research_case_id") or "")
        notebook_id = str(work_item.get("notebook_id") or work_item.get("notebook_reference") or "")
        try:
            from research import research_case_engine as cases
            if not case_id:
                # Owner missions enter the existing case engine; its objective
                # key makes retries join the same case. The playbook then uses
                # its normal dedicated-notebook create/reuse path.
                lowered = f"{objective} {question} {work_item.get('research_scope') or ''}".casefold()
                objective_type = str(work_item.get("objective_type") or "").upper()
                if objective_type == "TRADING_INTELLIGENCE" or any(token in lowered for token in ("forex", "currency pair", "fx strategy")):
                    family, owner, goal = "TRADING_INTELLIGENCE", "MERCURY_TRADING", "FOREX"
                elif objective_type == "BUSINESS_OPPORTUNITY" or any(token in lowered for token in (
                    "business", "opportunity", "tiktok shop", "shopify", "market", "product",
                    "vendor", "affiliate", "ecommerce",
                )) or (".com" in lowered and any(token in lowered for token in ("partner", "copy", "avoid", "use it"))):
                    family, owner, goal = "BUSINESS_OPPORTUNITIES", "BUSINESS_OPPORTUNITIES", "BUSINESS_OPPORTUNITY"
                else:
                    # Initial classification is not an admission gate. Start
                    # with general Research intake and refine category from
                    # source evidence during the workflow.
                    family, owner, goal = "RESEARCH_INTAKE", "RESEARCH", "RESEARCH_INTAKE"
                # A same-objective continuation explicitly requested by Ray
                # may resume the existing project lineage even when the
                # background deep-case concurrency ceiling is occupied. This
                # does not create a durable job or authorize paid/external work.
                explicit_owner_continuation = (
                    str(work_item.get("source_type") or "").upper() == "NOVA_OBJECTIVE"
                    and str(work_item.get("requested_by") or "").lower() == "hermes_nova"
                    and str(work_item.get("requested_intent") or "").upper() == "RESEARCH_MISSION"
                    and bool(work_item.get("objective_id"))
                    and str(work_item.get("followup_of") or "") == str(work_item.get("objective_id") or "")
                )
                opened = cases.open_or_join_case(objective=objective or question,
                    objective_family=family, business_or_nexus_goal=goal,
                    owner_department=owner, primary_question=question or objective,
                    priority=70, originating_goal_id=str(work_item.get("objective_id") or ""),
                    objective_id=str(work_item.get("objective_id") or ""),
                    project_id=str(work_item.get("work_id") or work_item.get("project_id") or ""),
                    requires_ray=False, force_existing=explicit_owner_continuation)
                case = opened.get("case") if isinstance(opened, dict) else None
                if not case or not case.get("case_id"):
                    if isinstance(opened, dict) and opened.get("wait_for_capacity"):
                        reason = str(opened.get("reason") or "RESEARCH_EXECUTION_CAPACITY_UNAVAILABLE")
                        return {"status": "WAITING_FOR_CAPACITY", "reason": reason,
                            "execution_path": "RESEARCH_INTAKE", "requested_intent": intent,
                            "routed_intent": intent, "retryable": True,
                            "objective_terminated": False, "case_created": False,
                            "public_search_performed": False}
                    return _blocked(intent, str(opened.get("reason") or "RESEARCH_CASE_NOT_OPENED"), path="RESEARCH_INTAKE")
                case_id = str(case["case_id"])
                notebook_id = str((case.get("notebook_workspace") or {}).get("notebook_id") or
                                  (case.get("notebook_playbook") or {}).get("notebook_id") or notebook_id)
            case = cases.get_case(case_id)
            bound_notebook_id = str((case.get("notebook_workspace") or {}).get("notebook_id") or
                                    (case.get("notebook_playbook") or {}).get("notebook_id") or case.get("notebook_id") or "") if case else ""
            if not case or (notebook_id and bound_notebook_id and bound_notebook_id != notebook_id):
                return _blocked(intent, "RESEARCH_CASE_CONTEXT_NOT_VERIFIED", path="RESEARCH_INTAKE")
            if intake["notebooklm_selected"]:
                from research.notebook_playbook_runner import run_case_playbook
                output = run_case_playbook(case_id, source_work_id=str(work_item.get("work_id") or ""),
                                           ask_followup=True, adaptive_director=True)
            else:
                source_url = str(intake.get("original_source_url") or "")
                source = {"source_type": intake["source_type"], "source_url": source_url or None,
                          "source_id": work_item.get("work_id") or source_url or case_id,
                          "title": work_item.get("title") or objective,
                          "objective": objective, "source_role": "PRIMARY_SOURCE"}
                attached = cases.add_source(case_id, source) if source_url else {"ok": True, "case": case}
                if not attached.get("ok"):
                    return _blocked(intent, str(attached.get("reason") or "RESEARCH_SOURCE_INTAKE_FAILED"),
                                    path="RESEARCH_INTAKE")
                output = {"ok": True, "status": "INTAKE_RECORDED", "case_id": case_id,
                          "source_attached": bool(source_url), "notebooklm_selected": False,
                          "original_objective": objective, "research_intake": intake,
                          "next_action": "RESEARCH_SOURCE_ACQUISITION_AND_EVIDENCE_GATHERING"}
            ok = bool(output.get("ok"))
            contract = result_contract(requested_intent=intent, routed_intent=intent,
                execution_path="RESEARCH_INTAKE", status="IN_PROGRESS" if ok else "BLOCKED",
                result=output if ok else None, blocker="RESEARCH_CONTINUATION_REQUIRED" if ok else
                    str(output.get("reason") or "RESEARCH_INTAKE_FAILED"))
            return {"status": "CONTINUATION_REQUIRED" if ok else "BLOCKED", "result": output,
                    "execution_path": "RESEARCH_INTAKE", "research_intake": intake,
                    "requested_intent": intent, "routed_intent": intent,
                    "case_id": case_id, "notebook_id": ((output.get("notebook_id") or notebook_id or bound_notebook_id or None)
                        if intake["notebooklm_selected"] else None),
                    "task_fulfillment": contract, "public_search_performed": False}
        except Exception as exc:
            return _blocked(intent, f"RESEARCH_INTAKE_FAILED:{type(exc).__name__}", path="RESEARCH_INTAKE")

    if intent == "PUBLIC_RESEARCH_SEARCH":
        if public_search is None:
            return _blocked(intent, "PUBLIC_SEARCH_EXECUTOR_UNAVAILABLE", path="PUBLIC_SEARCH")
        try:
            output = public_search(question)
            ok = bool(output)
            contract = result_contract(requested_intent=intent, routed_intent=intent,
                execution_path="GOVERNED_PUBLIC_RESEARCH_SEARCH", status="COMPLETED" if ok else "BLOCKED",
                result=output if ok else None, blocker=None if ok else "PUBLIC_SEARCH_RETURNED_NO_RESULT")
            return {"status": "COMPLETED" if ok else "BLOCKED", "result": output,
                    "execution_path": "GOVERNED_PUBLIC_RESEARCH_SEARCH",
                    "requested_intent": intent, "routed_intent": intent,
                    "task_fulfillment": contract, "public_search_performed": True}
        except Exception as exc:
            return _blocked(intent, f"PUBLIC_SEARCH_FAILED:{type(exc).__name__}", path="GOVERNED_PUBLIC_RESEARCH_SEARCH")

    if intent == "RESEARCH_EXECUTION":
        return _blocked(intent, "RESEARCH_EXECUTION_SCOPE_UNRESOLVED; CLASSIFY_AS_MISSION_OR_EXPLICIT_SEARCH", path="NO_EXECUTION")

    return _blocked(intent, "UNKNOWN_RESEARCH_INTENT; NO_SEARCH_OR_COMPLETION", path="NO_EXECUTION")
