"""Systems tick: Postiz OAuth/social-auth loss reports CAPABILITY=PRESENT,
AUTHORIZATION=DEGRADED (never capability missing); last success/failure come
from Nexus-owned receipts."""
from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
tick = importlib.import_module("maintenance_tick")

BASE = {"connection": "ONLINE", "TAILSCALE": "Running", "status": "PASS", "DISK_PCT": "10", "MEM_AVAIL_PCT": "50",
        "HTTP_POSTIZ": "401", "HTTP_N8N": "200", "POSTIZ_AUTH_API": "200", "POSTIZ_PROVIDERS_CONFIGURED": "",
        "POSTIZ_FRONTEND_SCHEME": "http", "POSTIZ_INTEGRATION_PROVIDERS": ""}


def _rows(monkeypatch, tmp_path, contabo, governed):
    db = tmp_path / "s.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE health_checks(id,environment_id,service_id,check_type,state,checked_at,evidence,payload)")
    monkeypatch.setattr(tick, "SYSTEMS_DB", db)
    tick._record_node_health({"node_contabo_app_services": contabo, "node_oracle": {"connection": "TIMEOUT"},
                              "postiz_governed": governed})
    with sqlite3.connect(db) as con:
        return {r[0]: (r[1], r[2], json.loads(r[3])) for r in con.execute(
            "SELECT service_id, check_type, state, payload FROM health_checks WHERE service_id LIKE 'postiz-%'")}


GOV = {"provider_router": "PRESENT", "last_success": "2026-11-13T14:40:00+00:00", "last_failure": None}


def test_no_social_accounts_is_authorization_degraded_not_capability_missing(monkeypatch, tmp_path):
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0"}, GOV)
    assert rows["postiz-api"][:2] == ("SERVICE", "HEALTHY")
    ctype, state, payload = rows["postiz-social-auth"]
    assert (ctype, state) == ("AUTHORIZATION", "DEGRADED")
    assert payload["CAPABILITY"] == "PRESENT" and payload["AUTHORIZATION"] == "DEGRADED"
    assert payload["capability_affected"] is False and payload["live_publish_enabled"] is False
    assert payload["last_success"] == GOV["last_success"]


def test_connected_accounts_authorized(monkeypatch, tmp_path):
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "2",
                                          "POSTIZ_INTEGRATION_PROVIDERS": "facebook,instagram"}, GOV)
    assert rows["postiz-social-auth"][1] == "HEALTHY"
    assert rows["postiz-social-auth"][2]["AUTHORIZATION"] == "AUTHORIZED"


def test_governed_receipts_last_success_and_failure(monkeypatch, tmp_path):
    f = tmp_path / "r.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in [
        {"provider": "POSTIZ", "state": "COMPLETED", "action": "account_discovery", "recorded_at": "t1"},
        {"workflow": "postiz_connectivity_certification", "state": "FAILED", "outcome": "X", "recorded_at": "t2"},
        {"provider": "OTHER", "state": "FAILED", "recorded_at": "t3"}]) + "\n")
    monkeypatch.setattr(tick, "POSTIZ_RECEIPTS", f)
    g = tick._postiz_governed()
    assert g["last_success"] == "t1" and g["last_failure"] == "t2" and g["last_failure_outcome"] == "X"
    assert g["provider_router"] == "PRESENT" and g["live_publish_enabled"] is False


OAUTH_OK = {"POSTIZ_IMAGE": "ghcr.io/gitroomhq/postiz-app:v2.25.3", "POSTIZ_IMAGE_MATCHES_MANIFEST": "YES",
            "POSTIZ_META_OAUTH_ORIGIN": "https://postiz-auth.goclearonline.cc",
            "POSTIZ_PROVIDER_FACEBOOK": "OVERRIDE", "POSTIZ_PROVIDER_INSTAGRAM": "OVERRIDE"}


def test_meta_oauth_override_healthy(monkeypatch, tmp_path):
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **OAUTH_OK}, GOV)
    ctype, state, payload = rows["postiz-meta-oauth"]
    assert (ctype, state) == ("CONFIGURATION", "HEALTHY") and payload["issues"] == []
    assert payload["effective_callbacks"] == ["https://postiz-auth.goclearonline.cc/integrations/social/facebook",
                                              "https://postiz-auth.goclearonline.cc/integrations/social/instagram"]


def test_meta_oauth_detects_drift_mismatch_missing_origin(monkeypatch, tmp_path):
    bad = {**OAUTH_OK, "POSTIZ_IMAGE": "ghcr.io/gitroomhq/postiz-app:v2.26.0", "POSTIZ_IMAGE_MATCHES_MANIFEST": "NO",
           "POSTIZ_PROVIDER_INSTAGRAM": "MISMATCH", "POSTIZ_META_OAUTH_ORIGIN": ""}
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **bad}, GOV)
    state, payload = rows["postiz-meta-oauth"][1:]
    assert state == "DEGRADED"
    assert {"POSTIZ_VERSION_DRIFT", "POSTIZ_IMAGE_NOT_MANIFEST_IMAGE", "PROVIDER_OVERRIDE_MISMATCH:instagram",
            "POSTIZ_META_OAUTH_ORIGIN_MISSING"} <= set(payload["issues"])
    assert payload["effective_callbacks"][0].startswith("https://nexus-app-services.tailb1e262.ts.net/")
    other = tmp_path / "unexpected_origin"
    other.mkdir()
    rows = _rows(monkeypatch, other,
                 {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **OAUTH_OK, "POSTIZ_META_OAUTH_ORIGIN": "https://evil.example"}, GOV)
    assert "CALLBACK_ORIGIN_UNEXPECTED" in rows["postiz-meta-oauth"][2]["issues"]


def _fake_fetch(responses):
    def f(url, timeout=6):
        return responses.get(url, (404, {}, ""))
    return f


GOOD_HDRS = {"content-security-policy": "default-src 'none'; script-src 'sha256-x'", "referrer-policy": "no-referrer",
             "cache-control": "no-store", "x-frame-options": "DENY"}
O = "https://postiz-auth.goclearonline.cc"
P = "https://nexus-app-services.tailb1e262.ts.net"


def test_bounce_pages_pass_and_fail():
    good = {f"{O}/integrations/social/{p}": (200, GOOD_HDRS, f'<script>var t="{P}/integrations/social/{p}";</script>')
            for p in ("facebook", "instagram", "tiktok")}
    assert tick._postiz_oauth_bounce(_fake_fetch(good))["status"] == "PASS"
    broken = dict(good); broken[f"{O}/integrations/social/instagram"] = (200, {}, "<html>spa</html>")
    r = tick._postiz_oauth_bounce(_fake_fetch(broken))
    assert r["status"] == "FAIL" and r["callback_pages"]["instagram"]["valid"] is False
    leaky = dict(good); leaky[f"{O}/"] = (200, {}, "")
    assert tick._postiz_oauth_bounce(_fake_fetch(leaky))["status"] == "FAIL"
    dns = tick._postiz_oauth_bounce(lambda url, timeout=6: (None, {}, "URLError"))
    assert dns["status"] == "UNREACHABLE"


def test_bounce_row_recorded(monkeypatch, tmp_path):
    db = tmp_path / "s.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE health_checks(id,environment_id,service_id,check_type,state,checked_at,evidence,payload)")
    monkeypatch.setattr(tick, "SYSTEMS_DB", db)
    tick._record_node_health({"node_contabo_app_services": {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **OAUTH_OK},
                              "node_oracle": {"connection": "TIMEOUT"}, "postiz_governed": GOV,
                              "postiz_oauth_bounce": {"status": "UNREACHABLE", "origin": O}})
    with sqlite3.connect(db) as con:
        st = con.execute("SELECT state FROM health_checks WHERE service_id='postiz-oauth-bounce'").fetchone()
    assert st == ("DEGRADED",)


TT_OK = {"POSTIZ_PROVIDER_TIKTOK": "OVERRIDE", "POSTIZ_TIKTOK_OAUTH_ORIGIN": "https://postiz-auth.goclearonline.cc",
         "POSTIZ_TIKTOK_SCOPES": "user.info.basic,video.upload",
         "POSTIZ_TIKTOK_REDIRECT_SITES_USING_ORIGIN": "2"}


def test_tiktok_override_healthy(monkeypatch, tmp_path):
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **OAUTH_OK, **TT_OK}, GOV)
    ctype, state, p = rows["postiz-tiktok-oauth"]
    assert (ctype, state) == ("CONFIGURATION", "HEALTHY") and p["issues"] == []
    assert p["effective_callback"] == "https://postiz-auth.goclearonline.cc/integrations/social/tiktok"
    assert p["video_publish_requested"] is False and p["direct_post_possible"] is False and p["third_party_redirect"] is False


def test_tiktok_override_detects_stock_scopes_missing_origin_and_drift(monkeypatch, tmp_path):
    stock = {**OAUTH_OK, "POSTIZ_IMAGE": "ghcr.io/gitroomhq/postiz-app:v2.26.0", "POSTIZ_PROVIDER_TIKTOK": "ORIGINAL",
             "POSTIZ_TIKTOK_OAUTH_ORIGIN": "", "POSTIZ_TIKTOK_REDIRECT_SITES_USING_ORIGIN": "0",
             "POSTIZ_TIKTOK_SCOPES": "video.list,user.info.basic,video.publish,video.upload,user.info.profile,user.info.stats"}
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **stock}, GOV)
    state, p = rows["postiz-tiktok-oauth"][1:]
    assert state == "DEGRADED"
    assert {"POSTIZ_VERSION_DRIFT", "PROVIDER_OVERRIDE_ORIGINAL:tiktok", "POSTIZ_TIKTOK_OAUTH_ORIGIN_MISSING",
            "TIKTOK_REDIRECT_NOT_OVERRIDDEN", "TIKTOK_SCOPES_UNEXPECTED", "TIKTOK_FORBIDDEN_SCOPE:video.publish",
            "TIKTOK_FORBIDDEN_SCOPE:video.list", "TIKTOK_FORBIDDEN_SCOPE:user.info.stats"} <= set(p["issues"])
    assert p["video_publish_requested"] is True
    assert p["effective_callback"] == "https://nexus-app-services.tailb1e262.ts.net/integrations/social/tiktok"


def test_bounce_fails_when_tiktok_page_missing():
    good = {f"{O}/integrations/social/{p}": (200, GOOD_HDRS, f'<script>var t="{P}/integrations/social/{p}";</script>')
            for p in ("facebook", "instagram")}
    r = tick._postiz_oauth_bounce(_fake_fetch(good))
    assert r["status"] == "FAIL" and r["callback_pages"]["tiktok"]["valid"] is False


def test_tiktok_three_scope_config_now_flagged(monkeypatch, tmp_path):
    rows = _rows(monkeypatch, tmp_path, {**BASE, "POSTIZ_INTEGRATIONS_ACTIVE": "0", **OAUTH_OK, **TT_OK,
                                          "POSTIZ_TIKTOK_SCOPES": "user.info.basic,user.info.profile,video.upload"}, GOV)
    assert "TIKTOK_SCOPES_UNEXPECTED" in rows["postiz-tiktok-oauth"][2]["issues"]
