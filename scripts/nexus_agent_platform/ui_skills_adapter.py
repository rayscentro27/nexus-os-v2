"""Governed adapter for the official UI Skills MCP server."""
from __future__ import annotations

import json
import ssl
import time
import urllib.request
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed.persistence import append_record, new_id

ROOT = Path(__file__).resolve().parents[2]
REMOTE = "https://www.ui-skills.com/mcp"
CACHE = ROOT / "data/runtime/ui_skills_cache.json"
MAX_SKILLS = 3
ALLOWED_CAPABILITIES = {"accessibility", "responsive", "layout", "typography", "motion", "performance", "component", "frontend", "metadata", "testing", "qa", "fidelity", "writing"}
RESTRICTED_CAPABILITIES = {"redesign", "branding", "information architecture", "framework", "dependency", "override"}
ALLOWLIST = {"ui-skills-root", "ibelick-baseline-ui", "ibelick-fixing-accessibility", "ibelick-fixing-motion-performance", "jakubkrehel-better-layout", "jakubkrehel-better-accessibility", "jakubkrehel-better-writing", "addyosmani-frontend-ui-engineering"}


def _call(method: str, request_id: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    request = urllib.request.Request(REMOTE, data=json.dumps(body).encode(), headers={"content-type": "application/json", "accept": "application/json, text/event-stream", "user-agent": "Nexus-UI-Skills-Adapter/1.0"})
    with urllib.request.urlopen(request, timeout=20, context=_ssl_context()) as response:
        return json.loads(response.read().decode())


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _receipt(action: str, result: dict[str, Any], **extra: Any) -> None:
    append_record("ui_skills_receipts", {"schema_version": "nexus.ui-skills-receipt.v1", "receipt_id": new_id("ui_skills"), "action": action, "remote_source": REMOTE, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "result": result, **extra})


def server_metadata() -> dict[str, Any]:
    request = urllib.request.Request("https://www.ui-skills.com/.well-known/mcp/server-card.json", headers={"accept": "application/json", "user-agent": "Nexus-UI-Skills-Adapter/1.0"})
    with urllib.request.urlopen(request, timeout=20, context=_ssl_context()) as response:
        result = json.loads(response.read().decode())
    _receipt("server_metadata", {"name": result.get("serverInfo", {}).get("name"), "version": result.get("serverInfo", {}).get("version"), "tools": [x.get("name") for x in result.get("tools", [])]})
    return result


def list_skills(query: str = "") -> list[dict[str, Any]]:
    result = _call("tools/call", 2, {"name": "list_skills", "arguments": ({"query": query} if query else {})})
    text = next((x.get("text", "") for x in result.get("result", {}).get("content", []) if x.get("type") == "text"), "")
    payload = json.loads(text) if text.startswith("{") else {"content": text}
    skills = payload.get("registry", payload.get("skills", [])) if isinstance(payload, dict) else []
    safe = [{k: item.get(k) for k in ("slug", "name", "description", "topics", "pathSlug", "sourceLabel") if k in item} for item in skills if isinstance(item, dict)]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"cached_at": time.time(), "skills": safe}, indent=2) + "\n")
    _receipt("list_skills", {"query": query, "count": len(safe)}, cache=str(CACHE))
    return safe


def get_skill(name: str) -> dict[str, Any]:
    result = _call("tools/call", 3, {"name": "get_skill", "arguments": {"name": name}})
    text = next((x.get("text", "") for x in result.get("result", {}).get("content", []) if x.get("type") == "text"), "")
    bounded = text[:12000]
    output = {"name": name, "source": REMOTE, "content": bounded, "truncated": len(text) > len(bounded)}
    _receipt("get_skill", {"name": name, "content_length": len(text), "bounded": True})
    return output


def route_task(task: str) -> dict[str, Any]:
    text = task.lower()
    query = "accessibility" if "accessibility" in text or "responsive" in text else ("typography" if "typography" in text else "frontend")
    candidates = list_skills(query)
    selected = []
    for skill in candidates:
        haystack = f"{skill.get('name', '')} {skill.get('description', '')}".lower()
        slug = skill.get("slug") or skill.get("name")
        if slug not in ALLOWLIST or any(term in haystack for term in RESTRICTED_CAPABILITIES):
            continue
        if any(term in haystack for term in ALLOWED_CAPABILITIES):
            selected.append(slug)
        if len(selected) >= MAX_SKILLS:
            break
    return {"task": task, "selected_skills": selected[:MAX_SKILLS], "why_selected": "smallest implementation/QA guidance set", "allowed_changes": sorted(ALLOWED_CAPABILITIES), "forbidden_changes": sorted(RESTRICTED_CAPABILITIES), "source_version": "UI Skills MCP 0.2.4"}


def governance_check(recommendation: dict[str, Any]) -> dict[str, Any]:
    proposed = str(recommendation.get("proposed_changes", "")).lower()
    forbidden = [term for term in RESTRICTED_CAPABILITIES if term in proposed]
    result = {"approved_design_source_of_truth": True, "ui_skills_can_override_approved_design": False, "ui_skills_can_change_branding": False, "ui_skills_can_change_framework": False, "governance_violation": bool(forbidden), "forbidden_matches": forbidden}
    _receipt("governance_check", result)
    return result
