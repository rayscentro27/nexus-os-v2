"""Local stdio MCP server for governed Google Workspace access.

MCP is an interface only. OAuth credentials remain in the existing Nexus
keychain control plane. Only bounded, auditable, reversible mutations are
registered; external send, sharing, and deletion methods are intentionally absent.
"""
from __future__ import annotations

import hashlib
import base64
from email.message import EmailMessage
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

from nexus_agent_platform.google_workspace import CREDENTIAL_ID
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
    "drive_search", "drive_read_file",
)
WRITE_TOOL_NAMES = ("gmail_create_draft", "gmail_modify_message", "calendar_create_private_event",
                    "calendar_update_event", "drive_create_nexus_file")


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
        "resource": ("GMAIL" if tool.startswith("gmail_") else
                     "GOOGLE_CALENDAR" if tool.startswith("calendar_") else
                     "GOOGLE_DRIVE"),
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


def _mutation_result(tool: str, *, resource: str, item: dict[str, Any] | None = None,
                     error: str | None = None, scope: str | None = None,
                     request_id: str | None = None) -> dict[str, Any]:
    """Persist a minimal receipt for an explicit reversible Google mutation."""
    now = _now()
    receipt = {"request_id": request_id or "google-mcp-" + uuid.uuid4().hex, "tool_name": tool,
               "timestamp": now, "resource": resource,
               "result_status": "error" if error else "ok", "item_id": (item or {}).get("id"),
               "required_scope": scope, "external_action": False, "content_recorded": False}
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    try:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (RECEIPT_DIR / f"{receipt['request_id']}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return {"status": "error", "error": "mutation_receipt_persistence_failed_after_execution",
                "mutation_performed": bool(item), "outcome_uncertain": True,
                "request_id": receipt["request_id"]}
    return {"status": "error" if error else "ok", "resource": resource, "tool": tool,
            "item": item, "error": error, "required_scope": scope,
            "mutation_performed": bool(item and not error), "request_id": receipt["request_id"],
            "receipt_hash": receipt["receipt_hash"], "read_only": False}


def _write_call(tool: str, resource: str, scope: str | None, operation: Any) -> dict[str, Any]:
    request_id = "google-mcp-" + uuid.uuid4().hex
    try:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        provisional = {"request_id": request_id, "tool_name": tool, "timestamp": _now(),
                       "resource": resource, "result_status": "STARTED",
                       "required_scope": scope, "external_action": False,
                       "content_recorded": False}
        provisional["receipt_hash"] = hashlib.sha256(json.dumps(provisional, sort_keys=True).encode()).hexdigest()
        (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps(provisional, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return {"status": "error", "error": "mutation_receipt_persistence_failed_before_execution",
                "mutation_performed": False}
    try:
        item = operation(_credentials())
        return _mutation_result(tool, resource=resource, item=item, scope=scope, request_id=request_id)
    except Exception as exc:
        # Google API errors are deliberately reduced to status/code. Never emit
        # request headers, refresh tokens, message bodies, or credential data.
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status == 403 and scope:
            error = f"GOOGLE_WRITE_SCOPE_MISSING:{scope}"
        else:
            error = f"google_write_unavailable:{type(exc).__name__}:HTTP_{status}" if status else f"google_write_unavailable:{type(exc).__name__}"
        return _mutation_result(tool, resource=resource, error=error, scope=scope, request_id=request_id)


@mcp.tool(description="READ ONLY Google authorization inspection. Returns granted OAuth scope names and capability implications; never returns tokens or credentials.")
def google_get_authority() -> dict[str, Any]:
    try:
        creds = _credentials()
        import requests
        response = requests.get("https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": creds.token}, timeout=12)
        response.raise_for_status()
        scope_urls = str(response.json().get("scope") or "").split()
        scopes = sorted({scope.rsplit("/", 1)[-1] for scope in scope_urls})
        authority = {"authorization_state": "AUTHORIZED",
                "granted_scope_names": scopes,
                "gmail_read": "gmail.readonly" in scopes or "gmail.modify" in scopes,
                "gmail_write": "gmail.modify" in scopes,
                "calendar_read": "calendar.events" in scopes,
                "calendar_write": "calendar.events" in scopes,
                "drive_access": "drive.file" in scopes,
                "drive_boundary": "app-created or user-selected files only" if "drive.file" in scopes else "UNKNOWN",
                "read_only": True, "secret_values_exposed": False}
        return _result("google_get_authority", query={}, items=[authority], source="oauth2.tokeninfo")
    except Exception as exc:
        return _result("google_get_authority", query={}, items=[], source="oauth2.tokeninfo",
                       error=f"google_authority_unavailable:{type(exc).__name__}")


@mcp.tool(description="GOVERNED Gmail write: create an unsent draft addressed only to the authenticated mailbox owner. Never sends email. Requires gmail.modify authorization.")
def gmail_create_draft(subject: str, body: str, to_self: bool = True) -> dict[str, Any]:
    scope = "https://www.googleapis.com/auth/gmail.modify"
    if not to_self:
        return _mutation_result("gmail_create_draft", resource="GMAIL", error="draft_recipient_must_be_owner", scope=scope)
    def run(creds: Any) -> dict[str, Any]:
        from googleapiclient.discovery import build
        api = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = api.users().getProfile(userId="me").execute()
        owner = str(profile.get("emailAddress") or "").strip()
        if not owner:
            raise RuntimeError("gmail_owner_identity_unavailable")
        message = EmailMessage()
        message["To"] = owner
        message["Subject"] = str(subject)[:200]
        message.set_content(str(body)[:20000])
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        draft = api.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"id": draft.get("id"), "message_id": (draft.get("message") or {}).get("id"), "recipient": "SELF"}
    return _write_call("gmail_create_draft", "GMAIL", scope, run)


@mcp.tool(description="GOVERNED Gmail organizational mutation: archive or mark a message read/unread. No send, forward, delete, or external communication. Requires gmail.modify authorization.")
def gmail_modify_message(message_id: str, operation: str) -> dict[str, Any]:
    allowed = {"ARCHIVE", "MARK_READ", "MARK_UNREAD"}
    action = str(operation or "").strip().upper()
    scope = "https://www.googleapis.com/auth/gmail.modify"
    if action not in allowed:
        return _mutation_result("gmail_modify_message", resource="GMAIL", error="operation_not_allowlisted", scope=scope)
    def run(creds: Any) -> dict[str, Any]:
        from googleapiclient.discovery import build
        api = build("gmail", "v1", credentials=creds, cache_discovery=False)
        body = {"removeLabelIds": ["INBOX"]} if action == "ARCHIVE" else (
            {"removeLabelIds": ["UNREAD"]} if action == "MARK_READ" else {"addLabelIds": ["UNREAD"]})
        result = api.users().messages().modify(userId="me", id=str(message_id)[:200], body=body).execute()
        return {"id": result.get("id"), "operation": action}
    return _write_call("gmail_modify_message", "GMAIL", scope, run)


@mcp.tool(description="GOVERNED Calendar write: create a private event with no guests or external invitations. Requires explicit owner-provided timezone-aware start/end.")
def calendar_create_private_event(title: str, start_time: str, end_time: str,
                                  description: str = "", location: str = "") -> dict[str, Any]:
    scope = "https://www.googleapis.com/auth/calendar.events"
    def run(creds: Any) -> dict[str, Any]:
        from googleapiclient.discovery import build
        begin, finish = _window(start_time, end=end_time)
        api = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = {"summary": str(title)[:200], "description": str(description)[:4000],
                 "location": str(location)[:500], "start": {"dateTime": begin},
                 "end": {"dateTime": finish}, "visibility": "private"}
        created = api.events().insert(calendarId="primary", body=event, sendUpdates="none").execute()
        return {"id": created.get("id"), "summary": created.get("summary"), "start": created.get("start"), "end": created.get("end"), "visibility": created.get("visibility"), "attendees": []}
    return _write_call("calendar_create_private_event", "GOOGLE_CALENDAR", scope, run)


@mcp.tool(description="GOVERNED Calendar write: update the title, description, location, or timezone-aware start/end of one exact event. Does not add guests or delete events.")
def calendar_update_event(event_id: str, title: str | None = None, description: str | None = None,
                          location: str | None = None, start_time: str | None = None,
                          end_time: str | None = None) -> dict[str, Any]:
    scope = "https://www.googleapis.com/auth/calendar.events"
    def run(creds: Any) -> dict[str, Any]:
        from googleapiclient.discovery import build
        api = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = api.events().get(calendarId="primary", eventId=str(event_id)[:200]).execute()
        patch: dict[str, Any] = {}
        if title is not None: patch["summary"] = str(title)[:200]
        if description is not None: patch["description"] = str(description)[:4000]
        if location is not None: patch["location"] = str(location)[:500]
        if start_time is not None: patch["start"] = {"dateTime": _window(start_time)[0]}
        if end_time is not None: patch["end"] = {"dateTime": _window(end_time)[0]}
        if not patch:
            raise ValueError("at_least_one_event_field_required")
        updated = api.events().patch(calendarId="primary", eventId=str(event_id)[:200], body=patch, sendUpdates="none").execute()
        return {"id": updated.get("id"), "summary": updated.get("summary"), "start": updated.get("start"), "end": updated.get("end")}
    return _write_call("calendar_update_event", "GOOGLE_CALENDAR", scope, run)


@mcp.tool(description="GOVERNED Drive write: create a Nexus-owned text artifact inside the configured approved folder. Scope is limited to drive.file; no sharing or delete operations are exposed.")
def drive_create_nexus_file(name: str, content: str, mime_type: str = "text/plain") -> dict[str, Any]:
    scope = "https://www.googleapis.com/auth/drive.file"
    folder_id = os.getenv("NEXUS_GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        return _mutation_result("drive_create_nexus_file", resource="GOOGLE_DRIVE", error="APPROVED_DRIVE_FOLDER_NOT_CONFIGURED", scope=scope)
    if mime_type not in {"text/plain", "text/markdown", "text/csv"}:
        return _mutation_result("drive_create_nexus_file", resource="GOOGLE_DRIVE", error="mime_type_not_allowlisted", scope=scope)
    def run(creds: Any) -> dict[str, Any]:
        from googleapiclient.discovery import build
        api = build("drive", "v3", credentials=creds, cache_discovery=False)
        metadata = {"name": str(name)[:200], "mimeType": mime_type, "parents": [folder_id]}
        created = api.files().create(body=metadata, media_body=__import__("googleapiclient.http", fromlist=["MediaInMemoryUpload"]).MediaInMemoryUpload(str(content)[:50000].encode("utf-8"), mimetype=mime_type), fields="id,name,mimeType,webViewLink,parents").execute()
        return {"id": created.get("id"), "name": created.get("name"), "mime_type": created.get("mimeType"), "web_view_link": created.get("webViewLink")}
    return _write_call("drive_create_nexus_file", "GOOGLE_DRIVE", scope, run)


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


def _file_summary(file: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": file.get("id"),
        "name": str(file.get("name") or "")[:500],
        "mime_type": file.get("mimeType"),
        "modified_time": file.get("modifiedTime"),
        "created_time": file.get("createdTime"),
        "web_view_link": file.get("webViewLink"),
        "size": file.get("size"),
        "owners": [{"display_name": row.get("displayName"), "email": row.get("emailAddress")}
                   for row in (file.get("owners") or []) if isinstance(row, dict)][:5],
        "source": "drive.files",
    }


@mcp.tool(description="VOLATILE Drive read: search accessible file metadata. Never uploads, edits, moves, shares, or deletes files.")
def drive_search(query: str | None = None, max_results: int = 25) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 50))
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("drive", "v3", credentials=creds, cache_discovery=False)
        q = str(query or "").strip()[:500]
        if q and "'" not in q:
            escaped = q.replace("\\", "\\\\").replace("'", "\\'")
            q = f"name contains '{escaped}' and trashed = false"
        else:
            q = "trashed = false"
        response = api.files().list(
            q=q, pageSize=max_results,
            fields="files(id,name,mimeType,modifiedTime,createdTime,webViewLink,size,owners(displayName,emailAddress))",
            orderBy="modifiedTime desc",
        ).execute()
        return [_file_summary(row) for row in response.get("files", [])]
    return _call("drive_search", {"query": str(query or "")[:500], "max_results": max_results}, run, "drive.files.list")


@mcp.tool(description="VOLATILE Drive read: read bounded metadata and text content for one accessible file when the current grant permits it. Never mutates files.")
def drive_read_file(file_id: str, include_text: bool = False) -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("drive", "v3", credentials=creds, cache_discovery=False)
        file = api.files().get(fileId=str(file_id)[:200], fields="id,name,mimeType,modifiedTime,createdTime,webViewLink,size,owners(displayName,emailAddress)").execute()
        item = _file_summary(file)
        # Content is opt-in and bounded.  Export is restricted to text-like
        # Google documents; binary downloads are never attempted here.
        if include_text and file.get("mimeType") in {"application/vnd.google-apps.document", "text/plain", "text/markdown", "text/csv"}:
            if file.get("mimeType") == "application/vnd.google-apps.document":
                response = api.files().export(fileId=str(file_id)[:200], mimeType="text/plain").execute()
            else:
                response = api.files().get_media(fileId=str(file_id)[:200]).execute()
            item["text_excerpt"] = (response.decode("utf-8", errors="replace") if isinstance(response, bytes) else str(response))[:2000]
        return [item]
    return _call("drive_read_file", {"file_id": str(file_id)[:200], "include_text": bool(include_text)}, run, "drive.files.get/export")


if __name__ == "__main__":
    mcp.run(transport="stdio")
