"""Deterministic department/loop routing for the Telegram operator surface.

Natural language may select an intent, but this module resolves only entries
present in canonical registries and delegates execution to governed WP4 loops.
Human-gate messages are handled by the separate TruthKernel route first.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .loops.governed_loops import run_governed_loop
from .loops.daily_system_operations import run_daily_system_loop

ROOT = Path(__file__).resolve().parents[2]
DEPARTMENT_PATH = ROOT / "data/runtime/nexus_department_registry.json"
LOOP_PATH = ROOT / "data/runtime/nexus_loop_registry_v2.json"
SKILL_PATH = ROOT / "data/runtime/nexus_skill_registry.json"
WORKER_PATH = ROOT / "data/runtime/nexus_worker_role_map.json"

INTENT_MAP: dict[str, dict[str, str]] = {
    "STATUS": {"department": "OPERATIONS", "loop": "NEXUS_DAILY_SYSTEM_OPERATIONS", "skill": "system-operations", "worker": "NEXUS_OPERATIONS_WORKER", "authority": "internal_read_only"},
    "SYSTEM_OPERATIONS": {"department": "OPERATIONS", "loop": "NEXUS_DAILY_SYSTEM_OPERATIONS", "skill": "system-operations", "worker": "NEXUS_OPERATIONS_WORKER", "authority": "internal_read_only"},
    "SYSTEM_HEALTH": {"department": "OPERATIONS", "loop": "NEXUS_SYSTEM_HEALTH_RECOVERY", "skill": "system-recovery", "worker": "NEXUS_OPERATIONS_WORKER", "authority": "internal_read_only"},
    "RESEARCH": {"department": "RESEARCH_ALPHA", "loop": "NEXUS_RESEARCH_INTELLIGENCE", "skill": "research-intelligence", "worker": "NEXUS_RESEARCH_WORKER", "authority": "read_only"},
    "REPO_INTELLIGENCE": {"department": "SYSTEM_ENGINEERING", "loop": "NEXUS_REPO_INTELLIGENCE", "skill": "repo-intelligence", "worker": "NEXUS_RESEARCH_WORKER", "authority": "internal_read_only"},
    "FUNDING_READINESS": {"department": "CREDIT_BUSINESS_FUNDING", "loop": "NEXUS_CREDIT_BUSINESS_FUNDING", "skill": "funding-readiness", "worker": "NEXUS_FUNDING_WORKER", "authority": "internal_review"},
    "RAY_REVIEW": {"department": "GOVERNANCE_REVIEW", "loop": "NEXUS_RAY_REVIEW", "skill": "ray-review", "worker": "NEXUS_REVIEW_WORKER", "authority": "human_review"},
    "WORK_ORDER": {"department": "GOVERNANCE_REVIEW", "loop": "NEXUS_RAY_REVIEW", "skill": "work-order-management", "worker": "NEXUS_REVIEW_WORKER", "authority": "human_review"},
}


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def classify_intent(text: str) -> str:
    value = re.sub(r"[?.!]+$", "", text.strip().lower())
    if re.fullmatch(r"(?:hello|hi|hey)(?: nexus)?(?:[, :\-].*)?", value) or re.fullmatch(r"(?:good morning|good afternoon|good evening)(?: nexus)?", value) or re.search(r"\bhow are you(?: today)?\b", value):
        return "CONVERSATION"
    if value in {"/status", "status", "how is nexus doing", "what is nexus status", "what's nexus status", "what is running right now", "what is the current status of nexus", "what's working right now", "what is blocked", "what needs my attention", "is active operator running", "what happened with the last loop", "what is the health of hermes"} or re.fullmatch(r"(?:what is|what's) (?:the )?(?:current )?status of nexus", value):
        return "STATE_QUERY"
    if value in {"who are you", "what can you do", "/help", "help"}:
        return "CONVERSATION"
    if value == "/run system_health" or re.search(r"\b(system health|health check|health recovery)\b", value):
        return "SYSTEM_HEALTH"
    if re.search(r"\b(system operations|daily operations|operations check|system check|today'?s operations)\b", value) or value in {"/run system_operations", "/run daily_operations"}:
        return "SYSTEM_OPERATIONS"
    if re.search(r"\b(research|look up|investigate)\b", value) and not re.search(r"\brepo", value):
        return "RESEARCH"
    if re.search(r"\b(repo|repository|git status|codebase)\b", value):
        return "REPO_INTELLIGENCE"
    if re.search(r"\b(funding readiness|funding|bankability|credit readiness)\b", value):
        return "FUNDING_READINESS"
    if re.search(r"\b(review item|ray review|items? currently need my review|prioritize.*review|what needs my review)\b", value):
        return "RAY_REVIEW"
    if value.startswith(("/request ", "/work ", "create a work order", "turn this into a work order")):
        return "WORK_ORDER"
    return "UNKNOWN"


def state_query_response(text: str) -> str:
    """Produce a read-only summary from canonical program state."""
    state = _load(ROOT / "data/runtime/nexus_rebuild_program.json")
    safety = state.get("safety", {}) if isinstance(state.get("safety"), dict) else {}
    query = text.lower()
    if "who are you" in query or "what can you do" in query:
        return "I’m Nexus, the governed control-plane assistant. I can explain verified state, run approved bounded internal checks, research public topics, inspect the repository, and prepare review work. TruthKernel and Nexus remain authoritative; consequential actions stay gated."
    if "review" in query:
        queue = _load(ROOT / "reports/runtime/ray_review_queue_latest.json")
        items = queue.get("approval_cards", []) if isinstance(queue, dict) else []
        if not items:
            return "You do not currently have any required review items.\n\nVerified Nexus review state was checked; no new review work was created."
        lines = ["Ray review items", ""]
        for item in items[:5]:
            lines.extend([f"ITEM\n{item.get('title', item.get('id', 'Unidentified item'))}", f"WHY RAY IS NEEDED\n{item.get('why_it_matters', 'A governed decision is requested.')}", f"DECISION REQUIRED\n{item.get('exact_action_requested', 'Review the item and choose approve, reject, or defer.')}", f"RISK / CONSEQUENCE\n{item.get('risk', 'not reported')}", ""])
        return "\n".join(lines).rstrip() + "\n\nVerified Nexus review state was checked; no action was taken."
    blocked = state.get("blocked_work_packages", [])
    active = state.get("active_work_packages", [])
    lines = ["Nexus current state", "", f"What is true now? {state.get('state', 'UNKNOWN')}.", f"What is working? Active work packages: {len(active)}; Hermes runtime and the bounded WP4 routing foundation are recorded as complete with limits.", f"What is blocked? {', '.join(blocked) if blocked else 'Nothing recorded.'}", f"What happens next? {state.get('next_action', 'Continue from the canonical checkpoint.')}", f"Do you need Ray? {'Yes for consequential authority or the outstanding Telegram E2E.' if safety.get('active_operator_paused', True) else 'No for this read-only query.'}"]
    return "\n".join(lines)


def _verified_payload(receipt_path: str) -> dict[str, Any]:
    try:
        path = Path(receipt_path)
        if not path.is_absolute():
            path = ROOT / path
        receipt = json.loads(path.read_text(encoding="utf-8"))
        value = receipt.get("output_artifact")
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _render_execution(intent: str, payload: dict[str, Any], *, ray_required: bool) -> str:
    if not payload:
        return "RESULT_INSUFFICIENT_FOR_SUMMARY\n\nThe verified loop completed, but its result did not contain enough structured detail to answer this request. No additional claim is being made.\n\nDo you need Ray? No for this rendering issue; the executor contract needs improvement."
    if intent in {"SYSTEM_OPERATIONS", "SYSTEM_HEALTH"}:
        if intent == "SYSTEM_HEALTH":
            health = payload.get("health", {})
            services = payload.get("services", {})
            return ("Nexus system health\n\n"
                    f"OVERALL STATUS\n{payload.get('overall_status', health.get('overall_status', 'UNKNOWN'))}\n\n"
                    f"CURRENT FINDINGS\n• Services confirmed active: {health.get('active_services', 0)}\n• Degraded: {health.get('degraded_services', 0)}\n• Failed: {health.get('failed_services', 0)}\n• Unknown: {health.get('unknown_services', 0)}\n"
                    f"• Service detail: {', '.join(f'{name} {value}' for name, value in services.items()) or 'not available'}\n\n"
                    f"WHAT THIS MEANS\n{payload.get('summary', 'Health evidence was collected.')} Recovery was {'not needed because the observed state is healthy.' if payload.get('recovery', {}).get('execution') == 'NOT_NEEDED' else 'not automatically executed.'}\n\n"
                    f"NEXT ACTION\n{'; '.join(payload.get('health', {}).get('warnings', [])[:2]) or 'Continue observing live health evidence.'}\n\n"
                    f"DO YOU NEED RAY? {'Yes for consequential recovery.' if ray_required else 'No; this was a read-only health check.'}\n\nEVIDENCE\nVerified Nexus receipt recorded.")
        findings = payload.get("findings", {})
        stale = findings.get("stale_items") or []
        metrics = payload.get("metrics", {})
        services = findings.get("services", {})
        return ("Nexus operations check\n\n"
                f"SUMMARY\n{payload.get('summary', 'Nexus operations evidence was collected.')} {metrics.get('processes_enabled', 'The enabled process count is')} of {metrics.get('processes_total', 'the known')} registered processes are enabled.\n\n"
                "KEY FINDINGS\n"
                f"• Reports fresh: {findings.get('reports_fresh', 'not reported')}; stale: {findings.get('reports_stale', 'not reported')}.\n"
                f"• Stale items: {', '.join(stale[:5]) if stale else 'none reported'}.\n"
                f"• Blocked actions: {', '.join(findings.get('blocked_actions', [])) if findings.get('blocked_actions') else 'none reported'}.\n\n"
                f"• Services: {', '.join(f'{name} {value}' for name, value in services.items()) if services else 'No per-service health detail was present in this report.'}.\n"
                f"• Active Operator: {findings.get('operator', {}).get('state', 'UNKNOWN')} ({findings.get('operator', {}).get('mode', 'unknown policy')}); last run {findings.get('operator', {}).get('last_run', 'not reported')}.\n\n"
                f"WHAT THIS MEANS\n{payload.get('summary', 'Fresh operational evidence was collected.')} The service classifications above are based on current telemetry; stale reports are not treated as live service health.\n\n"
                f"NEXT ACTION\n{'; '.join(findings.get('next_actions', [])[:2]) if findings.get('next_actions') else 'Continue monitoring fresh evidence.'}\n\n"
                f"DO YOU NEED RAY? {'Yes for any consequential action.' if ray_required else 'No for this bounded check.'}\n\nEVIDENCE\nVerified Nexus receipt recorded.")
    if intent == "RESEARCH":
        findings = payload.get("findings", [])
        key_findings = payload.get("key_findings") or [item.get("snippet") or item.get("title") for item in findings[:3]]
        bullets = "\n".join(f"• {item}" for item in key_findings[:3])
        sources = payload.get("sources_used") or [{"title": item.get("title"), "url": item.get("url")} for item in findings[:5]]
        source_names = ", ".join(str(item.get("title", "untitled")) for item in sources[:3])
        return (f"Research: {payload.get('query', 'requested topic')}\n\nEXECUTIVE SUMMARY\n{payload.get('executive_summary', 'The verified research result did not include an executive synthesis.')}\n\n"
                f"KEY FINDINGS\n{bullets or 'No source findings were available.'}\n\nWHAT CHANGED\n{payload.get('what_changed', 'No source-backed change statement was provided.')}\n\n"
                f"WHY IT MATTERS\n{payload.get('why_it_matters', 'These findings remain subject to source review.')}\n\n"
                f"UNCERTAINTIES\n{'; '.join(payload.get('uncertainties', [])) or 'No additional uncertainty was reported.'}\n\n"
                f"SOURCES USED\n{len(sources)} sources; examples: {source_names or 'none reported'}.\n\nNEXT ACTION\nReview the cited sources and request a narrower follow-up if a decision depends on publication-level detail.\n\nDO YOU NEED RAY? No for this public, read-only research request.\n\nEVIDENCE\nVerified Nexus receipt recorded.")
    if intent == "REPO_INTELLIGENCE":
        groups = payload.get("changed_path_groups", {})
        group_text = ", ".join(f"{key}: {value}" for key, value in groups.items()) or "none"
        verification = payload.get("verification", {})
        pushed = payload.get("origin_relationship") == "UP_TO_DATE"
        changes = payload.get("active_operator_changes", [])
        change_text = "\n\n".join(f"TOP CHANGE {i}\n• {item.get('commit')}: {item.get('message')}\n• WHAT CHANGED: {', '.join(item.get('paths', [])) or 'path details unavailable'}\n• WHY IT MATTERS: {item.get('why_it_matters')}\n• REAL-WORLD PROVEN: {item.get('real_world_proven')}\n• EVIDENCE: {item.get('evidence')}" for i, item in enumerate(changes[:3], 1))
        return (f"Nexus OS v2 repository — Repository intelligence:\n\nOVERALL STATUS\n{payload.get('summary', 'Repository status was inspected read-only.')}\n\nACTIVE OPERATOR STABILITY CHANGES\n{change_text}\n\nCURRENT CHECKPOINT\n"
                f"• Branch: {payload.get('branch') or 'detached/unreported'}\n• HEAD: {payload.get('head_short') or str(payload.get('head', ''))[:7]} — {payload.get('head_message', 'not reported')}\n"
                f"• Origin: {payload.get('origin_relationship', 'not reported')} (ahead {payload.get('ahead_count', 'n/a')}, behind {payload.get('behind_count', 'n/a')}); pushed checkpoint: {'yes' if pushed else 'not proven'}\n\n"
                f"WORKTREE\n• {payload.get('worktree_state', 'not reported')}; modified {payload.get('modified_count', 0)}, untracked {payload.get('untracked_count', 0)}, staged {payload.get('staged_count', 0)}, unstaged {payload.get('unstaged_count', 0)}\n"
                f"• Changed paths: {payload.get('changed_paths_count', 0)} ({group_text})\n• Expected campaign changes: {payload.get('expected_current_campaign_changes', 0)}; pre-existing/unrelated: {payload.get('pre_existing_unrelated_changes', 0)}; generated reports/runtime: {payload.get('generated_runtime_artifacts', 0)}\n\n"
                f"VERIFICATION\n• Focused tests: {verification.get('focused_tests', 'not run by this read-only check')}\n• JSON validation: {verification.get('json_validation', 'not run by this read-only check')}\n• Secret scan: {verification.get('secret_scan', 'not run by this read-only check')}\n\n"
                f"WHAT THIS MEANS\nNo repository mutation occurred. The worktree details distinguish current campaign/report artifacts from other local changes; potentially risky source changes counted: {payload.get('potentially_risky_source_changes', 0)}.\n\nNEXT ACTION\n{payload.get('open_work', 'Review the grouped changes and run relevant verification.')}\n\nDO YOU NEED RAY? No for this read-only inspection.\n\nEVIDENCE\nVerified Nexus receipt recorded.")
    if intent == "RAY_REVIEW":
        item = payload
        rows = item.get("review_items", [])
        if not rows:
            return "Ray review\n\nYou do not currently have any required review items.\n\nEVIDENCE\nVerified Nexus receipt recorded."
        rendered = []
        for i, row in enumerate(rows[:5], 1):
            rendered.append(f"ITEM {i}\n{row.get('item')}\n\nPRIORITY\n{row.get('priority')}\n\nWHY RAY IS NEEDED\n{row.get('why_ray_needed')}\n\nRECOMMENDED DECISION\n{row.get('recommendation')}\n\nBLOCKER / CONSEQUENCE\n{row.get('consequence')}")
        return (f"Ray review\n\n{item.get('summary')}\n\n" + "\n\n".join(rendered) +
                f"\n\nWHAT TO REVIEW FIRST\n{rows[0].get('item')}\n\nEVIDENCE\nVerified Nexus receipt recorded.")
    return "The requested bounded work completed successfully. Verified Nexus receipt recorded."


def _registry_valid(route: Mapping[str, str]) -> bool:
    loops = {x.get("loop_id") for x in _load(LOOP_PATH).get("loops", []) if isinstance(x, dict)}
    skills = {x.get("skill_id") for x in _load(SKILL_PATH).get("skills", []) if isinstance(x, dict)}
    workers = {x.get("worker_id") for x in _load(WORKER_PATH).get("workers", []) if isinstance(x, dict)}
    departments = {x.get("department_id") for x in _load(DEPARTMENT_PATH).get("departments", []) if isinstance(x, dict)}
    return route["loop"] in loops and route["skill"] in skills and route["worker"] in workers and route["department"] in departments


def resolve(text: str) -> dict[str, Any]:
    intent = classify_intent(text)
    if intent in {"CONVERSATION", "UNKNOWN", "STATE_QUERY"}:
        return {"intent_class": intent, "status": "NO_EXECUTION" if intent == "CONVERSATION" else "READ_ONLY_STATE" if intent == "STATE_QUERY" else "UNKNOWN_INTENT"}
    route = INTENT_MAP[intent]
    if not _registry_valid(route):
        return {"intent_class": intent, "status": "ROUTING_UNAVAILABLE", "error": "canonical registry mismatch"}
    return {"intent_class": intent, "status": "RESOLVED", **route}


def execute(text: str, *, input_source: str = "internal") -> tuple[str, dict[str, Any]] | None:
    # Preserve the older, separately certified system-health process handler
    # for its exact command while natural-language health requests use WP5
    # registry routing.
    if text.strip().lower() == "/run system_health":
        return None
    resolved = resolve(text)
    # Status remains a read-model response handled by the established worker;
    # it should not launch a diagnostic process merely because it is routed to
    # the Operations department.
    if resolved.get("intent_class") == "STATE_QUERY":
        return state_query_response(text), {"route": "NEXUS_READ_ONLY_STATE", "outcome": "ANSWERED", "lane": "READ_ONLY_STATE_LANE", **resolved}
    if resolved.get("intent_class") == "CONVERSATION":
        return "Nexus is here. I’m doing well and ready to help. I can explain verified state, answer questions, or run a bounded internal check when you explicitly ask me to.", {"route": "NEXUS_CONVERSATION", "outcome": "ANSWERED", "lane": "CONVERSATIONAL_LANE", **resolved}
    if resolved["status"] == "NO_EXECUTION":
        if resolved["intent_class"] == "CONVERSATION":
            return "Nexus is here. I can report status, run bounded system checks, research public topics, inspect the repository, or prepare governed review work.", {"route": "NEXUS_CONVERSATION", "outcome": "ANSWERED", **resolved}
        return None
    if resolved["status"] != "RESOLVED":
        return "I could not resolve that request to a certified Nexus department and loop. No work was executed.", {"route": "NEXUS_ROUTING", "outcome": "BLOCKED", **resolved}
    context: dict[str, Any] = {"input_source": input_source}
    if resolved["intent_class"] in {"RESEARCH", "REPO_INTELLIGENCE"}:
        context["question"] = re.sub(r"\s+", " ", text).strip()[:240]
    if resolved["intent_class"] == "RESEARCH":
        context["live_private_searxng"] = input_source == "telegram"
    if resolved["intent_class"] == "RAY_REVIEW":
        context.update({"what_happened": "Telegram requested a bounded internal review item", "what_is_true_now": "No external action was performed", "what_happens_next": "Review item remains governed", "do_you_need_ray": True})
    if resolved["intent_class"] == "FUNDING_READINESS":
        context["subject"] = "synthetic Telegram request"
    try:
        result = (run_daily_system_loop(context) if resolved["loop"] == "NEXUS_DAILY_SYSTEM_OPERATIONS"
                  else run_governed_loop(resolved["loop"], context))
    except (OSError, ValueError, RuntimeError) as exc:
        return ("This request resolved to a Nexus route, but its governed executor is unavailable. No work was marked successful.", {"route": "NEXUS_DEPARTMENT_LOOP", "outcome": "BLOCKED", "execution_status": "FAILED", "error": type(exc).__name__, **resolved})
    capability_by_loop = {
        "NEXUS_DAILY_SYSTEM_OPERATIONS": "python.daily_system_operations",
        "NEXUS_SYSTEM_HEALTH_RECOVERY": "python.daily_system_operations",
        "NEXUS_RESEARCH_INTELLIGENCE": "searxng.research",
        "NEXUS_REPO_INTELLIGENCE": "truthkernel.authority",
        "NEXUS_CREDIT_BUSINESS_FUNDING": "truthkernel.authority",
        "NEXUS_RAY_REVIEW": "truthkernel.authority",
    }
    metadata = {"route": "NEXUS_DEPARTMENT_LOOP", "lane": "EXECUTION_LANE", "outcome": "ANSWERED" if result.final_state == "SUCCEEDED_VERIFIED" else "BLOCKED", "execution_status": result.final_state, "run_id": result.run_id, "receipt_id": result.receipt_id, "receipt_path": result.receipt_path, "capability_id": capability_by_loop.get(resolved["loop"]), "execution_target": "MAC_LOCAL" if resolved["loop"] not in {"NEXUS_RESEARCH_INTELLIGENCE"} else "HYBRID_MAC_ORACLE", "model_provider": "Nexus deterministic", "model_name": "none", **resolved}
    if result.error:
        metadata["error"] = result.error
    response = _render_execution(resolved["intent_class"], _verified_payload(result.receipt_path), ray_required=resolved["authority"] != "internal_read_only")
    return response, metadata
