"""Intent and completion guards for owner-created Research assignments.

Classification is deliberately fail-closed: a sentence is never treated as a
public-search query merely because it contains the word "research".
"""
from __future__ import annotations

import re
from typing import Any


INTENTS = {
    "RESEARCH_EXECUTION",
    "RESEARCH_RUNTIME_INSPECTION",
    "RESEARCH_MISSION",
    "RESEARCH_STATUS_QUERY",
    "NOTEBOOKLM_OPERATION",
    "PUBLIC_RESEARCH_SEARCH",
    "RESEARCH_GAP_VERIFY",
    "UNKNOWN_RESEARCH_INTENT",
}


def research_objective_type(objective: str, question: str = "") -> str:
    """Classify the supported grouped-workflow domain without changing intent."""
    value = " ".join(str(x or "") for x in (objective, question)).casefold()
    if re.search(r"\b(forex|foreign exchange|currency pair|fx trading|trading strategy)\b", value):
        return "TRADING_INTELLIGENCE"
    domain = re.search(r"\b(?:https?://)?[a-z0-9][a-z0-9.-]*\.(?:com|org|net|io|co|ai)\b", value)
    strategic_decision = re.search(
        r"\b(use|partner|copy|avoid|vendor|affiliate|ecommerce|business opportunity|launch shortcut)\b",
        value,
    )
    if (domain and strategic_decision) or re.search(
        r"\b(business opportunity|vendor|affiliate opportunity|ecommerce|shopify|tiktok shop)\b", value
    ):
        return "BUSINESS_OPPORTUNITY"
    return "UNCLASSIFIED"


def classify_research_assignment(objective: str, question: str = "") -> str:
    text = " ".join(str(x or "") for x in (objective, question)).strip()
    value = re.sub(r"\s+", " ", text.casefold())
    if not value:
        return "UNKNOWN_RESEARCH_INTENT"

    # Status is a read request, not an instruction to create more work.
    if (re.search(r"\b(status|result|receipt|checkpoint)\b", value)
            and re.search(r"\b(job|assignment|research|task)\b", value)
            and (re.search(r"\b(check|show|get|retrieve|what is|what's|read)\b", value)
                 or re.search(r"\bjob[_ -][a-z0-9_-]+\b", value))):
        return "RESEARCH_STATUS_QUERY"

    # Runtime inspection requires an operational action plus a runtime,
    # capability, authentication, worker, queue, integration, or governor
    # target.  The compound cues avoid matching ordinary topical research.
    operational = bool(re.search(
        r"\b(inspect(?:ion)?|check|verify|diagnose|audit|retrieve|test|confirm)\b", value))
    runtime_target = bool(re.search(
        r"\b(runtime|capabilit(?:y|ies)|auth(?:entication)?|integration|grouped workflow|"
        r"dedicated notebook|notebook creation|adaptive follow[- ]?up|needle|research worker|"
        r"research queue|governor|dispatcher|alpha research director)\b", value))
    if operational and runtime_target:
        return "RESEARCH_RUNTIME_INSPECTION"

    explicit_public = bool(re.search(
        r"\b(search|look up|find sources|web research|public search)\b", value)
        and re.search(r"\b(web|online|public|sources?|internet)\b", value))
    if explicit_public:
        return "PUBLIC_RESEARCH_SEARCH"

    mission_verb = bool(re.search(
        r"\b(research|investigate|assess|evaluate|compare|find|identify|analy[sz]e)\b", value))
    mission_subject = bool(re.search(
        r"\b(profitability|viability|business|opportunity|market|strategy|product|customer|"
        r"shopify|tiktok|forex|funding|competitor|demand|pricing|vendor|affiliate|ecommerce)\b", value))
    domain_decision = bool(
        re.search(r"\b(?:https?://)?[a-z0-9][a-z0-9.-]*\.(?:com|org|net|io|co|ai)\b", value)
        and re.search(r"\b(?:should\s+.*\b)?(?:use|partner|copy|avoid|vendor|affiliate)\b", value)
    )
    research_workflow_mission = bool(re.search(
        r"\b(?:run|start|perform|conduct)\b.{0,50}\b(?:governed\s+)?research\s+(?:mission|workflow)\b", value))
    if (mission_verb and (mission_subject or domain_decision)) or research_workflow_mission:
        return "RESEARCH_MISSION"

    # Direct NotebookLM operations need an explicit notebook reference and an
    # action tied to that reference. Incidental workflow mentions and verbs in
    # unrelated/negative constraints (for example, "do not create duplicate
    # jobs") do not select this path. Mission classification takes precedence
    # so NotebookLM remains an internal Research stage when both are present.
    notebook_ref = r"\bnotebook(?:lm)?(?:\s+(?:id|#))?\s*[:#]?\s*[a-z0-9][a-z0-9_-]+\b"
    direct_notebook_action = re.search(
        rf"\b(?:ask|query|summari[sz]e|read|open)\s+(?:notebooklm\s+)?{notebook_ref}|"
        rf"\b(?:add|import|attach)\b.{{0,100}}\bto\s+(?:(?:the\s+)?existing\s+)?"
        rf"(?:notebooklm\s+)?{notebook_ref}|"
        rf"\brun\s+notebooklm\s+against\s+{notebook_ref}", value)
    if direct_notebook_action:
        action_start = direct_notebook_action.start()
        action_context = value[max(0, action_start - 32):direct_notebook_action.end()]
        if not re.search(r"\b(?:do\s+not|don't|never|must\s+not)\b", action_context):
            return "NOTEBOOKLM_OPERATION"

    if re.search(r"\b(research|investigate|assess|evaluate|compare|analy[sz]e)\b", value):
        return "RESEARCH_EXECUTION"
    return "UNKNOWN_RESEARCH_INTENT"


def assignment_job_type(intent: str) -> str:
    """Map intent onto the existing durable job taxonomy where possible."""
    return {
        "RESEARCH_RUNTIME_INSPECTION": "RESEARCH_RUNTIME_INSPECT",
        "RESEARCH_MISSION": "RESEARCH_INTAKE",
        "NOTEBOOKLM_OPERATION": "NOTEBOOKLM_RESEARCH",
        "PUBLIC_RESEARCH_SEARCH": "RESEARCH_GAP_VERIFY",
        "RESEARCH_GAP_VERIFY": "RESEARCH_GAP_VERIFY",
    }.get(intent, "")


def governor_policy_job_type(job_type: str, *, nova_research_assignment: bool) -> str:
    """Reuse the already-authorized scoped Research envelope policy.

    Durable job types describe task semantics. The existing governor scope is
    intentionally retained for bounded Nova Research assignments until an
    explicit policy is provisioned for the new semantic job types.
    """
    if nova_research_assignment and job_type in {
        "RESEARCH_INTAKE", "RESEARCH_RUNTIME_INSPECT", "NOTEBOOKLM_RESEARCH", "RESEARCH_GAP_VERIFY",
    }:
        return "RESEARCH_GAP_VERIFY"
    return job_type


def result_contract(*, requested_intent: str, routed_intent: str,
                    execution_path: str, status: str, result: Any = None,
                    blocker: str | None = None) -> dict[str, Any]:
    """A route mismatch or absent executor output can never be successful."""
    expected_paths = {
        "RESEARCH_RUNTIME_INSPECTION": {"READ_ONLY_RESEARCH_RUNTIME_INSPECTOR"},
        # Intake is an entry stage, not a mission-completion receipt. A
        # successful mission requires a separately verified handoff package.
        "RESEARCH_MISSION": {"RESEARCH_HANDOFF_COMPLETE"},
        "RESEARCH_STATUS_QUERY": {"EXISTING_DURABLE_JOB_READ", "NO_NEW_MISSION"},
        "NOTEBOOKLM_OPERATION": {"NOTEBOOKLM_GOVERNED_ADAPTER"},
        "PUBLIC_RESEARCH_SEARCH": {"GOVERNED_PUBLIC_RESEARCH_SEARCH"},
    }
    same_intent = requested_intent == routed_intent
    valid_path = execution_path in expected_paths.get(requested_intent, set())
    success = str(status).upper() in {"COMPLETED", "SUCCEEDED", "SUCCEEDED_VERIFIED"}
    has_result = result is not None and result != ""
    fulfilled = bool(same_intent and valid_path and success and has_result and not blocker)
    return {
        "requested_intent": requested_intent,
        "routed_intent": routed_intent,
        "execution_path": execution_path,
        "task_fulfilled": fulfilled,
        "routing_blocker": blocker or ("INTENT_ROUTE_MISMATCH" if not same_intent else
                                         "EXECUTION_PATH_MISMATCH" if not valid_path else None),
    }
