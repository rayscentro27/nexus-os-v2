"""Google Core consent + verifiers (fixtures; no Google call, no Keychain read, no consent)."""
import json
import sys
import types

import pytest

from nexus_agent_platform import google_workspace as gw
from nexus_agent_platform import youtube_upload as yu

CLIENT = "1088441762622-abc.apps.googleusercontent.com"


class Chain:
    def __init__(self, responses, path=""):
        self.r, self.p = responses, path

    def __getattr__(self, n):
        return Chain(self.r, f"{self.p}.{n}" if self.p else n)

    def __call__(self, *a, **kw):
        return self

    def execute(self):
        v = self.r.get(self.p, {})
        if isinstance(v, Exception):
            raise v
        return v


class FakeCreds:
    def __init__(self, **kw):
        self.token = "ACCESS-TOKEN-NEVER-PRINTED"

    def refresh(self, request):
        return None


class TokenInfo:
    def __init__(self, scopes, aud=CLIENT):
        self._j = {"scope": " ".join("https://www.googleapis.com/auth/" + s for s in scopes), "aud": aud}

    def raise_for_status(self):
        return None

    def json(self):
        return self._j


def _install(monkeypatch, scopes, apis, aud=CLIENT, refresh="SECRET-REFRESH"):
    monkeypatch.setattr(gw, "_configured", lambda: {"client_id": "CONFIGURED", "client_secret": "CONFIGURED", "refresh_token": "CONFIGURED"})
    monkeypatch.setattr(gw, "_keychain_value", lambda cid, part: {"client_id": CLIENT, "client_secret": "SECRET-CLIENT", "refresh_token": refresh}[part])
    import google.oauth2.credentials as goc
    import requests
    import googleapiclient.discovery as disc
    monkeypatch.setattr(goc, "Credentials", FakeCreds)
    monkeypatch.setattr(requests, "get", lambda *a, **kw: TokenInfo(scopes, aud))
    monkeypatch.setattr(disc, "build", lambda name, version, **kw: Chain(apis.get(name, {})))


CORE = ["gmail.readonly", "gmail.modify", "calendar.events", "drive.file", "webmasters.readonly", "analytics.readonly", "business.manage"]


def test_core_verifier_passes_and_identifies_properties(monkeypatch):
    _install(monkeypatch, CORE, {
        "searchconsole": {"sites.list": {"siteEntry": [{"siteUrl": "sc-domain:goclearonline.cc", "permissionLevel": "siteOwner"}]}},
        "analyticsadmin": {"accountSummaries.list": {"accountSummaries": [{"account": "accounts/1", "displayName": "GoClear", "propertySummaries": [{"property": "properties/77", "displayName": "goclear"}]}]}},
        "mybusinessaccountmanagement": {"accounts.list": {"accounts": [{"name": "accounts/5", "accountName": "GoClear", "type": "PERSONAL"}]}},
        "mybusinessbusinessinformation": {"accounts.locations.list": {"locations": [{"name": "locations/9", "title": "GoClear Credit"}]}},
    })
    r = gw.certify_read_only("core")
    assert r["status"] == "GOOGLE_WORKSPACE_READ_VERIFIED" and r["oauth_client_match"] is True
    assert (r["calendar_read"], r["gmail_read"], r["drive_read"]) == ("PASS", "PASS", "PASS")
    assert {k: v["status"] for k, v in r["services"].items()} == {"search_console": "PASS", "ga4": "PASS", "business_profile": "PASS"}
    assert r["inventory"]["search_console_sites"][0]["site_url"] == "sc-domain:goclearonline.cc"
    assert r["inventory"]["ga4_properties"][0]["property"] == "properties/77"
    assert r["inventory"]["business_profile_locations"][0]["title"] == "GoClear Credit"
    assert r["oauth_client_project_number"] == "1088441762622" and r["youtube_scope_present"] is False
    text = json.dumps(r)
    assert "SECRET" not in text and "ACCESS-TOKEN" not in text and r["secret_values_exposed"] is False and r["mutations_performed"] is False


def test_core_verifier_reports_partial_grant_and_disabled_api(monkeypatch):
    class Disabled(Exception):
        resp = type("R", (), {"status": 403})()
        content = json.dumps({"error": {"message": "Google Analytics Admin API has not been used in project 1088441762622 before or it is disabled.", "details": [{"reason": "SERVICE_DISABLED", "metadata": {"activationUrl": "https://console.developers.google.com/apis/api/analyticsadmin.googleapis.com/overview?project=1088441762622"}}]}}).encode()
    # owner unticked Business Profile on the granular consent screen; GA4 API is not enabled on the project
    _install(monkeypatch, [s for s in CORE if s != "business.manage"], {"searchconsole": {"sites.list": {"siteEntry": []}}, "analyticsadmin": {"accountSummaries.list": Disabled()}})
    r = gw.certify_read_only("core")
    assert r["status"] == "GOOGLE_WORKSPACE_READ_VERIFIED"
    assert r["services"]["search_console"]["status"] == "NO_ACCESSIBLE_PROPERTIES"
    assert r["services"]["ga4"]["status"] == "API_DISABLED" and "analyticsadmin" in r["services"]["ga4"]["activation_url"]
    assert r["services"]["business_profile"] == {"status": "SCOPE_NOT_GRANTED", "missing_scopes": ["business.manage"]}


def test_verifier_rejects_token_from_another_client(monkeypatch):
    _install(monkeypatch, CORE, {}, aud="999-other.apps.googleusercontent.com")
    r = gw.certify_read_only("workspace")
    assert r["status"] == "GOOGLE_OAUTH_CLIENT_MISMATCH" and r["oauth_client_match"] is False and r["gmail_read"] == "NOT_RUN"


def test_refresh_failure_is_truthful(monkeypatch):
    _install(monkeypatch, CORE, {})

    class Dead(FakeCreds):
        def refresh(self, request):
            raise RuntimeError("invalid_grant")
    import google.oauth2.credentials as goc
    monkeypatch.setattr(goc, "Credentials", Dead)
    r = gw.certify_read_only("core")
    assert r["status"] == "GOOGLE_TOKEN_REFRESH_FAILED" and r["failed_stage"] == "TOKEN_REFRESH"
    assert {v["status"] for v in r["services"].values()} == {"TOKEN_UNAVAILABLE"}


def test_reauthorize_profile_core_requests_core_scopes_only(monkeypatch):
    seen = {}

    class Flow:
        @classmethod
        def from_client_config(cls, cfg, scopes):
            seen["scopes"] = scopes
            return cls()

        def run_local_server(self, **kw):
            seen["kw"] = kw
            return types.SimpleNamespace(refresh_token="NEW-REFRESH")
    monkeypatch.setattr(gw, "_configured", lambda: {"client_id": "CONFIGURED", "client_secret": "CONFIGURED", "refresh_token": "CONFIGURED"})
    monkeypatch.setattr(gw, "_keychain_value", lambda cid, part: {"client_id": CLIENT, "client_secret": "S"}[part])
    stored = []
    monkeypatch.setattr(gw, "store_keychain", lambda cid, part, value, replace=False: stored.append((cid, part)) or "STORED")
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", types.SimpleNamespace(InstalledAppFlow=Flow))
    r = gw.reauthorize_existing(open_browser=False, profile="core")
    assert [s.rsplit("/", 1)[-1] for s in seen["scopes"]] == CORE
    assert seen["kw"]["host"] == "127.0.0.1" and seen["kw"]["prompt"] == "consent"
    assert stored == [("credential.google.workspace.prod.v1", "refresh_token")]  # same credential; client untouched
    assert r["profile"] == "core" and r["oauth_client_replaced"] is False and "NEW-REFRESH" not in json.dumps(r)


def test_youtube_verifier_checks_identity_scopes_client_and_reads(monkeypatch):
    monkeypatch.setattr(yu, "_get_oauth_client", lambda: {"client_id": CLIENT, "client_secret": "S", "token_uri": "t", "auth_uri": "a", "redirect_uris": []})
    import google.oauth2.credentials as goc
    import requests
    import googleapiclient.discovery as disc
    monkeypatch.setattr(goc, "Credentials", FakeCreds)
    monkeypatch.setattr(requests, "get", lambda *a, **kw: TokenInfo(["youtube.readonly", "youtube.upload", "yt-analytics.readonly"]))
    apis = {"youtube": {"channels.list": {"items": [{"id": "UC1", "snippet": {"title": "Nexus Operations Hub"}, "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}, "playlistItems.list": {"items": []}},
            "youtubeAnalytics": {"reports.query": {"rows": []}}}
    monkeypatch.setattr(disc, "build", lambda name, version, **kw: Chain(apis[name]))
    r = yu.validate_youtube_token("REFRESH")
    assert r["status"] == "AVAILABLE" and r["oauth_client_match"] is True and r["scope_separation_ok"] is True
    assert r["video_read"] == "PASS" and r["analytics_read"] == "PASS" and r["channels"][0]["channel_id"] == "UC1"
    assert r["mutations_performed"] is False and "REFRESH" not in json.dumps(r)
    monkeypatch.setattr(requests, "get", lambda *a, **kw: TokenInfo(["youtube.readonly", "youtube.upload", "drive.file"]))
    assert yu.validate_youtube_token("REFRESH")["status"] == "SCOPE_SEPARATION_VIOLATION"
    monkeypatch.setattr(requests, "get", lambda *a, **kw: TokenInfo(["youtube.readonly", "youtube.upload"], aud="other"))
    assert yu.validate_youtube_token("REFRESH")["status"] == "OAUTH_CLIENT_MISMATCH"


def test_youtube_scopes_never_include_workspace():
    with pytest.raises(ValueError):
        yu._validate_youtube_scopes(yu.YOUTUBE_SCOPES + ["https://www.googleapis.com/auth/drive.file"])
    assert yu.YOUTUBE_SCOPE_NAMES == ["youtube.upload", "youtube.readonly", "yt-analytics.readonly"]
