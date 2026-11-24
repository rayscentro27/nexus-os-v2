"""Governed Google Workspace desktop OAuth and read-only certification."""
from __future__ import annotations
import argparse, json, os, sys
import importlib.util
from pathlib import Path
from typing import Any

# Executing this file directly puts its package directory first on sys.path.
# That directory contains platform.py, which can shadow Python's stdlib
# platform module while third-party OAuth packages import it. Keep the
# explicit scripts/ entry (for nexus_agent_platform imports), but remove only
# this script's own directory from the import search path.
_SCRIPT_PACKAGE_DIR = Path(__file__).resolve().parent
for _path_entry in tuple(sys.path):
    try:
        if Path(_path_entry or os.getcwd()).resolve() == _SCRIPT_PACKAGE_DIR:
            sys.path.remove(_path_entry)
    except (OSError, RuntimeError):
        continue

from nexus_agent_platform.credential_control_plane import keychain_status, registry_entry, store_keychain, _keychain_value
from nexus_agent_platform import google_scopes as gscopes

ROOT = Path(__file__).resolve().parents[2]
CREDENTIAL_ID = "credential.google.workspace.prod.v1"
GMAIL_WRITE_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", GMAIL_WRITE_SCOPE,
          "https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/drive.file"]
SCOPE_NAMES = ["gmail.readonly", "gmail.modify", "calendar.events", "drive.file"]
MUTATIONS_PERFORMED = False

# The "Google Core" consent profile = existing Workspace scopes + read-only Search Console / GA4 (+ Business Profile).
# It is stored under the SAME credential id (one grant of the owner Google account); YouTube stays a separate grant.
COMBINED_SCOPES = gscopes.profile_scopes("core")
CORE_SCOPE_NAMES = [gscopes.name(s) for s in COMBINED_SCOPES]
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"  # must never appear in this grant

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

def build_google_credentials(credentials_cls: Any, *, client_id: str, client_secret: str, refresh_token: str) -> Any:
    """Construct refresh-only credentials; access tokens remain memory-only."""
    # SCOPES is used by a future explicit consent flow. Do not pass it while
    # refreshing an existing token: that would request newly added scopes from
    # a refresh token that has not been reauthorized.
    return credentials_cls(token=None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token", client_id=client_id, client_secret=client_secret)

def _reauth_import_diagnostics() -> dict[str, Any]:
    """Describe the active interpreter/import resolution without credential data."""
    package_path = None
    flow_path = None
    package_error = None
    flow_error = None
    try:
        package_spec = importlib.util.find_spec("google_auth_oauthlib")
        if package_spec:
            package_path = package_spec.origin or next(iter(package_spec.submodule_search_locations or ()), None)
    except Exception as exc:
        package_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    try:
        flow_spec = importlib.util.find_spec("google_auth_oauthlib.flow")
        if flow_spec:
            flow_path = flow_spec.origin
    except Exception as exc:
        flow_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    return {
        "python": sys.executable,
        "sys_path": list(sys.path),
        "package_resolved": package_path is not None,
        "package_path": package_path,
        "flow_resolved": flow_path is not None,
        "flow_path": flow_path,
        "package_resolution_error": package_error,
        "flow_resolution_error": flow_error,
    }

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

def reauthorize_existing(*, scopes: list[str] | None = None, open_browser: bool = False, with_youtube: bool = False, profile: str = "workspace") -> dict[str, Any]:
    """Renew the existing shared Google grant without replacing its OAuth client.

    The installed-app callback is loopback-only. Existing client credentials
    remain in the OS keychain; only the refresh token is updated after the
    owner completes Google's consent screen.
    """
    if with_youtube:
        raise RuntimeError(
            "GOOGLE_SCOPE_CONFLICT: Google prohibits combining Google Drive/Workspace scopes "
            "with YouTube upload scopes in a single OAuth grant. "
            "Use the dedicated YouTube authorization command: "
            "PYTHONPATH=scripts .venv-agent-platform/bin/python scripts/nexus_agent_platform/youtube_upload.py authorize"
        )
    existing = _configured()
    if existing.get("client_id") != "CONFIGURED" or existing.get("client_secret") != "CONFIGURED":
        raise RuntimeError("google_oauth_client_not_configured")
    diagnostics = _reauth_import_diagnostics()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except Exception as exc:
        message = str(exc)[:400]
        return {
            "status": "GOOGLE_OAUTH_IMPORT_FAILED",
            "import_error_type": type(exc).__name__,
            "import_error_message": message,
            "import_error_module": getattr(exc, "name", None),
            "runtime_diagnostics": diagnostics,
            "secret_values_exposed": False,
        }
    client = {
        "client_id": _keychain_value(CREDENTIAL_ID, "client_id"),
        "client_secret": _keychain_value(CREDENTIAL_ID, "client_secret"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
    if not client["client_id"] or not client["client_secret"]:
        raise RuntimeError("google_oauth_client_not_configured")
    if scopes is None and profile != "workspace":
        scopes = gscopes.profile_scopes(profile)
    target_scopes = scopes if scopes is not None else SCOPES
    gscopes.validate_separation(profile, target_scopes)
    target_names = [s.rsplit("/", 1)[-1] for s in target_scopes] if scopes is not None else SCOPE_NAMES
    flow = InstalledAppFlow.from_client_config({"installed": client}, target_scopes)
    print(json.dumps({
        "profile": profile,
        "event": "GOOGLE_REAUTH_FLOW_START",
        "runtime_diagnostics": diagnostics,
        "flow": "InstalledAppFlow.run_local_server",
        "browser_requested": bool(open_browser),
        "scopes": target_names,
        "secret_values_exposed": False,
    }, sort_keys=True), file=sys.stderr, flush=True)
    credentials = flow.run_local_server(
        host="127.0.0.1", port=0, access_type="offline", prompt="consent",
        open_browser=open_browser,
    )
    if not credentials.refresh_token:
        raise RuntimeError("google_refresh_token_not_returned")
    stored = store_keychain(CREDENTIAL_ID, "refresh_token", credentials.refresh_token, replace=True)
    return {"status":"GOOGLE_AUTHORIZED","credential_id":CREDENTIAL_ID,
            "stored":{"refresh_token":stored},"scopes":target_names,"profile":profile,
            "secret_values_exposed":False,"oauth_client_replaced":False}

def generate_authorization_url(*, scopes: list[str] | None = None, redirect_uri: str = "http://127.0.0.1") -> dict[str, Any]:
    """Generate the OAuth consent URL for Ray using the existing Desktop OAuth client."""
    import urllib.parse
    target_scopes = scopes or COMBINED_SCOPES
    cid = os.environ.get("NEXUS_GOOGLE_WORKSPACE_CLIENT_ID") or _keychain_value(CREDENTIAL_ID, "client_id")
    if not cid:
        return {"status": "CLIENT_NOT_CONFIGURED", "authorization_url": None, "secret_values_exposed": False}
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(target_scopes),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return {
        "status": "AUTHORIZATION_URL_CREATED",
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params),
        "client_id_reference": "NEXUS_GOOGLE_WORKSPACE_CLIENT_ID",
        "scopes": [s.rsplit("/", 1)[-1] for s in target_scopes],
        "access_type": "offline",
        "prompt": "consent",
        "secret_values_exposed": False,
    }

def classify_google_error(exc: Any) -> dict[str, Any]:
    """Reduce a Google API error to status + reason (+ the API activation link when Google gives one). No bodies, no tokens."""
    resp = getattr(exc, "resp", None)
    status = getattr(resp, "status", None) or getattr(getattr(exc, "response", None), "status_code", None)
    content = getattr(exc, "content", None) or getattr(getattr(exc, "response", None), "content", None) or b""
    try:
        err = json.loads(content.decode("utf-8") if isinstance(content, bytes) else str(content)).get("error", {}) or {}
    except Exception:
        err = {}
    reasons = [str(d.get("reason")) for d in (err.get("details") or []) if isinstance(d, dict) and d.get("reason")]
    reasons += [str(e.get("reason")) for e in (err.get("errors") or []) if isinstance(e, dict) and e.get("reason")]
    activation = None
    quota_zero = False
    for d in err.get("details") or []:
        if isinstance(d, dict):
            quota_zero = quota_zero or str((d.get("metadata") or {}).get("quota_limit_value")) == "0"
            activation = activation or (d.get("metadata") or {}).get("activationUrl")
            for link in d.get("links") or []:
                if isinstance(link, dict) and "console" in str(link.get("url", "")):
                    activation = activation or link.get("url")
    message = str(err.get("message") or "")
    if status == 403 and ("SERVICE_DISABLED" in reasons or "accessNotConfigured" in reasons or "has not been used in project" in message):
        kind = "API_DISABLED"
    elif status == 429 or "RESOURCE_EXHAUSTED" in str(err.get("status")) or "rateLimitExceeded" in reasons:
        kind = "API_ACCESS_NOT_APPROVED" if quota_zero else "QUOTA_EXCEEDED"
    elif status == 403 and ("ACCESS_TOKEN_SCOPE_INSUFFICIENT" in reasons or "insufficientPermissions" in reasons or "insufficient authentication scopes" in message.lower()):
        kind = "SCOPE_NOT_GRANTED"
    elif status == 403:
        kind = "PERMISSION_DENIED"
    elif status == 401:
        kind = "UNAUTHENTICATED"
    elif status == 404:
        kind = "NOT_FOUND"
    else:
        kind = "ERROR"
    out = {"status": kind, "http_status": status, "reasons": sorted(set(reasons))[:4], "error_type": type(exc).__name__}
    if activation:
        out["activation_url"] = str(activation)[:300]
    return out


def _probe_core_services(creds: Any, granted: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read-only identification probes for the marketing services in the Core grant. Each runs independently."""
    from googleapiclient.discovery import build
    services: dict[str, Any] = {}
    inventory: dict[str, Any] = {}

    def need(service: str) -> bool:
        missing = [gscopes.name(s) for s in gscopes.SERVICES[service]["scopes"] if gscopes.name(s) not in granted]
        if missing:
            services[service] = {"status": "SCOPE_NOT_GRANTED", "missing_scopes": missing}
            return False
        return True

    if need("search_console"):
        try:
            api = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
            rows = api.sites().list().execute().get("siteEntry", []) or []
            inventory["search_console_sites"] = [{"site_url": r.get("siteUrl"), "permission_level": r.get("permissionLevel")} for r in rows][:25]
            services["search_console"] = {"status": "PASS" if rows else "NO_ACCESSIBLE_PROPERTIES", "site_count": len(rows)}
        except Exception as exc:
            services["search_console"] = classify_google_error(exc)
    if need("ga4"):
        try:
            api = build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)
            accounts = api.accountSummaries().list(pageSize=50).execute().get("accountSummaries", []) or []
            props = [{"property": p.get("property"), "display_name": p.get("displayName"), "account": a.get("account"), "account_name": a.get("displayName")}
                     for a in accounts for p in (a.get("propertySummaries") or [])]
            inventory["ga4_properties"] = props[:25]
            services["ga4"] = {"status": "PASS" if props else "NO_ACCESSIBLE_PROPERTIES", "account_count": len(accounts), "property_count": len(props)}
        except Exception as exc:
            services["ga4"] = classify_google_error(exc)
    if need("business_profile"):
        try:
            api = build("mybusinessaccountmanagement", "v1", credentials=creds, cache_discovery=False)
            accts = api.accounts().list(pageSize=20).execute().get("accounts", []) or []
            inventory["business_profile_accounts"] = [{"name": a.get("name"), "account_name": a.get("accountName"), "type": a.get("type")} for a in accts][:10]
            locations: list[dict[str, Any]] = []
            info = build("mybusinessbusinessinformation", "v1", credentials=creds, cache_discovery=False)
            for a in accts[:3]:
                rows = info.accounts().locations().list(parent=a.get("name"), readMask="name,title,websiteUri", pageSize=20).execute().get("locations", []) or []
                locations += [{"name": r.get("name"), "title": r.get("title"), "website": r.get("websiteUri"), "account": a.get("name")} for r in rows]
            inventory["business_profile_locations"] = locations[:20]
            services["business_profile"] = {"status": "PASS" if accts else "NO_ACCESSIBLE_ACCOUNTS", "account_count": len(accts), "location_count": len(locations)}
        except Exception as exc:
            c = classify_google_error(exc)
            if c["status"] == "QUOTA_EXCEEDED":
                # a brand-new project gets 0 Business Profile requests/minute until Google approves API access
                c["status"] = "API_ACCESS_NOT_APPROVED"; c["note"] = "quota exhausted on first call: Business Profile API access is most likely not approved yet"
            services["business_profile"] = c
    return services, inventory


def certify_read_only(profile: str = "workspace") -> dict[str, Any]:
    """Read-only verification of the Workspace / Core grant. Never mutates anything and never returns secrets.

    profile=workspace: token refresh + tokeninfo scopes + OAuth client match + Calendar / Gmail / Drive reads.
    profile=core: the same, plus read-only identification of Search Console sites, GA4 properties and Business
    Profile accounts (each reported PASS / SCOPE_NOT_GRANTED / API_DISABLED / API_ACCESS_NOT_APPROVED / ...).
    """
    if profile not in ("workspace", "core"):
        raise ValueError(f"unknown_profile:{profile}")
    state = _configured(); result = {"credential_id":CREDENTIAL_ID,"profile":profile,"status":"GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED" if state["refresh_token"] != "CONFIGURED" else "GOOGLE_TOKEN_REFRESH_FAILED","oauth_client":"CONFIGURED" if state["client_id"] == state["client_secret"] == "CONFIGURED" else "NOT_FOUND","refresh_capability":state["refresh_token"],"granted_scopes":[],"calendar_read":"NOT_RUN","gmail_read":"NOT_RUN","drive_read":"NOT_RUN","mutations_performed":False,"secret_values_exposed":False,"oauth_publishing_mode":"TESTING_OR_EXTERNALLY_MANAGED"}
    if result["status"] != "GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED":
        stage = "TOKEN_REFRESH"
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            client_id = _keychain_value(CREDENTIAL_ID,"client_id")
            creds=build_google_credentials(Credentials, client_id=client_id, client_secret=_keychain_value(CREDENTIAL_ID,"client_secret"), refresh_token=_keychain_value(CREDENTIAL_ID,"refresh_token"))
            creds.refresh(Request())
            # Do not report requested scopes as if they were granted. Read the actual scope set (and the client the
            # token was issued to) from Google's tokeninfo endpoint without logging or returning the access token.
            stage = "TOKENINFO"
            import requests
            scope_response = requests.get("https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": creds.token}, timeout=12)
            scope_response.raise_for_status()
            info = scope_response.json()
            scope_text = str(info.get("scope") or "")
            granted = sorted({item.rsplit("/", 1)[-1] for item in scope_text.split()})
            result["granted_scopes"] = granted
            result["oauth_client_match"] = bool(client_id) and str(info.get("aud") or info.get("azp") or "") == client_id
            result["oauth_client_project_number"] = (client_id or "").split("-", 1)[0] or None
            result["status"]="GOOGLE_WORKSPACE_READ_VERIFIED"; result["refresh_capability"]="CONFIGURED"
            result["gmail_write_scope"] = "GRANTED" if GMAIL_WRITE_SCOPE in scope_text.split() else "MISSING"
            result["gmail_write_scope_required"] = GMAIL_WRITE_SCOPE
            # separation check: the Workspace / Core grant must never carry a YouTube scope
            result["youtube_scope_present"] = any(s in gscopes.YOUTUBE_SCOPE_NAMES for s in granted)
            stage = "OAUTH_CLIENT_CHECK"
            if not result["oauth_client_match"]:
                raise RuntimeError("token_issued_to_a_different_oauth_client")
            # calendar.events is intentionally narrower than calendar.readonly;
            # read the primary calendar's event collection rather than the
            # calendar-list endpoint, which requires a broader scope.
            stage = "CALENDAR_READ"; calendar=build("calendar","v3",credentials=creds,cache_discovery=False); calendar.events().list(calendarId="primary", maxResults=1, singleEvents=False).execute(); result["calendar_read"]="PASS"
            stage = "GMAIL_READ"; gmail=build("gmail","v1",credentials=creds,cache_discovery=False); gmail.users().getProfile(userId="me").execute(); result["gmail_read"]="PASS"
            stage = "DRIVE_READ"; drive=build("drive","v3",credentials=creds,cache_discovery=False); drive.files().list(pageSize=1,fields="files(id,name)").execute(); result["drive_read"]="PASS"
            if profile == "core":
                stage = "CORE_SERVICES"
                services, inventory = _probe_core_services(creds, set(granted))
                result["services"] = services; result["inventory"] = inventory
        except Exception as exc:
            result["error_type"]=exc.__class__.__name__; result["failed_stage"]=stage
            response=getattr(exc,"resp",None); result["http_status"]=getattr(response,"status",None)
            reason=getattr(exc,"reason",None); result["error_reason"] = str(reason)[:160] if reason else None
            if stage in ("TOKEN_REFRESH", "TOKENINFO"):
                result["status"] = "GOOGLE_TOKEN_REFRESH_FAILED"
            elif str(exc) == "token_issued_to_a_different_oauth_client":
                result["status"] = "GOOGLE_OAUTH_CLIENT_MISMATCH"
            else:
                result["status"]="GOOGLE_SCOPE_MISMATCH" if getattr(response,"status",None)==403 else "GOOGLE_READ_FAILED"
    if profile == "core":
        result.setdefault("services", {})
        granted = set(result.get("granted_scopes") or [])
        for svc in ("search_console", "ga4", "business_profile"):
            if svc not in result["services"]:
                result["services"][svc] = {"status": "NOT_RUN" if granted else "TOKEN_UNAVAILABLE"}
    return result

def write_certification_report(result: dict[str, Any]) -> None:
    out = ROOT / "reports/certification"; out.mkdir(parents=True, exist_ok=True)
    (out / "nexus_calendar_authorization_latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "nexus_calendar_authorization_latest.md").write_text("# Google Workspace Read-Only Certification\n\n" + "\n".join(f"- {key}: {value}" for key, value in result.items() if key not in {"granted_scopes"}) + "\n- granted_scopes: " + (", ".join(result.get("granted_scopes", [])) or "none") + "\n", encoding="utf-8")

def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True); a=sub.add_parser("authorize"); a.add_argument("--client-secrets-file",required=True); a.add_argument("--replace",action="store_true"); r=sub.add_parser("reauthorize-existing"); r.add_argument("--open-browser",action="store_true"); r.add_argument("--with-youtube",action="store_true"); r.add_argument("--profile",choices=["workspace","core"],default="workspace"); u=sub.add_parser("auth-url"); u.add_argument("--redirect-uri",default="http://127.0.0.1"); c=sub.add_parser("certify-read-only"); c.add_argument("--profile",choices=["workspace","core"],default="workspace"); args=p.parse_args()
    result=authorize(args.client_secrets_file,replace=args.replace) if args.command=="authorize" else reauthorize_existing(open_browser=args.open_browser,with_youtube=getattr(args,"with_youtube",False),profile=getattr(args,"profile","workspace")) if args.command=="reauthorize-existing" else generate_authorization_url(redirect_uri=getattr(args,"redirect_uri","http://127.0.0.1")) if args.command=="auth-url" else certify_read_only(getattr(args,"profile","workspace"));
    if args.command == "certify-read-only": write_certification_report(result)
    print(json.dumps(result,indent=2)); return 0 if result.get("status") in {"GOOGLE_AUTHORIZED","GOOGLE_WORKSPACE_READ_VERIFIED","GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED","AUTHORIZATION_URL_CREATED"} else 1
if __name__=="__main__": raise SystemExit(main())
