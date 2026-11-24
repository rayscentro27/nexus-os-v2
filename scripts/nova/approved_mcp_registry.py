"""Explicit Nova MCP approvals, live tool inventory, and write policy."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("NOVA_CODE_ROOT") or os.environ.get("NOVA_REPO_ROOT") or os.environ.get("NEXUS_REPO_ROOT")
            or Path(__file__).resolve().parents[2])
REGISTRY_PATH = ROOT / "config/nova/approved_mcp_servers.json"
CONTAINER = "nexus-hermes-0206"
PYTHON = "/opt/hermes/.venv/bin/python"
_CACHE: dict[str, Any] = {"at": 0.0, "servers": [], "tools": [], "error": None}

DISCOVER = r'''import asyncio,json,sys,yaml,httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.client.stdio import stdio_client,StdioServerParameters
req=json.load(sys.stdin); cfgs=(yaml.safe_load(open("/opt/data/profiles/nova_nexus/config.yaml")) or {}).get("mcp_servers",{})
async def one(sid):
 row={"server_id":sid,"connected":False,"tools":[],"error":None}; cfg=cfgs.get(sid) or {}
 if not cfg or not cfg.get("enabled",True): row["error"]="NOT_CONFIGURED_OR_DISABLED"; return row
 try:
  if cfg.get("url"):
   async with httpx.AsyncClient(headers=cfg.get("headers") or {},timeout=30) as client:
    async with streamable_http_client(cfg["url"],http_client=client) as (rd,wr):
     async with ClientSession(rd,wr) as s: await s.initialize(); result=await s.list_tools()
  elif cfg.get("command"):
   p=StdioServerParameters(command=cfg["command"],args=cfg.get("args") or [],env=cfg.get("env") or None,cwd=cfg.get("cwd"))
   async with stdio_client(p) as (rd,wr):
    async with ClientSession(rd,wr) as s: await s.initialize(); result=await s.list_tools()
  else: row["error"]="UNSUPPORTED_TRANSPORT"; return row
  for t in result.tools:
   a=getattr(t,"annotations",None)
   if hasattr(a,"model_dump"): a=a.model_dump(exclude_none=True)
   schema=getattr(t,"inputSchema",None) or getattr(t,"input_schema",None) or {}
   row["tools"].append({"server_id":sid,"name":t.name,"description":t.description or "","input_schema":schema,"annotations":a if isinstance(a,dict) else {}})
  row["connected"]=True
 except Exception as e: row["error"]=type(e).__name__
 return row
async def main():
 rows=[]
 for sid in req["server_ids"]: rows.append(await one(sid))
 print(json.dumps({"servers":rows}))
asyncio.run(main())
'''


def approved_server_records() -> list[dict[str, Any]]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [x for x in data.get("servers", []) if isinstance(x, dict) and x.get("approved") is True]


def approved_server_ids() -> list[str]:
    return [str(x["server_id"]) for x in approved_server_records() if x.get("server_id")]


def oracle_toolset() -> str:
    """Intersect explicit approvals with enabled profile MCPs; preserve web search."""
    try:
        p = subprocess.run(["podman", "exec", CONTAINER, PYTHON, "-c",
            "import yaml;d=yaml.safe_load(open('/opt/data/profiles/nova_nexus/config.yaml')) or {};print('\\n'.join(k for k,v in (d.get('mcp_servers') or {}).items() if v.get('enabled',True)))"],
            capture_output=True, text=True, timeout=15, check=False)
        if p.returncode != 0:
            return "web"
        configured = {x.strip() for x in p.stdout.splitlines() if x.strip()}
    except (OSError, subprocess.SubprocessError):
        return "web"
    ids = [x for x in approved_server_ids() if x in configured]
    return ",".join([*ids, "web"])


def _classify(tool: dict[str, Any], server: dict[str, Any]) -> dict[str, Any]:
    desc = str(tool.get("description") or "").casefold()
    ann = tool.get("annotations") if isinstance(tool.get("annotations"), dict) else {}
    read = (bool(ann.get("readOnlyHint")) or bool(re.search(r"read[ -]only", desc))
            or bool(re.match(r"\s*(?:(?:volatile|bounded)\s+)*(?:read|list|get|search|find|inspect|status)\b", desc)))
    zero = "cost=zero" in desc or server.get("cost_class") in {"ZERO", "ZERO_INCREMENTAL_COST"}
    no_external = "external_effect=no" in desc or server.get("external_effect") is False
    no_production = "production_effect=no" in desc or server.get("production_effect") is False
    reversible = "reversible=yes" in desc or server.get("reversible") is True
    return {**tool, "approved": True, "authority_class": server.get("authority_class"),
        "read_write_class": "READ" if read else "WRITE", "cost_class": "ZERO" if zero else server.get("cost_class", "UNKNOWN"),
        "external_effect": not no_external, "production_effect": not no_production,
        "destructive": bool(ann.get("destructiveHint")), "reversible": reversible,
        "sandbox_only": bool(server.get("sandbox_only")),
        "write_allowed": bool("write_allowed=yes" in desc and zero and no_external and no_production and reversible),
        "metadata_complete": bool(read or ("write_allowed=yes" in desc and zero and no_external and no_production and reversible))}


def discover_approved_mcp(*, force: bool = False) -> dict[str, Any]:
    if not force and time.monotonic() - float(_CACHE["at"]) < 30:
        return {k: _CACHE[k] for k in ("servers", "tools", "error")}
    records = {x["server_id"]: x for x in approved_server_records()}
    try:
        p = subprocess.run(["podman", "exec", "-i", CONTAINER, PYTHON, "-c", DISCOVER],
            input=json.dumps({"server_ids": list(records)}), capture_output=True, text=True, timeout=75, check=False)
        if p.returncode: raise RuntimeError("DISCOVERY_FAILED")
        rows = json.loads(p.stdout).get("servers", [])
        servers, tools = [], []
        for row in rows:
            base = records.get(row.get("server_id"), {})
            servers.append({**{k: base.get(k) for k in ("server_id", "server_name", "authority_class", "cost_class", "boundary", "route_mode", "sandbox_only", "external_effect", "production_effect", "reversible")},
                "approved": True, "connected": bool(row.get("connected")), "tool_count": len(row.get("tools", [])),
                "runtime_health": "PASS" if row.get("connected") else "UNKNOWN", "error": row.get("error")})
            tools.extend(_classify(t, base) for t in row.get("tools", []))
        _CACHE.update(at=time.monotonic(), servers=servers, tools=tools, error=None)
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, RuntimeError) as exc:
        _CACHE.update(at=time.monotonic(), servers=[], tools=[], error=type(exc).__name__)
    return {k: _CACHE[k] for k in ("servers", "tools", "error")}


def evaluate_mcp_tool_policy(tool: dict[str, Any], *, owner_authorized: bool) -> dict[str, str]:
    """Evaluate live tool authority before routing an action to Hermes."""
    record = next((x for x in approved_server_records() if x["server_id"] == tool.get("server_id")), None)
    if not record: return {"decision": "DENY", "reason": "SERVER_NOT_APPROVED"}
    if record.get("route_mode") == "NEXUS_GOVERNED": return {"decision": "DEFER_TO_NEXUS_GOVERNANCE", "reason": "NEXUS_INTERNAL_ACTION"}
    if not owner_authorized: return {"decision": "DENY", "reason": "OWNER_NOT_AUTHORIZED"}
    if tool.get("read_write_class") == "READ": return {"decision": "ALLOW", "reason": "APPROVED_READ_TOOL"}
    if (tool.get("write_allowed") and tool.get("cost_class") == "ZERO" and not tool.get("external_effect")
        and not tool.get("production_effect") and tool.get("reversible") and not tool.get("destructive")):
        return {"decision": "ALLOW", "reason": "APPROVED_BOUNDED_ZERO_COST_WRITE"}
    return {"decision": "APPROVAL_REQUIRED", "reason": "WRITE_METADATA_OR_BOUNDARY_INCOMPLETE"}


_VERBS = {"CREATE": {"create", "make", "new", "add"}, "UPDATE": {"update", "change", "edit", "modify"},
          "DELETE": {"delete", "remove", "discard"}, "READ": {"read", "show", "get", "list", "find", "open"},
          "STATUS": {"check", "status", "available", "connected", "inspect"}}
_STOP = {"nova", "mcp", "server", "tool", "please", "tell", "me", "the", "a", "an", "to", "for", "it", "this", "that", "my", "your", "can", "you", "and", "of", "in", "on", "whether", "is", "are", "called", "named", "with", "content"}


def resolve_approved_mcp_tool_request(text: str, *, owner_authorized: bool = True) -> dict[str, Any] | None:
    """Find an unambiguous approved non-Nexus tool using live names and schemas."""
    words = set(re.findall(r"[a-z0-9_-]+", str(text or "").casefold())) - _STOP
    operation = next((name for name, verbs in _VERBS.items() if words.intersection(verbs)), None)
    if not operation: return None
    inventory = discover_approved_mcp()
    servers = {x.get("server_id"): x for x in inventory["servers"]}
    matches = []
    for tool in inventory["tools"]:
        if tool.get("server_id") == "nexus_mcp_remote" or not tool.get("metadata_complete"): continue
        name_words = set(re.findall(r"[a-z0-9]+", str(tool.get("name") or "").casefold()))
        schema = tool.get("input_schema") if isinstance(tool.get("input_schema"), dict) else {}
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        schema_text = " ".join([*props, *(str(v.get("description") or "") for v in props.values() if isinstance(v, dict))])
        schema_words = set(re.findall(r"[a-z0-9]+", schema_text.casefold()))
        tool_op = next((key for key, verbs in _VERBS.items() if name_words.intersection(verbs)), None)
        if not tool_op and name_words.intersection({"status", "health"}): tool_op = "STATUS"
        if tool_op != operation: continue
        server = servers.get(tool.get("server_id"), {})
        server_words = set(re.findall(r"[a-z0-9]+", (str(server.get("server_name") or "") + " " + str(server.get("server_id") or "")).casefold())) - _STOP
        server_overlap = len(words.intersection(server_words))
        object_overlap = len(words.intersection(name_words | schema_words))
        if object_overlap == 0 and operation != "STATUS": continue
        score = object_overlap + 2 * server_overlap
        if score: matches.append((score, {**tool, "policy": evaluate_mcp_tool_policy(tool, owner_authorized=owner_authorized)}))
    matches.sort(key=lambda x: x[0], reverse=True)
    if not matches or (len(matches) > 1 and matches[0][0] == matches[1][0]): return None
    return matches[0][1]
