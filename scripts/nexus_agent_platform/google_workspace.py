"""Governed Google Workspace desktop OAuth and read-only certification."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from typing import Any
from nexus_agent_platform.credential_control_plane import keychain_status, registry_entry, store_keychain, _keychain_value

ROOT = Path(__file__).resolve().parents[2]
CREDENTIAL_ID = "credential.google.workspace.prod.v1"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/drive.file"]
SCOPE_NAMES = ["gmail.readonly", "calendar.events", "drive.file"]
MUTATIONS_PERFORMED = False

def validate_scopes(scopes: list[str]) -> bool: return set(scopes) == set(SCOPES) and len(scopes) == len(SCOPES)
def validate_client_secrets(path: str | Path) -> dict[str, str]:
    candidate = Path(path).expanduser().resolve()
    if ROOT == candidate or ROOT in candidate.parents: raise ValueError("client_secret_file_must_not_be_repo_local")
    data = json.loads(candidate.read_text(encoding="utf-8")); section = data.get("installed") or data.get("desktop")
    if not isinstance(section, dict) or not section.get("client_id") or not section.get("client_secret") or not section.get("auth_uri") or not section.get("token_uri"):
        raise ValueError("not_an_installed_desktop_oauth_client")
    return {"client_id": section["client_id"], "client_secret": section["client_secret"], "auth_uri": section["auth_uri"], "token_uri": section["token_uri"]}

def _configured() -> dict[str, str]:
    return {component: keychain_status(CREDENTIAL_ID, component) for component in ("client_id", "client_secret", "refresh_token")}

def authorize(client_secrets_file: str, *, replace: bool = False, open_browser: bool = True) -> dict[str, Any]:
    client = validate_client_secrets(client_secrets_file)
    existing = _configured()
    if not replace and any(value == "CONFIGURED" for value in existing.values()): raise RuntimeError("google_credentials_already_configured_use_replace")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc: return {"status":"GOOGLE_OAUTH_DEPENDENCY_MISSING","error":exc.__class__.__name__,"required_package":"google-auth-oauthlib","secret_values_exposed":False}
    flow = InstalledAppFlow.from_client_config({"installed": client}, SCOPES)
    credentials = flow.run_local_server(host="127.0.0.1", port=0, access_type="offline", prompt="consent", open_browser=open_browser)
    if not credentials.refresh_token: raise RuntimeError("google_refresh_token_not_returned")
    stored = {}
    for component, value in (("client_id", client["client_id"]), ("client_secret", client["client_secret"]), ("refresh_token", credentials.refresh_token)):
        stored[component] = store_keychain(CREDENTIAL_ID, component, value, replace=replace)
    return {"status":"GOOGLE_AUTHORIZED","credential_id":CREDENTIAL_ID,"stored":stored,"scopes":SCOPE_NAMES,"secret_values_exposed":False}

def certify_read_only() -> dict[str, Any]:
    state = _configured(); result = {"credential_id":CREDENTIAL_ID,"status":"GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED" if state["refresh_token"] != "CONFIGURED" else "GOOGLE_TOKEN_REFRESH_FAILED","oauth_client":"CONFIGURED" if state["client_id"] == state["client_secret"] == "CONFIGURED" else "NOT_FOUND","refresh_capability":state["refresh_token"],"granted_scopes":[],"calendar_read":"NOT_RUN","gmail_read":"NOT_RUN","drive_read":"NOT_RUN","mutations_performed":False,"secret_values_exposed":False,"oauth_publishing_mode":"TESTING_OR_EXTERNALLY_MANAGED"}
    if result["status"] != "GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED":
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds=Credentials(_keychain_value(CREDENTIAL_ID,"refresh_token"), refresh_token=_keychain_value(CREDENTIAL_ID,"refresh_token"), token_uri="https://oauth2.googleapis.com/token", client_id=_keychain_value(CREDENTIAL_ID,"client_id"), client_secret=_keychain_value(CREDENTIAL_ID,"client_secret"), scopes=SCOPES)
            creds.refresh(Request()); result["status"]="GOOGLE_WORKSPACE_READ_VERIFIED"; result["refresh_capability"]="CONFIGURED"
            from googleapiclient.discovery import build
            calendar=build("calendar","v3",credentials=creds,cache_discovery=False); calendar.calendarList().list(maxResults=1).execute(); result["calendar_read"]="PASS"
            gmail=build("gmail","v1",credentials=creds,cache_discovery=False); gmail.users().getProfile(userId="me").execute(); result["gmail_read"]="PASS"
            drive=build("drive","v3",credentials=creds,cache_discovery=False); drive.files().list(pageSize=1,fields="files(id,name)").execute(); result["drive_read"]="PASS"
        except Exception as exc: result["error_type"]=exc.__class__.__name__; result["status"]="GOOGLE_TOKEN_REFRESH_FAILED"
    return result

def write_certification_report(result: dict[str, Any]) -> None:
    out = ROOT / "reports/certification"; out.mkdir(parents=True, exist_ok=True)
    (out / "nexus_calendar_authorization_latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "nexus_calendar_authorization_latest.md").write_text("# Google Workspace Read-Only Certification\n\n" + "\n".join(f"- {key}: {value}" for key, value in result.items() if key not in {"granted_scopes"}) + "\n- granted_scopes: " + (", ".join(result.get("granted_scopes", [])) or "none") + "\n", encoding="utf-8")

def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True); a=sub.add_parser("authorize"); a.add_argument("--client-secrets-file",required=True); a.add_argument("--replace",action="store_true"); c=sub.add_parser("certify-read-only"); args=p.parse_args()
    result=authorize(args.client_secrets_file,replace=args.replace) if args.command=="authorize" else certify_read_only();
    if args.command == "certify-read-only": write_certification_report(result)
    print(json.dumps(result,indent=2)); return 0 if result.get("status") in {"GOOGLE_AUTHORIZED","GOOGLE_WORKSPACE_READ_VERIFIED","GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED"} else 1
if __name__=="__main__": raise SystemExit(main())
