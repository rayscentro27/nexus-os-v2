"""Isolated Hermes-native Nova shadow runner.

This module is deliberately not imported by the live Telegram worker.  It
keeps Nova's current identity but lets Hermes 0.20.6 own generic model/tool
continuation for development comparison only.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hermes_evidence_contract import (
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


def _require_shadow() -> None:
    if os.getenv(SHADOW_FLAG, "false").lower() != "true":
        raise RuntimeError("Hermes Nova shadow is disabled; set NOVA_HERMES_NATIVE_SHADOW=true")
    if os.getenv(PRIMARY_FLAG, "false").lower() == "true":
        raise RuntimeError("Hermes Nova primary cutover is intentionally not enabled")


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
        "and make a concrete recommendation when Ray asks for one. If an "
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

    def public_web_search(args: Dict[str, Any], **_: Any) -> str:
        return json.dumps(_search_free_chain(args["query"], int(args.get("limit", 6))), sort_keys=True, default=str)

    def public_web_retrieval(args: Dict[str, Any], **_: Any) -> str:
        return json.dumps(_retrieve_public_page(args["url"]), sort_keys=True, default=str)

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
    _require_shadow()
    _load_approved_provider_env()
    AIAgent = _load_hermes()
    _register_bounded_nexus_tools()
    chosen_model = model or os.getenv("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")
    toolsets = enabled_toolsets or ["shadow_web", "nexus", "research", "delegation"]
    if turn_contract := turn_requirements(prompt):
        if turn_contract.get("reuse_only"):
            # A result-retrieval follow-up uses the linked result in context;
            # Alpha remains available for an explicit new challenge.
            toolsets = [name for name in toolsets if name != "research"]
    active_session = session_id or "nova-shadow-" + uuid.uuid4().hex[:12]
    shadow_state = _load_shadow_state(active_session)
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
    current_context = _current_shadow_context(shadow_state)
    conversation_history = []
    for turn in (shadow_state.get("recent_turns") or [])[-8:]:
        if not isinstance(turn, dict):
            continue
        if turn.get("user"):
            conversation_history.append({"role": "user", "content": str(turn["user"])[:2000]})
        if turn.get("assistant"):
            conversation_history.append({"role": "assistant", "content": str(turn["assistant"])[:5000]})
    agent = AIAgent(
        model=chosen_model,
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        enabled_toolsets=toolsets,
        session_id=active_session,
        ephemeral_system_prompt=_nova_soul() + _shadow_resource_guidance() + current_context + correlation_context,
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
    result = agent.run_conversation(prompt + turn_contract_guidance, conversation_history=conversation_history or None, task_id=turn_id)
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
    first_state = evidence_state(prompt, _tool_messages(all_messages))
    first_state["page_payloads"] = [row["payload"] for row in _tool_messages(all_messages) if row.get("name") == "public_web_retrieval_shadow"]
    first_state["claim_validation"] = claim_feedback(prompt, str(result.get("final_response", "")) if isinstance(result, dict) else "", first_state)
    if first_state.get("missing_resources") or first_state.get("synthesis_required") or not first_state["claim_validation"].get("valid", True):
        continuation = continuation_guidance(first_state)
        if first_state.get("synthesis_required"):
            continuation += (
                "\n[SYNTHESIS FEEDBACK]\n"
                "The current objective requires a combined answer. The required "
                "Nexus and public-web evidence must appear in the final reasoning; "
                "any Alpha result is supplementary. Do not call another tool in "
                "this continuation unless a required resource is still missing.\n"
            )
        if first_state["claim_validation"].get("unsupported_claims"):
            continuation += (
                "\n[CLAIM SUPPORT FEEDBACK]\n"
                "The draft contains claims without direct support from the returned "
                "evidence: " + ", ".join(first_state["claim_validation"]["unsupported_claims"]) + ". "
                "Revise those claims to distinguish what the pages establish from "
                "what remains unknown; do not invent verification.\n"
            )
        follow_up = agent.run_conversation(
            "For the original user request: " + prompt[:2000] + "\n" + continuation,
            task_id=turn_id + "-evidence",
        )
        if isinstance(follow_up, dict):
            all_messages.extend(follow_up.get("messages", []))
            result = follow_up
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
                "request_id": request_id,
                "result_id": result_id,
                "job_id": job_id,
                "artifact_id": artifact_id,
                "objective": data.get("objective") or job.get("objective"),
                "completed_at": payload.get("completed_at") or payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
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
        state_contract = evidence_state(prompt, tool_rows)
        state_contract["page_payloads"] = [row["payload"] for row in tool_rows if row.get("name") == "public_web_retrieval_shadow"]
        draft = shadow_state.get("last_response", "")
        state_contract["claim_validation"] = claim_feedback(prompt, draft, state_contract)
        shadow_state["turn_contract"] = turn_contract
        shadow_state["evidence_state"] = state_contract
    _save_shadow_state(active_session, shadow_state)
    if isinstance(result, dict):
        result["turn_contract"] = turn_contract
        result["evidence_state"] = state_contract
        result["claim_validation"] = state_contract["claim_validation"]
        # Return the complete turn transcript so the canonical worker receipt
        # records tools from the initial pass and any evidence continuation.
        result["messages"] = all_messages
        return result
    return {"response": result, "model": chosen_model, "shadow": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run isolated Hermes-native Nova shadow")
    parser.add_argument("prompt")
    parser.add_argument("--session-id")
    args = parser.parse_args()
    print(json.dumps(run_shadow(args.prompt, session_id=args.session_id), default=str))
