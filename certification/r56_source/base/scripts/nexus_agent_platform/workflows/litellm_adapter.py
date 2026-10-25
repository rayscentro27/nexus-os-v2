"""LiteLLM gateway adapter — wraps LiteLLM behind Nexus-owned interface.

LiteLLM provides a unified OpenAI-compatible interface to 100+ LLM
providers.  This adapter sits in front so we can swap the underlying
provider without changing any agent code.
"""

from __future__ import annotations

import logging
import os
import asyncio
import json
import urllib.request
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

class LlmGatewayAdapter:
    """Compatibility API whose model calls always use the canonical router."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._enabled = False

    async def completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict]] = None,
        reasoning_class: str | None = None,
        sensitivity: str = "unknown_sensitive",
        task_type: str | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Route model judgment through Nexus' canonical registry and governor.

        ``model`` remains accepted for backwards-compatible call sites, but a
        workflow cannot override the centrally selected provider/model.
        Specialized media generation does not use this language-model adapter.
        """
        if reasoning_class not in {"LIGHT_REASONING", "STRONG_REASONING"}:
            return {"content": "", "model": model, "usage": {}, "tool_calls": [],
                "error": "EXECUTION_CLASS_REQUIRED", "error_detail": "Declare LIGHT_REASONING or STRONG_REASONING at the workflow step."}
        try:
            # The canonical environment loader grants this provider credential
            # only to this call path; never print or return it.
            from scripts.ops.nexus_runtime_env import load_runtime_env
            load_runtime_env(allowed_keys={"OPENROUTER_API_KEY"})
            import sys
            from pathlib import Path
            root = Path(__file__).resolve().parents[3]
            if str(root / "scripts") not in sys.path:
                sys.path.insert(0, str(root / "scripts"))
            import model_router
            payload = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            if tools:
                payload["tools"] = tools
            payload.update({k: v for k, v in kwargs.items() if k in {"response_format", "top_p", "seed"}})

            def invoke(request_payload: dict[str, Any], token: str) -> dict[str, Any]:
                body = json.dumps(request_payload).encode("utf-8")
                request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                        "HTTP-Referer": "https://goclearonline.cc", "X-Title": f"Nexus {self.agent_id}"}, method="POST")
                with urllib.request.urlopen(request, timeout=float(kwargs.get("timeout", 60))) as response:
                    return json.loads(response.read().decode("utf-8"))

            selected_task = task_type or os.getenv("NEXUS_REASONING_TASK_TYPE") or "reasoning"
            routed = await asyncio.to_thread(model_router.execute_reasoning,
                agent_key=self.agent_id, task_type=selected_task, sensitivity=sensitivity,
                reasoning_class=reasoning_class, payload=payload, operation=invoke,
                max_tokens=max_tokens, purpose=f"{self.agent_id}:{selected_task}:{reasoning_class}")
            result = routed["result"]
            choice = (result.get("choices") or [{}])[0] if isinstance(result, dict) else {}
            message = choice.get("message") or {}
            return {"content": message.get("content") or "", "model": routed.get("model"),
                "provider": routed.get("provider"), "usage": result.get("usage") or {},
                "tool_calls": message.get("tool_calls") or [], "route_key": routed.get("route_key"),
                "reasoning_class": routed.get("reasoning_class"),
                "cost_class": routed.get("cost_class"), "execution_metadata": routed.get("execution_metadata")}
        except Exception as exc:
            log.warning("Canonical model route denied/failed for %s: %s", self.agent_id, type(exc).__name__)
            return {"content": "", "model": model, "usage": {}, "tool_calls": [],
                "error": "MODEL_ROUTE_FAILED", "error_detail": str(exc)[:240]}

    @property
    def is_enabled(self) -> bool:
        return self._enabled
