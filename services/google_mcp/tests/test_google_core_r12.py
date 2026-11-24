"""r1.2 Google Core completion: read-only Search Console / GA4 / Business Profile / YouTube tools (fixtures only —
nothing here calls Google; fixture data is never live data)."""
import json

import pytest

from services.google_mcp import server
from nexus_agent_platform import google_scopes as gs
from nexus_agent_platform import google_workspace as gw


class Chain:
    """Minimal googleapiclient stand-in: api.sites().list(**kw).execute() -> responses['sites.list']."""

    def __init__(self, responses, path="", calls=None):
        self.r, self.p, self.calls = responses, path, calls if calls is not None else []

    def __getattr__(self, n):
        return Chain(self.r, f"{self.p}.{n}" if self.p else n, self.calls)

    def __call__(self, *a, **kw):
        self.calls.append((self.p, kw))
        return self

    def execute(self):
        v = self.r[self.p]
        if isinstance(v, Exception):
            raise v
        return v


class FakeHttpError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}")
        self.resp = type("R", (), {"status": status})()
        self.content = json.dumps(body).encode()


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    used = []
    monkeypatch.setattr(server, "_credentials", lambda credential_id=server.CREDENTIAL_ID: used.append(credential_id) or object())
    apis: dict = {}
    calls: list = []
    import googleapiclient.discovery as disc
    monkeypatch.setattr(disc, "build", lambda name, version, **kw: Chain(apis[name], calls=calls))
    return {"apis": apis, "used": used, "calls": calls}


def test_surface_is_read_only_plus_existing_governed_writes():
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert names == set(server.TOOL_NAMES) | set(server.WRITE_TOOL_NAMES) | set(server.CORE_READ_TOOL_NAMES) | set(server.AUTHORITY_TOOL_NAMES)
    forbidden = {"gmail_send", "drive_delete", "drive_share", "gbp_create_post", "gbp_reply_review", "gbp_update_location",
                 "youtube_upload", "youtube_update_video", "search_console_add_site", "ga4_create_property"}
    assert not names & forbidden
    # every new tool is described as READ ONLY
    for tool in server.mcp._tool_manager.list_tools():
        if tool.name in server.CORE_READ_TOOL_NAMES:
            assert tool.description.startswith("READ ONLY"), tool.name


def test_scope_profiles_and_separation():
    core = [gs.name(s) for s in gs.profile_scopes("core")]
    assert core == ["gmail.readonly", "gmail.modify", "calendar.events", "drive.file", "webmasters.readonly", "analytics.readonly", "business.manage"]
    assert [gs.name(s) for s in gs.profile_scopes("youtube")] == ["youtube.readonly", "youtube.upload", "yt-analytics.readonly"]
    assert [gs.name(s) for s in gs.profile_scopes("workspace")] == gw.SCOPE_NAMES
    with pytest.raises(ValueError, match="SCOPE_SEPARATION_VIOLATION"):
        gs.validate_separation("core", gs.profile_scopes("core") + [gs.G + "youtube.upload"])
    with pytest.raises(ValueError, match="SCOPE_SEPARATION_VIOLATION"):
        gs.validate_separation("youtube", gs.profile_scopes("youtube") + [gs.G + "drive.file"])
    assert gw.COMBINED_SCOPES == gs.profile_scopes("core")  # the old undefined name now means the Core profile
    assert gs.services_granted(core, "core") == {s: True for s in gs.PROFILES["core"]}
    assert gs.services_granted(["gmail.readonly"], "core")["ga4"] is False


def test_capabilities_declare_gated_writes_without_tools():
    item = server.google_get_capabilities()["items"][0]
    assert item["services"]["business_profile"]["declared_gated_writes_not_implemented"] == ["local_post_create", "business_information_update", "review_reply"]
    assert item["services"]["business_profile"]["governed_write_tools"] == []
    assert item["services"]["youtube"]["credential_id"] == "credential.google.youtube.upload.prod.v1"
    assert item["services"]["search_console"]["credential_id"] == "credential.google.workspace.prod.v1"
    assert item["secret_values_exposed"] is False


def test_search_console_query_maps_rows(fake):
    fake["apis"]["searchconsole"] = {"searchanalytics.query": {"rows": [{"keys": ["credit repair", "US"], "clicks": 3, "impressions": 120, "ctr": 0.025, "position": 14.2}]},
                                     "sites.list": {"siteEntry": [{"siteUrl": "sc-domain:example.com", "permissionLevel": "siteOwner"}]}}
    r = server.search_console_query("sc-domain:example.com", "2026-10-27", "2026-11-23", ["query", "country"])
    assert r["status"] == "ok" and r["read_only"] is True
    assert r["items"] == [{"keys": {"query": "credit repair", "country": "US"}, "clicks": 3, "impressions": 120, "ctr": 0.025, "position": 14.2}]
    body = [kw for p, kw in fake["calls"] if p == "searchanalytics.query"][0]["body"]
    assert body["dimensions"] == ["query", "country"] and body["type"] == "web"
    sites = server.search_console_list_sites()
    assert sites["items"][0]["permission_level"] == "siteOwner"
    assert set(fake["used"]) == {server.CREDENTIAL_ID}


def test_invalid_arguments_never_touch_credentials(fake):
    assert server.search_console_query("x", "2026-11-01", "2026-11-07", ["bogus"])["error"].startswith("invalid_request:dimension_not_allowlisted")
    assert server.ga4_run_report("abc", "2026-11-01", "2026-11-07")["error"] == "invalid_request:property_id_must_be_numeric"
    assert server.gbp_list_locations("locations/1")["error"].startswith("invalid_request:")
    assert server.youtube_analytics_report("2026-11-07", "2026-11-01")["error"] == "invalid_request:start_date_after_end_date"
    assert fake["used"] == []


def test_ga4_properties_and_report(fake):
    fake["apis"]["analyticsadmin"] = {"accountSummaries.list": {"accountSummaries": [{"account": "accounts/9", "displayName": "GoClear", "propertySummaries": [{"property": "properties/123456", "displayName": "goclearonline.cc", "propertyType": "PROPERTY_TYPE_ORDINARY"}]}]}}
    fake["apis"]["analyticsdata"] = {"properties.runReport": {"rows": [{"dimensionValues": [{"value": "google / organic"}], "metricValues": [{"value": "42"}, {"value": "30"}]}]}}
    p = server.ga4_list_properties()
    assert p["items"][0]["property_id"] == "123456" and p["resource"] == "GOOGLE_ANALYTICS"
    assert "data_streams" not in p["items"][0]
    fake["apis"]["analyticsadmin"]["properties.dataStreams.list"] = {"dataStreams": [{"name": "properties/123456/dataStreams/1", "type": "WEB_DATA_STREAM", "displayName": "site", "webStreamData": {"defaultUri": "https://goclearonline.cc", "measurementId": "G-TEST"}}]}
    ps = server.ga4_list_properties(include_streams=True)
    assert ps["items"][0]["data_streams"][0]["default_uri"] == "https://goclearonline.cc"
    h = server.ga4_run_report("123456", "2026-10-27", "2026-11-23", ["sessions"], ["hostName"])
    assert h["status"] == "ok"
    r = server.ga4_run_report("properties/123456", "2026-10-27", "2026-11-23", ["sessions", "engagedSessions"], ["sessionSourceMedium"])
    assert r["items"] == [{"dimensions": {"sessionSourceMedium": "google / organic"}, "metrics": {"sessions": "42", "engagedSessions": "30"}}]


def test_gbp_reads_and_error_classification(fake, monkeypatch):
    fake["apis"]["mybusinessaccountmanagement"] = {"accounts.list": FakeHttpError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded", "details": [{"reason": "RATE_LIMIT_EXCEEDED", "metadata": {"quota_limit_value": "0"}}]}})}
    r = server.gbp_list_accounts()
    assert r["status"] == "error" and r["error"].endswith("HTTP_429:API_ACCESS_NOT_APPROVED")
    monkeypatch.setattr(server, "_bearer_get", lambda creds, url, params=None: {"reviews": [{"reviewId": "r1", "starRating": "FIVE", "comment": "x" * 900, "reviewReply": {"comment": "thanks"}}], "averageRating": 5, "totalReviewCount": 1})
    rv = server.gbp_list_reviews("accounts/1", "locations/22")
    assert rv["items"][0]["has_reply"] is True and len(rv["items"][0]["comment"]) == 500 and rv["items"][0]["total_review_count"] == 1


def test_youtube_tools_use_the_separate_youtube_grant(fake):
    fake["apis"]["youtube"] = {"channels.list": {"items": [{"id": "UC1", "snippet": {"title": "Nexus Operations Hub", "customUrl": "@nexus"}, "statistics": {"subscriberCount": "5"}, "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}}
    r = server.youtube_channel_identity()
    assert r["items"][0]["channel_id"] == "UC1" and r["items"][0]["uploads_playlist"] == "UU1"
    assert fake["used"] == [server.YOUTUBE_CREDENTIAL_ID]


def test_classify_google_error_fixtures():
    disabled = FakeHttpError(403, {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "Google Search Console API has not been used in project 1 before or it is disabled.", "details": [{"reason": "SERVICE_DISABLED", "metadata": {"activationUrl": "https://console.developers.google.com/apis/api/searchconsole.googleapis.com/overview?project=1"}}]}})
    c = gw.classify_google_error(disabled)
    assert c["status"] == "API_DISABLED" and "searchconsole.googleapis.com" in c["activation_url"]
    scope = FakeHttpError(403, {"error": {"code": 403, "message": "Request had insufficient authentication scopes.", "details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]}})
    assert gw.classify_google_error(scope)["status"] == "SCOPE_NOT_GRANTED"
    assert gw.classify_google_error(FakeHttpError(403, {"error": {"message": "The caller does not have permission"}}))["status"] == "PERMISSION_DENIED"
    assert gw.classify_google_error(RuntimeError("x"))["status"] == "ERROR"
