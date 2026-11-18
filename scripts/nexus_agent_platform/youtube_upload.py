"""Nexus OS v2 — Dedicated YouTube Upload OAuth & Channel Certification.

Architecture (Scope Separation):
Google prohibits combining Google Drive/Workspace scopes with YouTube upload scopes
in a single OAuth grant. This module authorizes a dedicated, isolated OAuth grant
for YouTube publishing (credential.google.youtube.upload.prod.v1) using the existing
'Nexus OS Mac Mini' Desktop client while preserving the working Google Workspace grant
(credential.google.workspace.prod.v1).
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.parse, urllib.request, ssl
from pathlib import Path
from typing import Any, List, Optional

# Remove local directory shadowing platform stdlib
_SCRIPT_PACKAGE_DIR = Path(__file__).resolve().parent
for _p in tuple(sys.path):
    try:
        if Path(_p or os.getcwd()).resolve() == _SCRIPT_PACKAGE_DIR:
            sys.path.remove(_p)
    except (OSError, RuntimeError):
        continue

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_CREDENTIAL_ID = "credential.google.workspace.prod.v1"
YOUTUBE_CREDENTIAL_ID = "credential.google.youtube.upload.prod.v1"

# YouTube-ONLY scopes. Strictly NO Workspace, Drive, Gmail, or Calendar scopes.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_SCOPES = [YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE]
YOUTUBE_SCOPE_NAMES = ["youtube.upload", "youtube.readonly"]

PROHIBITED_SCOPE_KEYWORDS = ("drive", "gmail", "calendar", "mail.google.com")

from nexus_agent_platform.credential_control_plane import (
    keychain_status,
    store_keychain,
    _keychain_value,
    registry_entry,
)


def _validate_youtube_scopes(scopes: List[str]) -> None:
    """Enforce strict scope separation: reject any Workspace or Drive scope."""
    for s in scopes:
        s_lower = s.lower()
        if any(keyword in s_lower for keyword in PROHIBITED_SCOPE_KEYWORDS):
            raise ValueError(
                f"SCOPE_SEPARATION_VIOLATION: Scope '{s}' belongs to Google Workspace/Drive "
                f"and is strictly prohibited in the YouTube publishing grant."
            )


def _get_oauth_client() -> dict[str, str]:
    """Reuse existing 'Nexus OS Mac Mini' Desktop OAuth client without creating a new one."""
    client_id = os.environ.get("NEXUS_GOOGLE_WORKSPACE_CLIENT_ID") or _keychain_value(
        WORKSPACE_CREDENTIAL_ID, "client_id"
    )
    client_secret = os.environ.get("NEXUS_GOOGLE_WORKSPACE_CLIENT_SECRET") or _keychain_value(
        WORKSPACE_CREDENTIAL_ID, "client_secret"
    )
    if not client_id or not client_secret:
        raise RuntimeError("EXISTING_OAUTH_CLIENT_NOT_FOUND: client_id/client_secret missing from Keychain.")
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost", "http://127.0.0.1"],
    }


def generate_youtube_auth_url(redirect_uri: str = "http://127.0.0.1") -> dict[str, Any]:
    """Generate the YouTube-only OAuth consent URL. Do NOT use include_granted_scopes."""
    _validate_youtube_scopes(YOUTUBE_SCOPES)
    client = _get_oauth_client()
    params = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(YOUTUBE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        # NOTE: Do NOT set include_granted_scopes=true to avoid Google merging conflicting Workspace scopes
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {
        "status": "AUTHORIZATION_URL_CREATED",
        "authorization_url": url,
        "client_id_reference": "NEXUS_GOOGLE_WORKSPACE_CLIENT_ID",
        "oauth_client_reused": "Nexus OS Mac Mini (Desktop)",
        "scopes": YOUTUBE_SCOPE_NAMES,
        "target_credential_id": YOUTUBE_CREDENTIAL_ID,
        "secret_values_exposed": False,
    }


def authorize_youtube(*, open_browser: bool = True, port: int = 0) -> dict[str, Any]:
    """Run loopback authorization on Mac Mini for YouTube-only grant."""
    _validate_youtube_scopes(YOUTUBE_SCOPES)
    client = _get_oauth_client()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        return {
            "status": "GOOGLE_OAUTH_DEPENDENCY_MISSING",
            "error": exc.__class__.__name__,
            "secret_values_exposed": False,
        }

    flow = InstalledAppFlow.from_client_config({"installed": client}, YOUTUBE_SCOPES)
    print(
        json.dumps({
            "event": "YOUTUBE_OAUTH_FLOW_START",
            "scopes": YOUTUBE_SCOPE_NAMES,
            "browser_requested": open_browser,
            "target_credential": YOUTUBE_CREDENTIAL_ID,
            "secret_values_exposed": False,
        }),
        file=sys.stderr,
        flush=True,
    )

    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=port,
        access_type="offline",
        prompt="consent",
        open_browser=open_browser,
    )
    if not credentials.refresh_token:
        raise RuntimeError("YOUTUBE_REFRESH_TOKEN_NOT_RETURNED: Prompt did not yield a refresh token.")

    # Store in dedicated YouTube credential entry; do NOT touch Workspace
    stored = store_keychain(
        YOUTUBE_CREDENTIAL_ID, "refresh_token", credentials.refresh_token, replace=True
    )

    # Validate resulting token and discover channel
    cert = validate_youtube_token(credentials.refresh_token)

    return {
        "status": "YOUTUBE_AUTHORIZED",
        "credential_id": YOUTUBE_CREDENTIAL_ID,
        "stored": stored,
        "scopes": YOUTUBE_SCOPE_NAMES,
        "channel_info": cert.get("channels", []),
        "secret_values_exposed": False,
        "workspace_credential_preserved": True,
    }


def validate_youtube_token(refresh_token: Optional[str] = None) -> dict[str, Any]:
    """Validate YouTube OAuth credentials, granted scopes, and channel identity."""
    token = refresh_token or _keychain_value(YOUTUBE_CREDENTIAL_ID, "refresh_token")
    if not token:
        status_in_kc = keychain_status(YOUTUBE_CREDENTIAL_ID, "refresh_token")
        return {
            "status": "AUTH_REQUIRED",
            "credential_id": YOUTUBE_CREDENTIAL_ID,
            "keychain_status": status_in_kc,
            "youtube_upload_scope": "MISSING",
            "channels": [],
            "secret_values_exposed": False,
        }

    client = _get_oauth_client()
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import requests

        creds = Credentials(
            token=None,
            refresh_token=token,
            token_uri=client["token_uri"],
            client_id=client["client_id"],
            client_secret=client["client_secret"],
        )
        creds.refresh(Request())

        # Inspect tokeninfo without logging access token
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": creds.token},
            timeout=12,
        )
        resp.raise_for_status()
        scope_str = str(resp.json().get("scope") or "")
        granted = sorted({item.rsplit("/", 1)[-1] for item in scope_str.split()})
        has_upload = YOUTUBE_UPLOAD_SCOPE in scope_str.split()

        # Channel identity lookup
        from googleapiclient.discovery import build

        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        ch_resp = (
            yt.channels()
            .list(part="snippet,contentDetails,statistics", mine=True)
            .execute()
        )
        items = ch_resp.get("items", [])
        channels = [
            {
                "channel_id": it.get("id"),
                "channel_name": (it.get("snippet") or {}).get("title"),
                "channel_handle": (it.get("snippet") or {}).get("customUrl"),
            }
            for it in items
        ]

        return {
            "status": "AVAILABLE" if has_upload else "INSUFFICIENT_SCOPE",
            "credential_id": YOUTUBE_CREDENTIAL_ID,
            "granted_scopes": granted,
            "youtube_upload_scope": "GRANTED" if has_upload else "MISSING",
            "channel_count": len(channels),
            "channels": channels,
            "channel_selection_required": len(channels) > 1,
            "secret_values_exposed": False,
        }
    except Exception as exc:
        return {
            "status": "VALIDATION_FAILED",
            "credential_id": YOUTUBE_CREDENTIAL_ID,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc)[:200],
            "secret_values_exposed": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube-only OAuth Management")
    sub = parser.add_subparsers(dest="command", required=True)

    auth_p = sub.add_parser("authorize", help="Launch local browser OAuth for YouTube")
    auth_p.add_argument("--open-browser", action="store_true", default=True)
    auth_p.add_argument("--no-browser", dest="open_browser", action="store_false")
    auth_p.add_argument("--port", type=int, default=0)

    url_p = sub.add_parser("auth-url", help="Generate authorization URL")
    url_p.add_argument("--redirect-uri", default="http://127.0.0.1")

    sub.add_parser("status", help="Check YouTube credential and channel status")

    args = parser.parse_args()

    if args.command == "authorize":
        res = authorize_youtube(open_browser=args.open_browser, port=args.port)
    elif args.command == "auth-url":
        res = generate_youtube_auth_url(redirect_uri=args.redirect_uri)
    elif args.command == "status":
        res = validate_youtube_token()
    else:
        res = {"status": "UNKNOWN_COMMAND"}

    print(json.dumps(res, indent=2))
    return 0 if res.get("status") in {"YOUTUBE_AUTHORIZED", "AUTHORIZATION_URL_CREATED", "AVAILABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
