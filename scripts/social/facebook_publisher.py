"""Nexus OS v2 — Facebook publisher adapter (server/script-side only).

Pipeline position: social_posts -> approval -> agent_jobs -> THIS adapter ->
social_publish_receipts -> nexus_events -> system_health.

Safety: DRY-RUN by default. A real publish requires ALL of:
  1. real_publish=True passed explicitly,
  2. the social_posts row's approval (approval_id) has status 'approved',
  3. the account is Facebook Clear Credentials / page_id 131069194210954,
  4. the env token (social_accounts.token_env_key, default META_PAGE_ACCESS_TOKEN) exists,
  5. social_accounts.publish_enabled is true,
  6. caption/content is present.
Otherwise it dry-runs or reports a blocker. Tokens come from env ONLY (never Supabase,
never printed). No Telegram, no scheduling, no retries.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from _supabase import ENV, configured, get, insert, update, event, health, q

ALLOWED_FB_PAGE_ID = "131069194210954"  # Clear Credentials
GRAPH = "https://graph.facebook.com/v19.0"


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _load_post(post_id: str):
    st, rows = get("social_posts", f"id=eq.{q(post_id)}&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def _load_account(account_id: str):
    if not account_id:
        return None
    st, rows = get("social_accounts", f"id=eq.{q(account_id)}&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def _approval_status(approval_id: str | None) -> str:
    if not approval_id:
        return "none"
    st, rows = get("approvals", f"id=eq.{q(approval_id)}&select=status&limit=1")
    return rows[0]["status"] if isinstance(rows, list) and rows else "none"


def _receipt(post_id: str, status: str, external_id=None, url=None, error=None, response=None):
    insert("social_publish_receipts", {
        "social_post_id": post_id, "platform": "facebook", "status": status,
        "external_id": external_id, "published_url": url, "error": error,
        "receipt": response or {},
    }, prefer="return=minimal")


def _graph_post_feed(page_id: str, message: str, token: str) -> tuple[bool, dict]:
    """Read-write Graph call: POST /{page_id}/feed. Returns (ok, redacted_response)."""
    url = f"{GRAPH}/{page_id}/feed"
    data = urllib.parse.urlencode({"message": message, "access_token": token}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
            return True, json.loads(r.read().decode(errors="ignore"))
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        body = body.replace(token, "<redacted>") if token else body
        try:
            return False, json.loads(body)
        except Exception:
            return False, {"error": body[:200]}
    except Exception as e:
        msg = str(e).replace(token, "<redacted>") if token else str(e)
        return False, {"error": msg[:200]}


def publish(post_id: str, *, real_publish: bool = False) -> dict:
    """Validate + (dry-run or real) publish a single social_posts row. Token never printed."""
    if not configured():
        return {"ok": False, "blocker": "supabase_not_configured"}

    post = _load_post(post_id)
    if not post:
        return {"ok": False, "blocker": "social_post_not_found"}

    blockers = []
    if post.get("platform") != "facebook":
        blockers.append("platform_not_facebook")
    caption = post.get("content") or ""
    if not caption.strip():
        blockers.append("missing_caption")
    appr = _approval_status(post.get("approval_id"))
    if appr != "approved":
        blockers.append(f"approval_status={appr}")
    account = _load_account(post.get("account_id"))
    if not account or account.get("account_id") != ALLOWED_FB_PAGE_ID:
        blockers.append("account_not_clear_credentials")

    token_env = (account or {}).get("token_env_key") or "META_PAGE_ACCESS_TOKEN"
    token = ENV.get(token_env, "")
    page_id = (account or {}).get("account_id") or ALLOWED_FB_PAGE_ID

    # ── DRY RUN (default) ──
    if not real_publish:
        ready = not [b for b in blockers if b != f"approval_status={appr}" or appr != "approved"]
        _receipt(post_id, "dry_run", response={"would_publish": False, "blockers": blockers,
                                               "token_present": bool(token), "token_not_printed": True})
        update("social_posts", f"id=eq.{q(post_id)}",
               {"status": "dry_run_complete", "payload": {**(post.get("payload") or {}), "last_dry_run_blockers": blockers}})
        event("social", "facebook_dry_run", "success" if not blockers else "pending",
              "Facebook dry-run", f"blockers: {', '.join(blockers) or 'none'}", payload={"post_id": post_id})
        return {"ok": True, "mode": "dry_run", "would_publish": False, "blockers": blockers,
                "token_present": bool(token), "ready_for_real": not blockers and bool(token) and bool((account or {}).get("publish_enabled"))}

    # ── REAL PUBLISH (all gates must pass) ──
    if not (account or {}).get("publish_enabled"):
        blockers.append("publish_enabled_false")
    if not token:
        blockers.append(f"{token_env}_missing")
    if blockers:
        _receipt(post_id, "blocked", error=", ".join(blockers))
        event("social", "facebook_publish_blocked", "failed", "Facebook real publish blocked",
              ", ".join(blockers), payload={"post_id": post_id})
        return {"ok": False, "mode": "real", "blocker": ", ".join(blockers)}

    ok, resp = _graph_post_feed(page_id, caption, token)
    if ok and isinstance(resp, dict) and resp.get("id"):
        post_fb_id = resp["id"]
        permalink = f"https://www.facebook.com/{post_fb_id.replace('_', '/posts/')}"
        _receipt(post_id, "published", external_id=post_fb_id, url=permalink, response={"id": post_fb_id})
        update("social_posts", f"id=eq.{q(post_id)}",
               {"status": "published", "published_external_id": post_fb_id, "published_url": permalink})
        event("social", "facebook_published", "success", "Facebook post published",
              f"post {post_fb_id}", payload={"post_id": post_id, "permalink": permalink})
        health("social", "ok", "Facebook publish succeeded")
        return {"ok": True, "mode": "real", "published": True, "post_id": post_fb_id, "permalink": permalink}

    err = resp.get("error") if isinstance(resp, dict) else str(resp)
    _receipt(post_id, "failed", error=json.dumps(err)[:200], response=resp if isinstance(resp, dict) else {})
    update("social_posts", f"id=eq.{q(post_id)}",
           {"status": "failed", "payload": {**(post.get("payload") or {}), "publish_error": json.dumps(err)[:200]}})
    event("social", "facebook_publish_failed", "failed", "Facebook publish failed",
          json.dumps(err)[:160], payload={"post_id": post_id})
    health("social", "partial", "Facebook publish failed (see receipts)")
    return {"ok": False, "mode": "real", "published": False, "error": err}
