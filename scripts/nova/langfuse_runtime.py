"""Fail-open, redacted observability for the Hermes-native Nova runtime.

This module is deliberately independent of the Agent Platform execution brain.
It records metadata and bounded text only; it never selects tools or changes a
turn's result. Local JSONL is retained as a diagnostic fallback so tracing is
useful even when Langfuse Cloud is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRACE_DIR = ROOT / "reports" / "runtime" / "agent_traces"


def _hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def _safe_text(value: Any, limit: int = 500) -> str:
    text = str(value or "")[:limit]
    # Reuse the established redaction boundary when available.
    try:
        from nexus_agent_platform.adapters.otel_adapter import _redact_text
        return _redact_text(text)
    except Exception:
        return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "REDACTED_EMAIL", text)


def _safe_meta(value: dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        from nexus_agent_platform.adapters.otel_adapter import _redact_metadata
        return _redact_metadata(value)
    except Exception:
        return {str(k): _safe_text(v) if isinstance(v, str) else v for k, v in value.items()}


class NovaTrace:
    """Best-effort trace facade. Every method is safe to call on failures."""

    def __init__(self, *, update_id: Any, session_id: str = "", trace_id: str | None = None):
        self.update_id = str(update_id)
        self.session_id = session_id
        self.trace_id = trace_id or os.getenv("NOVA_LANGFUSE_TRACE_ID") or f"nova-{self.update_id}-{uuid.uuid4().hex[:16]}"
        self.started = time.monotonic()
        self.events: list[dict[str, Any]] = []
        self._adapter = None
        enabled = os.getenv("LANGFUSE_TRACING_ENABLED", "false").lower() == "true"
        if enabled:
            try:
                from nexus_agent_platform.adapters.otel_adapter import OtelAdapter
                self._adapter = OtelAdapter("nova")
            except Exception:
                self._adapter = None
        os.environ["NOVA_LANGFUSE_TRACE_ID"] = self.trace_id
        os.environ["NOVA_LANGFUSE_UPDATE_ID"] = self.update_id

    @property
    def enabled(self) -> bool:
        return self._adapter is not None and self._adapter.is_enabled

    def event(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        row = {
            "trace_id": self.trace_id,
            "parent": "nova.turn",
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": _safe_meta({"update_id": self.update_id, "session_id": self.session_id, **(metadata or {})}),
        }
        self.events.append(row)
        if self._adapter is not None:
            try:
                with self._adapter.span(name, metadata={"trace_id": self.trace_id, **(metadata or {})}):
                    pass
            except Exception:
                pass

    def generation(self, name: str, *, model: str = "", input_text: str = "", output_text: str = "", metadata: dict[str, Any] | None = None) -> None:
        self.event(name, {"kind": "generation", "model": model, **(metadata or {})})
        if self._adapter is not None:
            try:
                self._adapter.record_generation(name, model=model, input_text=input_text, output_text=output_text,
                                                metadata={"trace_id": self.trace_id, **(metadata or {})})
            except Exception:
                pass

    def finish(self, metadata: dict[str, Any] | None = None) -> None:
        self.event("nova.turn.complete", {"total_latency_ms": round((time.monotonic() - self.started) * 1000, 1), **(metadata or {})})
        try:
            TRACE_DIR.mkdir(parents=True, exist_ok=True)
            path = TRACE_DIR / f"nova_{self.trace_id}.json"
            path.write_text(json.dumps({"trace_id": self.trace_id, "events": self.events}, default=str) + "\n", encoding="utf-8")
        except Exception:
            pass
        if self._adapter is not None:
            try:
                self._adapter.flush()
            except Exception:
                pass


def claim_diagnostics(response: str, *, tool_names: list[str], prior_tool_result_count: int, prior_claim_count: int) -> dict[str, Any]:
    """Bounded deterministic source diagnostic; never invokes a model."""
    text = (response or "").lower()
    nexus_terms = [term for term in ("stripe", "paymentintent", "fake customer", "email mismatch", "active services", "opportunities", "reviews") if term in text]
    fresh_mcp = [name for name in tool_names if "nexus_get_" in name]
    source = "FRESH_MCP" if fresh_mcp else ("PRIOR_SESSION_CONTEXT" if prior_tool_result_count or prior_claim_count else "MODEL_INFERENCE")
    unsupported = bool(nexus_terms and not fresh_mcp)
    return {
        "material_claim_count": len(nexus_terms),
        "material_claim_terms": nexus_terms,
        "source": source,
        "support": "UNSUPPORTED" if unsupported else ("SUPPORTED" if fresh_mcp else "UNKNOWN"),
        "fresh_mcp_support": bool(fresh_mcp),
        "prior_volatile_context_present": bool(prior_tool_result_count or prior_claim_count),
    }
