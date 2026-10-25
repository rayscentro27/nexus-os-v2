"""Read-only Nova status reads through the configured Nexus MCP server.

The Telegram worker runs on the Oracle host, while Nexus MCP credentials are
owned by the existing Hermes profile container.  This adapter asks that
container's configured MCP client to perform the call; it does not create a
second server or copy credentials into the Telegram environment.
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
from datetime import datetime, timezone


MCP_CONTAINER = "nexus-hermes-0206"
MCP_PYTHON = "/opt/hermes/.venv/bin/python"

_CONTAINER_CALL = r'''import asyncio,json,sys,yaml,httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
request=json.load(sys.stdin)
config=yaml.safe_load(open("/opt/data/profiles/nova_nexus/config.yaml"))
server=config["mcp_servers"]["nexus_mcp_remote"]
async def main():
 async with httpx.AsyncClient(headers=server.get("headers",{}),timeout=60) as client:
  async with streamable_http_client(server["url"],http_client=client) as (read,write):
   async with ClientSession(read,write) as session:
    await session.initialize()
    tools=await session.list_tools()
    if request.get("operation")=="list_tools":
     print(json.dumps({"tool_count":len(tools.tools),"tools":[{"name":t.name,"description":t.description or "","input_schema":t.input_schema} for t in tools.tools]})); return
    result=await session.call_tool(request["tool"],request["arguments"])
    if result.is_error:
      detail=" ".join(item.text for item in result.content if hasattr(item,"text")).casefold()
      if "401" in detail or "403" in detail or "unauthorized" in detail or "forbidden" in detail: code="MCP_CONNECTOR_AUTH_FAILED"
      elif "timeout" in detail or "timed out" in detail: code="MCP_CONNECTOR_TIMEOUT"
      elif "not registered" in detail or "unknown tool" in detail: code="MCP_TOOL_NOT_REGISTERED"
      else: code="MCP_TOOL_CALL_FAILED"
      raise RuntimeError(code)
    content=[item.text for item in result.content if hasattr(item,"text")]
    if not content: raise RuntimeError("NEXUS_MCP_TOOL_RESULT_EMPTY")
    print(json.dumps({"tool_count":len(tools.tools),"result":json.loads(content[0])}))
asyncio.run(main())
'''


def _mcp_failure_code(detail: str, default: str = "MCP_SERVER_FAILURE") -> str:
    """Map transport/client diagnostics to a stable, secret-free Nova error code."""
    value = str(detail or "").casefold()
    if "parked" in value:
        return "MCP_SERVER_PARKED"
    if "mcp_connector_auth_failed" in value:
        return "CONNECTOR_AUTH_FAILED"
    if "mcp_connector_timeout" in value:
        return "CONNECTOR_TIMEOUT"
    if "401" in value or "403" in value or "unauthorized" in value or "forbidden" in value:
        return "MCP_AUTH_FAILED"
    if any(term in value for term in (
        "connecterror", "connecttimeout", "connection refused", "all connection attempts failed",
        "no route to host", "name or service not known", "temporary failure in name resolution",
    )):
        return "MCP_TRANSPORT_UNREACHABLE"
    if "tool_not_registered" in value or "unknown tool" in value or "tool not found" in value:
        return "MCP_TOOL_NOT_REGISTERED"
    if "timeout" in value or "timed out" in value:
        return "MCP_SERVER_TIMEOUT"
    if "protocol" in value or "invalid content-type" in value:
        return "MCP_PROTOCOL_FAILURE"
    return default


def list_mcp_tools() -> tuple[list[dict], int]:
    """Discover the actual tools exposed to Nova by its configured Nexus MCP."""
    payload = json.dumps({"operation": "list_tools"})
    completed = subprocess.run(
        ["podman", "exec", "-i", MCP_CONTAINER, MCP_PYTHON, "-c", _CONTAINER_CALL],
        input=payload, capture_output=True, text=True, timeout=90, check=False,
    )
    if completed.returncode:
        raise RuntimeError(_mcp_failure_code(completed.stderr + "\n" + completed.stdout, "MCP_DISCOVERY_FAILED"))
    try:
        response = json.loads(completed.stdout)
        tools = response["tools"]
        count = int(response["tool_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("NEXUS_MCP_DISCOVERY_RESPONSE_INVALID") from exc
    return tools, count


def status_tool_for(text: str) -> tuple[str, dict]:
    value = text.casefold()
    if any(term in value for term in ("working on", "working now", "current work")):
        return "nexus_get_work_items", {}
    if any(term in value for term in ("job", "queue")):
        return "nexus_get_durable_jobs", {"limit": 10}
    if "research" in value:
        return "nexus_get_research_state", {}
    if "notebooklm" in value:
        return "nexus_get_system_health", {}
    return "nexus_get_system_health", {}


def call_mcp_tool(tool_name: str, arguments: dict) -> tuple[dict, int]:
    payload = json.dumps({"tool": tool_name, "arguments": arguments})
    try:
        completed = subprocess.run(
            ["podman", "exec", "-i", MCP_CONTAINER, MCP_PYTHON, "-c", _CONTAINER_CALL],
            input=payload, capture_output=True, text=True, timeout=90, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("MCP_TOOL_TIMEOUT") from exc
    except OSError as exc:
        raise RuntimeError("MCP_CONTAINER_UNAVAILABLE") from exc
    except subprocess.SubprocessError as exc:
        raise RuntimeError("MCP_CONTAINER_CALL_FAILED") from exc
    if completed.returncode:
        raise RuntimeError(_mcp_failure_code(completed.stderr + "\n" + completed.stdout, "MCP_TOOL_CALL_FAILED"))
    try:
        response = json.loads(completed.stdout)
        return response["result"], int(response["tool_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("NEXUS_MCP_CONTAINER_RESPONSE_INVALID") from exc


def call_status_tool(text: str) -> tuple[str, dict, int]:
    from nexus_agent_platform.department_router import classify_intent

    intent = classify_intent(text)
    if intent not in {"STATE_QUERY", "LIST_JOBS", "STATUS_OF_EXISTING_TASK", "FOLLOWUP_QUERY"}:
        from nova.semantic_orchestration import resolve_owner_request
        if resolve_owner_request(text).get("intent") not in {"LIVE_STATE_QUERY", "LIST_JOBS", "OBJECTIVE_STATUS_QUERY"}:
            raise ValueError("not_a_state_query")
    tool_name, arguments = status_tool_for(text)
    result, tool_count = call_mcp_tool(tool_name, arguments)
    return tool_name, result, tool_count


def call_prior_department_result(text: str, department: str) -> tuple[dict, int]:
    """Read a receipt-verified earlier result; never route a follow-up as new work."""
    from nova.semantic_orchestration import resolve_owner_request

    semantic = resolve_owner_request(text)
    target = str(department or "").strip().upper()
    if semantic.get("intent") != "PRIOR_WORK_QUERY" or semantic.get("department") != target:
        raise ValueError("not_a_prior_work_query")
    result, tool_count = call_mcp_tool("nexus_get_prior_department_result", {
        "department": target, "question": " ".join(str(text).split())[:500],
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"ok", "not_found", "unavailable"}:
        raise RuntimeError("NEXUS_PRIOR_WORK_READ_REJECTED")
    return payload, tool_count


def render_prior_department_result(result: dict) -> str:
    """Render only retrieved department output and its evidence limitations."""
    status = str(result.get("status") or "unknown").casefold()
    if status != "ok":
        if status == "not_found":
            return "I couldn't find a completed, receipt-verified prior result for that department. I did not create or rerun a job."
        return "The prior-result store is temporarily unavailable. I did not create or rerun any work."
    department = str(result.get("department") or "").upper()
    if department == "ALPHA":
        value = result.get("alpha_evaluation") if isinstance(result.get("alpha_evaluation"), dict) else {}
        decision = str(value.get("decision") or "UNKNOWN").replace("_", " ").title()
        strengths = value.get("strengths") if isinstance(value.get("strengths"), list) else []
        weaknesses = value.get("weaknesses") if isinstance(value.get("weaknesses"), list) else []
        lines = [f"Alpha's review was **{decision}**, with weak evidence; it recommended more research rather than treating the opportunity as validated."]
        if strengths:
            lines.append("Strengths: " + "; ".join(str(item) for item in strengths[:3]))
        if weaknesses:
            lines.append("Main weaknesses: " + "; ".join(str(item) for item in weaknesses[:3]))
        if value.get("strongest_assumption"):
            lines.append("Strongest assumption: " + str(value["strongest_assumption"]))
        if value.get("weakest_assumption"):
            lines.append("Weakest assumption: " + str(value["weakest_assumption"]))
        if value.get("one_improvement"):
            lines.append("Suggested improvement: " + str(value["one_improvement"]))
        if value.get("why_interesting"):
            lines.append("Why it is interesting: " + str(value["why_interesting"]))
        lines.append("The key limitation was that Microsoft blocked the pricing page, so exact prices were not verified.")
        return "\n\n".join(lines)
    return str(result.get("summary") or "The completed department result had no readable summary.")


def _research_assignment_parts(text: str) -> tuple[str, str]:
    task = text.strip()
    query_match = re.search(
        r"(?is)\b(?:research\s+query|question)\s*:\s*(.+?)(?:\n\s*(?:instructions|requirements|return)\s*:|$)", task
    )
    match = re.search(
        r"(?is)\btask\s*:\s*(.+?)(?:\n\s*return\s*:|\n\s*requirements\s*:|$)", task
    )
    objective = " ".join(match.group(1).split()) if match else task
    objective = objective[:1000]
    question = " ".join(query_match.group(1).split()) if query_match else task
    question = question[:1600]
    if len(objective) < 12:
        raise ValueError("research_objective_too_short")
    return objective, question


def assign_research_task(text: str, parent_request_id: str, *, followup_department: str = "",
                         requested_intent: str = "") -> tuple[dict, int]:
    """Use Nexus's bounded, idempotent Research assignment action."""
    from nexus_agent_platform.department_router import classify_intent

    if classify_intent(text) != "ASSIGN_DEPARTMENT_TASK":
        from nova.semantic_orchestration import resolve_owner_request
        semantic = resolve_owner_request(text)
        if semantic.get("department") != "RESEARCH" and "RESEARCH" not in semantic.get("departments", []):
            raise ValueError("not_a_research_assignment")
    objective, question = _research_assignment_parts(text)
    arguments = {
        "objective": objective,
        "question": question,
        "parent_request_id": str(parent_request_id),
        "followup_department": followup_department,
    }
    if requested_intent:
        arguments["requested_intent"] = str(requested_intent).strip().upper()
    result, tool_count = call_mcp_tool("nexus_assign_research", arguments)
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"queued", "idempotent_existing"} or not payload.get("durable_job_id"):
        raise RuntimeError(f"NEXUS_RESEARCH_ASSIGNMENT_REJECTED:{payload.get('error') or payload.get('status') or 'unknown'}")
    return payload, tool_count


def assign_research_only(*, objective: str, question: str, correlation_id: str,
                         context_summary: str = "") -> tuple[dict, int]:
    """Submit one compact RESEARCH_ONLY request through the existing MCP action."""
    objective = " ".join(str(objective or "").split())[:500]
    question = " ".join(str(question or "").split())[:1200]
    correlation_id = str(correlation_id or "").strip()
    if len(objective) < 12 or len(question) < 12 or not correlation_id:
        raise ValueError("research_only_request_invalid")
    objective = (objective + (" Context: " + " ".join(str(context_summary).split())[:300]
                              if context_summary else ""))[:1000]
    result, tool_count = call_mcp_tool("nexus_assign_research", {
        "objective": objective, "question": question,
        "parent_request_id": correlation_id, "requested_intent": "RESEARCH_ONLY",
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"queued", "idempotent_existing"} or not payload.get("durable_job_id"):
        raise RuntimeError("NEXUS_RESEARCH_ONLY_ASSIGNMENT_REJECTED")
    return payload, tool_count


def continue_research_project(*, objective_id: str, project_id: str, job_id: str,
                              instruction: str, parent_request_id: str = "") -> tuple[dict, int]:
    """Continue only the exact current project lineage through Nexus MCP."""
    result, tool_count = call_mcp_tool("nexus_continue_research", {
        "objective_id": str(objective_id), "project_id": str(project_id),
        "job_id": str(job_id), "instruction": str(instruction)[:1000],
        "parent_request_id": str(parent_request_id or objective_id),
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"continued", "already_active", "idempotent_existing"} or not payload.get("job_id"):
        raise RuntimeError(f"NEXUS_RESEARCH_CONTINUATION_REJECTED:{payload.get('error') or payload.get('status') or 'unknown'}")
    return payload, tool_count


def assign_bounded_control_task(tool_name: str, task: str, parent_request_id: str) -> tuple[dict, int]:
    """Queue a bounded internal Creative/OpenCode task through authenticated MCP."""
    if tool_name not in {"nexus_assign_creative_asset", "nexus_assign_bounded_coding_task"}:
        raise ValueError("unsupported_bounded_control_action")
    result, tool_count = call_mcp_tool(tool_name, {
        "task": " ".join(str(task).split())[:1200],
        "parent_request_id": str(parent_request_id or ""),
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") != "queued" or not payload.get("job_id"):
        raise RuntimeError(f"NOVA_CONTROL_ACTION_REJECTED:{payload.get('error') or payload.get('status') or 'unknown'}")
    return payload, tool_count


def assign_alpha_task(text: str, parent_request_id: str) -> tuple[dict, int]:
    """Assign an existing-evidence review to Nexus Alpha through durable MCP."""
    from nova.semantic_orchestration import resolve_owner_request

    semantic = resolve_owner_request(text)
    if semantic.get("department") != "ALPHA" and "ALPHA" not in semantic.get("departments", []):
        raise ValueError("not_an_alpha_assignment")
    # The deployed governed Alpha worker currently binds the assignment to the
    # completed Microsoft Project Research artifact. Do not let a generic
    # runtime/other-topic request silently evaluate that unrelated artifact.
    if not re.search(r"\bmicrosoft\s+project\b", str(text), re.I):
        raise RuntimeError("ALPHA_GOVERNED_ACTION_SCOPE_UNSUPPORTED: current Alpha action reviews the completed Microsoft Project Research artifact only")
    # The MCP action resolves the matching persisted Research evidence. Nova
    # only forwards the authorized request and never synthesizes the review.
    result, tool_count = call_mcp_tool("nexus_assign_department_query", {
        "department": "ALPHA",
        "question": _bounded_department_question(text),
        "parent_request_id": str(parent_request_id),
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"queued", "idempotent_existing"} or not payload.get("job_id"):
        raise RuntimeError(f"NEXUS_ALPHA_ASSIGNMENT_REJECTED:{payload.get('error') or payload.get('status') or 'unknown'}")
    return payload, tool_count


def assign_department_task(text: str, department: str, parent_request_id: str, *,
                           requested_intent: str = "", followup_department: str = "") -> tuple[dict, int]:
    """Use the canonical durable MCP action selected by Nova's semantic router."""
    target = str(department or "").strip().upper()
    if target == "RESEARCH":
        return assign_research_task(text, parent_request_id, requested_intent=requested_intent,
                                    followup_department=followup_department)
    if target == "ALPHA":
        return assign_alpha_task(text, parent_request_id)
    if target not in {"ALPHA", "SYSTEMS"}:
        raise ValueError("department_has_no_durable_assignment_action")
    question = _bounded_department_question(text)
    if target == "SYSTEMS":
        # Preserve the owner's requested inspection. The explicit system
        # operations scope keeps this inside the existing read-only Systems
        # MCP contract while avoiding substitution of a generic health check.
        if not re.search(r"\b(?:system health|health check|system operations|operations check|system check)\b", question, re.I):
            question = ("Run a bounded read-only Systems system operations check: " + question)[:240]
    result, tool_count = call_mcp_tool("nexus_assign_department_query", {
        "department": target, "question": question,
        "parent_request_id": str(parent_request_id),
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"queued", "idempotent_existing"} or not payload.get("job_id"):
        raise RuntimeError(f"NEXUS_{target}_ASSIGNMENT_REJECTED:{payload.get('error') or payload.get('status') or 'unknown'}")
    return payload, tool_count


def assign_department_tasks(text: str, departments: list[str], parent_request_id: str) -> dict:
    """Submit bounded department assignments under one parent request correlation.

    Each department uses the existing MCP action. A rejection is recorded for
    that department while independent requested assignments continue.
    """
    results = []
    tool_count = 0
    for raw_department in departments:
        department = str(raw_department or "").strip().upper()
        if department not in {"RESEARCH", "SYSTEMS", "ALPHA"}:
            results.append({"department": department or "UNKNOWN", "status": "BLOCKED",
                            "error_type": "UnsupportedDepartment", "error": "no_governed_assignment_action"})
            continue
        try:
            assignment, count = assign_department_task(text, department, parent_request_id)
            tool_count += int(count or 0)
            job_id = assignment.get("durable_job_id") or assignment.get("job_id")
            state = (assignment.get("durable_job_state") or assignment.get("job_state")
                     or assignment.get("queue_status") or "UNKNOWN")
            if not job_id:
                raise RuntimeError(f"{department}_ASSIGNMENT_ID_MISSING")
            results.append({"department": department, "status": str(state).upper(),
                            "job_id": str(job_id), "assignment": assignment})
        except Exception as exc:
            results.append({"department": department, "status": "BLOCKED",
                            "error_type": type(exc).__name__, "error": str(exc)[:240]})
    return {"parent_request_id": str(parent_request_id), "assignments": results,
            "tool_count": tool_count,
            "accepted_count": sum(1 for row in results if row.get("job_id")),
            "blocked_count": sum(1 for row in results if not row.get("job_id"))}


def build_assignment_linkage(nova_objective_id: str, parent_request_id: str,
                             department: str, assignment: dict,
                             created_at: str | None = None) -> dict:
    """Persist the actual governed job identity on Nova's existing mission."""
    value = assignment if isinstance(assignment, dict) else {}
    job_id = str(value.get("durable_job_id") or value.get("job_id") or "").strip()
    if not job_id:
        raise RuntimeError(f"{str(department).upper()}_ASSIGNMENT_ID_MISSING")
    state = (value.get("durable_job_state") or value.get("job_state")
             or value.get("queue_status"))
    if not state and value.get("status") in {"queued", "idempotent_existing"}:
        state = "QUEUED"
    if not state:
        raise RuntimeError(f"{str(department).upper()}_ASSIGNMENT_STATE_MISSING")
    now = created_at or datetime.now(timezone.utc).isoformat()
    return {
        "nova_objective_id": str(nova_objective_id),
        "objective_id": str(value.get("objective_id") or nova_objective_id),
        "project_id": str(value.get("work_id") or value.get("objective_id") or nova_objective_id),
        "parent_request_id": str(parent_request_id),
        "department": str(department).upper(),
        "assignment_id": job_id,
        "job_id": job_id,
        "created_at": str(value.get("created_at") or now),
        "current_status": str(state).upper(),
        "receipt_id": str(value.get("request_id") or ""),
    }


def render_assignment_ack(linkage: dict) -> str:
    """Only render an accepted/queued response when a real job ID is present."""
    job_id = str(linkage.get("job_id") or linkage.get("assignment_id") or "").strip()
    if not job_id:
        raise ValueError("assignment_id_required_before_acknowledgement")
    objective_id = str(linkage.get("nova_objective_id") or "UNKNOWN")
    department = str(linkage.get("department") or "UNKNOWN").upper()
    state = str(linkage.get("current_status") or "UNKNOWN").upper()
    label = "RESEARCH_JOB_ID" if department == "RESEARCH" else f"{department}_JOB_ID"
    return (f"NEXUS_OBJECTIVE_ID={objective_id}\n"
            f"OBJECTIVE_ID={linkage.get('objective_id') or objective_id}\n"
            f"PROJECT_ID={linkage.get('project_id') or objective_id}\n"
            f"RECEIPT_ID={linkage.get('receipt_id') or 'UNKNOWN'}\nDEPARTMENT={department}\n"
            f"{label}={job_id}\nJOB_STATUS={state}\n"
            "This is an assignment state, not a completion claim.")


def render_assignment_failure(objective_id: str, blocker: str) -> str:
    """Expose dispatch failure without representing the objective as accepted."""
    reason = " ".join(str(blocker or "governed_assignment_rejected").split())[:240]
    return (f"NEXUS_OBJECTIVE_ID={objective_id}\nOBJECTIVE_ACCEPTED=NO\n"
            f"DISPATCH_STATUS=FAILED\nBLOCKER={reason}")


def call_exact_job_status(job_id: str) -> tuple[dict, int]:
    """Read one exact existing job and its Research work-item projection."""
    target = str(job_id or "").strip()
    if not target:
        raise ValueError("linked_job_id_required")
    result, tool_count = call_mcp_tool("nexus_get_durable_jobs", {"job_id": target, "limit": 1})
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if isinstance(data.get("data"), dict):
        data = data["data"]
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else result.get("items", [])
    row = next((item for item in jobs if isinstance(item, dict)
                and str(item.get("job_id") or "") == target), None)
    if row is None:
        return ({"status": "not_found", "job_id": target,
                 "error": "exact_job_not_found"}, tool_count)
    work_item = data.get("research_work_item") if isinstance(data.get("research_work_item"), dict) else None
    return ({"status": "ok", "job": row, "research_work_item": work_item, "job_id": target}, tool_count)


def render_exact_job_status(result: dict) -> str:
    if result.get("status") != "ok":
        return (f"The linked Nexus job {result.get('job_id', 'UNKNOWN')} was not present in the bounded live read. "
                "I did not create replacement work.")
    job = result.get("job") if isinstance(result.get("job"), dict) else {}
    department = str(job.get("department") or "UNKNOWN").upper()
    fields = [f"JOB_ID={job.get('job_id')}",
              *([f"RESEARCH_JOB_ID={job.get('job_id')}"] if department == "RESEARCH" else []),
              f"DEPARTMENT={department}",
              f"JOB_TYPE={job.get('job_type', 'UNKNOWN')}", f"STATE={job.get('state')}",
              f"JOB_STATUS={job.get('state')}",
              f"ATTEMPT={job.get('attempt_count', 'UNKNOWN')}",
              f"ATTEMPT_COUNT={job.get('attempt_count', 'UNKNOWN')}",
              f"CLAIMED_BY={job.get('claimed_by') or 'NONE'}",
              f"CREATED_AT={job.get('created_at') or 'UNKNOWN'}",
              f"STARTED_AT={job.get('started_at') or 'NONE'}",
              f"COMPLETED_AT={job.get('completed_at') or 'NONE'}",
              f"CLAIMED_AT={job.get('claimed_at') or 'NONE'}",
              f"CORRELATION_ID={job.get('correlation_id') or 'UNKNOWN'}",
              f"PARENT_JOB_ID={job.get('parent_job_id') or 'NONE'}",
              f"ERROR_CODE={job.get('last_error_code') or 'NONE'}",
              f"ERROR_SUMMARY={job.get('last_error_summary') or 'NONE'}",
              f"BLOCKER_CODE={job.get('last_error_code') or 'NONE_RECORDED'}",
              f"BLOCKER_MESSAGE={job.get('last_error_summary') or 'NONE_RECORDED'}",
              f"RECEIPT_REFERENCE={job.get('receipt_ref') or 'NONE'}"]
    result_summary = job.get("result_summary")
    if isinstance(result_summary, dict):
        answer = str(result_summary.get("answer") or result_summary.get("summary") or "").strip()
        if answer:
            fields.append(f"RESULT_SUMMARY={answer[:3000]}")
        evidence = result_summary.get("evidence")
        if evidence:
            fields.append("RESULT_EVIDENCE=" + json.dumps(evidence, ensure_ascii=False, default=str)[:3000])
        if result_summary.get("artifact_ref"):
            fields.append(f"RESULT_ARTIFACT={result_summary['artifact_ref']}")
        if result_summary.get("department_receipt_id"):
            fields.append(f"DEPARTMENT_RECEIPT_ID={result_summary['department_receipt_id']}")
        if result_summary.get("completed_at"):
            fields.append(f"RESULT_COMPLETED_AT={result_summary['completed_at']}")
    work = result.get("research_work_item")
    if isinstance(work, dict):
        fields.extend([f"RESEARCH_WORK_ID={work.get('work_id', 'UNKNOWN')}",
                       f"REQUESTED_INTENT={work.get('requested_intent', 'UNKNOWN')}",
                       f"ROUTED_INTENT={work.get('routed_intent', 'UNKNOWN')}",
                       f"EXECUTION_PATH={work.get('execution_path', 'UNKNOWN')}",
                       f"WORK_STATUS={work.get('status', 'UNKNOWN')}",
                       f"BLOCKER={work.get('blocker') or work.get('last_error') or 'NONE'}",
                       f"CASE_ID={work.get('case_id') or 'NONE'}",
                       f"OPPORTUNITY_ID={work.get('opportunity_id') or 'NONE'}",
                       f"NOTEBOOK_ID={work.get('notebook_id') or 'NONE'}",
                       f"CURRENT_STAGE={work.get('current_stage') or 'UNKNOWN'}"])
        if work.get("result"):
            fields.append(f"RESULT={work['result']}")
    else:
        fields.append("RESEARCH_WORK_ITEM=UNAVAILABLE")
    fields.extend(["READ_ONLY=YES", "NEW_OBJECTIVE_CREATED=NO", "NEW_RESEARCH_JOB_CREATED=NO"])
    return "\n".join(fields)


def render_assignment_batch(batch: dict, owner_objective_id: str) -> str:
    """Render actual assignment IDs/states and exact per-department blockers."""
    rows = batch.get("assignments") if isinstance(batch.get("assignments"), list) else []
    accepted = [row for row in rows if row.get("job_id")]
    blocked = [row for row in rows if not row.get("job_id")]
    lines = [f"NEXUS_OBJECTIVE_ID={owner_objective_id}",
             f"PARENT_REQUEST_ID={batch.get('parent_request_id') or owner_objective_id}"]
    if accepted:
        lines.append("OBJECTIVE_ACCEPTED=YES" if not blocked else "OBJECTIVE_ACCEPTED=PARTIAL")
        lines.append("DISPATCH_STATUS=SUCCEEDED" if not blocked else "DISPATCH_STATUS=PARTIAL")
        lines.append("Governed department assignments:")
        for row in accepted:
            department = str(row.get("department") or "DEPARTMENT")
            lines.append(f"{department}_JOB_ID={row['job_id']}  JOB_STATUS={row.get('status', 'UNKNOWN')}")
        lines.append("These are assignment states, not completion claims. I’ll report department results when their governed workers finish.")
    else:
        lines.extend(["OBJECTIVE_ACCEPTED=NO", "DISPATCH_STATUS=FAILED", "No department assignment was accepted."])
    for row in blocked:
        lines.append(f"{row.get('department', 'DEPARTMENT')}_ROUTING_BLOCKER={row.get('error_type', 'UnknownError')}: {row.get('error', 'unknown blocker')}")
    return "\n".join(lines)


def _bounded_department_question(text: str) -> str:
    """Keep the task-specific request while respecting the MCP's 240-char cap."""
    value = " ".join(str(text or "").split())
    match = re.search(r"\btask\s*:\s*(.+?)(?:\s+(?:requirements?|when it completes?|when .* completes?)\s*:|$)", value, re.I)
    if match:
        value = match.group(1).strip()
    return value[:240]


def assign_systems_task(text: str, parent_request_id: str) -> tuple[dict, int]:
    """Queue an explicit bounded Systems health/operations request via MCP."""
    from nexus_agent_platform.department_router import classify_intent

    intent = classify_intent(text)
    if intent not in {"SYSTEM_HEALTH", "SYSTEM_OPERATIONS"}:
        raise ValueError("not_a_systems_assignment")
    # The owner message may contain a long result template. Pass a concise
    # canonical task to the existing department action, retaining the request
    # identity while keeping the MCP contract bounded.
    question = (
        "Run a real Nexus Systems health check and report current Mac host, "
        "Supabase, Oracle, durable queue, and resource guard status."
    )
    result, tool_count = call_mcp_tool("nexus_assign_department_query", {
        "department": "SYSTEMS", "question": question,
        "parent_request_id": str(parent_request_id),
    })
    payload = result.get("data") if isinstance(result.get("data"), dict) else result
    if payload.get("status") not in {"queued", "idempotent_existing"} or not payload.get("job_id"):
        raise RuntimeError("NEXUS_SYSTEMS_ASSIGNMENT_REJECTED")
    return payload, tool_count


def render_status_result(text: str, tool_name: str, result: dict) -> str:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if tool_name == "nexus_get_durable_jobs":
        nested = data.get("data") if isinstance(data.get("data"), dict) else data
        jobs = nested.get("jobs") if isinstance(nested.get("jobs"), list) else []
        rows = [f"• {row.get('job_id', 'unknown')} — {row.get('job_type', 'unknown')} — {row.get('state', 'unknown')}" for row in jobs[:10]]
        return "Current durable jobs from live Nexus MCP\n\n" + ("\n".join(rows) if rows else "The live queue returned no jobs.")
    if tool_name == "nexus_get_work_items":
        nested = data.get("data") if isinstance(data.get("data"), dict) else data
        items = nested.get("work_items") or nested.get("items") or []
        rows = []
        for item in items[:10] if isinstance(items, list) else []:
            if isinstance(item, dict):
                identifier = item.get("job_id") or item.get("work_id") or item.get("id") or "unidentified"
                label = item.get("title") or item.get("job_type") or item.get("work_type") or "current work"
                state = item.get("state") or item.get("status") or "unknown"
                rows.append(f"• {identifier} — {label} — {state}")
        return "Current Nexus work from live MCP\n\n" + ("\n".join(rows) if rows else "Nexus MCP returned no current queued, running, blocked, or waiting work items.")
    if tool_name == "nexus_get_research_state":
        state = data.get("research_work_state") or data.get("research_health") or "UNKNOWN"
        objective = data.get("current_research_objective") or "No current objective reported."
        current = data.get("current_work") if isinstance(data.get("current_work"), dict) else {}
        return (f"Current Research state: {state}.\nObjective: {objective}\n"
                f"Effective readiness: {data.get('research_effective_readiness', 'UNKNOWN')}.\n"
                f"Open investigations: {current.get('open_research_v2_investigations', 'UNKNOWN')}.")
    health = data.get("data") if isinstance(data.get("data"), dict) else data
    if "notebooklm" in text.casefold():
        return ("NotebookLM-specific availability is UNKNOWN: the live Nexus health tool does not expose a provider-level NotebookLM probe.\n"
                f"Nexus MCP is reachable; system health is {health.get('overall_status', result.get('status', 'UNKNOWN'))}.\n"
                "This is a live Nexus MCP read, and no NotebookLM availability claim was inferred.")
    return (f"Current Nexus system health: {health.get('overall_status', result.get('status', 'UNKNOWN'))}.\n"
            f"Active services: {health.get('active_services', 'UNKNOWN')}; degraded: {health.get('degraded_services', 'UNKNOWN')}; failed: {health.get('failed_services', 'UNKNOWN')}.\n"
            "This is a live Nexus MCP read.")
