"""Read-only Nexus adapter for the existing authenticated n8n installation."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.nexus_agent_platform import agent_control_plane
from scripts.nexus_agent_platform.credential_control_plane import apply_to_process

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/nexus_n8n_adapter.json"
DEFAULT_CONFIG = {
    "schema_version": "nexus.n8n_adapter.v1",
    "base_url": "http://nexus-app-services.tailb1e262.ts.net:5678",
    "credential_id": "credential.n8n.nexus_control.prod.v1",
    "api_key_environment_name": "N8N_API_KEY",
    "workflow_list_limit": 100,
    "write_operations_enabled": False,
    "webhook_allowlist": [],
    "evidence": {"runtime": "Contabo", "version": "2.45.6",
                 "api_health": "HTTP 200", "workflow_list": "HTTP 200; bounded limit=100"},
}


def inspect_readonly(timeout: float = 8.0) -> dict:
    """Check health and bounded workflow metadata; never prints or returns auth."""
    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else DEFAULT_CONFIG
    connector = next((x for x in agent_control_plane.public_registry_snapshot()["connectors"]
                      if x.get("connector_id") == "N8N"), None)
    if not connector or connector.get("status") not in {"AVAILABLE_LIMITED", "LIVE_CERTIFIED"}:
        return {"status": "CONNECTOR_UNAVAILABLE", "health": None, "workflow_count": None}
    try:
        agent_control_plane.authorize(agent_id="SYSTEMS_LEAD", connector_id="N8N")
    except agent_control_plane.AuthorizationDenied:
        return {"status": "AUTHORIZATION_DENIED", "health": None, "workflow_count": None}
    resolved = apply_to_process(config["credential_id"])
    if "api_key" not in resolved.get("components_applied", []):
        return {"status": "AUTH_UNAVAILABLE", "health": None, "workflow_count": None}
    base = config["base_url"].rstrip("/")
    key = os.environ.get(config["api_key_environment_name"])
    if not key:
        return {"status": "AUTH_UNAVAILABLE", "health": None, "workflow_count": None}

    def get(path: str):
        req = Request(base + path, headers={"X-N8N-API-KEY": key, "Accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            body = response.read(256_000)
            return response.status, body
    try:
        health_code, _ = get("/healthz")
        list_code, body = get(f"/api/v1/workflows?limit={int(config['workflow_list_limit'])}")
        data = json.loads(body)
        rows = data.get("data", data.get("workflows", [])) if isinstance(data, dict) else []
        evidence = config.get("evidence", config.get("last_read_certification", {}))
        return {"status": "AVAILABLE_LIMITED" if health_code == 200 and list_code == 200 else "UNAVAILABLE",
                "health_http": health_code, "workflow_list_http": list_code, "workflow_count": len(rows),
                "runtime": evidence.get("runtime"), "version": evidence.get("version"),
                "write_operations_enabled": False, "values_included": False}
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        code = exc.code if isinstance(exc, HTTPError) else type(exc).__name__
        return {"status": "UNAVAILABLE", "error_code": str(code), "values_included": False}


def trigger_registered_webhook(*, webhook_id: str, approval_valid: bool = False) -> dict:
    """No live workflow trigger is exposed until a specific webhook is registered and approved."""
    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else DEFAULT_CONFIG
    if not approval_valid or webhook_id not in config.get("webhook_allowlist", []):
        return {"status": "DENIED", "error_code": "N8N_WEBHOOK_NOT_APPROVED"}
    return {"status": "DENIED", "error_code": "N8N_WRITE_ADAPTER_NOT_ENABLED"}
