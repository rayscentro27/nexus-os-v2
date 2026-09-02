"""Small, deterministic, authority-preserving client for Oracle Hermes.

The client uses Hermes' official OpenAI-compatible API over a caller-supplied
private transport. It never executes tools, writes TruthKernel state, or
interprets advisory text as authorization.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _keychain_secret(service: str) -> str | None:
    """Read a named macOS Keychain item without echoing its value.

    Keychain lookup is an optional local control-plane source.  The bridge
    never writes the result to disk, reports, subprocess arguments, or logs.
    Non-macOS hosts simply fall through to the environment path.
    """
    import platform
    import subprocess

    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", os.getenv("USER", ""),
             "-s", service, "-w"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


class BridgeError(RuntimeError):
    """A fail-closed bridge error."""


@dataclass(frozen=True)
class BridgeRequest:
    request_type: str
    purpose: str
    safe_context: dict[str, Any]
    caller: str = "nexus"
    allowed_capabilities: tuple[str, ...] = ()
    timeout_seconds: float = 30.0
    max_tokens: int = 256
    data_classification: str = "INTERNAL"
    pii_allowed: bool = False
    request_id: str = field(default_factory=lambda: f"nexus-hermes-{uuid.uuid4().hex}")
    timestamp: str = field(default_factory=_now)

    def validate(self) -> None:
        if not self.request_type or not self.purpose or not self.caller:
            raise BridgeError("invalid request: type, purpose, and caller are required")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 120:
            raise BridgeError("invalid request timeout")
        if self.max_tokens <= 0 or self.max_tokens > 1024:
            raise BridgeError("invalid max_tokens")
        if self.pii_allowed:
            raise BridgeError("PII is denied by the initial bridge contract")
        if _contains_obvious_pii(self.safe_context):
            raise BridgeError("request rejected: possible PII detected")


@dataclass(frozen=True)
class BridgeResponse:
    request_id: str
    status: str
    result: str | None = None
    model_provider_metadata: dict[str, Any] = field(default_factory=dict)
    tool_usage: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    started_at: str = ""
    completed_at: str = ""


def _contains_obvious_pii(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str)
    patterns = (
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-like
        r"\b\d{13,19}\b",  # payment/account-like number
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


class OracleHermesBridge:
    """HTTP adapter; inject ``transport`` for deterministic unit tests.

    ``transport`` receives ``(method, path, payload, headers, timeout)`` and
    returns a decoded JSON object. Production wiring should use a loopback
    SSH-forwarded base URL, never a public Hermes address.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        transport: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("NEXUS_ORACLE_HERMES_BASE_URL", "http://127.0.0.1:18642")).rstrip("/")
        self.api_key = api_key if api_key is not None else (
            os.getenv("NEXUS_ORACLE_HERMES_API_KEY")
            or _keychain_secret(os.getenv("NEXUS_ORACLE_HERMES_KEYCHAIN_SERVICE",
                                          "nexus-oracle-hermes-api"))
        )
        self._transport = transport or self._http_transport
        if not self.base_url.startswith("http://127.0.0.1:"):
            raise BridgeError("Hermes endpoint must be loopback/private")
        if not self.api_key:
            raise BridgeError("Hermes bridge credential is not configured")

    def _http_transport(self, method: str, path: str, payload: dict[str, Any] | None,
                        headers: dict[str, str], timeout: float) -> dict[str, Any]:
        import httpx
        response = httpx.request(method, f"{self.base_url}{path}", json=payload,
                                 headers=headers, timeout=timeout)
        response.raise_for_status()
        decoded = response.json()
        if not isinstance(decoded, dict):
            raise BridgeError("Hermes returned a non-object response")
        return decoded

    def health(self, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
        result = self._transport("GET", "/health", None, self._headers(), timeout_seconds)
        if not isinstance(result, dict):
            raise BridgeError("invalid health response")
        return result

    def ask(self, request: BridgeRequest) -> BridgeResponse:
        started = _now()
        attempts = 0
        try:
            request.validate()
            payload = {
                "model": os.getenv("NEXUS_ORACLE_HERMES_MODEL",
                                    "nvidia/nemotron-3.5-lightning:free"),
                "messages": [
                    {"role": "system", "content": (
                        "You are advisory intelligence for Nexus. TruthKernel is read-only "
                        "context; your response is never authority. Do not claim approvals "
                        "or successful side effects."
                    )},
                    {"role": "user", "content": json.dumps(asdict(request), sort_keys=True)},
                ],
                "stream": False,
                "max_tokens": request.max_tokens,
                "temperature": 0,
            }
            raw = None
            last_error = None
            # The Oracle lane is advisory/read-only. One bounded retry is safe
            # for transient provider reads and prevents a single upstream idle
            # timeout from becoming an unexplained user-visible failure. Never
            # retry validation/authentication failures or loop indefinitely.
            for attempts in range(1, 3):
                try:
                    raw = self._transport("POST", "/v1/chat/completions", payload,
                                          self._headers(request.request_id), request.timeout_seconds)
                    break
                except Exception as exc:
                    last_error = exc
                    if type(exc).__name__ not in {"ReadTimeout", "ConnectTimeout", "TimeoutError", "ReadError"} or attempts == 2:
                        raise
            if raw is None:
                raise last_error or BridgeError("Hermes returned no response")
            result = _extract_result(raw)
            metadata = _metadata(raw)
            metadata["bridge_attempts"] = attempts
            warnings = ["ADVISORY_ONLY"]
            if attempts > 1:
                warnings.append("RETRIED_TRANSIENT_PROVIDER_READ")
            return BridgeResponse(request_id=request.request_id, status="SUCCEEDED",
                                  result=result, model_provider_metadata=metadata,
                                  warnings=warnings, started_at=started,
                                  completed_at=_now())
        except Exception as exc:  # bridge must never invent success
            return BridgeResponse(request_id=request.request_id, status="UNAVAILABLE",
                                  model_provider_metadata={"bridge_attempts": attempts},
                                  error=type(exc).__name__, warnings=["FAIL_CLOSED"],
                                  started_at=started, completed_at=_now())

    def _headers(self, request_id: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if request_id:
            headers["X-Nexus-Request-Id"] = request_id
        return headers


def _extract_result(raw: dict[str, Any]) -> str:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise BridgeError("malformed Hermes response: choices missing")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise BridgeError("malformed Hermes response: message content missing")
    return message["content"]


def _metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {key: raw[key] for key in ("model", "id", "provider") if key in raw}
