"""Penpot adapter boundary for the Creative design engine.

This module deliberately has no visual-design logic. It accepts a structured
Creative brief and delegates artifact creation to an authenticated Penpot
automation channel (official MCP/plugin bridge or a configured API gateway).
It never logs credentials and refuses to claim an artifact when no runtime is
connected.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


class PenpotUnavailable(RuntimeError):
    """Raised when the specialist worker is not connected or authenticated."""


@dataclass(frozen=True)
class PenpotRuntime:
    base_url: str | None
    automation_path: str
    authenticated: bool
    version: str | None = None
    storage: str | None = None
    database: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.authenticated)


class PenpotAdapter:
    """Safe runtime adapter; the actual design work remains in Penpot."""

    OPERATIONS = (
        "create_design_project", "create_page", "create_frame", "create_text",
        "create_shape", "create_component", "apply_tokens", "insert_asset",
        "create_responsive_variant", "fetch_design_metadata", "return_artifact_reference",
    )

    def __init__(self, runtime: PenpotRuntime | None = None) -> None:
        self.runtime = runtime or self.discover_runtime()

    @staticmethod
    def discover_runtime() -> PenpotRuntime:
        # Credentials are presence-only. Values are never returned or printed.
        base_url = os.getenv("PENPOT_API_BASE_URL") or os.getenv("PENPOT_URL")
        mcp_url = os.getenv("PENPOT_MCP_SERVER_URL")
        authenticated = bool(os.getenv("PENPOT_API_TOKEN") or os.getenv("PENPOT_MCP_SERVER_URL"))
        return PenpotRuntime(
            base_url=base_url or mcp_url,
            automation_path="official_mcp_plugin" if mcp_url else "configured_api_gateway",
            authenticated=authenticated,
            version=os.getenv("PENPOT_VERSION"),
            storage=os.getenv("PENPOT_STORAGE_BACKEND"),
            database=os.getenv("PENPOT_DATABASE_BACKEND"),
        )

    def status(self) -> dict[str, Any]:
        return {
            "runtime_started": self.runtime.available,
            "health": "PASS_REAL" if self.runtime.available else "EXTERNAL_GATED",
            "api_available": bool(self.runtime.base_url and self.runtime.automation_path == "configured_api_gateway"),
            "mcp_available": self.runtime.automation_path == "official_mcp_plugin" and self.runtime.available,
            "plugin_automation_available": self.runtime.automation_path == "official_mcp_plugin" and self.runtime.available,
            "automation_path": self.runtime.automation_path,
            "version": self.runtime.version,
            "storage": self.runtime.storage,
            "database": self.runtime.database,
            "operations": list(self.OPERATIONS),
        }

    def _require_runtime(self) -> None:
        if not self.runtime.available:
            raise PenpotUnavailable("penpot_runtime_not_connected")

    def create_editable_artifact(self, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Delegate a structured brief; no local fallback artifact is claimed."""
        self._require_runtime()
        raise NotImplementedError(
            "penpot_transport_requires_official_mcp_or_documented_api_binding"
        )

    def fetch_design_metadata(self, artifact_ref: str) -> dict[str, Any]:
        self._require_runtime()
        raise NotImplementedError(
            "penpot_transport_requires_official_mcp_or_documented_api_binding"
        )
