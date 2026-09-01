"""Local stdio MCP server for read-only Gmail and Google Calendar access.

MCP is an interface only. OAuth credentials remain in the existing Nexus
keychain control plane, and no write-capability method is registered here.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.google_workspace import CREDENTIAL_ID, SCOPES
from nexus_agent_platform.credential_control_plane import keychain_status, _keychain_value

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("MCP SDK is required to run the Google MCP server") from exc

mcp = FastMCP("google-read")
RECEIPT_DIR = Path(os.getenv("GOOGLE_MCP_RECEIPT_DIR", str(ROOT / "data/runtime/google_mcp_receipts")))
TOOL_NAMES = (
    "gmail_search", "gmail_read_message", "gmail_read_thread",
    "calendar_search_events", "calendar_read_event", "calendar_get_availability",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _credentials() -> Any:
    if any(keychain_status(CREDENTIAL_ID, part) != "CONFIGURED" for part in ("client_id", "client_secret", "refresh_token")):
        raise RuntimeError("google_refresh_credentials_unavailable")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = Credentials(
        token=None,
        refresh_token=_keychain_value(CREDENTIAL_ID, "refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_keychain_value(CREDENTIAL_ID, "client_id"),
        client_secret=_keychain_value(CREDENTIAL_ID, "client_secret"),
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def _headers(payload: dict[str, Any]) -> dict[str, str]:
    result = {}
    for row in payload.get("headers", []) or []:
        if isinstance(row, dict) and row.get("name") in {"Subject", "From", "To", "Date"}:
            result[str(row["name"]).lower()] = str(row.get("value", ""))[:500]
    return result


def _message_summary(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "internal_date": message.get("internalDate"),
        "label_ids": list(message.get("labelIds") or [])[:20],
        "headers": _headers(message.get("payload") or {}),
        "snippet": str(message.get("snippet") or "")[:500],
        "source": "gmail.users.messages",
    }


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event.get("id"),
        "calendar_id": event.get("organizer", {}).get("email") if isinstance(event.get("organizer"), dict) else None,
        "summary": str(event.get("summary") or "")[:500],
        "status": event.get("status"),
        "start": event.get("start"),
        "end": event.get("end"),
        "updated": event.get("updated"),
        "html_link": event.get("htmlLink"),
        "source": "calendar.events",
    }


def _result(tool: str, *, query: dict[str, Any], items: list[dict[str, Any]], source: str, warnings: list[str] | None = None, error: str | None = None) -> dict[str, Any]:
    payload = {
        "status": "error" if error else "ok",
        "resource": "GMAIL" if tool.startswith("gmail_") else "GOOGLE_CALENDAR",
        "tool": tool,
        "source": source,
        "fetched_at": _now(),
        "currentness": "LIVE_READ",
        "query": query,
        "items": items,
        "item_count": len(items),
        "warnings": warnings or [],
        "error": error,
        "read_only": True,
    }
    receipt = {"request_id": "google-mcp-" + uuid.uuid4().hex, "tool_name": tool, "timestamp": payload["fetched_at"], "source": source, "result_status": payload["status"], "item_count": len(items), "read_only": True}
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    try:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (RECEIPT_DIR / f"{receipt['request_id']}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except OSError:
        payload["warnings"].append("receipt_write_failed")
    payload["request_id"] = receipt["request_id"]
    return payload


def _call(tool: str, query: dict[str, Any], fn: Any, source: str) -> dict[str, Any]:
    try:
        return _result(tool, query=query, items=fn(_credentials()), source=source)
    except Exception as exc:
        return _result(tool, query=query, items=[], source=source, error=f"google_read_unavailable:{type(exc).__name__}")


@mcp.tool(description="VOLATILE Gmail read: search the authorized mailbox. Returns bounded message metadata and snippets; never sends or mutates email.")
def gmail_search(query: str, max_results: int = 10) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 25))
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("gmail", "v1", credentials=creds, cache_discovery=False)
        rows = api.users().messages().list(userId="me", q=str(query)[:500], maxResults=max_results).execute().get("messages", [])
        return [_message_summary(api.users().messages().get(userId="me", id=row["id"], format="metadata", metadataHeaders=["Subject", "From", "To", "Date"]).execute()) for row in rows]
    return _call("gmail_search", {"query": str(query)[:500], "max_results": max_results}, run, "gmail.users.messages.list/get")


@mcp.tool(description="VOLATILE Gmail read: read one message by ID with bounded metadata/snippet only. Never sends, labels, archives, or mutates email.")
def gmail_read_message(message_id: str) -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return [_message_summary(api.users().messages().get(userId="me", id=str(message_id), format="metadata", metadataHeaders=["Subject", "From", "To", "Date"]).execute())]
    return _call("gmail_read_message", {"message_id": str(message_id)[:200]}, run, "gmail.users.messages.get")


@mcp.tool(description="VOLATILE Gmail read: read a thread by ID with bounded message metadata/snippets. Never sends or mutates email.")
def gmail_read_thread(thread_id: str) -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("gmail", "v1", credentials=creds, cache_discovery=False)
        thread = api.users().threads().get(userId="me", id=str(thread_id), format="metadata", metadataHeaders=["Subject", "From", "To", "Date"]).execute()
        return [_message_summary(row) for row in thread.get("messages", [])]
    return _call("gmail_read_thread", {"thread_id": str(thread_id)[:200]}, run, "gmail.users.threads.get")


def _window(value: str, *, end: str | None = None) -> tuple[str, str]:
    start_dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else start_dt + timedelta(days=1)
    if start_dt.tzinfo is None or end_dt.tzinfo is None:
        raise ValueError("calendar timestamps require timezone")
    return start_dt.astimezone(timezone.utc).isoformat(), end_dt.astimezone(timezone.utc).isoformat()


@mcp.tool(description="VOLATILE Calendar read: search events in an explicit timezone-aware time window. Never creates, updates, deletes, or responds to invitations.")
def calendar_search_events(start_time: str, end_time: str, query: str | None = None, max_results: int = 50) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 100))
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        begin, finish = _window(start_time, end=end_time)
        api = build("calendar", "v3", credentials=creds, cache_discovery=False)
        response = api.events().list(calendarId="primary", timeMin=begin, timeMax=finish, q=(str(query)[:200] if query else None), maxResults=max_results, singleEvents=True, orderBy="startTime").execute()
        return [_event_summary(row) for row in response.get("items", [])]
    return _call("calendar_search_events", {"start_time": start_time, "end_time": end_time, "query": query, "max_results": max_results, "timezone": os.getenv("NOVA_TIMEZONE", "system")}, run, "calendar.events.list")


@mcp.tool(description="VOLATILE Calendar read: read one event by ID. Never mutates the event or invitation state.")
def calendar_read_event(event_id: str, calendar_id: str = "primary") -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return [_event_summary(api.events().get(calendarId=str(calendar_id)[:200], eventId=str(event_id)[:200]).execute())]
    return _call("calendar_read_event", {"event_id": str(event_id)[:200], "calendar_id": str(calendar_id)[:200]}, run, "calendar.events.get")


@mcp.tool(description="VOLATILE Calendar read: report busy intervals for a timezone-aware window. Never creates or changes events.")
def calendar_get_availability(start_time: str, end_time: str, calendar_ids: list[str] | None = None) -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        begin, finish = _window(start_time, end=end_time)
        api = build("calendar", "v3", credentials=creds, cache_discovery=False)
        # The existing authorized grant includes calendar.events, but not the
        # broader calendar.freebusy scope. Derive busy intervals from the
        # authorized event-read surface instead of requesting new authority.
        result = []
        for calendar_id in (calendar_ids or ["primary"]):
            response = api.events().list(calendarId=str(calendar_id)[:200], timeMin=begin, timeMax=finish, maxResults=100, singleEvents=True, orderBy="startTime").execute()
            busy = [{"start": row.get("start"), "end": row.get("end"), "event_id": row.get("id")} for row in response.get("items", []) if row.get("status") != "cancelled"]
            result.append({"calendar_id": calendar_id, "busy": busy, "errors": [], "source": "calendar.events.list", "availability_method": "event_read_projection"})
        return result
    return _call("calendar_get_availability", {"start_time": start_time, "end_time": end_time, "calendar_ids": calendar_ids or ["primary"], "timezone": os.getenv("NOVA_TIMEZONE", "system")}, run, "calendar.events.list")


if __name__ == "__main__":
    mcp.run(transport="stdio")
