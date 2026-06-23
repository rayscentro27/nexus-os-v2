"""Nexus OS v2 — Facebook token status (adapted from v1 facebook_token_status.py).

Read-only. Reads the Page token from env ONLY (never Supabase, never printed). If present,
checks type/validity/expiry/scopes via the Graph debug_token endpoint. Writes a system_health
row + nexus_events. If the token is missing, records social=partial / missing_token. No publish.

Usage:
    python3 scripts/social/facebook_token_status.py
    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/social/facebook_token_status.py
"""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _supabase import ENV, configured, event, health  # noqa: E402

TOKEN_ENV = "META_PAGE_ACCESS_TOKEN"


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    token = ENV.get(TOKEN_ENV, "")
    app_id, secret = ENV.get("META_APP_ID", ""), ENV.get("META_APP_SECRET", "")

    if not token:
        health("social", "partial", f"{TOKEN_ENV} missing — Facebook publish blocked until token added")
        event("social", "facebook_token_status", "pending", "Facebook token missing",
              f"{TOKEN_ENV} not set in env; dry-run only", payload={"token_present": False})
        print(f"token_present=no ({TOKEN_ENV} missing) — dry-run only. (no secret printed)")
        return 0

    if not (app_id and secret):
        health("social", "partial", "META_APP_ID/SECRET missing — cannot debug_token")
        event("social", "facebook_token_status", "pending", "Cannot verify token",
              "META_APP_ID/META_APP_SECRET missing", payload={"token_present": True})
        print("token present but META_APP_ID/SECRET missing — cannot verify. (no secret printed)")
        return 0

    app_token = f"{app_id}|{secret}"
    url = ("https://graph.facebook.com/v19.0/debug_token?input_token="
           + urllib.parse.quote(token) + "&access_token=" + urllib.parse.quote(app_token))
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20, context=_ctx()) as r:
            d = json.loads(r.read()).get("data", {})
    except Exception as e:
        msg = str(e).replace(token, "<redacted>")
        health("social", "partial", f"token check failed: {msg[:80]}")
        event("social", "facebook_token_status", "failed", "Token check failed", msg[:160])
        print("token check failed (no secret printed)")
        return 1

    exp = d.get("expires_at")
    long_lived = exp in (0, None) or (isinstance(exp, int) and exp - datetime.now(timezone.utc).timestamp() > 86400)
    scopes = d.get("scopes", []) or []
    can_publish = "pages_manage_posts" in scopes and "pages_read_engagement" in scopes
    valid = bool(d.get("is_valid"))
    status = "ok" if (valid and can_publish) else "partial"
    summary = (f"type={d.get('type')} valid={valid} long_lived={long_lived} "
               f"publish_scopes={can_publish} page={d.get('profile_id')}")
    health("social", status, summary)
    event("social", "facebook_token_status", "success" if valid else "failed",
          "Facebook token status", summary, payload={"token_not_printed": True})
    print(summary + "  (no secret printed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
