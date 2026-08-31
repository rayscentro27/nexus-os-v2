"""Isolated Hermes-native Nova shadow runner.

This module is deliberately not imported by the live Telegram worker.  It
keeps Nova's current identity but lets Hermes 0.20.6 own generic model/tool
continuation for development comparison only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
HERMES_ROOT = Path(os.getenv("NOVA_HERMES_ROOT", str(Path.home() / ".hermes/hermes-agent")))
SHADOW_FLAG = "NOVA_HERMES_NATIVE_SHADOW"
PRIMARY_FLAG = "NOVA_HERMES_NATIVE_PRIMARY"


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

    registry.register("nexus_read_shadow", "nexus", nexus_schema, nexus_read,
                      description=nexus_schema["description"], max_result_size_chars=50000)
    registry.register("alpha_challenge_shadow", "research", alpha_schema, alpha_challenge,
                      description=alpha_schema["description"], max_result_size_chars=50000)


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
    toolsets = enabled_toolsets or ["web", "nexus", "research", "delegation"]
    agent = AIAgent(
        model=chosen_model,
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        enabled_toolsets=toolsets,
        session_id=session_id,
        ephemeral_system_prompt=_nova_soul(),
        load_soul_identity=False,
        save_trajectories=False,
        quiet_mode=True,
        max_iterations=8,
        platform="nova-shadow",
    )
    result = agent.run_conversation(prompt, task_id="nova-hermes-shadow")
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
