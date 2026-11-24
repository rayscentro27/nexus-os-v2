#!/usr/bin/env python3
"""Owner-consent OAuth helper for the Holiday Meta credential.

Diagnosis (Meta debug_token, 2026-11-12): the existing Clear Credentials grant
holds every required scope, but its granular targets cover only the GoClear
Page (131069194210954) and IG (17841480265043148). Raytestpage was never
selected on the asset screen, so a fresh owner consent that adds it is needed.

This helper runs the official Facebook Login code flow for the EXISTING app
(1889438111704778) and stores only the derived Page token in the macOS
Keychain through the canonical Nexus credential control plane.

Secrets (app secret, user tokens, Page token) are never printed, logged,
written to files, or passed on argv to anything but the Keychain store.

Subcommands:
  store-app-secret   hidden prompt; stores the app secret in Keychain
  authorize          opens Meta consent, receives the callback on
                     https://localhost:8765/meta/callback, derives + stores
                     the Raytestpage Page token, prints non-secret metadata
  url                prints the consent URL only (no secrets in it)
"""
from __future__ import annotations

import getpass
import http.server
import json
import secrets
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform import credential_control_plane as ccp  # noqa: E402

APP_ID = "1889438111704778"
CREDENTIAL_ID = "credential.meta.social.holiday.prod.v1"
PAGE_ID = "1722332634511930"
PAGE_NAME = "Raytestpage"
IG_USERNAME = "the612amritual"
GRAPH = "v23.0"
PORT = 8765
REDIRECT_URI = f"https://localhost:{PORT}/meta/callback"
SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "instagram_basic",
    "instagram_content_publish",
    "business_management",
]
TLS_DIR = Path.home() / ".config/nexus/tls"


def _ctx() -> ssl.SSLContext:
    return ccp._get_ssl_context()


def _graph(path: str, params: dict[str, str]) -> dict:
    url = f"https://graph.facebook.com/{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=20, context=_ctx()) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        try:
            body = json.load(exc)
        except Exception:
            body = {}
        err = body.get("error", {})
        # Only non-secret error fields are surfaced.
        return {"error": {"code": err.get("code"), "message": str(err.get("message", ""))[:200]}}


def consent_url(state: str) -> str:
    return "https://www.facebook.com/{v}/dialog/oauth?{q}".format(
        v=GRAPH,
        q=urllib.parse.urlencode(
            {
                "client_id": APP_ID,
                "redirect_uri": REDIRECT_URI,
                "state": state,
                "response_type": "code",
                "scope": ",".join(SCOPES),
                # reauthorize forces the asset-selection screen even when every
                # scope was already granted (rerequest only re-asks declined scopes).
                "auth_type": "reauthorize",
            }
        ),
    )


def store_app_secret() -> int:
    value = getpass.getpass("Clear Credentials App Secret (hidden): ").strip()
    if not value:
        print("APP_SECRET_STORED=NO (empty)")
        return 1
    half = len(value) // 2
    if len(value) == 64 and value[:half] == value[half:]:
        value = value[:half]  # common double-paste
    if not all(c in "0123456789abcdef" for c in value) or len(value) != 32:
        print(f"APP_SECRET_STORED=NO (expected 32 hex chars, got {len(value)} chars)")
        return 1
    check = _graph(APP_ID, {"fields": "id", "access_token": f"{APP_ID}|{value}"})
    if check.get("id") != APP_ID:
        print(f"APP_SECRET_STORED=NO (Meta rejected secret: {check.get('error')})")
        return 1
    res = ccp.store_keychain(CREDENTIAL_ID, "app_secret", value, replace=True)
    del value
    print(f"APP_SECRET_STORED={'YES' if res.get('stored') else 'NO'} status={res.get('status')}")
    return 0 if res.get("stored") else 1


def _ensure_cert() -> tuple[Path, Path]:
    TLS_DIR.mkdir(parents=True, exist_ok=True)
    cert, key = TLS_DIR / "localhost.crt", TLS_DIR / "localhost.key"
    if not (cert.exists() and key.exists()):
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "825",
             "-subj", "/CN=localhost", "-keyout", str(key), "-out", str(cert)],
            check=True, capture_output=True,
        )
        key.chmod(0o600)
    return cert, key


def _receive_code(state: str) -> dict[str, str]:
    result: dict[str, str] = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):  # never log query strings (they carry the code)
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/meta/callback":
                self.send_response(404)
                self.end_headers()
                return
            q = urllib.parse.parse_qs(parsed.query)
            if q.get("state", [""])[0] != state:
                result["error"] = "STATE_MISMATCH"
            elif "error" in q:
                result["error"] = q.get("error_reason", q["error"])[0]
            else:
                result["code"] = q.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Authorization received. You can close this tab and return to Claude Code."
            if "error" in result:
                msg = f"Authorization not completed ({result['error']}). Return to Claude Code."
            self.wfile.write(f"<html><body><p>{msg}</p></body></html>".encode())
            done.set()

    cert, key = _ensure_cert()
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sctx.load_cert_chain(str(cert), str(key))
    server.socket = sctx.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("WAITING_FOR_OWNER_CONSENT (browser opened; timeout 10 min)", flush=True)
    done.wait(timeout=600)
    server.shutdown()
    if not result:
        result["error"] = "TIMEOUT"
    return result


def discover_pages(user_token: str, max_pages: int = 10) -> list[dict]:
    """List Pages the user granted, with Page tokens, via /me/accounts.

    `tasks` exists only on the user->Page accounts edge (never on the Page
    node). It is optional metadata: if Meta rejects it, retry without it so
    Page-token discovery never depends on it.
    """
    field_sets = ["id,name,access_token,tasks", "id,name,access_token"]
    for fields in field_sets:
        rows: list[dict] = []
        params = {"fields": fields, "limit": "100", "access_token": user_token}
        resp = _graph("me/accounts", params)
        if "error" in resp:
            msg = str(resp["error"].get("message", ""))
            if "tasks" in msg and fields != field_sets[-1]:
                print("TASKS_FIELD_UNSUPPORTED=YES (retrying without tasks)")
                continue
            print(f"ME_ACCOUNTS_ERROR={resp['error']}")
            return []
        for _ in range(max_pages):
            rows.extend(resp.get("data", []))
            after = (resp.get("paging") or {}).get("cursors", {}).get("after")
            if not (resp.get("paging") or {}).get("next") or not after:
                break
            resp = _graph("me/accounts", dict(params, after=after))
            if "error" in resp:
                break
        return rows
    return []


def authorize(open_browser: bool = True) -> int:
    app_secret = ccp._keychain_value(CREDENTIAL_ID, "app_secret")
    if not app_secret:
        print("BLOCKED=APP_SECRET_NOT_IN_KEYCHAIN (run: store-app-secret)")
        return 2
    state = secrets.token_urlsafe(24)
    url = consent_url(state)
    if open_browser:
        webbrowser.open(url)
    else:
        print(f"CONSENT_URL={url}")
    got = _receive_code(state)
    if "error" in got:
        print(f"OWNER_CONSENT=FAILED reason={got['error']}")
        return 3

    short = _graph("oauth/access_token", {
        "client_id": APP_ID, "redirect_uri": REDIRECT_URI,
        "client_secret": app_secret, "code": got.pop("code"),
    })
    if "access_token" not in short:
        print(f"CODE_EXCHANGE=FAILED {short.get('error')}")
        return 4
    long = _graph("oauth/access_token", {
        "grant_type": "fb_exchange_token", "client_id": APP_ID,
        "client_secret": app_secret, "fb_exchange_token": short.pop("access_token"),
    })
    user_token = long.get("access_token")
    if not user_token:
        print(f"LONG_LIVED_EXCHANGE=FAILED {long.get('error')}")
        return 5

    app_token = f"{APP_ID}|{app_secret}"
    dbg = _graph("debug_token", {"input_token": user_token, "access_token": app_token}).get("data", {})
    granular = {g.get("scope"): g.get("target_ids", []) for g in dbg.get("granular_scopes", [])}
    print(f"TOKEN_APP_ID={dbg.get('app_id')} TOKEN_TYPE={dbg.get('type')} VALID={dbg.get('is_valid')}")
    print(f"GRANTED_SCOPES={','.join(sorted(s for s in dbg.get('scopes', []) if s in SCOPES))}")
    page_granted = PAGE_ID in granular.get("pages_show_list", []) or PAGE_ID in granular.get("pages_manage_posts", [])
    print(f"PAGE_GRANULAR_ACCESS={'YES' if page_granted else 'NO'}")
    print(f"GRANTED_PAGE_IDS={','.join(granular.get('pages_show_list', []))}")
    print(f"GRANTED_IG_IDS={','.join(granular.get('instagram_basic', []))}")
    print(f"GRANTED_BUSINESS_IDS={','.join(granular.get('business_management', []))}")
    if dbg.get("app_id") != APP_ID:
        print("BLOCKED=TOKEN_APP_MISMATCH")
        return 6

    pages = discover_pages(user_token)
    del user_token
    for row in pages:
        print(f"ME_ACCOUNT id={row.get('id')} name={row.get('name')} tasks={','.join(row.get('tasks') or []) or 'UNREPORTED'}")
    target = next((row for row in pages if row.get("id") == PAGE_ID), None)
    if target is None:
        others = ",".join(f"{r.get('name')}({r.get('id')})" for r in pages) or "NONE"
        print(f"TARGET_PAGE_NOT_GRANTED target={PAGE_NAME}({PAGE_ID}) returned={others}")
        print("HOLIDAY_META_TOKEN_STORED=NO (other Pages are never accepted for Holiday)")
        print("OWNER_ACTION=re-run authorize; on the Pages screen select Raytestpage (keep Clear Credentials)")
        return 7
    page_token = target.pop("access_token", None)
    if not page_token:
        print("PAGE_TOKEN=UNAVAILABLE (Raytestpage returned without a Page token; check CREATE_CONTENT role)")
        return 7
    if target.get("name") != PAGE_NAME:
        print(f"BLOCKED=PAGE_IDENTITY_MISMATCH name={target.get('name')} (token not stored)")
        return 8
    tasks = target.get("tasks") or []
    print(f"FACEBOOK_PAGE_NAME={target.get('name')} FACEBOOK_PAGE_ID={target.get('id')}")
    print(f"PAGE_TASKS={','.join(tasks) or 'UNREPORTED'}")
    if tasks and "CREATE_CONTENT" not in tasks:
        print("BLOCKED=PAGE_ROLE_LACKS_CREATE_CONTENT (token not stored)")
        return 8

    page_node = _graph(PAGE_ID, {
        "fields": "id,name,instagram_business_account{id,username}",
        "access_token": page_token,
    })
    ig = page_node.get("instagram_business_account") or {}
    if "error" in page_node:
        print(f"INSTAGRAM_LOOKUP_ERROR={page_node['error']}")
    print(f"INSTAGRAM_ACCOUNT_ID={ig.get('id')} INSTAGRAM_USERNAME={ig.get('username')}")

    pt_dbg = _graph("debug_token", {"input_token": page_token, "access_token": app_token}).get("data", {})
    print(f"PAGE_TOKEN_EXPIRES_AT={pt_dbg.get('expires_at')} (0 = non-expiring)")

    stored = ccp.store_keychain(CREDENTIAL_ID, "page_access_token", page_token, replace=True)
    del page_token
    ccp.store_keychain(CREDENTIAL_ID, "page_id", PAGE_ID, replace=True)
    if ig.get("id"):
        ccp.store_keychain(CREDENTIAL_ID, "instagram_account_id", ig["id"], replace=True)
    print(f"HOLIDAY_META_TOKEN_STORED={'YES' if stored.get('stored') else 'NO'} SECRET_SOURCE=MACOS_KEYCHAIN")
    print(f"CONNECTED_PAIR_VERIFIED={'YES' if ig.get('username') == IG_USERNAME else 'NO'}")
    print("RAW_TOKEN_EXPOSED=NO")
    return 0 if stored.get("stored") else 9


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "authorize"
    if cmd == "store-app-secret":
        return store_app_secret()
    if cmd == "authorize":
        return authorize(open_browser="--no-browser" not in argv)
    if cmd == "url":
        print(consent_url("preview"))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
