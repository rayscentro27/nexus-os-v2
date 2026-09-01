"""Isolated Hermes-native Nova runner.

The canonical Telegram worker invokes this through the Hermes-supported
interpreter. The same runner supports silent certification shadow execution
and user-visible primary execution; the worker remains the sole Telegram
delivery owner.
"""

from __future__ import annotations

import json
import hashlib
import os
import sys
import base64
import re
import urllib.parse
import urllib.request
import ssl
import uuid
import time
import contextvars
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
NOVA_HERMES_HOME = Path(os.getenv("NOVA_HERMES_HOME", str(REPO_ROOT / "config" / "hermes" / "nova-profile")))
SHADOW_FLAG = "NOVA_HERMES_NATIVE_SHADOW"
PRIMARY_FLAG = "NOVA_HERMES_NATIVE_PRIMARY"
SHADOW_STATE_DIR = REPO_ROOT / "data" / "runtime" / "nova_hermes_shadow_sessions"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
_ACTIVE_HERMES_TURN: contextvars.ContextVar[str] = contextvars.ContextVar("nova_active_hermes_turn", default="")


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return "unavailable"


def _resource_name(capability: Any) -> str:
    """Map tool identifiers to a resource family for generic continuity."""
    name = str(capability or "")
    lowered = name.lower()
    if "nexus_get_" in lowered or lowered == "nexus_read_shadow" or "nexus_mcp" in lowered:
        return "NEXUS"
    if lowered.startswith(("gmail_", "calendar_")) or "google_mcp" in lowered:
        return "GOOGLE"
    if lowered.startswith(("public_web", "web_")):
        return "PUBLIC_WEB"
    if lowered.startswith(("alpha_", "research_")):
        return "ALPHA"
    return name


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
        "For present-tense questions about Nexus operational state, use the "
        "relevant Nexus read rather than asking the user to choose a business "
        "category; the read may truthfully return an empty result. "
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


def _volatile_resource_guidance() -> str:
    """Minimal generic freshness contract for the profile-local MCP tools."""
    return (
        "\n\n[VOLATILE RESOURCE FRESHNESS]\n"
        "Nexus operational reads are volatile. When the user asks for present, "
        "current, live, or still-true operational state, perform a fresh "
        "authoritative Nexus read; prior conversation is context for meaning, "
        "not proof of current state. Reuse a prior result only when answering "
        "without a current-state claim. Within one turn, do not repeat the same "
        "capability unless the read failed or genuinely needs retry/pagination.\n"
    )


def _json_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        # MCP tool results arrive as content parts (normally one text part).
        # Parse the structured JSON part and keep the wire envelope out of the
        # evidence layer.
        for part in value:
            if isinstance(part, dict) and part.get("type") == "text":
                parsed = _json_object(part.get("text"))
                if parsed:
                    return parsed
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            # Hermes wraps MCP text results in an untrusted-data envelope.
            # Decode only the JSON object carried by that envelope, preferring
            # structuredContent and otherwise the JSON result string.
            start = value.find("{")
            if start < 0:
                return {}
            try:
                wrapped, _ = json.JSONDecoder().raw_decode(value[start:])
            except (TypeError, ValueError):
                return {}
            if isinstance(wrapped, dict) and isinstance(wrapped.get("structuredContent"), dict):
                return wrapped["structuredContent"]
            result = wrapped.get("result") if isinstance(wrapped, dict) else None
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                    return parsed if isinstance(parsed, dict) else {}
                except (TypeError, ValueError):
                    return {}
            return wrapped if isinstance(wrapped, dict) else {}
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
        "nexus_executed": "nexus_read_shadow" in counts or any(name.startswith("mcp__nexus_mcp__nexus_get_") for name in counts),
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
    nexus_recent = [
        row for row in recent
        if isinstance(row, dict) and (
            row.get("resource") == "NEXUS"
            or str(row.get("capability", "")).startswith("nexus_get_")
        )
    ]
    if nexus_recent:
        latest_nexus = nexus_recent[-1]
        lines.append("CURRENT_REFERENT_DOMAIN=" + str(latest_nexus.get("capability") or "NEXUS")[:120])
        lines.append(
            "REFERENT_RULE=Use the current conversational referent to identify the domain; "
            "if the user asks whether it is still current, refresh that same Nexus capability."
        )
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


def _conversation_history_for_model(state: Dict[str, Any]) -> list[Dict[str, str]]:
    """Build continuity context without turning resource output into truth.

    The session sidecar intentionally retains prior answers for conversational
    continuity.  A prior answer is not, however, a current Nexus resource
    result.  Keep the text available for explanation and referents while
    making its provenance explicit to the native model.  Older sidecars do not
    have provenance fields, so those entries are conservatively labeled as
    unclassified prior context rather than being promoted to current state.
    """
    history: list[Dict[str, str]] = []
    for turn in (state.get("recent_turns") or [])[-8:]:
        if not isinstance(turn, dict):
            continue
        if turn.get("user"):
            history.append({"role": "user", "content": str(turn["user"])[:2000]})
        if turn.get("assistant"):
            source_type = str(turn.get("source_type") or "UNCLASSIFIED_PRIOR_CONTEXT")
            domains = ",".join(str(item) for item in (turn.get("resource_domains") or []) if item)
            if source_type == "RESOURCE_BACKED":
                # Preserve the prior resource as a referent without placing
                # stale factual prose beside the fresh result. The complete
                # response remains in the sidecar for historical/audit use.
                label = (
                    "[PRIOR RESOURCE-BACKED EXCHANGE — referent continuity only; "
                    "retrieve fresh state for facts"
                    + (f"; resource={domains}" if domains else "")
                    + "]"
                )
            else:
                # Unannotated legacy entries cannot safely be distinguished
                # from old resource output. Keep the turn's user text above,
                # but do not promote unknown assistant prose into model facts.
                label = "[PRIOR UNCLASSIFIED RESPONSE — continuity metadata only; facts require current evidence]"
            history.append({"role": "assistant", "content": label})
    return history


def _referent_snapshot(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Return bounded, non-body metadata useful for anaphoric follow-ups."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return []
    snapshot: list[Dict[str, Any]] = []
    for item in items[:10]:
        if not isinstance(item, dict):
            continue
        allowed = (
            "id", "event_id", "message_id", "thread_id", "summary", "subject",
            "from", "sender", "start", "end", "internal_date", "date", "status",
            "updated_at", "labels", "snippet",
        )
        row = {key: item[key] for key in allowed if key in item}
        if isinstance(row.get("snippet"), str):
            row["snippet"] = row["snippet"][:300]
        snapshot.append(row)
    return snapshot


def _install_google_turn_dedupe() -> None:
    """Memoize successful identical Google reads only within one Hermes task."""
    try:
        from tools.registry import registry
    except Exception:
        return
    for name, entry in list(getattr(registry, "_tools", {}).items()):
        if "google_mcp" not in str(name):
            continue
        handler = getattr(entry, "handler", None)
        if not callable(handler) or getattr(handler, "_nova_turn_dedupe", False):
            continue
        cache: Dict[tuple[str, str, str], str] = {}

        def deduped(args: Dict[str, Any], _handler=handler, _cache=cache, _name=str(name), **kwargs: Any) -> str:
            task_id = str(kwargs.get("task_id") or kwargs.get("effective_task_id") or _ACTIVE_HERMES_TURN.get() or "")
            if not task_id:
                return _handler(args, **kwargs)
            key = (task_id, _name, json.dumps(args or {}, sort_keys=True, default=str))
            if key in _cache:
                return _cache[key]
            result = _handler(args, **kwargs)
            try:
                parsed = json.loads(result)
            except (TypeError, json.JSONDecodeError):
                parsed = None
            if not isinstance(parsed, dict) or not parsed.get("error"):
                _cache[key] = result
                # Keep this process-local cache bounded even when a worker
                # handles many turns before its MCP registry is reloaded.
                if len(_cache) > 256:
                    del _cache[next(iter(_cache))]
            return result

        deduped._nova_turn_dedupe = True
        entry.handler = deduped


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
    """Register the non-Nexus Nova adapters in the Hermes process only.

    Nexus operational reads are provided by the profile-local ``nexus_mcp``
    server.  The historical ``nexus_read_shadow`` adapter is retained only as
    an explicit compatibility escape hatch for old fixtures and is not
    registered in normal Nova execution.
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

    if os.getenv("NOVA_ENABLE_LEGACY_SHADOW_NEXUS", "false").lower() == "true":
        # Compatibility-only path; production Nova uses nexus_mcp from the
        # dedicated profile and must not silently fall back to summaries.
        legacy_schema = {
            "name": "nexus_read_shadow",
            "description": "Legacy compatibility read; not the primary Nexus operational interface.",
            "parameters": {"type": "object", "properties": {
                "resource": {"type": "string", "enum": ["NEXUS_CAPABILITY_MAP", "NEXUS_LIVE_TRUTH"]}
            }, "required": ["resource"]},
        }
        def legacy_nexus_read(args: Dict[str, Any], **_: Any) -> str:
            result = execute_shared_capability(
                "hermes_nova", "get_capability_registry" if args["resource"] == "NEXUS_CAPABILITY_MAP" else "get_runtime_capabilities", {},
                conversation_id="shadow", trace_id="hermes_legacy_shadow",
            )
            return json.dumps(result, sort_keys=True, default=str)
        registry.register("nexus_read_shadow", "nexus", legacy_schema, legacy_nexus_read,
                          description=legacy_schema["description"], max_result_size_chars=50000)
    registry.register("alpha_challenge_shadow", "research", alpha_schema, alpha_challenge,
                      description=alpha_schema["description"], max_result_size_chars=50000)
    registry.register("public_web_search_shadow", "shadow_web", web_search_schema, public_web_search,
                      description=web_search_schema["description"], max_result_size_chars=50000)
    registry.register("public_web_retrieval_shadow", "shadow_web", web_retrieval_schema, public_web_retrieval,
                      description=web_retrieval_schema["description"], max_result_size_chars=50000)
    # The Nova adapters are registered dynamically, so expose their toolsets
    # to Hermes' supported resolver just as a discovered plugin/MCP server
    # would. This keeps the dedicated profile's tool surface identical to the
    # certified Nova surface without inheriting global tool configuration.
    for toolset_name in ("nexus", "google", "research", "shadow_web"):
        registry.register_toolset_alias(toolset_name, toolset_name)


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
    from langfuse_runtime import NovaTrace, claim_diagnostics
    # Nova runs in an invocation-scoped Hermes home. This prevents the global
    # operator SOUL and memory from entering the primary conversation prompt.
    os.environ["HERMES_HOME"] = str(NOVA_HERMES_HOME)
    hermes_load_started = time.monotonic()
    AIAgent = _load_hermes()
    phase_timings["hermes_init_ms"] = round((time.monotonic() - hermes_load_started) * 1000, 1)
    _register_bounded_nexus_tools()
    active_session = session_id or "nova-shadow-" + uuid.uuid4().hex[:12]
    turn_id = "shadow-turn-" + uuid.uuid4().hex[:12]
    _ACTIVE_HERMES_TURN.set(turn_id)
    trace = NovaTrace(update_id=os.getenv("NOVA_SHADOW_UPDATE_ID", turn_id), session_id=active_session)
    trace.event("telegram.intake", {"runtime": "hermes", "agent": "nova", "turn_id": turn_id})
    chosen_model = model or os.getenv("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")
    # Load prior structured resource metadata before deciding which tools are
    # available. A volatile follow-up may omit the resource name, but its
    # current-state wording still requires the relevant fresh Nexus surface.
    shadow_state = _load_shadow_state(active_session)
    prior_records = [dict(row) for row in (shadow_state.get("resource_results") or []) if isinstance(row, dict)]
    toolsets = enabled_toolsets if enabled_toolsets is not None else ["shadow_web", "mcp-nexus_mcp", "mcp-google_mcp", "research", "delegation"]
    if turn_contract := turn_requirements(prompt, prior_records):
        if turn_contract.get("reuse_only"):
            # A result-retrieval follow-up uses the linked result in context;
            # Alpha remains available for an explicit new challenge.
            toolsets = [name for name in toolsets if name != "research"]
        # ``reasoning_first`` describes how Hermes should approach a
        # self-contained question; it must not remove optional resources from
        # the model's semantic tool surface. Availability is not selection.
    # Hermes intentionally removed MCP discovery as a module import side
    # effect. Nova is a bounded synchronous entry point, so explicitly load
    # the profile-local MCP server before taking the tool snapshot. This is
    # the only primary Nexus read surface; the legacy shadow adapter remains
    # disabled unless explicitly requested by an old fixture.
    # The turn identifier must exist before discovery so MCP receipts and
    # Langfuse events share the same correlation boundary.
    os.environ["NEXUS_MCP_TURN_ID"] = turn_id
    os.environ["NEXUS_MCP_UPDATE_ID"] = os.getenv("NOVA_SHADOW_UPDATE_ID", "")
    if "mcp-nexus_mcp" in toolsets:
        from tools.mcp_tool import discover_mcp_tools
        discover_mcp_tools()
    _install_google_turn_dedupe()
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
    turn_contract = turn_requirements(prompt, prior_records)
    turn_contract_guidance = ""
    if turn_contract["required_resources"]:
        turn_contract_guidance = (
            "\n\n[CURRENT TURN RESOURCE CONTRACT]\n"
            "The current user request explicitly names resources that must be "
            "consulted for this task: " + ", ".join(turn_contract["required_resources"]) + ". "
            "Use native tools for those resources in this turn. Prior conversation "
            "is context, not a substitute for a required current read.\n"
        )
    elif turn_contract["fresh_execution_required"]:
        turn_contract_guidance = (
            "\n\n[CURRENT INFORMATION CONTRACT]\n"
            "This request asks about present information. Use the available "
            "resource whose semantic domain matches the request before asking "
            "for unnecessary clarification; a truthful empty result is valid. "
            "Do not treat prior conversation as current external or operational "
            "truth.\n"
        )
    if turn_contract.get("referent_capability") and not re.search(r"\b(?:nexus|reviews?|blockers?|opportunit(?:y|ies)|work items?)\b", prompt, re.I):
        turn_contract_guidance += (
            "\n[CURRENT REFERENT SCOPE]\n"
            "This is an anaphoric follow-up to the latest linked resource result. Preserve "
            "the prior conversational subject and use its linked capability when needed: "
            + turn_contract["referent_capability"]
            + ". Do not call unrelated resource capabilities in this turn.\n"
        )
    current_context = _current_shadow_context(shadow_state)
    immutable_objective = (
        "\n\n[IMMUTABLE TURN OBJECTIVE]\n"
        "The original user objective for this turn is: " + turn_contract["turn_objective"] + "\n"
        "Tool calls may collect evidence, but they must not replace or change this objective. "
        "The final response must answer the original objective.\n"
    )
    conversation_history = _conversation_history_for_model(shadow_state)
    referent_context = ""
    referent_capability = turn_contract.get("referent_capability")
    if referent_capability:
        for row in reversed(prior_records):
            if str(row.get("capability")) == referent_capability:
                snapshot = row.get("referent_snapshot")
                if snapshot:
                    referent_context = (
                        "\n\n[LINKED REFERENT DATA — use only for the prior subject; "
                        "current-state questions still require a fresh read]\n"
                        + json.dumps(snapshot, sort_keys=True, default=str)[:5000]
                    )
                break
    native_conversation = not turn_contract["required_resources"]
    trace.event("nova.session_context", {
        "session_turn_count": len(shadow_state.get("recent_turns") or []),
        "prior_assistant_message_count": sum(1 for row in shadow_state.get("recent_turns", []) if isinstance(row, dict) and row.get("assistant")),
        "prior_tool_result_count": len(prior_records),
        "prior_volatile_claim_count": sum(1 for row in prior_records if row.get("currentness") or row.get("resource") == "NEXUS"),
        "profile_hash": _file_hash(NOVA_HERMES_HOME / "SOUL.md"),
        "volatile_guidance_present": True,
        "available_mcp": "mcp-nexus_mcp" in toolsets,
        "available_web": "shadow_web" in toolsets,
        "available_alpha": "research" in toolsets,
        "chain_of_thought_captured": False,
    })
    # The dedicated Hermes profile owns ordinary conversation. Nova-specific
    # guidance is added only when resource-backed execution needs it.
    ephemeral_prompt = (
        _volatile_resource_guidance()
        + (_shadow_resource_guidance() if turn_contract["fresh_execution_required"] else "")
        + referent_context
        if native_conversation
        else _nova_soul() + _shadow_resource_guidance() + _volatile_resource_guidance() + current_context + immutable_objective + correlation_context + referent_context
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
        skip_memory=True,
        save_trajectories=False,
        quiet_mode=True,
        max_iterations=8,
        platform="nova-shadow",
    )
    # AIAgent may refresh profile MCP registrations during construction; apply
    # the task-scoped wrapper after that refresh as well.
    _install_google_turn_dedupe()
    # A volatile anaphoric follow-up inherits only the previously resolved
    # Nexus capability. Restricting the exposed MCP definitions for this turn
    # prevents Hermes from widening “those” into a survey of unrelated state;
    # the capability is derived from prior tool provenance, never from a
    # phrase-specific route.
    if referent_capability and _resource_name(referent_capability) == "NEXUS" and not re.search(r"\b(?:nexus|reviews?|blockers?|opportunit(?:y|ies)|work items?)\b", prompt, re.I):
        scoped_tools = [
            tool for tool in getattr(agent, "tools", [])
            if str(tool.get("function", {}).get("name", "")).endswith(referent_capability)
        ]
        if scoped_tools:
            agent.tools = scoped_tools
            agent.valid_tool_names = {tool["function"]["name"] for tool in scoped_tools}
    elif referent_capability and _resource_name(referent_capability) == "GOOGLE" and turn_contract.get("referent_mode") == "OBJECT":
        # An object follow-up reasons over the linked bounded result set. If
        # it needs more detail, item/thread reads remain available; a broad
        # discovery search is not a substitute for the already-resolved set.
        scoped_tools = [
            tool for tool in getattr(agent, "tools", [])
            if "google_mcp" in str(tool.get("function", {}).get("name", ""))
            and not str(tool.get("function", {}).get("name", "")).endswith("gmail_search")
            and not str(tool.get("function", {}).get("name", "")).endswith("calendar_search_events")
        ]
        if scoped_tools:
            agent.tools = scoped_tools
            agent.valid_tool_names = {tool["function"]["name"] for tool in scoped_tools}
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
    first_tool_names = [str(row.get("name") or row.get("tool_name")) for row in all_messages if row.get("role") == "tool"]
    trace.generation("hermes.generation", model=chosen_model, input_text=prompt,
                     output_text=str(result.get("final_response", "")) if isinstance(result, dict) else "",
                     metadata={"generation_type": "INITIAL_GENERATION", "tool_calls_requested": first_tool_names,
                               "selected_resource_type": "NEXUS_MCP" if any("nexus_get_" in x for x in first_tool_names) else ("GOOGLE" if any(x.startswith(("gmail_", "calendar_")) or "google_mcp" in x for x in first_tool_names) else ("WEB" if any("web_" in x for x in first_tool_names) else ("ALPHA" if any("alpha_" in x for x in first_tool_names) else "NONE"))),
                               "model_call_count": len(model_calls)})

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
            trace.event("hermes.final_synthesis", {
                "response_chars": len(draft),
                "claim_source_diagnostic": claim_diagnostics(
                    draft,
                    tool_names=[],
                    prior_tool_result_count=len(prior_records),
                    prior_claim_count=sum(1 for row in prior_records if row.get("currentness") or row.get("resource") == "NEXUS"),
                ),
                "tool_result_fingerprint": hashlib.sha256(b"[]").hexdigest()[:16],
            })
            trace.finish({"runtime": "hermes", "model": chosen_model, "completed": bool(result.get("completed"))})
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
            skip_memory=True,
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
                "resource": _resource_name(capability),
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
                "referent_snapshot": _referent_snapshot(payload),
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
        tool_rows = _tool_messages(messages)
        turns = shadow_state.setdefault("recent_turns", [])
        turns.append({
            "user": prompt[:1000],
            "assistant": shadow_state.get("last_response", ""),
            "source_type": "RESOURCE_BACKED" if tools_seen else "NATIVE_CONVERSATION",
            "resource_domains": sorted({
                str(row.get("resource")) for row in tool_rows
                if row.get("resource")
            }),
            "turn_id": turn_id,
        })
        shadow_state["recent_turns"] = turns[-8:]
        trace.event("nexus.mcp" if any("nexus_get_" in str(row.get("name")) for row in tool_rows) else "resource.selection", {
            "tool_names": [str(row.get("name") or row.get("tool_name")) for row in tool_rows],
            "actual_tool_count": len(tool_rows),
            "mcp_tool_count": sum(1 for row in tool_rows if "nexus_get_" in str(row.get("name"))),
            "web_tool_count": sum(1 for row in tool_rows if "web_" in str(row.get("name"))),
            "alpha_tool_count": sum(1 for row in tool_rows if "alpha_" in str(row.get("name"))),
            "trace_id": trace.trace_id,
        })
        state_contract = evidence_state(prompt, tool_rows, prior_records)
        if not tool_rows and prior_records and turn_contract.get("reuse_only"):
            # A result follow-up may reuse evidence, but only through its
            # structured receipt linkage. Ordinary conversation text alone is
            # never promoted to current evidence.
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
        trace.event("hermes.final_synthesis", {
            "response_chars": len(str(result.get("final_response", ""))),
            "claim_source_diagnostic": claim_diagnostics(
                str(result.get("final_response", "")),
                tool_names=[str(row.get("name") or row.get("tool_name")) for row in all_messages if row.get("role") == "tool"],
                prior_tool_result_count=len(prior_records),
                prior_claim_count=sum(1 for row in prior_records if row.get("currentness") or row.get("resource") == "NEXUS"),
            ),
            "tool_result_fingerprint": hashlib.sha256(json.dumps([row.get("payload", {}) for row in tool_rows], sort_keys=True, default=str).encode()).hexdigest()[:16],
        })
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
        # Normal dict results must finalize the trace before returning.
        trace.finish({"runtime": "hermes", "model": chosen_model, "completed": bool(result.get("completed"))})
        return result
    trace.finish({"runtime": "hermes", "model": chosen_model, "completed": bool(isinstance(result, dict) and result.get("completed"))})
    return {"response": result, "model": chosen_model, "shadow": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run isolated Hermes-native Nova shadow")
    parser.add_argument("prompt")
    parser.add_argument("--session-id")
    args = parser.parse_args()
    print(json.dumps(run_shadow(args.prompt, session_id=args.session_id), default=str))
