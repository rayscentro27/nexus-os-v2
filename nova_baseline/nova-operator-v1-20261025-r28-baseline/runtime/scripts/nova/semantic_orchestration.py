"""Semantic front-door routing for Nova's governed Nexus capabilities.

This layer separates the owner's goal from executor identifiers.  It only
returns a direct route when an existing governed action supports it; all other
requests continue to Hermes with the discovered capability surface.
"""
from __future__ import annotations

import re
from typing import Any


_ACTION = re.compile(
    r"\b(?:have|ask|tell|let|run|put|pass|send|assign|queue|start|check|make|find|look|"
    r"review|evaluate|assess|analy[sz]e|investigate|continue|create|build|prepare|compare)\b",
    re.I,
)
_QUESTION = re.compile(r"\b(?:what|which|who|when|where|why|how|is|are|can|could|do|does|did)\b", re.I)
_ALPHA_REVIEW = re.compile(
    r"\b(?:alpha|challenge|critique|review|evaluate|assess|think about|run .* through)\b", re.I
)
_HEALTH = re.compile(r"\b(?:health|healthy|working|operational|check|make sure|verify|system)\b", re.I)
_BUSINESS_DISCOVERY = re.compile(
    r"\b(?:business|business model|opportunit|company|venture|market)\b", re.I
)
_PAST_RESULT_QUESTION = re.compile(
    r"\b(?:what did|what was|what were|show me what|show me the result|tell me what|tell me about the result|"
    r"give me the result|what happened with|what was the result of)\b",
    re.I,
)
_PRIOR_WORK_REFERENT = re.compile(
    r"\b(?:last|latest|prior|previous|earlier|already|found|say|said|think|thought|result|review|asked|that|the one|the business|the idea)\b",
    re.I,
)
_ASSIGNMENT_ACTION = re.compile(
    r"\b(?:assign|delegate|ask|tell|send|run|perform|execute|check|inspect|audit|diagnose|review|"
    r"evaluate|investigate|research|verify|make sure|look into|work on)\b", re.I
)
_DEPARTMENT_PATTERNS = {
    "RESEARCH": re.compile(r"\bresearch\b", re.I),
    "SYSTEMS": re.compile(r"\bsystems?\b", re.I),
    "ALPHA": re.compile(r"\balpha\b", re.I),
}
_MULTI_DEPARTMENT_ACTION = re.compile(
    r"\b(?:inspect|audit|diagnose|check|review|evaluate|investigate|research|verify|"
    r"analy[sz]e|monitor|repair|fix|test|validate)\b", re.I
)
_EXISTING_JOB_ID = re.compile(r"\b(job_[a-z0-9][a-z0-9_-]*)\b", re.I)
_JOB_INSPECTION_ACTION = re.compile(
    r"\b(?:check|inspect|status|progress|blocker|result|complete|completed|finished|current state|what happened|"
    r"why(?:\s+\w+){0,3}\s+blocked|retrieve|show|read|look up|report)\b", re.I,
)
_RESEARCH_PROJECT_CREATE = re.compile(
    r"\b(?:create|start|launch|open|assign|queue)\b.{0,80}\b(?:research\s+)?(?:project|objective|mission|investigation)\b|"
    r"\b(?:research\s+)?(?:project|objective|mission)\b.{0,60}\b(?:create|start|launch|open)\b",
    re.I,
)
_LEADING_ACTION = re.compile(
    r"^(?:nova[, :]*)?(?:please\s+)?(?:create|start|assign|continue|advance|run|execute|save|update|build|"
    r"write|edit|delete|send|schedule|move|archive|label|draft|publish|purchase)\b", re.I,
)


def _explicit_secondary_department_action(text: str) -> str | None:
    """Find a second department only when the request gives it its own action."""
    value = re.sub(r"\balpha\s+research\s+director\b", " ", text, flags=re.I)
    if re.search(
        rf"\b(?:research|systems?|alpha)\s+(?:and|plus)\s+(?:research|systems?|alpha)\s+"
        rf"(?:both\s+)?(?:to\s+)?{_MULTI_DEPARTMENT_ACTION.pattern}", value, re.I,
    ):
        return "MULTI"
    for department, label in (("RESEARCH", r"research"), ("SYSTEMS", r"systems?"), ("ALPHA", r"alpha")):
        if re.search(
            rf"\b(?:and|also|then)\s+(?:(?:have|ask|tell|assign|delegate|route|send)\s+)?"
            rf"(?:the\s+)?{label}\s+(?:team\s+)?(?:independently\s+|separately\s+)?"
            rf"(?:to\s+)?{_MULTI_DEPARTMENT_ACTION.pattern}",
            value, re.I,
        ):
            return department
    return None


def _is_research_mission_request(text: str) -> bool:
    """Recognize a user-owned Research mission, including a named recipient handoff."""
    first_clause = re.split(r"(?<=[.!?])\s+|\n", text, maxsplit=1)[0].strip()
    if not re.search(r"\bresearch\b", first_clause):
        return False
    if re.match(r"^(?:nova[, :]*)?(?:continue|keep going|pick up|resume|carry on|check|show|tell me|what|status)\b", first_clause):
        return False
    # Research owns the investigation when it is the requested activity.
    # Mentions of recipient departments, specialist tools, or internal stages
    # elsewhere in the objective do not create parallel Nova assignments.
    return bool(
        re.match(r"^(?:nova[, :]*)?research\b", first_clause)
        or re.search(r"\b(?:mission|objective|acceptance test|determine whether)\b", first_clause)
        or re.search(
            r"^(?:nova[, :]*)?(?:please\s+)?(?:have\s+(?:nexus|research)\s+|ask\s+(?:nexus\s+)?to\s+)?"
            r"(?:have\s+nexus\s+)?(?:research|review\s+and\s+research|investigate|look\s+into)\b",
            first_clause,
        )
    )


def _is_research_runtime_inspection(text: str) -> bool:
    """Reserve runtime inspection for an explicit Research runtime diagnostic."""
    return bool(
        re.search(
            r"\bresearch\s+(?:dispatcher|worker|queue|runtime)\b|"
            r"\b(?:dispatcher|worker|queue|runtime)\s+(?:for|of|in)\s+research\b",
            text, re.I,
        )
        and re.search(r"\b(?:inspect|diagnos\w*|check|why|not\s+claim\w*|stuck|blocked)\b", text, re.I)
    )


def _is_nexus_operational_diagnostic(text: str) -> bool:
    """Recognize requests to inspect or repair existing Nexus execution state.

    This guard intentionally runs before capability-question matching: action
    requests often mention available capabilities while asking for diagnostics.
    """
    action = re.search(
        r"\b(?:inspect|diagnos\w*|repair|restart|check|verify|fix|resume|claim|start|"
        r"check\s+(?:the\s+)?logs?|look\s+at\s+logs?)\b", text, re.I)
    target = re.search(
        r"\b(?:this|that|existing|same)\s+(?:research\s+)?job\b|"
        r"\b(?:research\s+)?(?:worker|scheduler|dispatcher|queue|heartbeat|lease|claim|"
        r"routing\s+mismatch|claim\s+failure|logs?)\b", text, re.I)
    return bool(action and target)


def _research_destination(text: str) -> str | None:
    """Extract an eventual recipient as Research context, never a parallel assignment."""
    patterns = (
        ("TRADING", r"\b(?:handoff\s+to\s+(?:the\s+)?trading|for\s+(?:nexus\s+)?trading|to\s+(?:the\s+)?trading(?:\s+department)?|trading\s+department|paper\s+trad\w*)\b"),
        ("MARKETING", r"\b(?:so\s+(?:the\s+)?marketing(?:\s+department)?\s+(?:can|could|may)|for\s+(?:the\s+)?marketing(?:\s+department)?|marketing\s+department)\b"),
        ("FUNDING", r"\b(?:so\s+(?:the\s+)?funding(?:\s+department)?\s+(?:can|could|may)|for\s+(?:the\s+)?funding(?:\s+department)?|funding\s+department)\b"),
        ("SYSTEMS", r"\b(?:so\s+(?:the\s+)?systems?\s+(?:can|could|may)|systems?\s+(?:should|can|could|will)\s+(?:implement|build|integrate|review|evaluate)|for\s+(?:the\s+)?systems?(?:\s+department)?|systems?\s+department)\b"),
    )
    for department, pattern in patterns:
        if re.search(pattern, text, re.I):
            return department
    return None


def resolve_owner_request(text: str) -> dict[str, Any]:
    """Return a confidence-scored semantic intent and any supported executor.

    Department names are entity signals only.  Task/read intent is inferred
    separately from the request's action and question structure.  Unknown or
    unsupported work is left to the Hermes executive layer rather than being
    silently forced into a department.
    """
    value = re.sub(r"\s+", " ", str(text or "").strip())
    folded = value.casefold()
    if not folded:
        return _result("UNKNOWN_OR_AMBIGUOUS", confidence=0)

    # Existing-job operations must not be swallowed by a later phrase such as
    # "available capabilities" in a request explaining its own constraints.
    if _is_nexus_operational_diagnostic(folded):
        existing_job = _EXISTING_JOB_ID.search(folded)
        return _result("NEXUS_OPERATIONAL_DIAGNOSTIC_AND_REPAIR",
                       department="SYSTEMS", capability="nexus.existing_work.diagnostics",
                       executor="nexus_existing_work_diagnostics", confidence=.99,
                       job_id=existing_job.group(1) if existing_job else None)

    if (re.search(r"\b(?:what|which|can|is|are|how many|how much|does|do)\b", folded)
            and re.search(r"\b(?:google|gmail|email|calendar|drive|tools|capabilit|services|available|access|authorized|connected)\b", folded)
            and not _LEADING_ACTION.search(value)):
        return _result("CAPABILITY_QUERY", confidence=.99)

    # A create/start request for a Research project is a durable assignment,
    # even when its subject matches a Research Room analysis mode. Analysis is
    # never a substitute for creating the requested work.
    if _RESEARCH_PROJECT_CREATE.search(folded) and re.search(r"\bresearch\b", folded):
        return _result("RESEARCH_MISSION", department="RESEARCH",
                       executor="nexus_assign_research", confidence=.99)

    # An explicit existing durable job reference plus inspection language is
    # a read, even when the same message contains Research mission vocabulary.
    # Keep this ahead of all mission and assignment classifiers.
    existing_job = _EXISTING_JOB_ID.search(folded)
    if existing_job and _JOB_INSPECTION_ACTION.search(folded):
        return _result("RESEARCH_STATUS_QUERY", department="RESEARCH",
                       capability="nexus.durable_jobs.read", executor="nexus_get_durable_jobs",
                       confidence=.99, job_id=existing_job.group(1))

    # Natural-language references to a named prior mission are valid status
    # follow-ups even when the user does not repeat its durable job ID.
    if re.search(
        r"\b(?:what(?:'s|\s+is)\s+happening\s+with|what\s+happened\s+with|"
        r"check\s+(?:the\s+)?status\s+of)\s+(?:that|the)\s+"
        r"[a-z0-9.-]+\s+(?:research|mission|objective)\b",
        folded,
    ):
        return _result("OBJECTIVE_STATUS_QUERY", department="RESEARCH",
                       capability="nexus.durable_jobs.read", executor="nexus_get_durable_jobs",
                       confidence=.94)

    # A queue/worker/dispatcher diagnostic is a runtime inspection, not research
    # about an external subject. Keep it ahead of the normal Research mission.
    if _is_research_runtime_inspection(folded):
        return _result("RESEARCH_RUNTIME_INSPECTION", department="RESEARCH",
                       executor="nexus_assign_research", confidence=.98)

    # Research intent takes precedence over incidental mentions of coding tools
    # or tests.  For example, evaluating OpenCode and proposing a disposable
    # test is a Research Room objective, not a request to queue a coding job.
    from nova.research_intent import route_research_intent
    research_intent = route_research_intent(value)
    if research_intent and research_intent["primary_mode"] == "NEXUS_ENHANCEMENT_MODE":
        result = _result("RESEARCH_ROOM_REQUEST", department="RESEARCH",
            executor="research_room_shadow_intake", confidence=.96,
            execution_mode=research_intent["primary_mode"])
        result["intent_object"] = research_intent
        return result

    # Natural requests for bounded Creative work and temporary coding tasks
    # are first-class capability intents. They remain durable worker actions;
    # no command syntax is required from Ray.
    if (re.search(r"\bcreative\b", folded)
            and re.search(r"\b(?:make|create|design|draw|build|produce)\b", folded)
            and re.search(r"\b(?:logo|graphic|image|visual|asset|design)\b", folded)):
        return _result("CREATIVE_ASSET_REQUEST", department="CREATIVE",
                       executor="nexus_assign_creative_asset", confidence=.96)
    if (re.search(r"\b(?:opencode|coding agent|code agent)\b", folded)
            and re.search(r"\b(?:create|make|build|write|run|execute|test)\b", folded)):
        return _result("BOUNDED_CODING_REQUEST", department="OPENCODE",
                       executor="nexus_assign_bounded_coding_task", confidence=.96)

    # Other Research Room modes retain their established classification order;
    # enhancement reviews alone must preempt the incidental coding-task match.
    if research_intent:
        result = _result("RESEARCH_ROOM_REQUEST", department="RESEARCH",
            executor="research_room_shadow_intake", confidence=.96,
            execution_mode=research_intent["primary_mode"])
        result["intent_object"] = research_intent
        return result

    if re.search(r"\b(?:change|modify|revise|update|replace)\b", folded) and re.search(r"\b(?:objective|goal|plan|project|task|campaign|that|it)\b", folded):
        return _result("MODIFY_EXISTING_OBJECTIVE", confidence=.82)
    if re.search(r"\b(?:current durable jobs|show .*jobs|list .*jobs|job queue)\b", folded):
        return _result("LIST_JOBS", capability="nexus.durable_jobs.read", confidence=.98)
    if (re.search(r"\b(?:check|show|tell me|what is|what's|give me)\b", folded)
            and re.search(r"\b(?:status|progress|state|update)\b", folded)
            and re.search(r"\b(?:objective|mission|assignment|job|research|systems?|alpha)\b", folded)):
        return _result("OBJECTIVE_STATUS_QUERY", confidence=.96)
    # A Google services/access question is a capability inventory read even
    # when it also says "current" or names Nexus. Classify it before the
    # generic Nexus state/status path so it cannot receive an unrelated
    # operating-status answer.
    if ((re.search(r"\b(?:what|which)\b", folded)
            and re.search(r"\bgoogle\b", folded)
            and re.search(r"\b(?:services?|tools?|capabilities|gmail|calendar|drive)\b", folded)
            and re.search(r"\b(?:access|use|connected|available|read)\b", folded)
            and not re.search(r"\b(?:send|modify|delete|archive|label|create|purchase|schedule)\b", folded))
            or (re.search(r"\b(?:is|are)\b", folded)
                and re.search(r"\b(?:google|gmail|calendar|drive)\b", folded)
                and re.search(r"\b(?:authorized|connected|working|available|accessible)\b", folded))):
        return _result("CAPABILITY_QUERY", capability="google.workspace.read_access",
                       executor="nexus_live_capability_status", confidence=.99)
    if re.search(r"\b(?:what is|what's|show|tell me).{0,40}\b(?:nexus|research|systems|supervisor|worker|notebooklm)\b.{0,32}\b(?:doing|status|state|working|available|connected|running|healthy)\b", folded):
        return _result("LIVE_STATE_QUERY", confidence=.9)

    # Past-tense questions about specialist work are reads of completed Nexus
    # evidence. Keep these ahead of assignment detection so "what did Alpha
    # think" can never create a new Alpha job.
    if _PAST_RESULT_QUESTION.search(folded) and _PRIOR_WORK_REFERENT.search(folded):
        if re.search(r"\b(?:alpha|review|evaluat(?:e|ion)|critique)\b", folded):
            return _result("PRIOR_WORK_QUERY", department="ALPHA", capability="nexus.prior_work.read", confidence=.97)
        if re.search(r"\b(?:research|found|discovered|idea|opportunity)\b", folded):
            return _result("PRIOR_WORK_QUERY", department="RESEARCH", capability="nexus.prior_work.read", confidence=.94)
        if re.search(r"\b(?:systems?|health|nexus)\b", folded):
            return _result("PRIOR_WORK_QUERY", department="SYSTEMS", capability="nexus.prior_work.read", confidence=.94)

    # A request to close one department's finding and return it to another is
    # one existing continuation workflow, not parallel independent jobs.
    if (re.search(r"\b(?:research|investigat|verify|find evidence)\b", folded)
            and re.search(r"\b(?:alpha|review|reevaluat|send .* back|then .* through)\b", folded)
            and re.search(r"\b(?:gap|weak|evidence|improv|fix|close|address)\b", folded)):
        return _result("CROSS_DEPARTMENT_CONTINUATION", department="RESEARCH",
                       capabilities=["RESEARCH", "ALPHA"], executor="nexus_assign_research", confidence=.97)

    # A Research result may explicitly request a governed handoff to Systems.
    # Only dispatch that later escalation when the marker and a concrete Systems
    # action are both present.
    if ("cross_department_required" in folded or "cross-department-required" in folded) and re.search(
        r"\b(?:have|ask|tell|assign|delegate|route|send)\s+(?:the\s+)?systems?\s+(?:team\s+)?(?:to\s+)?"
        + _MULTI_DEPARTMENT_ACTION.pattern,
        folded, re.I,
    ):
        return _result("DEPARTMENT_ASSIGNMENT", department="SYSTEMS",
                       executor="nexus_assign_department_query", confidence=.97)

    # Explicitly requested independent department actions remain multi-work.
    # Names inside Research workflow titles (for example, Alpha Research
    # Director) do not count as assignments.
    secondary_department = _explicit_secondary_department_action(folded)
    multi_target_text = re.sub(r"\balpha\s+research\s+director\b", " ", folded)
    multi_target_text = re.sub(
        r"\bresearch(?:'s)?\s+(?:last|latest|prior|previous|existing)\s+(?:idea|result|finding|review|evidence)\b|"
        r"\bresearch\s+(?:found|discovered|said|reported)\b", " ", multi_target_text)
    requested_for_multi = [name for name, pattern in _DEPARTMENT_PATTERNS.items()
                           if pattern.search(multi_target_text)]
    if secondary_department == "MULTI" and len(requested_for_multi) > 1:
        return _result("MULTI_DEPARTMENT_ASSIGNMENT", departments=requested_for_multi,
                       executor="nexus_assign_department_query", confidence=.96)
    if secondary_department and len(requested_for_multi) > 1:
        return _result("MULTI_DEPARTMENT_ASSIGNMENT", departments=requested_for_multi,
                       executor="nexus_assign_department_query", confidence=.96)

    # A scoped, actionable Research mission takes precedence over generic
    # continuation language elsewhere in its requirements and over planner
    # decomposition of Research-owned workflow components.
    if _is_research_mission_request(folded):
        return _result("RESEARCH_MISSION", department="RESEARCH",
                       executor="nexus_assign_research", confidence=.98,
                       likely_destination=_research_destination(folded))

    if re.search(r"\b(?:continue|keep going|pick up where|resume|carry on)\b", folded):
        return _result("CONTINUE_EXISTING_WORK", confidence=.88)
    # Action intent must win over capability-description matching. In
    # particular, mentioning Research/NotebookLM while asking Nova to delegate
    # work must reach the existing governed write actions. References to prior
    # Research evidence are not themselves assignment targets.
    target_text = re.sub(
        r"\bresearch(?:'s)?\s+(?:last|latest|prior|previous|existing)\s+(?:idea|result|finding|review|evidence)\b|"
        r"\bresearch\s+(?:found|discovered|said|reported)\b",
        " ", folded)
    requested_departments = [name for name, pattern in _DEPARTMENT_PATTERNS.items()
                             if pattern.search(target_text)]
    explicit_have_department = bool(re.search(r"\bhave\s+(?:the\s+)?(?:research|systems?|alpha)\b", folded))
    use_department_for_task = bool(re.search(
        r"\buse\s+(?:the\s+)?(?:research|systems?|alpha)\s+to\s+(?:inspect|audit|diagnose|check|review|evaluate|investigate|research|verify|analy[sz]e)\b",
        folded))
    if requested_departments and (_ASSIGNMENT_ACTION.search(folded) or explicit_have_department or use_department_for_task):
        # A mere mention of multiple departments (for example Alpha as the
        # Research advisor) is not an independent parallel assignment. That
        # route was already selected above when an explicit second action exists.
        if len(requested_departments) > 1:
            if "RESEARCH" in requested_departments:
                return _result("RESEARCH_MISSION", department="RESEARCH",
                               executor="nexus_assign_research", confidence=.95,
                               likely_destination=_research_destination(folded))
            return _result("MULTI_DEPARTMENT_ASSIGNMENT", departments=requested_departments,
                           executor="nexus_assign_department_query", confidence=.92)
        department = requested_departments[0]
        if department == "RESEARCH":
            intent = "RESEARCH_MISSION" if re.search(r"\b(?:objective|mission|acceptance test)\b", folded) or re.search(r"\bdetermine whether\b", folded) else "RESEARCH_REQUEST"
            return _result(intent, department=department,
                           executor="nexus_assign_research", confidence=.94)
        return _result("DEPARTMENT_ASSIGNMENT", department=department,
                       executor="nexus_assign_department_query", confidence=.94)

    # Capability discovery is a read-only fallback after explicit work
    # assignment, so an actionable Systems/Creative request cannot be
    # shadowed by incidental "tools" or "access" language.
    if re.search(
        r"\b(?:how many|count|list|show|tell me|what)\b.{0,55}\b(?:nexus\s+mcp\s+)?tools?\b"
        r"|\bwhat\s+do\s+you\s+have\s+access\s+to\b"
        r"|\bwhat\s+(?:can|could)\s+you\s+(?:access|use|do)\b"
        r"|\b(?:current|currently|available)\s+(?:nexus\s+mcp\s+)?tools?\b",
        folded,
    ):
        return _result("CAPABILITY_QUERY", capability="nexus.mcp.tool_discovery",
                       executor="nexus_mcp_tool_discovery", confidence=.99)

    if re.search(r"\b(?:create|start|launch|build|work toward)\b", folded) and re.search(r"\b(?:objective|goal|project|company|business|program)\b", folded):
        return _result("NEW_OWNER_OBJECTIVE", confidence=.82)

    if re.search(r"\b(?:what tools|what can you|what are you able|capabilit(?:y|ies)|connected to google|access to google|can you (?:use|make|create|generate|run|access|browse|search))\b", folded) or (
        "notebooklm" in folded and re.search(r"\b(?:available|connected|use|access)\b", folded)
    ):
        return _result("CAPABILITY_QUERY", confidence=.98)

    # A request to discover a company or market opportunity is Research work,
    # even when the owner does not name the department.
    if _BUSINESS_DISCOVERY.search(folded) and re.search(r"\b(?:find|discover|identify|surface|look for|worth looking|promising|potential)\b", folded):
        return _result("RESEARCH_REQUEST", department="RESEARCH", executor="nexus_assign_research", confidence=.92)

    # Cross-check a named specialist against the conversational subject. The
    # specialist name is a target; the semantic review language is the task.
    if re.search(r"\balpha\b", folded) and _ALPHA_REVIEW.search(folded):
        return _result("DEPARTMENT_ASSIGNMENT", department="ALPHA", executor="nexus_assign_department_query", confidence=.96)

    if re.search(r"\b(?:nexus|system|systems|supervisor|worker|service)\b", folded) and re.search(r"\b(?:health|healthy|operational|check|verify|make sure)\b", folded):
        return _result("DEPARTMENT_ASSIGNMENT", department="SYSTEMS", executor="nexus_assign_department_query", confidence=.9)

    if re.search(r"\bsystems?\b", folded) and _HEALTH.search(folded) and (
        _ACTION.search(folded) or re.search(r"\b(?:everything|all services|the system)\b", folded)
    ):
        if not re.search(r"\b(?:what is|what's|show me|status of|is .* available)\b", folded):
            return _result("DEPARTMENT_ASSIGNMENT", department="SYSTEMS", executor="nexus_assign_department_query", confidence=.93)

    # Named Research assignments and ordinary research requests share the
    # same Nexus Research capability. Reads about existing Research state are
    # handled above as state queries.
    if re.search(r"\bresearch\b", folded) and _ACTION.search(folded):
        return _result("RESEARCH_REQUEST", department="RESEARCH", executor="nexus_assign_research", confidence=.9)

    if re.search(r"\b(?:send|message|notify|tell)\b", folded) and re.search(r"\b(?:ray|owner|telegram|email|gmail)\b", folded):
        return _result("COMMUNICATION_ACTION", capability="communication", confidence=.8)
    if re.search(r"\b(?:analy[sz]e|evaluate|review|compare|assess|what do you think|how good)\b", folded):
        return _result("ANALYSIS_REQUEST", confidence=.76)

    if re.search(r"\b(?:look at|inspect|review|evaluate|improve|conversion)\b", folded) and re.search(r"\b(?:landing page|website|web page|site|url)\b", folded):
        required = ["BROWSER", "MARKETING"]
        if re.search(r"\b(?:competitor|customer|market|demand|compare)\b", folded):
            required.append("RESEARCH")
        if re.search(r"\b(?:visual|design|image|video|creative)\b", folded):
            required.append("CREATIVE")
        return _result("MULTI_CAPABILITY_ORCHESTRATION", capabilities=required, confidence=.88)

    # Other domains are identified for executive planning. The result records
    # capability intent without claiming a durable executor exists.
    domains = (
        ("MARKETING_REQUEST", r"\b(?:marketing|campaign|positioning|funnel|landing page|customer acquisition)\b", "MARKETING"),
        ("CREATIVE_REQUEST", r"\b(?:creative|video|image|visual|design|thumbnail|asset)\b", "CREATIVE"),
        ("FINANCE_REQUEST", r"\b(?:finance|financial model|unit economics|cash flow|break-even)\b", "FINANCE"),
        ("TRADING_REQUEST", r"\b(?:forex|trading|backtest|paper trade|indicator)\b", "TRADING"),
        ("GOOGLE_ACTION", r"\b(?:gmail|email|calendar|google drive|drive)\b", "GOOGLE"),
        ("BROWSER_ACTION", r"\b(?:browser|web page|website|landing page|look at this page)\b", "BROWSER"),
        ("FILE_OR_DOCUMENT_ACTION", r"\b(?:file|document|pdf|spreadsheet|report)\b", "FILES"),
        ("CODE_OR_SYSTEM_ACTION", r"\b(?:code|repository|software|integration|runtime|service)\b", "SYSTEMS"),
    )
    for intent, pattern, capability in domains:
        if re.search(pattern, folded):
            return _result(intent, capability=capability, confidence=.82)
    # Preserve action semantics when no governed executor exists. The worker
    # must return ACTION_NOT_AVAILABLE; it cannot fall through to read-only or
    # conversational synthesis.
    if _LEADING_ACTION.search(value):
        return _result("ACTION_NOT_AVAILABLE", confidence=.99)
    if _QUESTION.search(folded) and not _ACTION.search(folded):
        return _result("INFORMATION_QUERY", confidence=.65)
    if re.search(r"\b(?:continue|keep going|pick up where|what happened|make it better|do that|send that)\b", folded):
        return _result("FOLLOWUP_TO_EXISTING_OBJECTIVE", confidence=.6)
    return _result("UNKNOWN_OR_AMBIGUOUS", confidence=.25)


def _result(intent: str, *, department: str | None = None,
            executor: str | None = None, capability: str | None = None,
            capabilities: list[str] | None = None, departments: list[str] | None = None,
            confidence: float, job_id: str | None = None,
            likely_destination: str | None = None,
            execution_mode: str | None = None) -> dict[str, Any]:
    return {"intent": intent, "department": department, "executor": executor,
            "capability": capability, "capabilities": capabilities or ([capability] if capability else ([department] if department else (departments or []))),
            "departments": departments or ([department] if department else []),
            "execution_mode": execution_mode,
            "job_id": job_id,
            "likely_destination": likely_destination,
            "confidence": confidence,
            "requires_clarification": confidence < .55}
