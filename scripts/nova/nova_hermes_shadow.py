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


def _search_free_chain(query: str, limit: int = 6) -> Dict[str, Any]:
    """Use existing free/private adapters, deliberately excluding Brave."""
    from hermes.hermes_web_search import _search_bing_html, _search_duckduckgo_html, _search_searxng
    attempts = []
    for provider, fn in (("searxng", _search_searxng), ("duckduckgo_html", _search_duckduckgo_html), ("bing_html", _search_bing_html)):
        result = fn(query, limit)
        attempts.append({"provider": provider, "status": result.get("status"), "notes": result.get("notes", [])})
        if result.get("status") == "ok" and result.get("results"):
            result["attempted_providers"] = attempts
            result["cost_class"] = "free_private_no_new_spend"
            result["shadow_provider_chain"] = True
            return result
    return {"status": "all_free_providers_failed", "provider": "none", "query": query,
            "results": [], "attempted_providers": attempts,
            "cost_class": "free_private_no_new_spend"}


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
        return {"status": "ok", "url": final_url, "requested_url": url,
                "content_type": content_type, "content": text,
                "content_length": len(text), "source_type": "LIVE_PUBLIC_PAGE",
                "retrieved_at": datetime.now(timezone.utc).isoformat()}
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
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    from tools.registry import registry  # type: ignore
    from nexus_agent_platform.capabilities.shared import execute_shared_capability

    nexus_schema = {
        "name": "nexus_read_shadow",
        "description": "Read an authorized Nexus capability/status resource; never mutate Nexus.",
        "parameters": {"type": "object", "properties": {
            "resource": {"type": "string", "enum": ["NEXUS_CAPABILITY_MAP", "NEXUS_LIVE_TRUTH"]}
        }, "required": ["resource"]},
    }
    alpha_schema = {
        "name": "alpha_challenge_shadow",
        "description": "Request a bounded Alpha challenge/research review; no operational execution.",
        "parameters": {"type": "object", "properties": {
            "objective": {"type": "string", "minLength": 10}
        }, "required": ["objective"]},
    }
    web_search_schema = {
        "name": "public_web_search_shadow",
        "description": "Search current public information using approved free/private providers; Brave is excluded.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "minLength": 3}, "limit": {"type": "integer", "minimum": 1, "maximum": 6}}, "required": ["query"]},
    }
    web_retrieval_schema = {
        "name": "public_web_retrieval_shadow",
        "description": "Read a public result URL through bounded HTTP retrieval and return source content/provenance.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string", "format": "uri"}}, "required": ["url"]},
    }

    def nexus_read(args: Dict[str, Any], **_: Any) -> str:
        result = execute_shared_capability(
            "hermes_nova", "get_capability_registry" if args["resource"] == "NEXUS_CAPABILITY_MAP" else "get_runtime_capabilities", {},
            conversation_id="shadow", trace_id="hermes_native_shadow",
        )
        return json.dumps(result, sort_keys=True, default=str)

    def alpha_challenge(args: Dict[str, Any], **_: Any) -> str:
        result = execute_shared_capability(
            "hermes_nova", "submit_alpha_request", {"objective": args["objective"], "execute": True, "requested_by": "hermes_nova"},
            conversation_id="shadow", trace_id="hermes_native_shadow",
        )
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
    _register_bounded_nexus_tools()
    AIAgent = _load_hermes()
    chosen_model = model or os.getenv("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")
    toolsets = enabled_toolsets or ["shadow_web", "nexus", "research", "delegation"]
    active_session = session_id or "nova-shadow-" + uuid.uuid4().hex[:12]
    shadow_state = _load_shadow_state(active_session)
    turn_id = "shadow-turn-" + uuid.uuid4().hex[:12]
    correlation_context = (
        "\n\n[SHADOW CORRELATION — internal]\n"
        f"turn_id={turn_id}; session_id={active_session}. Volatile tool results must be linked to this turn. "
        "When a user refers to a recommendation or Research result, use the current conversational referent and its linked request/result, never an unrelated older artifact."
    )
    agent = AIAgent(
        model=chosen_model,
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        enabled_toolsets=toolsets,
        session_id=active_session,
        ephemeral_system_prompt=_nova_soul() + correlation_context,
        load_soul_identity=False,
        save_trajectories=False,
        quiet_mode=True,
        max_iterations=8,
        platform="nova-shadow",
    )
    result = agent.run_conversation(prompt, task_id=turn_id)
    shadow_state.update({"last_turn_id": turn_id, "last_prompt": prompt[:500], "updated_at": datetime.now(timezone.utc).isoformat()})
    if isinstance(result, dict):
        tools_seen = [m.get("name") for m in result.get("messages", []) if m.get("role") == "tool"]
        shadow_state["last_tools"] = tools_seen
        if "alpha_challenge_shadow" in tools_seen:
            shadow_state["last_alpha_result_id"] = "alpha-result-" + uuid.uuid4().hex[:12]
            shadow_state["last_alpha_request_id"] = "alpha-request-" + uuid.uuid4().hex[:12]
    _save_shadow_state(active_session, shadow_state)
    if isinstance(result, dict):
        return result
    return {"response": result, "model": chosen_model, "shadow": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run isolated Hermes-native Nova shadow")
    parser.add_argument("prompt")
    parser.add_argument("--session-id")
    args = parser.parse_args()
    print(json.dumps(run_shadow(args.prompt, session_id=args.session_id), default=str))
