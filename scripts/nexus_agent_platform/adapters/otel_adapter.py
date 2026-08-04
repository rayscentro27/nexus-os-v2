"""OpenTelemetry adapter — wraps Langfuse behind a Nexus-owned interface.

Langfuse is installed as an optional dependency behind the
``LANGFUSE_TRACING_ENABLED`` flag.  When disabled the adapter becomes
a no-op so the rest of the system runs without tracing overhead.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

log = logging.getLogger(__name__)

_USE_LANGFUSE = os.getenv("LANGFUSE_TRACING_ENABLED", "").lower() == "true"


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
        import os, json
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
        if self._client is not None:
            try:
                with self._client.start_as_current_observation(
                    as_type="trace", name=name, metadata=metadata or {}
                ) as trace:
                    yield trace
            except Exception as exc:
                log.warning("Langfuse trace error for %s: %s", self.agent_id, exc)
                yield None
        else:
            # Local trace fallback
            self._write_local_trace(name, {"type": "trace", "metadata": metadata or {}})
            yield None

    @contextmanager
    def span(self, name: str, parent: Optional[Any] = None,
             metadata: Optional[Dict] = None) -> Generator[Optional[Any], None, None]:
        if not self._enabled:
            yield None
            return
        if self._client is not None:
            try:
                with self._client.start_as_current_observation(
                    as_type="span", name=name, metadata=metadata or {}
                ) as span:
                    yield span
            except Exception as exc:
                log.warning("Langfuse span error for %s: %s", self.agent_id, exc)
                yield None
        else:
            self._write_local_trace(name, {"type": "span", "metadata": metadata or {}})
            yield None

    def record_generation(self, name: str, model: str = "", input_text: str = "",
                          output_text: str = "", metadata: Optional[Dict] = None) -> None:
        if not self._enabled:
            return
        if self._client is not None:
            try:
                with self._client.start_as_current_observation(
                    as_type="generation", name=name,
                    model=model, input=input_text, output=output_text,
                    metadata=metadata or {}
                ):
                    pass
            except Exception as exc:
                log.warning("Langfuse generation record error: %s", exc)
        else:
            self._write_local_trace(name, {
                "type": "generation",
                "model": model,
                "input": input_text[:500],
                "output": output_text[:500],
                "metadata": metadata or {},
            })

    def record_score(self, name: str, value: float, comment: str = "") -> None:
        if not self._enabled or self._client is None:
            return
        try:
            with self._client.start_as_current_observation(
                as_type="score", name=name, value=value, comment=comment
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
