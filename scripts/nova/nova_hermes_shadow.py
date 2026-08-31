"""Isolated Hermes-native Nova runner.

The canonical Telegram worker invokes this through the Hermes-supported
interpreter. The same runner supports silent certification shadow execution
and user-visible primary execution; the worker remains the sole Telegram
delivery owner.
"""

from __future__ import annotations

import json
import os
import sys
import base64
import re
import urllib.parse
import urllib.request
import ssl
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hermes_evidence_contract import (
    claim_attribution,
    claim_feedback,
    continuation_guidance,
    currentness,
    evidence_state,
    source_quality,
    turn_requirements,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HERMES_ROOT = Path(os.getenv("NOVA_HERMES_ROOT", str(Path.home() / ".hermes/hermes-agent")))
SHADOW_FLAG = "NOVA_HERMES_NATIVE_SHADOW"
PRIMARY_FLAG = "NOVA_HERMES_NATIVE_PRIMARY"
SHADOW_STATE_DIR = REPO_ROOT / "data" / "runtime" / "nova_hermes_shadow_sessions"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def _require_runtime() -> None:
    shadow = os.getenv(SHADOW_FLAG, "false").lower() == "true"
    primary = os.getenv(PRIMARY_FLAG, "false").lower() == "true"
    if shadow == primary:
        raise RuntimeError("exactly one Hermes Nova runtime mode must be enabled")


def _load_hermes():
    """Load the installed Hermes checkout only when the shadow is invoked."""
    scripts_root = REPO_ROOT / "scripts"
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    if str(HERMES_ROOT) not in sys.path:
        sys.path.insert(0, str(HERMES_ROOT))
    from run_agent import AIAgent  # type: ignore
    return AIAgent


def _load_approved_provider_env() -> None:
    """Reuse the existing Nova runtime.env without printing or persisting it."""
    env_path = Path(os.getenv("NOVA_RUNTIME_ENV", str(Path.home() / ".config/nexus/runtime.env")))
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("\"'")
        if key.strip() and value and key.strip() not in os.environ:
            os.environ[key.strip()] = value


def _nova_soul() -> str:
    from nexus_agent_platform.agents.nova import SOUL
    return SOUL


def _state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "default")[:120]
    return SHADOW_STATE_DIR / f"{safe}.json"


def _load_shadow_state(session_id: str) -> Dict[str, Any]:
    path = _state_path(session_id)
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_shadow_state(session_id: str, state: Dict[str, Any]) -> None:
    SHADOW_STATE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(session_id).write_text(json.dumps(state, sort_keys=True) + "\n")


def _shadow_resource_guidance() -> str:
    """Positive, model-facing evidence guidance for the native tools.

    Search is intentionally discovery-only.  The model decides whether the
    returned evidence is sufficient; this text gives it the distinction it
    needs without adding a pre-model router or phrase rule.
    """
    return (
        "\n\n[SHADOW RESOURCE GUIDANCE]\n"
        "You own the question and choose resources after understanding it. "
        "If Ray explicitly asks you to use named resources, honor that request "
        "by calling each applicable resource and synthesize their results in "
        "the same reasoning turn; do not substitute Alpha or Nexus for another "
        "named resource. "
        "public_web_search_shadow discovers candidate sources; its snippets "
        "are discovery evidence, not verification. When the answer depends on "
        "terms, pricing, eligibility, features, current company actions, or "
        "other details, inspect the candidates and call "
        "public_web_retrieval_shadow for the relevant source pages before "
        "concluding. For a simple fact, do not use a resource unnecessarily. "
        "For a self-contained conversational hypothetical, use the supplied "
        "context first and research only if missing evidence would materially "
        "change the answer; do not delegate a self-contained hypothetical just "
        "because it concerns business. When Ray supplies named alternatives for "
        "comparison, preserve those alternatives as the conversational objects "
        "and reason over them first; do not delegate merely to compare them "
        "unless Ray asks for independent research or current evidence is needed. "
        "A supplied candidate comparison must produce a concrete provisional "
        "choice before any optional challenge delegation. "
        "After retrieval, distinguish source facts from your interpretation, "
        "and make a concrete recommendation when Ray asks for one. For normal "
        "business prioritization without an explicitly named external subject or "
        "resource, reason first; urgency words such as right now do not by "
        "themselves require web research. For a named volatile subject such as a "
        "company, product, or market and a question about what it is doing right "
        "now, use public web search and retrieval when needed to support the "
        "current factual portion. "
        "conversation, answer first, keep paragraphs compact, prefer short "
        "bullets, and avoid schema headings or wide tables; preserve formal "
        "structure when Ray explicitly asks for a report or audit. If an "
        "optional resource such as Alpha is used, it supplements required "
        "resources and must not replace their evidence in the final synthesis.\n"
    )


def _json_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _tool_execution_state(tool_rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Build compact authoritative execution state for final synthesis."""
    counts: Dict[str, int] = {}
    statuses: Dict[str, list[str]] = {}
    currentness: Dict[str, list[str]] = {}
    for row in tool_rows:
        name = str(row.get("name") or row.get("tool_name") or "unknown")
        counts[name] = counts.get(name, 0) + 1
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("status"):
            statuses.setdefault(name, []).append(str(payload["status"]))
        if payload.get("currentness"):
            currentness.setdefault(name, []).append(str(payload["currentness"]))
    return {
        "search_executed": "public_web_search_shadow" in counts,
        "retrieval_executed": "public_web_retrieval_shadow" in counts,
        "nexus_executed": "nexus_read_shadow" in counts,
        "alpha_executed": "alpha_challenge_shadow" in counts,
        "tool_call_counts": counts,
        "tool_statuses": statuses,
        "tool_currentness": currentness,
        "retrieved_page_count": counts.get("public_web_retrieval_shadow", 0),
        "retrieved_page_statuses": statuses.get("public_web_retrieval_shadow", []),
        "retrieval_status": "COMPLETED" if "public_web_retrieval_shadow" in counts else "NOT_EXECUTED",
    }


def _final_presentation_prompt(prompt: str, draft: str, tool_state: Dict[str, Any], claim_state: Dict[str, Any]) -> str:
    currentness_values = [
        value
        for values in (tool_state.get("tool_currentness") or {}).values()
        for value in values
    ]
    currentness_rule = (
        "At least one retrieved source is marked CURRENT; keep current factual claims bounded to that evidence."
        if "CURRENT" in {str(value).upper() for value in currentness_values}
        else "No retrieved source is marked CURRENT; do not state current trends, growth, growing demand, market access, market potential, surging markets, or verified recent facts as established facts. Recast them as a qualified hypothesis or say the evidence is not current enough."
    )
    alpha_rule = (
        "Alpha was executed. Open by stating plainly whether you still agree with the prior recommendation. "
        "Then explain only the one or two findings that changed, confirmed, or failed to strengthen your view. "
        "Do not reproduce Alpha's objective, status, key findings, risks, recommendations, or next steps as sections; "
        "do not substitute a generic monetization plan for the decision about the prior recommendation. "
        "Do not say Alpha confirmed or validated a recommendation unless its result explicitly supports that; "
        "unverified or empty findings must be described as failing to strengthen the case."
        if tool_state.get("alpha_executed")
        else ""
    )
    return (
        "[FINAL NOVA PRESENTATION — USER-FACING PROSE ONLY]\n"
        "Nova owns the final answer. Tools provide evidence, Alpha provides "
        "research, Nexus provides state, and web provides outside information; "
        "none of them owns the response. Rewrite the draft as your own answer to "
        "the original objective. Do not quote, dump, or imitate a tool/Alpha "
        "report. Answer first and give a choice or view early when one is actually "
        "requested. Explain only the reasons that matter, state meaningful "
        "uncertainty, and stop naturally; do not end with a question or offer unless "
        "the user cannot act on the answer without clarification. Use two to five compact paragraphs or one "
        "opening paragraph plus at most four short bullets. Do not use VERIFIED, "
        "BLOCKERS, RECOMMENDATION, NEXT ACTION, OBJECTIVE, STATUS, KEY FINDINGS, "
        "BUSINESS OPPORTUNITY ANALYSIS, EVIDENCE OVERVIEW, or ALPHA RESEARCH "
        "FINDINGS as default headings. If the user explicitly requested a formal "
        "report, audit, status, certification, or detailed evidence review, "
        "structured headings remain allowed. Otherwise keep it mobile-friendly.\n"
        "The execution state below is authoritative and outranks planning text or "
        "prior context. If retrieval is COMPLETED, never say URLs/pages still "
        "need retrieval. If retrieval is NOT_EXECUTED, do not imply a page was "
        "reviewed or claim that you are about to run a command/tool. If no tool "
        "ran, answer self-contained questions from your judgment and available "
        "conversation context; do not promise pending execution. If evidence is weak or unknown, say so naturally. When no current or external evidence was gathered, present business, market, and revenue claims as general reasoning or clearly qualified judgment, never as fresh verification. Do not "
        "turn a prioritization question into a catalog of projects: make one "
        "clear priority, explain why it comes first, and mention other options "
        "only as brief context.\n"
        "introduce current/latest/trend claims without current evidence; recast "
        "them as judgment or qualify them. If no retrieved source is marked "
        "CURRENT, do not use market-demand, growth, market-access, or market-potential language as fact. When Alpha is executed, explain what "
        "its findings change in your own recommendation; do not present Alpha's "
        "objective/status/findings/recommendations as the answer. Preserve the "
        "original objective and concrete recommendation. Output only the final "
        "answer. In normal conversation, do not use a heading for each internal "
        "field, do not append a generic research offer after the answer, and do "
        "not turn a simple choice into a numbered action plan. At most, include "
        "one concrete next move when it materially helps.\n\n"
        "CLOSING RULE: For ordinary conversation, stop after answering. Do not "
        "append next step, moving forward, would you like me to, I recommend "
        "conducting, or we should now unless the user explicitly asks for a next "
        "step or cannot act without one.\n"
        "ATTRIBUTION RULE: Treat a numeric goal, estimate, or business target as "
        "a target or your judgment unless a source directly supports that exact "
        "claim. Alpha with zero supported findings cannot establish market "
        "saturation, dominant competitors, or any other factual finding; those "
        "may only be framed as your hypothesis or risk. Never say research found "
        "something absent from supported Alpha findings.\n\n"
        f"CURRENTNESS RULE:\n{currentness_rule}\n\n"
        f"ALPHA DECISION-OWNERSHIP RULE:\n{alpha_rule or 'Alpha was not executed; answer from the available evidence and your own judgment.'}\n\n"
        f"ORIGINAL OBJECTIVE:\n{prompt[:3000]}\n\n"
        f"AUTHORITATIVE CURRENT-TURN TOOL STATE:\n{json.dumps(tool_state, sort_keys=True, default=str)}\n\n"
        f"EVIDENCE AND CLAIM STATE:\n{json.dumps(claim_state, sort_keys=True, default=str)}\n\n"
        f"DRAFT TO REWRITE:\n{draft[:12000]}"
    )


def _current_shadow_context(state: Dict[str, Any]) -> str:
    """Return a compact, volatile index for follow-up referent resolution."""
    resources = state.get("resource_results") or []
    if not isinstance(resources, list):
        resources = []
    recent = resources[-6:]
    lines = [
        "\n\n[CURRENT SHADOW CONTEXT — volatile, not historical memory]",
        "Use this index for follow-ups. The latest result linked to the current turn outranks older results.",
    ]
    if state.get("last_recommendation"):
        lines.append("CURRENT_RECOMMENDATION=" + str(state["last_recommendation"])[:1800])
    if state.get("active_request"):
        lines.append("ACTIVE_REQUEST=" + str(state["active_request"])[:500])
    turns = state.get("recent_turns") or []
    for turn in turns[-6:]:
        if isinstance(turn, dict):
            lines.append("CONVERSATION_TURN=" + json.dumps({
                "user": str(turn.get("user", ""))[:700],
                "assistant": str(turn.get("assistant", ""))[:1400],
            }, ensure_ascii=False))
    for row in recent:
        if isinstance(row, dict):
            lines.append(
                "RESOURCE_RESULT=" + json.dumps({
                    "capability": row.get("capability"),
                    "request_id": row.get("request_id"),
                    "result_id": row.get("result_id"),
                    "completed_at": row.get("completed_at"),
                    "current_for_turn": row.get("current_for_turn", False),
                }, sort_keys=True)
            )
    if len(lines) == 2:
        lines.append("No linked resource result exists yet; do not imply that research happened.")
    return "\n".join(lines) + "\n"


def _search_free_chain(query: str, limit: int = 6) -> Dict[str, Any]:
    """Use existing free/private adapters, deliberately excluding Brave."""
    if str(REPO_ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from hermes.hermes_web_search import _search_bing_html, _search_duckduckgo_html, _search_searxng
    attempts = []
    for provider, fn in (("searxng", _search_searxng), ("duckduckgo_html", _search_duckduckgo_html), ("bing_html", _search_bing_html)):
        if provider == "searxng" and os.getenv("NOVA_SHADOW_FORCE_SEARXNG_FAILURE", "false").lower() == "true":
            result = {"status": "error", "results": [], "notes": ["forced bounded preflight failure"]}
        else:
            result = fn(query, limit)
        attempts.append({"provider": provider, "status": result.get("status"), "notes": result.get("notes", [])})
        if result.get("status") == "ok" and result.get("results"):
            result["attempted_providers"] = attempts
            result["cost_class"] = "free_private_no_new_spend"
            result["shadow_provider_chain"] = True
            result["evidence_role"] = "discovery_only"
            result["retrieval_recommended"] = bool(result.get("results"))
            result["retrieval_guidance"] = (
                "Search results identify candidates only. Retrieve one or more candidate URLs "
                "before relying on claims that require page detail or current verification."
                if result.get("results") else "No candidate URLs were returned."
            )
            return result
    return {"status": "all_free_providers_failed", "provider": "none", "query": query,
            "results": [], "attempted_providers": attempts,
            "cost_class": "free_private_no_new_spend", "evidence_role": "discovery_only",
            "retrieval_recommended": False,
            "retrieval_guidance": "No candidate URLs were returned; use another authorized source or explain the uncertainty."}


def _resolve_public_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    encoded = params.get("u", [""])[0]
    if encoded.startswith("a1"):
        try:
            return base64.b64decode(encoded[2:] + "===").decode("utf-8")
        except Exception:
            pass
    return url


def _retrieve_public_page(url: str, max_chars: int = 50000) -> Dict[str, Any]:
    target = _resolve_public_url(url)
    request = urllib.request.Request(target, headers={"User-Agent": "NexusHermes-NovaShadow/1.0", "Accept": "text/html,text/plain"})
    try:
        with urllib.request.urlopen(request, timeout=20, context=SSL_CTX) as response:
            raw = response.read(max_chars * 3)
            content_type = response.headers.get("Content-Type", "")
            final_url = response.geturl()
        text = raw.decode("utf-8", errors="replace")
        text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()[:max_chars]
        retrieved_at = datetime.now(timezone.utc).isoformat()
        date_match = re.search(r"\b(20\d{2})[-/]([01]\d)[-/]([0-3]\d)\b|\b([A-Z][a-z]+ \d{1,2}, 20\d{2})\b", text)
        source_date = None
        if date_match:
            raw_date = date_match.group(0)
            try:
                source_date = datetime.strptime(raw_date, "%B %d, %Y").replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                try:
                    source_date = datetime.strptime(raw_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    source_date = None
        if not text:
            return {"status": "no_content", "url": final_url, "requested_url": url,
                    "content_type": content_type, "content": "", "content_length": 0,
                    "source_type": "LIVE_PUBLIC_PAGE", "error": "empty_page"}
        return {"status": "ok", "url": final_url, "requested_url": url,
                "content_type": content_type, "content": text,
                "content_length": len(text), "source_type": "LIVE_PUBLIC_PAGE",
                "retrieved_at": retrieved_at, "source_date": source_date,
                "source_quality": source_quality(final_url),
                "currentness": currentness(source_date, retrieved_at, required=True)}
    except Exception as exc:
        return {"status": "error", "url": target, "requested_url": url,
                "error": type(exc).__name__, "content": "", "content_length": 0,
                "source_type": "LIVE_PUBLIC_PAGE"}


def _register_bounded_nexus_tools() -> None:
    """Register read/delegation adapters in the Hermes process only.

    These names are intentionally shadow-specific and expose no mutation or
    arbitrary SQL.  Existing Nexus capability boundaries remain authoritative.
    """
    scripts_root = REPO_ROOT / "scripts"
    # Hermes' registry is a top-level package.  Ensure its checkout is on the
    # import path before registering tools; the shadow runner may be invoked
    # directly from the repository rather than through the Hermes CLI.
    if str(HERMES_ROOT) not in sys.path:
        sys.path.insert(0, str(HERMES_ROOT))
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    from tools.registry import registry  # type: ignore
    from nexus_agent_platform.capabilities.shared import execute_shared_capability

    nexus_schema = {
        "name": "nexus_read_shadow",
        "description": "Read an authorized Nexus capability/status resource when the question asks about Nexus or how Nexus could help; return the real capability/status evidence. This is a read only resource and never mutates Nexus.",
        "parameters": {"type": "object", "properties": {
            "resource": {"type": "string", "enum": ["NEXUS_CAPABILITY_MAP", "NEXUS_LIVE_TRUTH"]}
        }, "required": ["resource"]},
    }
    alpha_schema = {
        "name": "alpha_challenge_shadow",
        "description": "Request a bounded Alpha challenge/research review when Ray explicitly asks for independent research or when missing evidence materially prevents the answer; for a self-contained comparison with a supplied candidate set, reason and choose first instead of delegating. No operational execution.",
        "parameters": {"type": "object", "properties": {
            "objective": {"type": "string", "minLength": 10}
        }, "required": ["objective"]},
    }
    web_search_schema = {
        "name": "public_web_search_shadow",
        "description": "Discover current public sources using approved free/private providers; results are discovery evidence only. After inspecting candidates, retrieve relevant source pages when claims require terms, pricing, eligibility, features, or current company details. Brave is excluded.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "minLength": 3}, "limit": {"type": "integer", "minimum": 1, "maximum": 6}}, "required": ["query"]},
    }
    web_retrieval_schema = {
        "name": "public_web_retrieval_shadow",
        "description": "Read a candidate public result URL through bounded HTTP retrieval. Use this after search when snippets are insufficient for verification or detailed/current claims; return source content and provenance.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string", "format": "uri"}}, "required": ["url"]},
    }

    def nexus_read(args: Dict[str, Any], **_: Any) -> str:
        result = execute_shared_capability(
            "hermes_nova", "get_capability_registry" if args["resource"] == "NEXUS_CAPABILITY_MAP" else "get_runtime_capabilities", {},
            conversation_id="shadow", trace_id="hermes_native_shadow",
        )
        return json.dumps(result, sort_keys=True, default=str)

    def alpha_challenge(args: Dict[str, Any], **kwargs: Any) -> str:
        if os.getenv("NOVA_SHADOW_FORCE_ALPHA_FAILURE", "false").lower() == "true":
            request_id = "alpha_req_" + uuid.uuid4().hex
            return json.dumps({
                "status": "FAILED",
                "error": "forced bounded preflight failure",
                "correlation": {
                    "alpha_request_id": request_id,
                    "alpha_job_id": "alpha-job-failed-" + request_id[-12:],
                },
            })
        result = execute_shared_capability(
            "hermes_nova", "submit_alpha_request", {"objective": args["objective"], "execute": True, "requested_by": "hermes_nova"},
            conversation_id="shadow", trace_id="hermes_native_shadow",
        )
        # Preserve the canonical Alpha identifiers inside the native tool
        # result.  Hermes may provide a provider tool-call ID; it is metadata,
        # not a replacement for the governed Alpha IDs.
        if isinstance(result, dict):
            data = result.get("data") if isinstance(result.get("data"), dict) else result
            job = data.get("job") if isinstance(data.get("job"), dict) else {}
            receipt = data.get("receipt") if isinstance(data.get("receipt"), dict) else {}
            result.setdefault("correlation", {})
            result["correlation"].update({
                "hermes_tool_call_id": kwargs.get("tool_call_id") or kwargs.get("call_id"),
                "alpha_request_id": data.get("request_id") or data.get("alpha_request_id") or job.get("request_id"),
                "alpha_job_id": data.get("job_id") or data.get("research_job_id") or job.get("research_job_id"),
                "alpha_result_id": data.get("result_id") or receipt.get("result_id") or receipt.get("receipt_id"),
                "alpha_artifact_id": data.get("artifact_id") or receipt.get("artifact_id") or receipt.get("research_pack_ref"),
            })
        return json.dumps(result, sort_keys=True, default=str)

    # Per-turn memoization prevents an equivalent model retry from repeating a
    # network request. The returned payload remains the original tool result,
    # so provenance is not weakened and only duplicate work is removed.
    search_cache: Dict[tuple[str, int], str] = {}
    retrieval_cache: Dict[str, str] = {}
    timing = _register_bounded_nexus_tools.timing = getattr(_register_bounded_nexus_tools, "timing", {})
    timing.clear()

    def public_web_search(args: Dict[str, Any], **_: Any) -> str:
        query = re.sub(r"\s+", " ", str(args["query"]).strip()).casefold()
        limit = int(args.get("limit", 6))
        key = (query, limit)
        if key in search_cache:
            timing["duplicate_search_calls"] = timing.get("duplicate_search_calls", 0) + 1
            return search_cache[key]
        started = time.monotonic()
        value = json.dumps(_search_free_chain(query, limit), sort_keys=True, default=str)
        timing["search_ms"] = timing.get("search_ms", 0.0) + (time.monotonic() - started) * 1000
        timing["search_calls"] = timing.get("search_calls", 0) + 1
        search_cache[key] = value
        return value

    def public_web_retrieval(args: Dict[str, Any], **_: Any) -> str:
        url = _resolve_public_url(str(args["url"]).strip())
        if url in retrieval_cache:
            timing["duplicate_retrieval_calls"] = timing.get("duplicate_retrieval_calls", 0) + 1
            return retrieval_cache[url]
        started = time.monotonic()
        value = json.dumps(_retrieve_public_page(url), sort_keys=True, default=str)
        timing["retrieval_ms"] = timing.get("retrieval_ms", 0.0) + (time.monotonic() - started) * 1000
        timing["retrieval_calls"] = timing.get("retrieval_calls", 0) + 1
        retrieval_cache[url] = value
        return value

    registry.register("nexus_read_shadow", "nexus", nexus_schema, nexus_read,
                      description=nexus_schema["description"], max_result_size_chars=50000)
    registry.register("alpha_challenge_shadow", "research", alpha_schema, alpha_challenge,
                      description=alpha_schema["description"], max_result_size_chars=50000)
    registry.register("public_web_search_shadow", "shadow_web", web_search_schema, public_web_search,
                      description=web_search_schema["description"], max_result_size_chars=50000)
    registry.register("public_web_retrieval_shadow", "shadow_web", web_retrieval_schema, public_web_retrieval,
                      description=web_retrieval_schema["description"], max_result_size_chars=50000)


def run_shadow(
    prompt: str,
    *,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    enabled_toolsets: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Run one bounded, non-primary Hermes-native Nova turn."""
    started_at = time.monotonic()
    phase_timings: Dict[str, Any] = {}
    _require_runtime()
    phase_timings["runtime_validation_ms"] = round((time.monotonic() - started_at) * 1000, 1)
    _load_approved_provider_env()
    hermes_load_started = time.monotonic()
    AIAgent = _load_hermes()
    phase_timings["hermes_init_ms"] = round((time.monotonic() - hermes_load_started) * 1000, 1)
    _register_bounded_nexus_tools()
    chosen_model = model or os.getenv("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")
    toolsets = enabled_toolsets if enabled_toolsets is not None else ["shadow_web", "nexus", "research", "delegation"]
    if turn_contract := turn_requirements(prompt):
        if turn_contract.get("reuse_only"):
            # A result-retrieval follow-up uses the linked result in context;
            # Alpha remains available for an explicit new challenge.
            toolsets = [name for name in toolsets if name != "research"]
        if turn_contract.get("reasoning_first"):
            # A self-contained object comparison is completed by the model
            # before optional resources are exposed. This is a generic
            # reason-first contract, not a candidate-specific router; callers
            # can still request current evidence explicitly.
            toolsets = []
    active_session = session_id or "nova-shadow-" + uuid.uuid4().hex[:12]
    shadow_state = _load_shadow_state(active_session)
    prior_records = [dict(row) for row in (shadow_state.get("resource_results") or []) if isinstance(row, dict)]
    turn_id = "shadow-turn-" + uuid.uuid4().hex[:12]
    shadow_state["active_request"] = prompt[:1000]
    for row in shadow_state.get("resource_results", []) or []:
        if isinstance(row, dict):
            row["current_for_turn"] = False
    correlation_context = (
        "\n\n[SHADOW CORRELATION — internal]\n"
        f"turn_id={turn_id}; session_id={active_session}. Volatile tool results must be linked to this turn. "
        "When a user refers to a recommendation or Research result, use the current conversational referent and its linked request/result, never an unrelated older artifact. "
        "A tool result is evidence for this turn only when it is returned in this turn's native tool exchange."
        " For a follow-up asking what Research found, reuse the current linked Alpha result when one exists; do not rerun Alpha unless the user requests a new challenge."
    )
    turn_contract = turn_requirements(prompt)
    turn_contract_guidance = ""
    if turn_contract["required_resources"]:
        turn_contract_guidance = (
            "\n\n[CURRENT TURN RESOURCE CONTRACT]\n"
            "The current user request explicitly names resources that must be "
            "consulted for this task: " + ", ".join(turn_contract["required_resources"]) + ". "
            "Use native tools for those resources in this turn. Prior conversation "
            "is context, not a substitute for a required current read.\n"
        )
    if turn_contract.get("reasoning_first"):
        turn_contract_guidance += (
            "\n\n[REASONING-FIRST OBJECT PRESERVATION]\n"
            "This is a self-contained comparison. Preserve the supplied candidate "
            "objects and reason over them before any optional delegation. The "
            "candidate set is: " + ", ".join(turn_contract["candidate_set"]) + ". "
            "If an optional resource is later useful, its objective must discuss "
            "these same candidates and its result is additive evidence; it must "
            "not replace the candidate set or become the answer.\n"
        )
    current_context = _current_shadow_context(shadow_state)
    immutable_objective = (
        "\n\n[IMMUTABLE TURN OBJECTIVE]\n"
        "The original user objective for this turn is: " + turn_contract["turn_objective"] + "\n"
        "Tool calls may collect evidence, but they must not replace or change this objective. "
        "The final response must answer the original objective.\n"
    )
    conversation_history = []
    for turn in (shadow_state.get("recent_turns") or [])[-8:]:
        if not isinstance(turn, dict):
            continue
        if turn.get("user"):
            conversation_history.append({"role": "user", "content": str(turn["user"])[:2000]})
        if turn.get("assistant"):
            conversation_history.append({"role": "assistant", "content": str(turn["assistant"])[:5000]})
    native_conversation = not turn_contract["required_resources"]
    ephemeral_prompt = (
        "You are a conversational assistant. Answer the user's question directly and naturally using the conversation history. Treat opinions as opinions and do not invent current facts."
        if native_conversation
        else _nova_soul() + _shadow_resource_guidance() + current_context + immutable_objective + correlation_context
    )
    agent = AIAgent(
        model=chosen_model,
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        enabled_toolsets=toolsets,
        session_id=active_session,
        ephemeral_system_prompt=ephemeral_prompt,
        load_soul_identity=False,
        save_trajectories=False,
        quiet_mode=True,
        max_iterations=8,
        platform="nova-shadow",
    )
    # The worker is intentionally short-lived, so the stable session ID alone
    # is insufficient for referents unless the prior exchange is explicitly
    # reopened.  Pass the sidecar's bounded conversational history into the
    # native Hermes continuation path; structured tool provenance remains in
    # the separate resource index below.
    model_calls = []
    model_started = time.monotonic()
    result = agent.run_conversation(prompt + turn_contract_guidance, conversation_history=conversation_history or None, task_id=turn_id)
    model_calls.append(round((time.monotonic() - model_started) * 1000, 1))
    all_messages = list(result.get("messages", [])) if isinstance(result, dict) else []

    def _tool_messages(messages):
        rows = []
        for message in messages:
            if message.get("role") != "tool":
                continue
            rows.append({
                "name": message.get("name") or message.get("tool_name"),
                "payload": _json_object(message.get("content")),
            })
        return rows

    # If an explicit current-turn resource was omitted, let Hermes continue the
    # same session and request the missing native tools. This is an execution
    # contract, not a question router or a canned answer path.
    first_state = evidence_state(prompt, _tool_messages(all_messages), prior_records)
    first_state["page_payloads"] = [row["payload"] for row in _tool_messages(all_messages) if row.get("name") == "public_web_retrieval_shadow"]
    first_tool_rows = _tool_messages(all_messages)
    # Native conversation is already Hermes' user-facing answer. Evidence
    # validators and operator presentation are for resource-backed claims;
    # they must not suppress or rewrite an ordinary zero-tool turn.
    first_state["claim_validation"] = (
        claim_feedback(prompt, str(result.get("final_response", "")) if isinstance(result, dict) else "", first_state)
        if first_tool_rows else {"valid": True, "unsupported_claims": []}
    )
    draft_text = str(result.get("final_response", "")) if isinstance(result, dict) else ""
    synthesis_terms_missing = []
    if first_state.get("synthesis_required"):
        lower_draft = draft_text.lower()
        for label, patterns in {
            "actual_choice": ("recommend", "choose", "would test", "pick"),
            "cost_range": ("cost", "budget", "$"),
            "revenue_hypothesis": ("revenue", "earn", "income", "monetiz"),
            "biggest_risk": ("risk", "downside", "blocker"),
            "confidence": ("confidence", "uncertain", "moderate", "low confidence"),
            "what_would_change_my_mind": ("change my mind", "what would change", "reconsider"),
        }.items():
            if not any(term in lower_draft for term in patterns):
                synthesis_terms_missing.append(label)
    if first_state.get("missing_resources") or first_state.get("synthesis_required") or synthesis_terms_missing or (first_tool_rows and not first_state["claim_validation"].get("valid", True)):
        continuation = continuation_guidance(first_state)
        if first_state.get("synthesis_required"):
            continuation += (
                "\n[SYNTHESIS FEEDBACK]\n"
                "The current objective requires a combined answer. The required "
                "Nexus and public-web evidence must appear in the final reasoning; "
                "any Alpha result is supplementary. Do not call another tool in "
                "this continuation unless a required resource is still missing. "
                "State an actual choice, why it wins, the concrete Nexus advantage, "
                "the outside-market signal, the fastest validation test, an honest "
                "cost range, a revenue hypothesis, the biggest risk, confidence, "
                "and what evidence would change your mind. If a field cannot be "
                "supported, label it unknown or qualify it rather than inventing "
                "precision.\n"
            )
            if synthesis_terms_missing:
                continuation += "The draft is missing these synthesis fields: " + ", ".join(synthesis_terms_missing) + ". Fill them from the evidence and label unsupported fields as unknown; do not omit the decision.\n"
            continuation += "Evidence state for this turn (not a new objective): " + json.dumps({
                "required_resources": first_state.get("required_resources"),
                "executed_resources": first_state.get("executed_resources"),
                "missing_resources": first_state.get("missing_resources"),
                "source_quality": first_state.get("source_quality"),
                "currentness": first_state.get("currentness"),
                "supported_claims": first_state.get("supported_claims", [])[-8:],
                "partial_claims": first_state.get("partial_claims", [])[-8:],
            }, default=str) + "\n"
        if first_state["claim_validation"].get("unsupported_claims"):
            continuation += (
                "\n[CLAIM SUPPORT FEEDBACK]\n"
                "The draft contains claims without direct support from the returned "
                "evidence: " + ", ".join(first_state["claim_validation"]["unsupported_claims"]) + ". "
                "Revise those claims to distinguish what the pages establish from "
                "what remains unknown; do not invent verification.\n"
            )
        follow_up_started = time.monotonic()
        follow_up = agent.run_conversation(
            "For the original user request: " + prompt[:2000] + "\n" + continuation,
            task_id=turn_id + "-evidence",
        )
        model_calls.append(round((time.monotonic() - follow_up_started) * 1000, 1))
        if isinstance(follow_up, dict):
            all_messages.extend(follow_up.get("messages", []))
            result = follow_up
            # Validate the revised draft once more. If it still uses strong
            # currentness language over undated/partial evidence, give the
            # model one bounded correction opportunity rather than accepting
            # the claim or turning the resource gap into a refusal.
            revised_rows = _tool_messages(all_messages)
            revised_state = evidence_state(prompt, revised_rows, prior_records)
            revised_state["page_payloads"] = [row["payload"] for row in revised_rows if row.get("name") == "public_web_retrieval_shadow"]
            revised_claim = claim_feedback(prompt, str(result.get("final_response", "")), revised_state)
            if not revised_claim.get("valid", True):
                correction = (
                    "\n[FINAL PROVENANCE CORRECTION]\n"
                    "The revised answer still makes an unsupported evidence claim: "
                    + ", ".join(revised_claim.get("unsupported_claims", []))
                    + ". Keep the useful recommendation, but explicitly say that "
                    "the outside evidence is partial, undated, or otherwise not "
                    "strongly current, lower confidence accordingly, and separate "
                    "verified facts from your working hypothesis. Do not say current, "
                    "verified, or confirmed unless the returned evidence supports it.\n"
                )
                correction_started = time.monotonic()
                final_correction = agent.run_conversation(
                    "For the original user request: " + prompt[:2000] + correction,
                    task_id=turn_id + "-provenance",
                )
                model_calls.append(round((time.monotonic() - correction_started) * 1000, 1))
                if isinstance(final_correction, dict):
                    all_messages.extend(final_correction.get("messages", []))
                    result = final_correction
            if first_state.get("synthesis_required"):
                final_text = str(result.get("final_response", ""))
                final_lower = final_text.lower()
                required_synthesis_terms = {
                    "actual_choice": ("recommend", "choose", "would test", "pick"),
                    "cost_range": ("cost", "budget", "$"),
                    "revenue_hypothesis": ("revenue", "earn", "income", "monetiz"),
                    "biggest_risk": ("risk", "downside", "blocker"),
                    "confidence": ("confidence", "uncertain", "moderate", "low confidence"),
                    "what_would_change_my_mind": ("change my mind", "what would change", "reconsider"),
                }
                final_missing = [label for label, terms in required_synthesis_terms.items() if not any(term in final_lower for term in terms)]
                if final_missing:
                    synthesis_started = time.monotonic()
                    final_synthesis = agent.run_conversation(
                        "For the original user request: " + prompt[:2000] +
                        "\n[SYNTHESIS COMPLETION]\nThe final draft still omits: " + ", ".join(final_missing) +
                        ". Provide one clear working choice and fill every requested field using the returned Nexus and outside evidence. Mark weak or missing outside evidence explicitly and reduce confidence; do not claim verification that did not occur.",
                        task_id=turn_id + "-synthesis",
                    )
                    model_calls.append(round((time.monotonic() - synthesis_started) * 1000, 1))
                    if isinstance(final_synthesis, dict):
                        all_messages.extend(final_synthesis.get("messages", []))
                        result = final_synthesis

    # Hermes' native draft is an internal reasoning artifact. Give Nova one
    # final, tool-disabled model pass so the response owner is explicit and
    # structured evidence cannot become Telegram prose by inheritance. The
    # model still decides whether the user asked for a formal report; this is
    # presentation guidance, not phrase-specific routing or a canned answer.
    if isinstance(result, dict):
        final_rows = _tool_messages(all_messages)
        final_state = evidence_state(prompt, final_rows, prior_records)
        final_state["page_payloads"] = [row["payload"] for row in final_rows if row.get("name") == "public_web_retrieval_shadow"]
        draft = str(result.get("final_response", ""))
        final_state["claim_validation"] = claim_feedback(prompt, draft, final_state) if final_rows else {"valid": True, "unsupported_claims": []}
        if not final_rows:
            # Preserve the native Hermes response verbatim for ordinary
            # conversation. No report formatter, prose validator, or repair
            # model is allowed to turn a valid answer into a failed turn.
            result["turn_contract"] = turn_contract
            result["evidence_state"] = final_state
            result["claim_validation"] = final_state["claim_validation"]
            result["messages"] = all_messages
            result["native_conversation"] = True
            result["claim_attribution"] = claim_attribution(prompt, draft, final_state)
            return result
        presentation_state = {
            "required_resources": final_state.get("required_resources", []),
            "executed_resources": final_state.get("executed_resources", []),
            "missing_resources": final_state.get("missing_resources", []),
            "currentness": final_state.get("currentness"),
            "source_quality": final_state.get("source_quality", []),
            "supported_claims": final_state.get("supported_claims", [])[-8:],
            "partial_claims": final_state.get("partial_claims", [])[-8:],
            "claim_validation": final_state["claim_validation"],
        }
        presentation_agent = AIAgent(
            model=chosen_model,
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            enabled_toolsets=[],
            session_id=active_session,
            ephemeral_system_prompt=_nova_soul(),
            load_soul_identity=False,
            save_trajectories=False,
            quiet_mode=True,
            max_iterations=1,
            platform="nova-shadow-final-presentation",
        )
        presentation_started = time.monotonic()
        presented = presentation_agent.run_conversation(
            _final_presentation_prompt(prompt, draft, _tool_execution_state(final_rows), presentation_state),
            conversation_history=conversation_history or None,
            task_id=turn_id + "-presentation",
        )
        model_calls.append(round((time.monotonic() - presentation_started) * 1000, 1))
        if isinstance(presented, dict) and presented.get("final_response"):
            all_messages.extend(presented.get("messages", []))
            result["final_response"] = presented["final_response"]
            final_claim = claim_feedback(prompt, str(result["final_response"]), final_state)
            # A final no-tool repair keeps user-facing evidence language honest
            # without reopening resource selection or changing the answer.
            if not final_claim.get("valid", True):
                correction_started = time.monotonic()
                corrected = presentation_agent.run_conversation(
                    _final_presentation_prompt(
                        prompt,
                        str(result["final_response"]),
                        _tool_execution_state(final_rows),
                        {**presentation_state, "claim_validation": {"valid": False, "unsupported_claims": final_claim.get("unsupported_claims", [])}},
                    ) + "\nCorrect every listed claim-state issue before answering.",
                    conversation_history=conversation_history or None,
                    task_id=turn_id + "-presentation-correction",
                )
                model_calls.append(round((time.monotonic() - correction_started) * 1000, 1))
                if isinstance(corrected, dict) and corrected.get("final_response"):
                    all_messages.extend(corrected.get("messages", []))
                    result["final_response"] = corrected["final_response"]
                    corrected_claim = claim_feedback(prompt, str(result["final_response"]), final_state)
                    # Give the presentation model one bounded opportunity to
                    # repair its own repair. This remains tool-disabled and
                    # cannot alter resource selection or execution state.
                    if not corrected_claim.get("valid", True):
                        second_correction_started = time.monotonic()
                        strict_claim_repair = (
                            "\nSTRICT CLAIM REPAIR: The answer is still invalid for "
                            + ", ".join(corrected_claim.get("unsupported_claims", []))
                            + ". If currentness is not proven, remove factual growth, "
                            "demand, market-access, market-potential, or recent-trend "
                            "language and describe the evidence as limited; any choice "
                            "must be clearly your judgment. If retrieval state is at issue, "
                            "describe the actual completed or failed state. If Alpha ran, "
                            "state whether you agree with the prior recommendation and say "
                            "whether Alpha strengthened it; do not list Alpha report fields. "
                            "Use no schema headings and do not offer generic next steps. Return only the answer."
                        )
                        corrected_again = presentation_agent.run_conversation(
                            _final_presentation_prompt(
                                prompt,
                                str(result["final_response"]),
                                _tool_execution_state(final_rows),
                                {**presentation_state, "claim_validation": corrected_claim},
                            ) + strict_claim_repair,
                            conversation_history=conversation_history or None,
                            task_id=turn_id + "-presentation-correction-final",
                        )
                        model_calls.append(round((time.monotonic() - second_correction_started) * 1000, 1))
                        if isinstance(corrected_again, dict) and corrected_again.get("final_response"):
                            all_messages.extend(corrected_again.get("messages", []))
                            result["final_response"] = corrected_again["final_response"]
    shadow_state.update({"last_turn_id": turn_id, "last_prompt": prompt[:500], "updated_at": datetime.now(timezone.utc).isoformat()})
    if isinstance(result, dict):
        messages = all_messages
        tools_seen = [m.get("name") for m in messages if m.get("role") == "tool"]
        shadow_state["last_tools"] = tools_seen
        records = shadow_state.setdefault("resource_results", [])
        for message in messages:
            if message.get("role") != "tool":
                continue
            payload = _json_object(message.get("content"))
            if not payload:
                continue
            capability = message.get("name") or message.get("tool_name") or "unknown"
            data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
            correlation = payload.get("correlation") if isinstance(payload.get("correlation"), dict) else {}
            job = data.get("job") if isinstance(data.get("job"), dict) else {}
            receipt = data.get("receipt") if isinstance(data.get("receipt"), dict) else {}
            request_id = (correlation.get("alpha_request_id") or data.get("request_id") or
                          data.get("alpha_request_id") or job.get("request_id"))
            result_id = (correlation.get("alpha_result_id") or data.get("result_id") or
                         receipt.get("result_id") or receipt.get("receipt_id"))
            job_id = (correlation.get("alpha_job_id") or data.get("job_id") or
                      data.get("research_job_id") or job.get("research_job_id"))
            artifact_id = (correlation.get("alpha_artifact_id") or data.get("artifact_id") or
                           receipt.get("artifact_id") or receipt.get("research_pack_ref"))
            if capability == "alpha_challenge_shadow":
                request_id = request_id or payload.get("job_id")
                result_id = result_id or payload.get("artifact_id") or payload.get("receipt_id")
            record = {
                "capability": capability,
                "resource": {"nexus_read_shadow": "NEXUS", "public_web_search_shadow": "PUBLIC_WEB", "public_web_retrieval_shadow": "PUBLIC_WEB_RETRIEVAL", "alpha_challenge_shadow": "ALPHA"}.get(capability, capability),
                "source_turn_id": turn_id,
                "request_id": request_id,
                "result_id": result_id,
                "job_id": job_id,
                "artifact_id": artifact_id,
                "objective": data.get("objective") or job.get("objective"),
                "completed_at": payload.get("completed_at") or payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
                "retrieved_at": payload.get("retrieved_at") or payload.get("checked_at") or payload.get("completed_at") or datetime.now(timezone.utc).isoformat(),
                "currentness": payload.get("currentness") or payload.get("freshness") or "UNKNOWN",
                "relevance": "current_turn_execution",
                "valid_for_current_turn": True,
                "current_for_turn": True,
                "status": payload.get("status"),
            }
            records.append(record)
            if capability == "alpha_challenge_shadow":
                shadow_state["last_alpha_result_id"] = result_id
                shadow_state["last_alpha_request_id"] = request_id
        # Keep the sidecar as an index, not a second evidence store.
        shadow_state["resource_results"] = records[-20:]
        for message in reversed(messages):
            if message.get("role") == "assistant" and message.get("content"):
                assistant_text = str(message["content"])[-3000:]
                shadow_state["last_response"] = assistant_text
                if any(word in assistant_text.lower() for word in ("recommend", "i would choose", "best option")):
                    shadow_state["last_recommendation"] = assistant_text
                break
        turns = shadow_state.setdefault("recent_turns", [])
        turns.append({"user": prompt[:1000], "assistant": shadow_state.get("last_response", "")})
        shadow_state["recent_turns"] = turns[-8:]
        tool_rows = _tool_messages(messages)
        state_contract = evidence_state(prompt, tool_rows, prior_records)
        if not tool_rows and prior_records and not turn_contract.get("required_resources"):
            # A follow-up may reuse evidence, but only through its structured
            # receipt linkage. Conversation text alone is not provenance.
            for row in prior_records[-8:]:
                row["valid_for_current_turn"] = True
                row["relevance"] = "prior_turn_followup"
            state_contract["reused_evidence"] = [
                {k: row.get(k) for k in ("source_turn_id", "resource", "capability", "request_id", "result_id", "artifact_id", "retrieved_at", "currentness", "relevance", "valid_for_current_turn")}
                for row in prior_records[-8:]
            ]
        state_contract["page_payloads"] = [row["payload"] for row in tool_rows if row.get("name") == "public_web_retrieval_shadow"]
        draft = shadow_state.get("last_response", "")
        state_contract["claim_validation"] = claim_feedback(prompt, draft, state_contract)
        if not state_contract["claim_validation"].get("valid", True):
            # Fail closed after the bounded repair path. An invalid draft must
            # never be returned to the Telegram worker as if it were clean.
            result["final_response"] = ""
            result["claim_validation"] = state_contract["claim_validation"]
        shadow_state["turn_contract"] = turn_contract
        shadow_state["evidence_state"] = state_contract
    _save_shadow_state(active_session, shadow_state)
    if isinstance(result, dict):
        result["turn_contract"] = turn_contract
        result["evidence_state"] = state_contract
        result["claim_validation"] = state_contract["claim_validation"]
        result["claim_attribution"] = claim_attribution(prompt, str(result.get("final_response", "")), state_contract)
        # Return the complete turn transcript so the canonical worker receipt
        # records tools from the initial pass and any evidence continuation.
        result["messages"] = all_messages
        timing = getattr(_register_bounded_nexus_tools, "timing", {})
        assistant_messages = [m for m in all_messages if m.get("role") == "assistant" and m.get("content")]
        result["latency_telemetry"] = {
            "model_call_count": len(model_calls),
            "model_call_ms": model_calls,
            "model_total_ms": round(sum(model_calls), 1),
            "continuation_count": max(0, len(model_calls) - 1),
            "tool_call_count": len([m for m in all_messages if m.get("role") == "tool"]),
            "assistant_message_count": len(assistant_messages),
            "search_ms": round(float(timing.get("search_ms", 0.0)), 1),
            "retrieval_ms": round(float(timing.get("retrieval_ms", 0.0)), 1),
            "search_calls": timing.get("search_calls", 0),
            "retrieval_calls": timing.get("retrieval_calls", 0),
            "duplicate_search_calls": timing.get("duplicate_search_calls", 0),
            "duplicate_retrieval_calls": timing.get("duplicate_retrieval_calls", 0),
            "total_runner_ms": round((time.monotonic() - started_at) * 1000, 1),
            **phase_timings,
        }
        return result
    return {"response": result, "model": chosen_model, "shadow": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run isolated Hermes-native Nova shadow")
    parser.add_argument("prompt")
    parser.add_argument("--session-id")
    args = parser.parse_args()
    print(json.dumps(run_shadow(args.prompt, session_id=args.session_id), default=str))
