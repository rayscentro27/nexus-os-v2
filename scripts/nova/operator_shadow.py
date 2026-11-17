"""Pure, side-effect-free Operator decision shadow for Phase 1.

This module is deliberately not imported by the live Telegram worker. It resolves
fixtures and emits a decision envelope; it has no database, network, provider,
MCP, subprocess, filesystem-write, or Telegram execution path.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from nova.context_authority import resolve_context
from nova.semantic_orchestration import resolve_owner_request

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_SNAPSHOT = ROOT / "config/nova/shadow_capability_inventory_20261020.json"


def decide_wave2_action(user_text: str, *, lineage: dict[str, Any] | None = None,
                        previous_turn: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Resolve only the eight bounded internal NOTE/FILE CRUD route classes.

    This is decision-only. It does not inspect the filesystem, call MCP, or
    create a mission. NOTE entities are note-shaped workspace artifacts; their
    concrete identity is the immutable workspace-relative path returned by MCP.
    """
    text = " ".join(str(user_text or "").split())
    folded = text.casefold()
    kind = _entity_type(text)
    if kind is None:
        previous_ids = (lineage or {}).copy()
        previous_ids.update(previous_turn or {})
        entity_ids = previous_ids.get("entity_ids") if isinstance(previous_ids.get("entity_ids"), dict) else {}
        if previous_ids.get("note_id") or entity_ids.get("note_id"):
            kind = "NOTE"
        elif previous_ids.get("file_id") or entity_ids.get("file_id"):
            kind = "FILE"
    if kind not in {"NOTE", "FILE"}:
        return None
    if re.search(r"\b(?:research|customer|production|google|drive|email|e-mail|trading|financial|publish|browser|"
                 r"send|share|invite|external|gmail|telegram|system|infrastructure)\b", folded):
        return None
    action_sequence = _ordered_crud_actions(text)
    if not action_sequence:
        return None
    action = action_sequence[0]

    entity_id = _lineage_id(kind, lineage or {}, previous_turn or {})
    route_id = f"{kind}_{action}"
    explicit_create = action == "CREATE" and bool(re.search(r"\b(?:new|another|create|make|write|save)\b", folded))
    if action in {"READ", "UPDATE", "DELETE"} and not entity_id:
        return {"ROUTE_ID": route_id, "ACTION_CLASS": action, "ENTITY_TYPE": kind,
                "ENTITY_ID": None, "CREATE_NEW_ENTITY": False, "DECISION_OWNER": "UNRESOLVED",
                "ERROR_CODE": "EXACT_ENTITY_REQUIRED", "SIDE_EFFECTS": 0}

    tool = {
        ("NOTE", "CREATE"): "nexus_write_workspace_artifact",
        ("FILE", "CREATE"): "nexus_write_workspace_artifact",
        ("NOTE", "READ"): "nexus_read_workspace_file",
        ("FILE", "READ"): "nexus_read_workspace_file",
        ("NOTE", "UPDATE"): "nexus_update_workspace_artifact",
        ("FILE", "UPDATE"): "nexus_update_workspace_artifact",
        ("NOTE", "DELETE"): "nexus_delete_workspace_artifact",
        ("FILE", "DELETE"): "nexus_delete_workspace_artifact",
    }.get((kind, action))
    capability_id = (f"mcp:nexus_mcp_remote:{tool}" if tool else None)
    postcondition = {
        "CREATE": "exact requested content exists at one newly assigned workspace path and read-back matches",
        "READ": "the exact lineage path is read; no substitute entity is used",
        "UPDATE": "the same path contains the requested content",
        "DELETE": "the exact path is absent after deletion",
    }[action]
    error_code = None
    return {"ROUTE_ID": route_id, "ACTION_CLASS": action, "ACTION_SEQUENCE": action_sequence,
            "ENTITY_TYPE": kind,
            "ENTITY_ID": None if explicit_create else entity_id,
            "CREATE_NEW_ENTITY": explicit_create, "CAPABILITY_ID": capability_id,
            "EXECUTION_ADAPTER": "R08.workspace_file_mcp",
            "SUCCESS_CONDITION": postcondition, "SIDE_EFFECTS": 0,
            "DECISION_OWNER": "NOVA_OPERATOR", "SHADOW_ONLY": True,
            "ERROR_CODE": error_code}


def decide_research_case_resolution(
    user_text: str,
    *,
    lineage: dict[str, Any] | None = None,
    previous_turn: dict[str, Any] | None = None,
    active_mission: dict[str, Any] | None = None,
    conversation_cases: list[str] | None = None,
) -> dict[str, Any] | None:
    """Resolve Research case intent without creating work or calling Research.

    Exact case selection follows the Phase 5 precedence: explicit ID, immediate
    delivered turn, active mission, current conversation candidates, then
    durable lineage. A new-case request is represented explicitly and never
    inferred from a missing case reference.
    """
    text = " ".join(str(user_text or "").split())
    folded = text.casefold()
    if not re.search(r"\bresearch\b|\bresearch\s+cases?\b|\bthat\s+case\b", folded):
        return None
    lineage = lineage if isinstance(lineage, dict) else {}
    previous_turn = previous_turn if isinstance(previous_turn, dict) else {}
    active_mission = active_mission if isinstance(active_mission, dict) else {}

    explicit_new = bool(re.search(
        r"\b(?:start|create|open|begin)\s+(?:(?:a|an)\s+)?(?:new|another|separate)\s+"
        r"(?:research(?:\s+case)?|case|project|objective)\b", folded
    ))
    if explicit_new:
        return {
            "ROUTE_IDS": ["R13.case_resolution", "R13.continue_vs_new"],
            "DECISION": "CREATE_NEW_CASE", "TARGET_ENTITY_TYPE": "RESEARCH_CASE",
            "TARGET_ENTITY_ID": None, "CREATE_NEW_ENTITY": True,
            "MISSION_REQUIRED": True, "EXECUTION_PERFORMED": False,
            "SIDE_EFFECTS": 0, "DECISION_OWNER": "NOVA_OPERATOR",
            "SUCCESS_CONDITION": "A new Research case is created only through a later explicitly authorized execution path.",
            "RESOLUTION_SOURCE": "EXPLICIT_NEW_CASE_REQUEST",
        }

    explicit_id = re.search(r"\brcase_[A-Za-z0-9_.:-]{4,120}\b", text, re.I)
    candidates: list[tuple[str, str]] = []
    if explicit_id:
        candidates.append(("EXPLICIT_CASE_ID", explicit_id.group(0)))

    def add(source: str, value: Any) -> None:
        if isinstance(value, str) and value.strip():
            candidates.append((source, value.strip()))

    def from_case_container(source: str, value: Any) -> None:
        if isinstance(value, dict):
            for key in ("case_id", "research_case_id"):
                add(source, value.get(key))
            for item in value.get("entity_lineage", []) if isinstance(value.get("entity_lineage"), list) else []:
                if isinstance(item, dict) and str(item.get("entity_type", "")).upper() == "RESEARCH_CASE":
                    add(source, item.get("entity_id"))

    # Immediate-turn references are trusted only when this request refers to
    # that turn (or the turn itself carried an exact Research case identifier).
    previous_ids = previous_turn.get("entity_ids") if isinstance(previous_turn.get("entity_ids"), dict) else {}
    add("IMMEDIATE_PREVIOUS_TURN", previous_turn.get("research_case_id"))
    add("IMMEDIATE_PREVIOUS_TURN", previous_turn.get("case_id"))
    add("IMMEDIATE_PREVIOUS_TURN", previous_ids.get("research_case_id"))
    add("IMMEDIATE_PREVIOUS_TURN", previous_ids.get("case_id"))
    for field in ("user_text", "assistant_text"):
        match = re.search(r"\brcase_[A-Za-z0-9_.:-]{4,120}\b", str(previous_turn.get(field) or ""), re.I)
        if match:
            add("IMMEDIATE_PREVIOUS_TURN", match.group(0))

    from_case_container("ACTIVE_MISSION", active_mission)
    active_lineage = active_mission.get("current_objective_lineage")
    from_case_container("ACTIVE_MISSION", active_lineage)

    for case_id in conversation_cases or []:
        add("CURRENT_CONVERSATION", case_id)

    # Durable lineage is deliberately last; generic job/objective IDs cannot
    # displace a case identity.
    add("DURABLE_LINEAGE", lineage.get("case_id"))
    add("DURABLE_LINEAGE", lineage.get("research_case_id"))
    from_case_container("DURABLE_LINEAGE", lineage.get("case_entity"))
    for item in lineage.get("entity_lineage", []) if isinstance(lineage.get("entity_lineage"), list) else []:
        if isinstance(item, dict) and str(item.get("entity_type", "")).upper() == "RESEARCH_CASE":
            add("DURABLE_LINEAGE", item.get("entity_id"))

    # Do not use previous-turn lineage for unrelated text. It is exact only
    # when the request has a continuation/status reference.
    refers_existing = bool(re.search(
        r"\b(?:that|this|same|existing|current|the|which|what|who)\b|\b(?:continue|continuing|keep|finish|resume|answer|status|read|check|"
        r"synthesi[sz]e|review|recommendation|remaining questions)\b", folded
    ))
    if not refers_existing:
        candidates = [item for item in candidates if item[0] == "EXPLICIT_CASE_ID"]
    selected = next(((source, case_id) for source, case_id in candidates
                     if re.fullmatch(r"rcase_[A-Za-z0-9_.:-]{4,120}", case_id, re.I)), None)
    if selected is None:
        decision = "UNRESOLVED"
        case_id = None
        source = "NO_EXACT_CASE_REFERENCE"
    else:
        source, case_id = selected
        decision = "READ_CASE" if re.search(r"\b(?:status|show|read|check|which|what|where)\b", folded) and not re.search(
            r"\b(?:continue|keep working|keep going|finish|answer|gather|try another|outside review|synthesize)\b", folded
        ) else "CONTINUE_EXISTING_CASE"
    return {
        "ROUTE_IDS": ["R13.case_resolution", "R13.continue_vs_new"],
        "DECISION": decision, "TARGET_ENTITY_TYPE": "RESEARCH_CASE",
        "TARGET_ENTITY_ID": case_id, "CREATE_NEW_ENTITY": False,
        "MISSION_REQUIRED": decision == "CONTINUE_EXISTING_CASE",
        "EXECUTION_PERFORMED": False, "SIDE_EFFECTS": 0,
        "DECISION_OWNER": "NOVA_OPERATOR", "RESOLUTION_SOURCE": source,
        "SUCCESS_CONDITION": ("Resolve the exact existing Research case; no case, objective, project, or job is created by resolution."
                              if case_id else None),
    }


def plan_research_continuation(
    *,
    case_id: str,
    objective_id: str | None,
    project_id: str | None,
    durable_job_id: str | None,
    case_state: dict[str, Any] | None,
    approved_capability_ids: Iterable[str],
    worker_failure: bool = False,
    receipt_missing_source_exists: bool = False,
    outside_review_requested: bool = False,
    boundary_evidence: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Choose a bounded same-case continuation step without executing it.

    The only inputs are exact lineage, a read-only case snapshot, and the live
    approved capability IDs. Empty plans and worker/receipt failures remain
    recoverable; a true-boundary candidate requires explicit exhaustion proof.
    """
    state = case_state if isinstance(case_state, dict) else {}
    capabilities = set(approved_capability_ids)
    exact_case = bool(re.fullmatch(r"rcase_[A-Za-z0-9_.:-]{4,120}", str(case_id or ""), re.I))
    open_questions = state.get("open_questions") if isinstance(state.get("open_questions"), list) else []
    case_ready = str(state.get("status") or "").upper() in {"RECOMMENDATION_READY", "COMPLETE"}
    complete = case_ready and not open_questions
    ids = {
        "case_read": "mcp:nexus_mcp_remote:nexus_get_research_case",
        "controller_status": "mcp:nexus_mcp_remote:nexus_get_research_controller_status",
        "controller_questions": "mcp:nexus_mcp_remote:nexus_get_research_controller_open_questions",
        "controller_results": "mcp:nexus_mcp_remote:nexus_get_research_controller_results",
        "controller_continue": "mcp:nexus_mcp_remote:nexus_research_controller_continue",
        "controller_advisor": "mcp:nexus_mcp_remote:nexus_research_controller_advisor_request",
        "case_continue": "mcp:nexus_mcp_remote:nexus_research_controller_continue",
        "execution_trace": "mcp:nexus_mcp_remote:nexus_get_research_execution_trace",
        "synthesis": "mcp:nexus_mcp_remote:nexus_record_research_synthesis",
        "recommendation": "mcp:nexus_mcp_remote:nexus_record_research_recommendation",
    }
    selected: list[str] = []
    action = "UNRESOLVED"
    next_step = "Preserve the mission and resolve exact Research lineage before planning."
    recovery = "NO_EXECUTION"
    blocker = False
    blocker_class = None
    if not exact_case:
        action = "UNRESOLVED"
    elif complete and ids["case_read"] in capabilities:
        action = "VERIFY_FINAL_STATE"
        selected = [ids["case_read"]]
        next_step = "Read the same exact case and independently verify its terminal state and requested outcome."
    elif receipt_missing_source_exists and ids["case_read"] in capabilities:
        action = "VERIFY_SOURCE_POSTCONDITION"
        selected = [ids["case_read"]]
        next_step = "Read the same case/source registry; treat a usable existing source as authoritative despite the missing receipt."
        recovery = "VERIFY_POSTCONDITION"
    elif worker_failure and ids["controller_continue"] in capabilities:
        action = "RECOVER_SAME_CASE_THROUGH_RESEARCH_ROOM"
        selected = [ids["controller_continue"]]
        next_step = "Continue or reroute the exact case through the Research Room controller and Advisor path; do not use the legacy notebook worker."
        recovery = "REPAIR_OR_REROUTE"
    elif outside_review_requested and ids["controller_advisor"] in capabilities:
        action = "REQUEST_SAME_CASE_CHALLENGER_REVIEW"
        selected = [ids["controller_advisor"]]
        next_step = "Request a challenger/second opinion through Research Room against the same case and persist it as a review record."
    elif open_questions and ids["controller_continue"] in capabilities:
        action = "CONTINUE_SAME_CASE_THROUGH_RESEARCH_ROOM"
        selected = [ids["controller_continue"]]
        next_step = "Continue one bounded Research Room participant turn on the same exact case, then read controller status/results and reassess required questions."
        recovery = "SAME_CASE_CONTINUATION"
    elif state.get("synthesis_complete") is False and ids["synthesis"] in capabilities:
        action = "COMPLETE_SAME_CASE_SYNTHESIS"
        selected = [ids["synthesis"]]
        next_step = "Complete evidence-linked synthesis on the same case before evaluating completion."
    elif ids["controller_status"] in capabilities:
        action = "VERIFY_RESEARCH_ROOM_CASE_STATUS"
        selected = [ids["controller_status"]]
        next_step = "Read the same production case's Research Room controller status before deciding completion."
    elif state.get("recommendation_required") and not state.get("recommendation") and ids["recommendation"] in capabilities:
        action = "PERSIST_SAME_CASE_RECOMMENDATION"
        selected = [ids["recommendation"]]
        next_step = "Persist the evidence-backed recommendation on the same case, then read it back."
    else:
        evidence = boundary_evidence if isinstance(boundary_evidence, dict) else {}
        exhausted = all(evidence.get(key) is True for key in (
            "direct_capability_checked", "alternate_capability_checked", "adapter_reroute_checked",
            "schema_lineage_repair_checked", "capability_acquisition_checked",
            "postcondition_recovery_checked", "same_case_resume_checked", "alternatives_exhausted",
        ))
        if exhausted:
            action = "TRUE_BOUNDARY_CANDIDATE"
            blocker = True
            blocker_class = "EVIDENCE_BACKED_CAPABILITY_BOUNDARY"
            next_step = "Report the verified remaining boundary with the exhausted-path evidence."
            recovery = "EXHAUSTED_WITH_EVIDENCE"
        else:
            action = "CAPABILITY_PREFLIGHT_REQUIRED"
            next_step = "Inspect approved capabilities and safe acquisition/substitution paths; do not declare blocked."
            recovery = "DISCOVER_SUBSTITUTE_OR_ACQUIRE"
    target = {"case_id": case_id, "objective_id": objective_id, "project_id": project_id,
              "durable_job_id": durable_job_id}
    return {
        "TARGET_ENTITY_TYPE": "RESEARCH_CASE", "TARGET_ENTITY_ID": case_id if exact_case else None,
        "TARGET_OBJECTIVE_ID": objective_id, "TARGET_PROJECT_ID": project_id,
        "TARGET_EXECUTION_JOB_ID": durable_job_id, "ACTION_CLASS": action,
        "SELECTED_CAPABILITY_IDS": selected, "NEXT_STEP": next_step,
        "SUCCESS_CONDITION": ("The same exact Research case reaches the requested result; required questions are answered or explicitly bounded, synthesis/recommendation state is persisted when requested, and final case state is verified." if exact_case else None),
        "EXPECTED_POSTCONDITION": {"same_case": case_id, "case_complete": complete,
                                   "open_question_count": len(open_questions)},
        "BLOCKER": blocker, "BLOCKER_CLASS": blocker_class,
        "RECOVERY_CLASS": recovery, "CREATE_NEW_ENTITY": False,
        "MISSION_COMPLETE": bool(complete and action == "VERIFY_FINAL_STATE"),
        "SIDE_EFFECTS": 0, "EXECUTION_PERFORMED": False,
        "UNKNOWN_CAPABILITY_IDS": [value for value in selected if value not in capabilities],
        "ENTITY_LINEAGE": target,
    }


def _ordered_crud_actions(text: str) -> list[str]:
    patterns = {
        "CREATE": r"\b(?:create|make|write|save)\b",
        "READ": r"\b(?:read|show|open|inspect)\b|\bwhat did you just create\b",
        "UPDATE": r"\b(?:update|edit|change|overwrite|revise)\b",
        "DELETE": r"\b(?:delete|remove)\b",
    }
    found: list[tuple[int, str]] = []
    for action, pattern in patterns.items():
        found.extend((match.start(), action) for match in re.finditer(pattern, text, re.I))
    # Keep absence verification explicit in the requested action graph. The
    # worker maps it to the bounded read capability; it is not a mutation verb.
    delete_positions = [position for position, action in found if action == "DELETE"]
    if delete_positions:
        verify_pattern = r"\b(?:verify|confirm|check)\b.{0,64}\b(?:gone|absent|not\s+found|deleted)\b"
        for match in re.finditer(verify_pattern, text, re.I | re.S):
            if match.start() > delete_positions[-1]:
                found.append((match.start(), "VERIFY_ABSENT"))
                break
    return [action for _, action in sorted(found)]


def approved_shadow_capabilities(path: Path = CAPABILITY_SNAPSHOT) -> dict[str, dict[str, Any]]:
    """Read only the timestamped allow-list captured from live approved discovery."""
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return {
        f"{row['server_id']}:{row['name']}": row
        for row in snapshot.get("capabilities", [])
        if isinstance(row, dict) and row.get("server_id") and row.get("name")
    }


def _entity_type(text: str) -> str | None:
    value = text.casefold()
    for pattern, kind in (
        (r"\b(?:research\s+)?cases?\b", "RESEARCH_CASE"),
        (r"\bjobs?\b", "RESEARCH_JOB"),
        (r"\bnotes?\b", "NOTE"),
        (r"\bfiles?|documents?\b", "FILE"),
        (r"\bprojects?\b", "RESEARCH_PROJECT"),
        (r"\bmissions?|objectives?\b", "OPERATOR_MISSION"),
    ):
        if re.search(pattern, value):
            return kind
    return None


def _lineage_id(kind: str | None, lineage: dict[str, Any], previous_turn: dict[str, Any]) -> str | None:
    key = {
        "RESEARCH_CASE": "case_id", "RESEARCH_JOB": "job_id", "NOTE": "note_id",
        "FILE": "file_id", "RESEARCH_PROJECT": "project_id", "OPERATOR_MISSION": "mission_id",
    }.get(kind)
    if key and lineage.get(key):
        return str(lineage[key])
    ids = previous_turn.get("entity_ids") or {}
    if key and isinstance(ids, dict) and ids.get(key):
        return str(ids[key])
    if key and previous_turn.get(key):
        return str(previous_turn[key])
    return None


def _capability_id(name: str | None, inventory: dict[str, dict[str, Any]]) -> str | None:
    if not name:
        return None
    server = "nova_operator" if name == "nexus_get_operator_mission_status" else "nexus_mcp_remote"
    key = f"{server}:{name}"
    if key not in inventory:
        return None
    return f"nova:operator:{name}" if server == "nova_operator" else f"mcp:{server}:{name}"


def _success_condition(action: str, kind: str | None, entity_id: str | None) -> dict[str, str] | None:
    if action in {"READ", "CONVERSATIONAL"}:
        return None
    if action == "CONTINUE":
        return {"description": "The same exact Research case reaches the requested result.",
                "verifier": f"Read back {entity_id or 'the exact case id'} and verify the requested terminal/postcondition."}
    if action == "RETRY":
        return {"description": "The same exact job completes or reaches a verified recoverable state.",
                "verifier": f"Read back {entity_id or 'the exact job id'}; no replacement job is created."}
    if action == "DELETE":
        return {"description": "The exact requested note is absent and no other note changed.",
                "verifier": f"Read back {entity_id or 'the exact note id'} and confirm absence."}
    if action == "UPDATE":
        return {"description": "The same exact file/note reflects the requested change.",
                "verifier": f"Read back {entity_id or 'the exact entity id'} and compare the requested fields."}
    if action == "CREATE_VERSION":
        return {"description": "A distinct new version exists and the source entity remains unchanged.",
                "verifier": "Read back the new id and source id; verify they are distinct."}
    if action == "CREATE":
        return {"description": f"One new {kind or 'entity'} exists for the requested subject.",
                "verifier": "Read back one created entity and verify its parent/request id."}
    if action == "SYSTEMS_ACTION":
        return {"description": "The original Systems fault is gone and the target worker is healthy.",
                "verifier": "Read the original fault evidence and live worker health."}
    if action == "MULTI_CAPABILITY":
        return {"description": "Each explicitly requested subgoal reaches its own verified postcondition.",
                "verifier": "Verify every subgoal against the same parent request; do not infer completion from one step."}
    return {"description": "The requested objective postcondition is verified.",
            "verifier": "Use the exact target id and independent read-back evidence."}


def decide_shadow_request(
    user_text: str,
    *,
    lineage: dict[str, Any] | None = None,
    previous_turn: dict[str, Any] | None = None,
    active_mission: dict[str, Any] | None = None,
    completed_mission: dict[str, Any] | None = None,
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a normalized decision without creating or executing anything."""
    text = " ".join(str(user_text or "").split())
    lineage = lineage or {}
    previous_turn = previous_turn or {}
    inventory = capabilities if capabilities is not None else approved_shadow_capabilities()
    semantic = resolve_owner_request(text)
    context = resolve_context(text, previous_turn=previous_turn, active_mission=active_mission,
                              recent_completed_mission=completed_mission,
                              authoritative_mission_snapshot=completed_mission,
                              entity_lineage=lineage)
    folded = text.casefold()
    explicit_new = bool(re.search(
        r"\b(?:create|start|open|make)\s+(?:(?:a|an)\s+)?(?:another|new|additional|separate)\s+"
        r"(?:(?:research|internal|small|bounded)\s+){0,3}(?:case|job|project|note|file|objective)\b", folded
    ))
    kind = _entity_type(text)
    entity_id = _lineage_id(kind, lineage, previous_turn)
    if kind is None and re.search(r"\b(?:update|edit|overwrite|delete|remove)\b", folded):
        ids = previous_turn.get("entity_ids") or {}
        if isinstance(ids, dict):
            for key, inferred in (("note_id", "NOTE"), ("file_id", "FILE")):
                if ids.get(key):
                    kind, entity_id = inferred, str(ids[key])
                    break
    if kind is None and re.search(r"\b(?:another|new)\s+version\b", folded):
        ids = previous_turn.get("entity_ids") or {}
        if isinstance(ids, dict):
            for key, inferred in (("file_id", "FILE"), ("note_id", "NOTE")):
                if ids.get(key):
                    kind, entity_id = inferred, str(ids[key])
                    break
    resolved = context.get("resolved_referent") if isinstance(context.get("resolved_referent"), dict) else {}
    context_entity_id = context.get("resolved_entity_id") or resolved.get("case_id") or resolved.get("job_id")
    if context_entity_id and not explicit_new:
        entity_id = str(context_entity_id)

    if kind and entity_id and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", entity_id):
        action, capability = "UNRESOLVED", None
    elif context.get("intent") == "CURRENT_STATE":
        action, kind, entity_id, capability = "READ", "OPERATOR_MISSION", None, "nexus_get_operator_mission_status"
    elif context.get("intent") == "RECENT_COMPLETED_WORK":
        action, kind = "READ", "OPERATOR_MISSION"
        entity_id = str((completed_mission or {}).get("mission_id") or "") or None
        capability = "nexus_get_operator_mission_status"
    elif context.get("intent") == "COMPLETION_EXPLANATION":
        action, kind = "READ", "OPERATOR_MISSION"
        entity_id = str((completed_mission or {}).get("mission_id") or "") or None
        capability = "nexus_get_operator_mission_status"
    elif context.get("intent") == "IMMEDIATE_REFERENT" or re.search(r"\b(?:summari[sz]e|explain|repeat)\s+(?:that|it|this)\b", folded):
        action, capability = "READ", None
        previous_ids = previous_turn.get("entity_ids") or {}
        if not kind and isinstance(previous_ids, dict):
            kind = next((k for k in ("case_id", "job_id", "file_id", "note_id") if previous_ids.get(k)), None)
            kind = {"case_id":"RESEARCH_CASE", "job_id":"RESEARCH_JOB", "file_id":"FILE", "note_id":"NOTE"}.get(kind, kind)
            entity_id = _lineage_id(kind, {}, previous_turn)
    elif re.search(r"\bdelete\b", folded):
        action, capability = "DELETE", None
    elif re.search(r"\b(?:retry|re-run|rerun)\b", folded):
        action, capability = "RETRY", None
    elif re.search(r"\b(?:create|start|open|make)\b", folded) and explicit_new:
        action = "CREATE"
        capability = "nexus_assign_research" if kind == "RESEARCH_CASE" else "nexus_write_workspace_artifact"
        entity_id = None
    elif re.search(r"\b(?:another|new)\s+version\b", folded):
        action, capability = "CREATE_VERSION", "nexus_write_workspace_artifact"
    elif re.search(r"\b(?:update|edit|overwrite)\b", folded):
        action, capability = "UPDATE", None
    elif re.search(r"\b(?:and then|then|also)\b", folded) and re.search(r"\b(?:research|systems?)\b", folded):
        action, capability = "MULTI_CAPABILITY", None
    elif (kind == "RESEARCH_CASE" and entity_id and
          re.search(r"\b(?:outside review|outside reviewer|challenger|second opinion|advisor review)\b", folded)):
        action, capability = "ADVISOR_REVIEW", "nexus_research_controller_advisor_request"
    elif (kind == "RESEARCH_CASE" and entity_id and
          re.search(r"\b(?:continue|keep working|keep going|resume|advance|finish|answer the remaining)\b", folded)):
        action, capability = "CONTINUE", "nexus_research_controller_continue"
    elif re.search(r"\b(?:systems?|worker|dispatcher)\b", folded) and re.search(r"\b(?:fix|repair|restart|make healthy)\b", folded):
        action, kind, capability = "SYSTEMS_ACTION", "SYSTEM_COMPONENT", "nexus_assign_department_query"
        entity_id = _lineage_id(kind, lineage, previous_turn)
    elif re.search(r"\b(?:read|show|open|inspect)\b", folded) and kind == "FILE":
        action, capability = "READ", "nexus_read_workspace_file"
    elif re.search(r"\b(?:status|health|healthy|working on|working right now)\b", folded):
        action, capability = "READ", "nexus_get_system_health"
    else:
        imperative = bool(re.search(r"\b(?:create|start|open|make|update|edit|delete|remove|retry|continue|resume|fix|repair|send|write|build)\b", folded))
        action = "ACTION" if imperative else "CONVERSATIONAL"
        capability = None

    if action == "MULTI_CAPABILITY":
        selected_names = []
        if "case_id" in lineage and "continue" in folded:
            selected_names.append("nexus_research_controller_continue")
        selected_names.append("nexus_get_system_health" if "systems" in folded else "nexus_get_research_state")
    else:
        selected_names = [capability] if capability else []
    selected_ids = [_capability_id(name, inventory) for name in selected_names]
    unknown = [name for name, cap_id in zip(selected_names, selected_ids) if cap_id is None]
    selected_ids = [cap_id for cap_id in selected_ids if cap_id]
    if unknown:
        selected_ids = []

    if action == "DELETE" and not selected_ids:
        boundary = "APPROVED_EXACT_ENTITY_DELETE_CAPABILITY_NOT_PRESENT"
    elif action == "UPDATE" and not selected_ids:
        boundary = "APPROVED_IN_PLACE_UPDATE_CAPABILITY_NOT_PRESENT"
    elif action == "RETRY" and not selected_ids:
        boundary = "APPROVED_SAME_JOB_RETRY_CAPABILITY_NOT_PRESENT"
    else:
        boundary = "OWNER_APPROVAL_REQUIRED_FOR_DESTRUCTIVE_OR_EXTERNAL_WRITE" if action in {"DELETE", "UPDATE"} else None

    new_entity = explicit_new or action in {"CREATE_VERSION", "CREATE"}
    if action in {"CONTINUE", "RETRY", "UPDATE", "DELETE"}:
        new_entity = False
    success = _success_condition(action, kind, entity_id)
    subgoals = []
    if action == "MULTI_CAPABILITY":
        if "case_id" in lineage and "continue" in folded:
            subgoals.append({"target_entity_type": "RESEARCH_CASE", "target_entity_id": str(lineage["case_id"]),
                             "action_class": "CONTINUE", "capability_id": selected_ids[0] if selected_ids else None})
        if "systems" in folded:
            subgoals.append({"target_entity_type": "SYSTEM_COMPONENT", "target_entity_id": None,
                             "action_class": "READ_HEALTH", "capability_id": selected_ids[-1] if selected_ids else None})
    source = context.get("context_source")
    data_source = ("PREVIOUS_ASSISTANT_TURN" if source == "PREVIOUS_ASSISTANT_TURN" else
                   "AUTHORITATIVE_OPERATOR_SNAPSHOT" if action == "READ" else
                   "EXACT_DURABLE_LINEAGE" if entity_id else "USER_REQUEST")
    active_status = (active_mission or {}).get("status")
    final_status = ((completed_mission or {}).get("status")
                    if context.get("intent") in {"RECENT_COMPLETED_WORK", "COMPLETION_EXPLANATION"} else None)
    error_behavior = ("MALFORMED_ENTITY_ID_NO_EXECUTION" if action == "UNRESOLVED" else
                      "UNAVAILABLE_SNAPSHOT_NO_FABRICATION" if active_status in {"CURRENT_STATE_UNAVAILABLE", "CURRENT_STATE_UNKNOWN"} else
                      "MISSING_ENTITY_RETURNS_NOT_FOUND" if action == "READ" and entity_id is None and kind == "OPERATOR_MISSION" and context.get("intent") in {"RECENT_COMPLETED_WORK", "COMPLETION_EXPLANATION"} else
                      "STRUCTURED_GOVERNED_ERROR" if action not in {"READ", "CONVERSATIONAL"} else "NONE")
    return {
        "REQUEST_ID": hashlib.sha256(text.encode("utf-8")).hexdigest()[:20],
        "USER_TEXT": text,
        "INTENT": semantic.get("intent") or action,
        "TARGET_ENTITY_TYPE": kind,
        "TARGET_ENTITY_ID": entity_id,
        "ACTION_CLASS": action,
        "MISSION_REQUIRED": action not in {"READ", "CONVERSATIONAL"},
        "CREATE_NEW_ENTITY": bool(new_entity),
        "SELECTED_CAPABILITY_ID": selected_ids[0] if len(selected_ids) == 1 else selected_ids or None,
        "SELECTED_EXECUTION_ADAPTER": ("ordered governed MCP adapters" if len(selected_ids) > 1 else
                                        "Operator internal read adapter" if selected_ids and selected_ids[0].startswith("nova:operator:") else
                                        "governed MCP adapter" if selected_ids else None),
        "SUCCESS_CONDITION": success,
        "APPROVAL_BOUNDARY": boundary,
        "EXPECTED_POSTCONDITION": success,
        "RECOVERY_CLASS": "RETRY_SAME_ENTITY" if action == "RETRY" else "SAME_ENTITY_CONTINUATION" if action == "CONTINUE" else "NONE",
        "SHADOW_ONLY": True,
        "EXECUTION_PERFORMED": False,
        "SIDE_EFFECTS": 0,
        "UNKNOWN_CAPABILITY_IDS": unknown,
        "CONTEXT_SOURCE": context.get("context_source"),
        "DATA_SOURCE": data_source,
        "RESULT_SHAPE": "AUTHORITATIVE_MISSION_SNAPSHOT" if kind == "OPERATOR_MISSION" else "READ_ONLY_REFERENT" if action == "READ" else "ACTION_DECISION",
        "CURRENT_STATE": active_status,
        "FINAL_STATE": final_status,
        "ERROR_BEHAVIOR": error_behavior,
        "SUBGOALS": subgoals,
    }


def completion_authorized(*, tool_succeeded: bool, postcondition_verified: bool,
                          receipt_valid: bool) -> bool:
    """A successful step alone is never enough to complete the mission."""
    return bool(tool_succeeded and postcondition_verified and receipt_valid)


def recovery_class(failure: str, *, genuine_boundary: bool = False) -> str:
    """Failures remain recoverable unless a real approval/security boundary exists."""
    if genuine_boundary:
        return "WAIT_FOR_APPROVAL_BOUNDARY"
    return {
        "tool_failure": "RETRY_OR_ALTERNATE",
        "retry_limit": "ALTERNATE_OR_REPAIR",
        "capability_gap": "ACQUIRE_OR_ALTERNATE_CAPABILITY",
        "worker_failure": "REPAIR_OR_REROUTE",
        "missing_receipt": "VERIFY_POSTCONDITION",
    }.get(failure, "DIAGNOSE_AND_PRESERVE_MISSION")


def compare_decisions(live: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    live_target = (live.get("target_type"), live.get("target_id"))
    shadow_target = (shadow.get("TARGET_ENTITY_TYPE"), shadow.get("TARGET_ENTITY_ID"))
    entity_match = live_target == shadow_target
    action_match = live.get("action") == shadow.get("ACTION_CLASS")
    live_cap = live.get("capability")
    shadow_cap = shadow.get("SELECTED_CAPABILITY_ID")
    capability_equivalent = live_cap == shadow_cap or (isinstance(shadow_cap, list) and live_cap in shadow_cap)
    status = "EQUIVALENT" if entity_match and action_match and capability_equivalent else "AMBIGUOUS"
    return {"ENTITY_MATCH": entity_match, "ACTION_MATCH": action_match,
            "CAPABILITY_EQUIVALENT": capability_equivalent, "SHADOW_BETTER": False,
            "DISAGREEMENT_REASON": None if status == "EQUIVALENT" else "fixture live route and shadow decision differ; review required",
            "CLASSIFICATION": status}
