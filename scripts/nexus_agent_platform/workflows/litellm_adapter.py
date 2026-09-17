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
        return await self._fallback_completion(model, messages, temperature, max_tokens, **kwargs)

    async def _litellm_completion(
        self, model: str, messages: List[Dict[str, str]],
        temperature: float, max_tokens: int,
        tools: Optional[List[Dict]] = None, **kwargs: Any,
    ) -> Dict[str, Any]:
        timeout = kwargs.get("timeout") or kwargs.get("request_timeout")
        try:
            import litellm
            kwargs.pop("timeout", None)
            kwargs.pop("request_timeout", None)
            kwargs["model"] = model
            kwargs["messages"] = messages
            kwargs["temperature"] = temperature
            kwargs["max_tokens"] = max_tokens
            if timeout:
                kwargs["timeout"] = timeout
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
            return await self._fallback_completion(
                model, messages, temperature, max_tokens, timeout=timeout
            )

    async def _fallback_completion(
        self, model: str, messages: List[Dict[str, str]],
        temperature: float, max_tokens: int, **kwargs: Any,
    ) -> Dict[str, Any]:
        """Fallback to OpenRouter direct."""
        try:
            import httpx
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            timeout = kwargs.get("timeout") or kwargs.get("request_timeout") or 60
            if not api_key:
                return {"content": "", "model": model, "usage": {}, "tool_calls": [], "error": "AUTH_FAILURE", "error_detail": "OPENROUTER_API_KEY is not present in the service environment"}
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
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
                try:
                    data = resp.json()
                except ValueError:
                    data = {}
                if resp.status_code >= 400:
                    error_payload = data.get("error") if isinstance(data, dict) else None
                    if isinstance(error_payload, dict):
                        detail = str(error_payload.get("message") or error_payload.get("code") or "provider rejected request")[:240]
                    else:
                        detail = "provider rejected request"
                    if resp.status_code in (401, 403):
                        error_type = "AUTH_FAILURE"
                    elif resp.status_code == 429:
                        error_type = "RATE_LIMIT"
                    elif resp.status_code >= 500:
                        error_type = "UPSTREAM_PROVIDER_ERROR"
                    else:
                        error_type = "INVALID_REQUEST"
                    log.error("OpenRouter completion failed for %s: status=%s type=%s detail=%s", self.agent_id, resp.status_code, error_type, detail)
                    return {"content": "", "model": model, "usage": {}, "tool_calls": [], "error": error_type, "http_status": resp.status_code, "error_detail": detail}
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "tool_calls": [],
                }
        except Exception as exc:
            # Do not return an error sentence as successful model content. The
            # caller must be able to distinguish provider failure and invoke
            # its governed deterministic advisory fallback.
            log.error("Fallback completion failed for %s: %s", self.agent_id, exc)
            error_type = "PROVIDER_TIMEOUT" if exc.__class__.__name__ in {"TimeoutException", "ReadTimeout", "ConnectTimeout"} else ("NETWORK_FAILURE" if exc.__class__.__name__ in {"ConnectError", "NetworkError", "RequestError"} else type(exc).__name__)
            return {"content": "", "model": model, "usage": {}, "tool_calls": [], "error": error_type, "error_detail": str(exc)[:240]}

    @property
    def is_enabled(self) -> bool:
        return self._enabled
