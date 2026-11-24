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
# r1.2 (Google Core completion): read-only marketing + YouTube tools on the same MCP, same OAuth client
CORE_READ_TOOL_NAMES = (
    "google_get_capabilities",
    "search_console_list_sites", "search_console_query",
    "ga4_list_properties", "ga4_run_report",
    "gbp_list_accounts", "gbp_list_locations", "gbp_list_reviews", "gbp_get_performance",
    "youtube_channel_identity", "youtube_list_videos", "youtube_list_playlists", "youtube_analytics_report",
)
AUTHORITY_TOOL_NAMES = ("google_get_authority",)
WRITE_TOOL_NAMES = ("gmail_create_draft", "gmail_modify_message", "calendar_create_private_event",
                    "calendar_update_event", "drive_create_nexus_file")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


YOUTUBE_CREDENTIAL_ID = "credential.google.youtube.upload.prod.v1"


def _credentials(credential_id: str = CREDENTIAL_ID) -> Any:
    """Refresh-only credentials from the existing Keychain control plane. The OAuth client (id/secret) is always the
    one 'Nexus OS Mac Mini' client stored with the Workspace credential; YouTube has its own refresh token only."""
    if any(keychain_status(CREDENTIAL_ID, part) != "CONFIGURED" for part in ("client_id", "client_secret")) or keychain_status(credential_id, "refresh_token") != "CONFIGURED":
        raise RuntimeError("google_refresh_credentials_unavailable")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = Credentials(
        token=None,
        refresh_token=_keychain_value(credential_id, "refresh_token"),
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
        "resource": _resource(tool),
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
    if tool == "drive_search" and error is None and not items:
        payload["no_results"] = True
        payload["result_note"] = (
            "Search completed successfully with no matching files visible to the current "
            "drive.file authorization. Treat this as a final no-match result; do not repeat "
            "alternate searches unless the user requests them."
        )
    receipt = {"request_id": "google-mcp-" + uuid.uuid4().hex, "tool_name": tool, "timestamp": payload["fetched_at"], "source": source, "result_status": payload["status"], "item_count": len(items), "read_only": True}
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    try:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (RECEIPT_DIR / f"{receipt['request_id']}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except OSError:
        payload["warnings"].append("receipt_write_failed")
    payload["request_id"] = receipt["request_id"]
    return payload


RESOURCE_PREFIXES = (("gmail_", "GMAIL"), ("calendar_", "GOOGLE_CALENDAR"), ("drive_", "GOOGLE_DRIVE"),
                     ("search_console_", "GOOGLE_SEARCH_CONSOLE"), ("ga4_", "GOOGLE_ANALYTICS"),
                     ("gbp_", "GOOGLE_BUSINESS_PROFILE"), ("youtube_", "YOUTUBE_CHANNEL_OAUTH"))


def _resource(tool: str) -> str:
    for prefix, resource in RESOURCE_PREFIXES:
        if tool.startswith(prefix):
            return resource
    return "GOOGLE"


def _error_code(exc: Exception) -> str:
    """google_read_unavailable:<Type>[:HTTP_<status>:<KIND>] — status and a classified reason only (never bodies or tokens)."""
    status = getattr(getattr(exc, "resp", None), "status", None) or getattr(getattr(exc, "response", None), "status_code", None)
    if not status:
        return f"google_read_unavailable:{type(exc).__name__}"
    from nexus_agent_platform.google_workspace import classify_google_error
    return f"google_read_unavailable:{type(exc).__name__}:HTTP_{status}:{classify_google_error(exc)['status']}"


def _call(tool: str, query: dict[str, Any], fn: Any, source: str, credential_id: str | None = None, validate: Any = None) -> dict[str, Any]:
    if validate is not None:
        try:
            validate()  # argument allowlists are checked before any credential or network use
        except ValueError as exc:
            return _result(tool, query=query, items=[], source=source, error=f"invalid_request:{str(exc)[:160]}")
    try:
        creds = _credentials() if credential_id is None else _credentials(credential_id)
        return _result(tool, query=query, items=fn(creds), source=source)
    except ValueError as exc:
        # argument validation (allowlisted dimensions / metrics / dates): not a Google failure
        return _result(tool, query=query, items=[], source=source, error=f"invalid_request:{str(exc)[:160]}")
    except Exception as exc:
        return _result(tool, query=query, items=[], source=source, error=_error_code(exc))


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


@mcp.tool(description="READ ONLY Google Drive search of accessible file metadata. Searches names and returns bounded metadata only. Access is limited to app-created or user-selected files visible to the current drive.file authorization. An empty successful result (item_count=0) is a final no-match, not an error; do not retry alternate searches unless the user requests it. Never uploads, edits, moves, shares, or deletes files.")
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


# ---------------------------------------------------------------------------------------------------------------
# r1.2 Google Core completion: READ-ONLY Search Console, GA4, Business Profile and YouTube tools.
# Same MCP, same OAuth client, same Keychain control plane. No create / update / delete / publish / reply tool is
# registered for any of these services; write capabilities are only DECLARED (approval-gated, not implemented here).
# ---------------------------------------------------------------------------------------------------------------
import re as _re
from datetime import date as _date

GSC_DIMENSIONS = {"date", "query", "page", "country", "device", "searchAppearance"}
GSC_SEARCH_TYPES = {"web", "image", "video", "news", "discover", "googleNews"}
GA4_METRICS = {"totalUsers", "activeUsers", "newUsers", "sessions", "engagedSessions", "engagementRate", "keyEvents",
               "conversions", "screenPageViews", "averageSessionDuration", "bounceRate", "eventCount"}
GA4_DIMENSIONS = {"date", "sessionSourceMedium", "sessionSource", "sessionMedium", "sessionCampaignName",
                  "sessionDefaultChannelGroup", "landingPage", "landingPagePlusQueryString", "pagePath", "pageTitle",
                  "country", "deviceCategory", "firstUserSourceMedium", "eventName"}
GBP_DAILY_METRICS = {"BUSINESS_IMPRESSIONS_DESKTOP_MAPS", "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
                     "BUSINESS_IMPRESSIONS_MOBILE_SEARCH", "BUSINESS_CONVERSATIONS", "BUSINESS_DIRECTION_REQUESTS",
                     "CALL_CLICKS", "WEBSITE_CLICKS", "BUSINESS_BOOKINGS", "BUSINESS_FOOD_ORDERS"}
YT_METRICS = {"views", "estimatedMinutesWatched", "averageViewDuration", "likes", "comments", "shares",
              "subscribersGained", "subscribersLost"}
YT_DIMENSIONS = {"day", "month", "video", "country", "insightTrafficSourceType", "deviceType"}
_ISO_DAY = _re.compile(r"^\d{4}-\d{2}-\d{2}$")

# write capabilities that exist in Google's APIs but are deliberately NOT tools here (each needs Ray's approval and a
# separate governed implementation)
DECLARED_GATED_WRITES = {
    "search_console": [],
    "ga4": [],
    "business_profile": ["local_post_create", "business_information_update", "review_reply"],
    "youtube": ["video_upload (OS2 youtube_upload, per-video approval)", "video_metadata_update", "comment_reply"],
}


def _days(start_date: str, end_date: str) -> tuple[str, str]:
    if not (_ISO_DAY.match(str(start_date)) and _ISO_DAY.match(str(end_date))):
        raise ValueError("dates_must_be_YYYY-MM-DD")
    if str(start_date) > str(end_date):
        raise ValueError("start_date_after_end_date")
    return str(start_date), str(end_date)


def _only(values: list[str] | None, allowed: set[str], default: list[str], what: str) -> list[str]:
    vals = [str(v) for v in (values or default)]
    bad = [v for v in vals if v not in allowed]
    if bad:
        raise ValueError(f"{what}_not_allowlisted:{','.join(bad)[:120]}")
    return vals


def _bearer_get(creds: Any, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    import requests
    r = requests.get(url, params=params or {}, headers={"Authorization": f"Bearer {creds.token}"}, timeout=20)
    if r.status_code >= 400:
        err = requests.HTTPError(f"HTTP {r.status_code}")
        err.response = r  # type: ignore[attr-defined]
        raise err
    return r.json()


@mcp.tool(description="READ ONLY: what this Google MCP can do per service (tools, scopes, credential grant, declared-but-not-implemented gated writes). No network call; never returns credentials.")
def google_get_capabilities() -> dict[str, Any]:
    from nexus_agent_platform import google_scopes as gs
    services = {}
    for svc, spec in gs.SERVICES.items():
        prefix = {"gmail": "gmail_", "calendar": "calendar_", "drive": "drive_", "search_console": "search_console_", "ga4": "ga4_", "business_profile": "gbp_", "youtube": "youtube_"}[svc]
        services[svc] = {
            "read_tools": [t for t in TOOL_NAMES + CORE_READ_TOOL_NAMES if t.startswith(prefix)],
            "governed_write_tools": [t for t in WRITE_TOOL_NAMES if t.startswith(prefix)],
            "declared_gated_writes_not_implemented": DECLARED_GATED_WRITES.get(svc, []),
            "scopes": [gs.name(x) for x in spec["scopes"]], "credential_id": gs.CREDENTIALS[spec["credential"]],
            "consent_profile": "youtube" if spec["credential"] == "youtube" else "core", "apis": gs.APIS.get(svc, []), "note": spec["note"],
        }
    item = {"oauth_client": "Nexus OS Mac Mini (Desktop; existing)", "consent_profiles": {k: [gs.name(x) for x in gs.profile_scopes(k)] for k in gs.PROFILES},
            "services": services, "secret_values_exposed": False}
    return _result("google_get_capabilities", query={}, items=[item], source="static:google_scopes")


@mcp.tool(description="READ ONLY Search Console: list the sites/properties the authorized account can access, with its permission level on each. Never adds, verifies or removes properties.")
def search_console_list_sites() -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        return [{"site_url": r.get("siteUrl"), "permission_level": r.get("permissionLevel"), "source": "searchconsole.sites"}
                for r in api.sites().list().execute().get("siteEntry", []) or []][:100]
    return _call("search_console_list_sites", {}, run, "searchconsole.sites.list")


@mcp.tool(description="READ ONLY Search Console analytics: clicks, impressions, CTR and position for one property over a date range, grouped by allowlisted dimensions (date, query, page, country, device, searchAppearance). Never mutates Search Console.")
def search_console_query(site_url: str, start_date: str, end_date: str, dimensions: list[str] | None = None,
                         row_limit: int = 100, search_type: str = "web") -> dict[str, Any]:
    row_limit = max(1, min(int(row_limit), 1000))
    query = {"site_url": str(site_url)[:300], "start_date": start_date, "end_date": end_date, "dimensions": dimensions or ["date"], "row_limit": row_limit, "search_type": search_type}
    def check() -> tuple[str, str, list[str]]:
        start, end = _days(start_date, end_date)
        dims = _only(dimensions, GSC_DIMENSIONS, ["date"], "dimension")
        if search_type not in GSC_SEARCH_TYPES:
            raise ValueError("search_type_not_allowlisted")
        return start, end, dims
    def run(creds: Any) -> list[dict[str, Any]]:
        start, end, dims = check()
        from googleapiclient.discovery import build
        api = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        body = {"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": row_limit, "type": search_type}
        rows = api.searchanalytics().query(siteUrl=str(site_url)[:300], body=body).execute().get("rows", []) or []
        return [{"keys": dict(zip(dims, r.get("keys") or [])), "clicks": r.get("clicks"), "impressions": r.get("impressions"),
                 "ctr": r.get("ctr"), "position": r.get("position")} for r in rows]
    return _call("search_console_query", query, run, "searchconsole.searchanalytics.query", validate=check)


@mcp.tool(description="READ ONLY GA4: list accessible Analytics accounts and their GA4 properties (property ids). Never creates or edits properties, streams or events.")
def ga4_list_properties() -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)
        out: list[dict[str, Any]] = []
        for a in api.accountSummaries().list(pageSize=200).execute().get("accountSummaries", []) or []:
            for p in a.get("propertySummaries") or []:
                out.append({"property": p.get("property"), "property_id": str(p.get("property") or "").split("/")[-1],
                            "display_name": p.get("displayName"), "property_type": p.get("propertyType"),
                            "account": a.get("account"), "account_name": a.get("displayName"), "source": "analyticsadmin.accountSummaries"})
        return out[:200]
    return _call("ga4_list_properties", {}, run, "analyticsadmin.accountSummaries.list")


@mcp.tool(description="READ ONLY GA4 report (Data API runReport) for one property: allowlisted metrics (users, sessions, engagedSessions, keyEvents/conversions, ...) by allowlisted dimensions (date, source/medium, campaign, landing page, page path, ...). Never mutates GA4.")
def ga4_run_report(property_id: str, start_date: str, end_date: str, metrics: list[str] | None = None,
                   dimensions: list[str] | None = None, limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    pid = str(property_id).split("/")[-1][:40]
    query = {"property_id": pid, "start_date": start_date, "end_date": end_date, "metrics": metrics or ["totalUsers", "sessions"], "dimensions": dimensions or ["date"], "limit": limit}
    def check() -> tuple[str, str, list[str], list[str]]:
        if not pid.isdigit():
            raise ValueError("property_id_must_be_numeric")
        start, end = _days(start_date, end_date)
        return start, end, _only(metrics, GA4_METRICS, ["totalUsers", "sessions"], "metric"), _only(dimensions, GA4_DIMENSIONS, ["date"], "dimension")
    def run(creds: Any) -> list[dict[str, Any]]:
        start, end, mets, dims = check()
        from googleapiclient.discovery import build
        api = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
        body = {"dateRanges": [{"startDate": start, "endDate": end}], "metrics": [{"name": m} for m in mets],
                "dimensions": [{"name": d} for d in dims], "limit": limit}
        resp = api.properties().runReport(property=f"properties/{pid}", body=body).execute()
        return [{"dimensions": dict(zip(dims, [v.get("value") for v in r.get("dimensionValues") or []])),
                 "metrics": dict(zip(mets, [v.get("value") for v in r.get("metricValues") or []]))} for r in resp.get("rows", []) or []]
    return _call("ga4_run_report", query, run, "analyticsdata.properties.runReport", validate=check)


@mcp.tool(description="READ ONLY Business Profile: list accessible accounts. Requires Google-approved Business Profile API access for the Cloud project. Never edits anything.")
def gbp_list_accounts() -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        from googleapiclient.discovery import build
        api = build("mybusinessaccountmanagement", "v1", credentials=creds, cache_discovery=False)
        return [{"name": a.get("name"), "account_name": a.get("accountName"), "type": a.get("type"), "role": a.get("role"),
                 "verification_state": a.get("verificationState"), "source": "mybusinessaccountmanagement.accounts"}
                for a in api.accounts().list(pageSize=20).execute().get("accounts", []) or []]
    return _call("gbp_list_accounts", {}, run, "mybusinessaccountmanagement.accounts.list")


@mcp.tool(description="READ ONLY Business Profile: list locations (business identity: title, address, phone, website, categories) for one account (accounts/<id>). Never edits business information.")
def gbp_list_locations(account: str) -> dict[str, Any]:
    acct = str(account)[:80]
    def check() -> None:
        if not acct.startswith("accounts/"):
            raise ValueError("account_must_be_accounts/<id>")
    def run(creds: Any) -> list[dict[str, Any]]:
        check()
        from googleapiclient.discovery import build
        api = build("mybusinessbusinessinformation", "v1", credentials=creds, cache_discovery=False)
        mask = "name,title,storefrontAddress,phoneNumbers,websiteUri,categories,openInfo,metadata"
        rows = api.accounts().locations().list(parent=acct, readMask=mask, pageSize=100).execute().get("locations", []) or []
        return [{"name": r.get("name"), "title": r.get("title"), "address": r.get("storefrontAddress"),
                 "primary_phone": (r.get("phoneNumbers") or {}).get("primaryPhone"), "website": r.get("websiteUri"),
                 "primary_category": ((r.get("categories") or {}).get("primaryCategory") or {}).get("displayName"),
                 "open_status": (r.get("openInfo") or {}).get("status"), "maps_uri": (r.get("metadata") or {}).get("mapsUri"),
                 "source": "mybusinessbusinessinformation.locations"} for r in rows]
    return _call("gbp_list_locations", {"account": acct}, run, "mybusinessbusinessinformation.accounts.locations.list", validate=check)


@mcp.tool(description="READ ONLY Business Profile reviews for one location (accounts/<id>/locations/<id>): rating, bounded comment, whether a reply exists. Never replies to or deletes reviews (review replies are approval-gated and not implemented).")
def gbp_list_reviews(account: str, location: str, max_results: int = 50) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 50))
    acct, loc = str(account)[:80], str(location)[:120]
    def check() -> None:
        if not acct.startswith("accounts/") or not loc.split("/")[-1].isdigit():
            raise ValueError("account_and_location_ids_required")
    def run(creds: Any) -> list[dict[str, Any]]:
        check()
        loc_id = loc.split("/")[-1]
        data = _bearer_get(creds, f"https://mybusiness.googleapis.com/v4/{acct}/locations/{loc_id}/reviews", {"pageSize": max_results})
        out = [{"review_id": r.get("reviewId"), "star_rating": r.get("starRating"), "comment": str(r.get("comment") or "")[:500],
                "create_time": r.get("createTime"), "has_reply": bool(r.get("reviewReply")), "reviewer": (r.get("reviewer") or {}).get("displayName"),
                "source": "mybusiness.v4.reviews"} for r in data.get("reviews", []) or []]
        if out:
            out[0]["average_rating"] = data.get("averageRating"); out[0]["total_review_count"] = data.get("totalReviewCount")
        return out
    return _call("gbp_list_reviews", {"account": acct, "location": loc, "max_results": max_results}, run, "mybusiness.v4.accounts.locations.reviews.list", validate=check)


@mcp.tool(description="READ ONLY Business Profile performance: daily metric time series (impressions, calls, website clicks, direction requests, ...) for one location (locations/<id>). Never mutates.")
def gbp_get_performance(location: str, start_date: str, end_date: str, metrics: list[str] | None = None) -> dict[str, Any]:
    loc = str(location)[:120]
    query = {"location": loc, "start_date": start_date, "end_date": end_date, "metrics": metrics or ["WEBSITE_CLICKS", "CALL_CLICKS"]}
    def check() -> tuple[str, str, list[str], str]:
        start, end = _days(start_date, end_date)
        mets = _only(metrics, GBP_DAILY_METRICS, ["WEBSITE_CLICKS", "CALL_CLICKS"], "metric")
        loc_id = loc.split("/")[-1]
        if not loc_id.isdigit():
            raise ValueError("location_must_be_locations/<id>")
        return start, end, mets, loc_id
    def run(creds: Any) -> list[dict[str, Any]]:
        start, end, mets, loc_id = check()
        s, e = _date.fromisoformat(start), _date.fromisoformat(end)
        params = [("dailyMetrics", m) for m in mets] + [("dailyRange.startDate.year", s.year), ("dailyRange.startDate.month", s.month), ("dailyRange.startDate.day", s.day),
                                                         ("dailyRange.endDate.year", e.year), ("dailyRange.endDate.month", e.month), ("dailyRange.endDate.day", e.day)]
        data = _bearer_get(creds, f"https://businessprofileperformance.googleapis.com/v1/locations/{loc_id}:fetchMultiDailyMetricsTimeSeries", params)  # type: ignore[arg-type]
        out = []
        for multi in data.get("multiDailyMetricTimeSeries", []) or []:
            for series in multi.get("dailyMetricTimeSeries", []) or []:
                points = ((series.get("timeSeries") or {}).get("datedValues")) or []
                out.append({"metric": series.get("dailyMetric"), "total": sum(int(p.get("value") or 0) for p in points), "days": len(points)})
        return out
    return _call("gbp_get_performance", query, run, "businessprofileperformance.locations.fetchMultiDailyMetricsTimeSeries", validate=check)


def _yt(creds: Any) -> Any:
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


@mcp.tool(description="READ ONLY YouTube (owned channel grant): authenticated channel identity and metadata (id, title, handle, subscriber/video counts, uploads playlist). Never uploads or edits.")
def youtube_channel_identity() -> dict[str, Any]:
    def run(creds: Any) -> list[dict[str, Any]]:
        rows = _yt(creds).channels().list(part="snippet,contentDetails,statistics,status", mine=True).execute().get("items", []) or []
        return [{"channel_id": r.get("id"), "title": (r.get("snippet") or {}).get("title"), "handle": (r.get("snippet") or {}).get("customUrl"),
                 "published_at": (r.get("snippet") or {}).get("publishedAt"), "privacy_status": (r.get("status") or {}).get("privacyStatus"),
                 "subscriber_count": (r.get("statistics") or {}).get("subscriberCount"), "video_count": (r.get("statistics") or {}).get("videoCount"),
                 "view_count": (r.get("statistics") or {}).get("viewCount"),
                 "uploads_playlist": ((r.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads"), "source": "youtube.channels"} for r in rows]
    return _call("youtube_channel_identity", {}, run, "youtube.channels.list(mine)", credential_id=YOUTUBE_CREDENTIAL_ID)


@mcp.tool(description="READ ONLY YouTube: recent videos of the authenticated channel (uploads playlist) with bounded metadata and public stats. Never uploads, edits or deletes.")
def youtube_list_videos(max_results: int = 25) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 50))
    def run(creds: Any) -> list[dict[str, Any]]:
        yt = _yt(creds)
        chans = yt.channels().list(part="contentDetails", mine=True).execute().get("items", []) or []
        uploads = ((chans[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads") if chans else None
        if not uploads:
            return []
        ids = [((r.get("contentDetails") or {}).get("videoId")) for r in yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=max_results).execute().get("items", []) or []]
        ids = [i for i in ids if i]
        if not ids:
            return []
        vids = yt.videos().list(part="snippet,statistics,status,contentDetails", id=",".join(ids)).execute().get("items", []) or []
        return [{"video_id": v.get("id"), "title": str((v.get("snippet") or {}).get("title") or "")[:200], "published_at": (v.get("snippet") or {}).get("publishedAt"),
                 "privacy_status": (v.get("status") or {}).get("privacyStatus"), "duration": (v.get("contentDetails") or {}).get("duration"),
                 "caption_available": (v.get("contentDetails") or {}).get("caption"),
                 "views": (v.get("statistics") or {}).get("viewCount"), "likes": (v.get("statistics") or {}).get("likeCount"),
                 "comments": (v.get("statistics") or {}).get("commentCount"), "source": "youtube.videos"} for v in vids]
    return _call("youtube_list_videos", {"max_results": max_results}, run, "youtube.playlistItems+videos.list", credential_id=YOUTUBE_CREDENTIAL_ID)


@mcp.tool(description="READ ONLY YouTube: playlists of the authenticated channel. Never creates or edits playlists.")
def youtube_list_playlists(max_results: int = 25) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 50))
    def run(creds: Any) -> list[dict[str, Any]]:
        rows = _yt(creds).playlists().list(part="snippet,contentDetails,status", mine=True, maxResults=max_results).execute().get("items", []) or []
        return [{"playlist_id": r.get("id"), "title": str((r.get("snippet") or {}).get("title") or "")[:200], "item_count": (r.get("contentDetails") or {}).get("itemCount"),
                 "privacy_status": (r.get("status") or {}).get("privacyStatus"), "source": "youtube.playlists"} for r in rows]
    return _call("youtube_list_playlists", {"max_results": max_results}, run, "youtube.playlists.list(mine)", credential_id=YOUTUBE_CREDENTIAL_ID)


@mcp.tool(description="READ ONLY YouTube Analytics for the authenticated channel: allowlisted metrics (views, watch time, likes, subscribers gained, ...) by allowlisted dimensions (day, month, video, country, traffic source, device). Needs yt-analytics.readonly. Never mutates.")
def youtube_analytics_report(start_date: str, end_date: str, metrics: list[str] | None = None, dimensions: list[str] | None = None,
                             max_results: int = 100) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 200))
    query = {"start_date": start_date, "end_date": end_date, "metrics": metrics or ["views"], "dimensions": dimensions or ["day"], "max_results": max_results}
    def check() -> tuple[str, str, list[str], list[str]]:
        start, end = _days(start_date, end_date)
        return start, end, _only(metrics, YT_METRICS, ["views"], "metric"), _only(dimensions, YT_DIMENSIONS, ["day"], "dimension")
    def run(creds: Any) -> list[dict[str, Any]]:
        start, end, mets, dims = check()
        from googleapiclient.discovery import build
        api = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        resp = api.reports().query(ids="channel==MINE", startDate=start, endDate=end, metrics=",".join(mets), dimensions=",".join(dims),
                                   maxResults=max_results, **({"sort": "-" + mets[0]} if "video" in dims else {})).execute()
        cols = [h.get("name") for h in resp.get("columnHeaders", []) or []]
        return [dict(zip(cols, row)) for row in resp.get("rows", []) or []]
    return _call("youtube_analytics_report", query, run, "youtubeAnalytics.reports.query", credential_id=YOUTUBE_CREDENTIAL_ID, validate=check)


if __name__ == "__main__":
    mcp.run(transport="stdio")
