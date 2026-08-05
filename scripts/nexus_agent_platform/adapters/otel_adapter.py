"""OpenTelemetry adapter — wraps Langfuse behind a Nexus-owned interface.

Langfuse is installed as an optional dependency behind the
``LANGFUSE_TRACING_ENABLED`` flag.  When disabled the adapter becomes
a no-op so the rest of the system runs without tracing overhead.

All trace payloads are redacted before leaving the machine — both for
Langfuse Cloud export and for local trace file persistence.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

log = logging.getLogger(__name__)

_USE_LANGFUSE = os.getenv("LANGFUSE_TRACING_ENABLED", "").lower() == "true"

# Patterns to redact from text and metadata values
_REDACT_PATTERNS = [
    # Telegram bot tokens: digits:AAF...
    (re.compile(r'\d{9,10}:[A-Za-z0-9_-]{35}'), 'REDACTED_BOT_TOKEN'),
    # Bearer / Authorization headers
    (re.compile(r'[Bb]earer\s+[A-Za-z0-9._-]{20,}'), 'REDACTED_BEARER'),
    (re.compile(r'[Aa]uthorization["\s:=]+[A-Za-z0-9._ -]{10,}'), 'REDACTED_AUTH'),
    # API keys — common prefixes
    (re.compile(r'(?:sk|pk|api|key|token|secret)[_-][A-Za-z0-9._ -]{15,}'), 'REDACTED_KEY'),
    # OpenRouter keys
    (re.compile(r'sk-or-v1-[A-Za-z0-9]{20,}'), 'REDACTED_OPENROUTER'),
    # Supabase / general JWT tokens
    (re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), 'REDACTED_JWT'),
    # Stripe keys
    (re.compile(r'(?:sk_live|sk_test|pk_live|pk_test)_[A-Za-z0-9]{20,}'), 'REDACTED_STRIPE'),
    # Resend keys
    (re.compile(r're_[A-Za-z0-9_]{20,}'), 'REDACTED_RESEND'),
    # Oanda tokens (hex-hex-hex or hex-hex)
    (re.compile(r'[a-f0-9]{20,}-[a-f0-9]{20,}'), 'REDACTED_OANDA'),
    # Email addresses (general)
    (re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'), 'REDACTED_EMAIL'),
    # Phone numbers (US-style)
    (re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'), 'REDACTED_PHONE'),
    # Social Security numbers
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 'REDACTED_SSN'),
    # Netlify tokens
    (re.compile(r'nfc_[A-Za-z0-9]{20,}'), 'REDACTED_NETLIFY'),
    # Meta tokens
    (re.compile(r'EAA[A-Za-z0-9]{20,}'), 'REDACTED_META'),
]

# Metadata keys to always redact
_REDACT_META_KEYS = frozenset({
    'bot_token', 'token', 'secret', 'api_key', 'apikey',
    'authorization', 'cookie', 'supabase_service_role_key',
    'service_role_key', 'webhook_secret', 'password',
    'credit_report', 'ssn', 'account_number', 'card_number',
})

# Metadata keys whose values should be hashed, not redacted
_HASH_META_KEYS = frozenset({
    'chat_id', 'user_id', 'telegram_chat_id', 'telegram_user_id',
    'message_id', 'update_id',
})


def _safe_hash(value: str) -> str:
    """Salted hash for sensitive identifiers. Deterministic per-process."""
    salt = os.getenv('NEXUS_TRACE_SALT', 'nexus-default-salt')
    return hashlib.sha256(f'{salt}:{value}'.encode()).hexdigest()[:16]


def _redact_text(text: str) -> str:
    """Redact sensitive patterns from trace text."""
    if not text:
        return text
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_metadata(meta: Optional[Dict]) -> Dict:
    """Redact sensitive keys and hash identifiers in metadata."""
    if not meta:
        return {}
    result = {}
    for k, v in meta.items():
        kl = k.lower()
        if kl in _REDACT_META_KEYS:
            result[k] = 'REDACTED'
        elif kl in _HASH_META_KEYS and isinstance(v, (str, int)):
            result[k] = _safe_hash(str(v))
        elif isinstance(v, str):
            result[k] = _redact_text(v)
        elif isinstance(v, dict):
            result[k] = _redact_metadata(v)
        else:
            result[k] = v
    return result


class OtelAdapter:
    """Nexus-owned wrapper around Langfuse tracing.

    When Langfuse is disabled or unavailable every method is a no-op
    so call-sites never need conditional logic.
    """

    def __init__(self, agent_id: str, public_key: Optional[str] = None,
                 secret_key: Optional[str] = None, base_url: Optional[str] = None):
        self.agent_id = agent_id
        self._client: Any = None
        self._enabled = _USE_LANGFUSE and self._langfuse_available()

        if self._enabled:
            self._init_client(public_key, secret_key, base_url)

    @staticmethod
    def _langfuse_available() -> bool:
        try:
            from langfuse import get_client  # noqa: F401
            return True
        except ImportError:
            return False

    def _init_client(self, public_key: Optional[str], secret_key: Optional[str],
                     base_url: Optional[str]) -> None:
        import os
        try:
            from langfuse import Langfuse
            self._client = Langfuse(
                public_key=public_key or os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=secret_key or os.getenv("LANGFUSE_SECRET_KEY"),
                base_url=base_url or os.getenv("LANGFUSE_BASE_URL"),
            )
            log.info("Langfuse client initialized for agent %s", self.agent_id)
        except Exception as exc:
            log.warning("Langfuse init failed for %s: %s — using local trace files", self.agent_id, exc)
            self._client = None
            self._use_local_traces = True
            self._trace_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "reports", "runtime", "agent_traces"
            )
            os.makedirs(self._trace_dir, exist_ok=True)

    def _write_local_trace(self, name: str, trace_data: Dict) -> None:
        """Write trace to local JSON file when Langfuse server unavailable."""
        import json
        from datetime import datetime, timezone
        if not hasattr(self, "_trace_dir") or not self._trace_dir:
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{self.agent_id}_{name}_{ts}.json"
        filepath = os.path.join(self._trace_dir, filename)
        trace_data["agent_id"] = self.agent_id
        trace_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(filepath, "w") as f:
            json.dump(trace_data, f, indent=2, default=str)

    @contextmanager
    def trace(self, name: str, metadata: Optional[Dict] = None,
              trace_id: Optional[str] = None) -> Generator[Optional[Any], None, None]:
        if not self._enabled:
            yield None
            return
        safe_meta = _redact_metadata(metadata or {})
        if self._client is not None:
            try:
                with self._client.start_as_current_observation(
                    as_type="span", name=name, metadata=safe_meta,
                ) as trace:
                    yield trace
            except Exception as exc:
                log.warning("Langfuse trace error for %s: %s", self.agent_id, exc)
                yield None
        else:
            self._write_local_trace(name, {"type": "trace", "metadata": safe_meta})
            yield None

    @contextmanager
    def span(self, name: str, parent: Optional[Any] = None,
             metadata: Optional[Dict] = None) -> Generator[Optional[Any], None, None]:
        if not self._enabled:
            yield None
            return
        safe_meta = _redact_metadata(metadata or {})
        if self._client is not None:
            try:
                with self._client.start_as_current_observation(
                    as_type="span", name=name, metadata=safe_meta,
                ) as span:
                    yield span
            except Exception as exc:
                log.warning("Langfuse span error for %s: %s", self.agent_id, exc)
                yield None
        else:
            self._write_local_trace(name, {"type": "span", "metadata": safe_meta})
            yield None

    def record_generation(self, name: str, model: str = "", input_text: str = "",
                          output_text: str = "", metadata: Optional[Dict] = None) -> None:
        if not self._enabled:
            return
        safe_input = _redact_text(input_text[:500])
        safe_output = _redact_text(output_text[:500])
        safe_meta = _redact_metadata(metadata or {})
        if self._client is not None:
            try:
                with self._client.start_as_current_observation(
                    as_type="span", name=name, metadata=safe_meta,
                ):
                    with self._client.start_as_current_observation(
                        as_type="generation", name=f"{name}_gen",
                        model=model, input=safe_input, output=safe_output,
                        metadata=safe_meta,
                    ):
                        pass
            except Exception as exc:
                log.warning("Langfuse generation record error: %s", exc)
        else:
            self._write_local_trace(name, {
                "type": "generation",
                "model": model,
                "input": safe_input,
                "output": safe_output,
                "metadata": safe_meta,
            })

    def record_score(self, name: str, value: float, comment: str = "") -> None:
        if not self._enabled or self._client is None:
            return
        safe_comment = _redact_text(comment)
        try:
            with self._client.start_as_current_observation(
                as_type="score", name=name, value=value, comment=safe_comment
            ):
                pass
        except Exception as exc:
            log.warning("Langfuse score record error: %s", exc)

    def flush(self) -> None:
        if self._enabled and self._client is not None:
            try:
                self._client.flush()
            except Exception:
                pass

    @property
    def is_enabled(self) -> bool:
        return self._enabled
