"""LiteLLM gateway adapter — wraps LiteLLM behind Nexus-owned interface.

LiteLLM provides a unified OpenAI-compatible interface to 100+ LLM
providers.  This adapter sits in front so we can swap the underlying
provider without changing any agent code.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_USE_LITELLM = os.getenv("LITELLM_GATEWAY_ENABLED", "").lower() == "true"


class LlmGatewayAdapter:
    """Nexus-owned wrapper around LiteLLM.

    When LiteLLM is disabled, calls fall back to the ``OPENROUTER_API_KEY``
    environment variable (existing behavior).
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._enabled = _USE_LITELLM and self._litellm_available()
        self._router: Any = None

    @staticmethod
    def _litellm_available() -> bool:
        try:
            import litellm  # noqa: F401
            return True
        except ImportError:
            return False

    async def completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Send a completion request via LiteLLM or fallback."""
        if self._enabled:
            return await self._litellm_completion(
                model, messages, temperature, max_tokens, tools, **kwargs
            )
        return await self._fallback_completion(model, messages, temperature, max_tokens)

    async def _litellm_completion(
        self, model: str, messages: List[Dict[str, str]],
        temperature: float, max_tokens: int,
        tools: Optional[List[Dict]] = None, **kwargs: Any,
    ) -> Dict[str, Any]:
        try:
            import litellm
            kwargs["model"] = model
            kwargs["messages"] = messages
            kwargs["temperature"] = temperature
            kwargs["max_tokens"] = max_tokens
            if tools:
                kwargs["tools"] = tools
            response = await litellm.acompletion(**kwargs)
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else {},
                "tool_calls": [
                    {"id": tc.id, "function": tc.function}
                    for tc in (response.choices[0].message.tool_calls or [])
                ],
            }
        except Exception as exc:
            log.warning("LiteLLM completion failed for %s: %s", self.agent_id, exc)
            return await self._fallback_completion(model, messages, temperature, max_tokens)

    async def _fallback_completion(
        self, model: str, messages: List[Dict[str, str]],
        temperature: float, max_tokens: int,
    ) -> Dict[str, Any]:
        """Fallback to OpenRouter direct."""
        try:
            import httpx
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                data = resp.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "tool_calls": [],
                }
        except Exception as exc:
            log.error("Fallback completion failed for %s: %s", self.agent_id, exc)
            return {"content": "I encountered an error processing your request.", "model": model, "usage": {}, "tool_calls": []}

    @property
    def is_enabled(self) -> bool:
        return self._enabled
