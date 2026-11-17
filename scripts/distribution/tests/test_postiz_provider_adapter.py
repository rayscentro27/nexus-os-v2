"""Postiz LAB adapter + n8n orchestration: Nexus-owned receipts, no publishing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "distribution"))

import postiz_provider_adapter as pa  # noqa: E402

TOKEN = "FAKE_WEBHOOK_TOKEN_never_print"


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))


def n8n(status, body_fn):
    calls = []
    def http(method, url, headers, body=None, timeout=30):
        calls.append((method, url, headers.get("X-Nexus-Webhook-Token")))
        req = json.loads(body) if body else {}
        return status, body_fn(req)
    return http, calls


def receipts():
    return list(reversed(pa.persistence.read_records(pa.RECEIPTS)))


def test_round_trip_completed_writes_requested_then_completed():
    http, calls = n8n(200, lambda r: {"request_id": r["request_id"], "ok": True, "postiz_http_status": 200,
                                      "postiz_connected": True, "n8n_execution_id": "9", "live_publish": False})
    res = pa.run_n8n_certification("health_check", http=http, token_provider=lambda: TOKEN)
    assert res["state"] == "COMPLETED" and res["outcome"] == "POSTIZ_REACHED_VIA_N8N"
    rs = receipts()
    assert [r["state"] for r in rs] == ["REQUESTED", "COMPLETED"]
    assert rs[0]["provider_route"]["primary_provider"] == "POSTIZ" and rs[0]["provider_route"]["channel_environment"] == "LAB"
    assert all(r["authority"] == "NEXUS" and r["live_publish"] is False for r in rs)
    assert calls[0][0] == "POST" and calls[0][1] == pa.N8N_CERT_WEBHOOK and calls[0][2] == TOKEN
    store = "".join(p.read_text() for p in Path(pa.persistence.governed_data_dir()).glob("*.jsonl"))
    assert TOKEN not in store and TOKEN not in json.dumps(res)


def test_provider_failure_is_failed_not_lost():
    http, _ = n8n(502, lambda r: {"request_id": r["request_id"], "ok": False, "postiz_http_status": 404, "n8n_execution_id": "10"})
    res = pa.run_n8n_certification("invalid_endpoint_test", http=http, token_provider=lambda: TOKEN)
    assert res["state"] == "FAILED" and res["outcome"] == "PROVIDER_FAILURE_REPORTED_BY_N8N" and res["postiz_http_status"] == 404
    assert [r["state"] for r in receipts()] == ["REQUESTED", "FAILED"]


def test_n8n_unreachable_still_recorded():
    http, _ = n8n(None, lambda r: {"transport_error": "URLError"})
    res = pa.run_n8n_certification("health_check", http=http, token_provider=lambda: TOKEN)
    assert res["state"] == "FAILED" and res["outcome"] == "N8N_CONNECTION_UNAVAILABLE"


def test_mismatched_request_id_never_counts_as_success():
    http, _ = n8n(200, lambda r: {"request_id": "someone_else", "ok": True})
    res = pa.run_n8n_certification("health_check", http=http, token_provider=lambda: TOKEN)
    assert res["state"] == "FAILED" and res["request_id_echoed"] is False


def test_rejected_by_n8n_validation():
    http, _ = n8n(422, lambda r: {"request_id": r["request_id"], "ok": False, "rejected": True})
    res = pa.run_n8n_certification("health_check", http=http, token_provider=lambda: TOKEN)
    assert res["outcome"] == "REJECTED_BY_N8N_VALIDATION"


def test_disallowed_action_and_publish_guard():
    with pytest.raises(ValueError):
        pa.run_n8n_certification("publish_post", http=lambda *a, **k: (200, {}), token_provider=lambda: TOKEN)
    assert receipts() == []
    with pytest.raises(PermissionError):
        pa.PostizAdapter(http=lambda *a, **k: (200, {}), key_provider=lambda: "k").publish()


def test_postiz_health_blocked_by_auth_without_integrations():
    def http(method, url, headers, body=None, timeout=30):
        return (200, {"connected": True}) if url.endswith("is-connected") else (200, [])
    h = pa.PostizAdapter(http=http, key_provider=lambda: "k").health()
    assert h["health"] == "HEALTHY" and h["execution"] == "BLOCKED_BY_AUTH" and h["connected_social_integrations"] == 0


# ---- account binding, capability discovery, draft-only certification -------
def _doc(verified=True):
    doc = pa.load_bindings()
    for b in doc["bindings"]:
        if b["channel_account_id"] == "acc_holiday_facebook_01":
            b["postiz_integration_id"] = "int_fb"
            b["verified_internal_id_at"] = "2026-11-13T00:00:00Z" if verified else None
    return doc


INTEGRATIONS = [
    {"id": "int_fb", "name": "Raytestpage", "identifier": "facebook", "profile": "raytestpage", "disabled": False},
    {"id": "int_x", "name": "Something", "identifier": "instagram", "profile": "x", "disabled": False},
    {"id": "int_gc", "name": "Clear Credentials", "identifier": "facebook", "profile": "", "disabled": False},
]


def test_classification_binds_only_verified_and_flags_goclear():
    r = pa.classify_integrations(INTEGRATIONS, _doc())
    status = {a["postiz_integration_id"]: a["binding_status"] for a in r["accounts"]}
    assert status == {"int_fb": "BOUND_VERIFIED", "int_x": "UNBOUND_QUARANTINED", "int_gc": "ISOLATION_VIOLATION"}
    assert r["usable_accounts"] == ["acc_holiday_facebook_01"] and r["venture_isolation"] == "FAIL"
    assert pa.classify_integrations(INTEGRATIONS[:1], _doc(verified=False))["accounts"][0]["usable"] is False


def test_capability_reads_auth_url_without_keeping_it():
    ok = pa.describe_auth_url("facebook", 200, "https://www.facebook.com/v20.0/dialog/oauth?client_id=123&redirect_uri=https%3A%2F%2Fpostiz.example.ts.net%2Fintegrations%2Fsocial%2Ffacebook&state=SECRETSTATE")
    assert ok["oauth_ready"] and ok["redirect_origin"] == "postiz.example.ts.net" and "SECRETSTATE" not in json.dumps(ok)
    assert not pa.describe_auth_url("facebook", 200, "https://x/?client_id=undefined&redirect_uri=http%3A%2F%2Fh%3A4007%2Fi")["oauth_ready"]
    tt = pa.describe_auth_url("tiktok", 200, "https://www.tiktok.com/v2/auth/authorize/?client_key=k&redirect_uri=https%3A%2F%2Fredirectmeto.com%2Fhttp%3A%2F%2Fh")
    assert tt["third_party_redirect"] and not tt["oauth_ready"]


class FakePostiz:
    def __init__(self, state="DRAFT", integration="int_fb", readback_error=False):
        self.calls, self.state, self.integration, self.deleted = [], state, integration, set()
        self.readback_error = readback_error

    def __call__(self, method, url, headers, body=None, timeout=30):
        self.calls.append((method, url.split("/api")[-1].split("?")[0], json.loads(body) if body else None))
        if method == "GET" and url.endswith("/integrations"):
            return 200, INTEGRATIONS[:1]
        if method == "POST":
            return 201, [{"postId": "post_1", "integration": "int_fb"}]
        if method == "GET" and "/posts?" in url:
            if self.readback_error and not self.deleted:
                raise TimeoutError("readback")
            posts = [{"id": "post_1", "state": self.state, "integration": {"id": self.integration}}]
            return 200, {"posts": [p for p in posts if p["id"] not in self.deleted]}
        if method == "DELETE":
            self.deleted.add(url.rsplit("/", 1)[-1])
            return 200, {}
        return 404, {}


IDS_OK = lambda: [{"id": "int_fb", "provider": "facebook", "internal_id": "1722332634511930", "name": "Raytestpage"}]


def adapter(fake):
    return pa.PostizAdapter(http=fake, key_provider=lambda: "FAKE_POSTIZ_KEY_never_print")


def test_draft_certification_round_trip_is_draft_only_and_receipted():
    fake = FakePostiz()
    r = adapter(fake).create_certification_draft("acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026",
                                                 "Nexus Postiz draft certification - not for publishing", bindings_doc=_doc(),
                                                 internal_ids=IDS_OK)
    assert r["state"] == "COMPLETED" and r["outcome"] == "POSTIZ_DRAFT_CERTIFIED_NOT_PUBLISHED"
    post = next(c for c in fake.calls if c[0] == "POST")
    assert post[2]["type"] == "draft" and post[2]["posts"][0]["integration"]["id"] == "int_fb"
    assert ("DELETE", "/public/v1/posts/post_1", None) in fake.calls
    states = [x["state"] for x in receipts() if x.get("action") == "certification_draft"]
    assert states == ["REQUESTED", "COMPLETED"]
    stages = [(x["action"], x["state"]) for x in receipts() if x.get("action", "").startswith("certification_draft_")]
    assert stages == [("certification_draft_create", "COMPLETED"), ("certification_draft_readback", "COMPLETED"),
                      ("certification_draft_delete", "COMPLETED")]
    assert r["remaining_after_delete"] == 0 and r["readback_integration_ids"] == ["int_fb"]
    assert r["identity"]["platform_account_id"] == "1722332634511930"
    store = "".join(p.read_text() for p in Path(pa.persistence.governed_data_dir()).glob("*.jsonl"))
    assert "FAKE_POSTIZ_KEY_never_print" not in store


def test_draft_readback_not_draft_fails():
    r = adapter(FakePostiz(state="QUEUE")).create_certification_draft(
        "acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026", "t", bindings_doc=_doc(), internal_ids=IDS_OK)
    assert r["state"] == "FAILED" and r["outcome"] == "POSTIZ_DRAFT_READBACK_MISMATCH"


@pytest.mark.parametrize("account,venture,doc,reason", [
    ("acc_holiday_facebook_01", "vnt_goclear_credit_2026", True, "VENTURE_ACCOUNT_SCOPE_MISMATCH"),
    ("acc_goclear_facebook_01", "vnt_goclear_credit_2026", True, "CHANNEL_ACCOUNT_NOT_BOUND_TO_POSTIZ"),
    ("acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026", False, "POSTIZ_BINDING_NOT_VERIFIED"),
])
def test_draft_fails_closed_without_calling_postiz(account, venture, doc, reason):
    fake = FakePostiz()
    r = adapter(fake).create_certification_draft(account, venture, "t", bindings_doc=_doc(verified=doc),
                                                 internal_ids=IDS_OK)
    assert r["state"] == "BLOCKED" and r["outcome"] == reason
    assert not [c for c in fake.calls if c[0] in ("POST", "DELETE")]


def test_publish_remains_blocked():
    with pytest.raises(PermissionError, match="BLOCKED_BY_OWNER"):
        pa.PostizAdapter(http=FakePostiz(), key_provider=lambda: "k").publish()


def test_verify_bindings_exact_id_only_and_goclear_never_bound():
    doc = pa.load_bindings()
    ig_before = dict(next(b for b in doc["bindings"] if b["channel_account_id"] == "acc_holiday_instagram_01"))
    rows = [{"id": "int_fb", "provider": "facebook", "internal_id": "1722332634511930", "name": "Raytestpage"},
            {"id": "int_gc", "provider": "facebook", "internal_id": "999", "name": "Clear Credentials"},
            {"id": "int_ig_wrong", "provider": "instagram", "internal_id": "123", "name": "the612amritual"}]
    r = pa.verify_bindings(rows, doc, path=None)
    assert r["bound"] == [{"channel_account_id": "acc_holiday_facebook_01", "postiz_integration_id": "int_fb"}]
    reasons = {u["id"]: u["reason"] for u in r["unbound"]}
    assert reasons == {"int_gc": "FORBIDDEN_IDENTITY", "int_ig_wrong": "NO_EXACT_NEXUS_BINDING"}
    ig = next(b for b in doc["bindings"] if b["channel_account_id"] == "acc_holiday_instagram_01")
    assert ig == ig_before  # a wrong-id Instagram row never changes the Instagram binding


@pytest.mark.parametrize("rows,reason", [
    ([{"id": "int_fb", "provider": "facebook", "internal_id": "999", "name": "Raytestpage"}], "POSTIZ_PLATFORM_IDENTITY_MISMATCH"),
    ([], "POSTIZ_PLATFORM_IDENTITY_MISMATCH"),
    ([{"id": "int_fb", "provider": "facebook", "internal_id": "1722332634511930", "name": "Clear Credentials"}],
     "POSTIZ_FORBIDDEN_IDENTITY"),
    ([{"id": "int_fb", "provider": "facebook", "internal_id": "1722332634511930", "name": "Some Other Page"}],
     "POSTIZ_ACCOUNT_NAME_MISMATCH"),
    (IDS_OK() + [{"id": "int_fb2", "provider": "facebook", "internal_id": "1722332634511930", "name": "Raytestpage"}],
     "POSTIZ_DUPLICATE_PROVIDER_INTEGRATION"),
])
def test_draft_blocks_on_platform_identity(rows, reason):
    fake = FakePostiz()
    r = adapter(fake).create_certification_draft("acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026", "t",
                                                 bindings_doc=_doc(), internal_ids=lambda: rows)
    assert r["state"] == "BLOCKED" and r["outcome"] == reason
    assert not [c for c in fake.calls if c[0] in ("POST", "DELETE")]


def test_draft_blocks_when_identity_lookup_fails():
    def boom():
        raise OSError("ssh")
    fake = FakePostiz()
    r = adapter(fake).create_certification_draft("acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026", "t",
                                                 bindings_doc=_doc(), internal_ids=boom)
    assert r["state"] == "BLOCKED" and r["outcome"] == "POSTIZ_IDENTITY_LOOKUP_FAILED:OSError"
    assert not [c for c in fake.calls if c[0] == "POST"]


def test_readback_wrong_integration_fails_and_still_deletes():
    fake = FakePostiz(integration="int_other")
    r = adapter(fake).create_certification_draft("acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026", "t",
                                                 bindings_doc=_doc(), internal_ids=IDS_OK)
    assert r["state"] == "FAILED" and r["outcome"] == "POSTIZ_DRAFT_READBACK_MISMATCH"
    assert ("DELETE", "/public/v1/posts/post_1", None) in fake.calls and r["remaining_after_delete"] == 0


def test_delete_runs_even_if_readback_raises():
    fake = FakePostiz(readback_error=True)
    with pytest.raises(TimeoutError):
        adapter(fake).create_certification_draft("acc_holiday_facebook_01", "vnt_holiday_commerce_pilot_2026", "t",
                                                 bindings_doc=_doc(), internal_ids=IDS_OK)
    assert ("DELETE", "/public/v1/posts/post_1", None) in fake.calls
    assert [x["state"] for x in receipts() if x.get("action") == "certification_draft_delete"] == ["COMPLETED"]


def _ig_doc():
    doc = pa.load_bindings()
    for b in doc["bindings"]:
        if b["channel_account_id"] == "acc_holiday_instagram_01":
            b["postiz_integration_id"], b["verified_internal_id_at"] = "int_ig", "2026-11-13T00:00:00Z"
    return doc


def _row(i, ext, name, profile, provider="instagram", **flags):
    return {"id": i, "provider": provider, "internal_id": ext, "name": name, "profile": profile,
            "deleted": False, "disabled": False, "in_between_steps": False, **flags}


IG_OK = [_row("int_ig", "17841480885973564", "Ray", "the612amritual")]


class FakeIG(FakePostiz):
    def __call__(self, method, url, headers, body=None, timeout=30):
        if method == "GET" and url.endswith("/integrations"):
            self.calls.append((method, "/public/v1/integrations", None))
            return 200, [{"id": "int_ig", "name": "Ray", "identifier": "instagram", "profile": "the612amritual", "disabled": False}]
        self.integration = "int_ig"
        return super().__call__(method, url, headers, body, timeout)


def test_instagram_draft_uses_feed_post_type_and_username_identity():
    fake = FakeIG()
    r = adapter(fake).create_certification_draft("acc_holiday_instagram_01", "vnt_holiday_commerce_pilot_2026", "t",
                                                 bindings_doc=_ig_doc(), internal_ids=lambda: IG_OK)
    assert r["state"] == "COMPLETED", r.get("outcome")
    post = next(c for c in fake.calls if c[0] == "POST")[2]
    assert post["type"] == "draft"
    assert post["posts"][0]["settings"] == {"__type": "instagram", "post_type": "post", "collaborators": []}
    assert r["identity"]["username"] == "the612amritual" and r["identity"]["platform_account_id"] == "17841480885973564"


@pytest.mark.parametrize("rows,reason", [
    ([_row("int_ig", "17841480885973564", "Ray", "someoneelse")], "POSTIZ_USERNAME_MISMATCH"),
    (IG_OK + [_row("int_old", "17841480885973564", "Ray", "the612amritual", deleted=True)],
     "POSTIZ_DUPLICATE_PROVIDER_INTEGRATION"),
    ([_row("int_ig", "17841480885973564", "Ray", "the612amritual", in_between_steps=True)],
     "POSTIZ_PLATFORM_IDENTITY_MISMATCH"),
])
def test_instagram_identity_guards(rows, reason):
    fake = FakeIG()
    r = adapter(fake).create_certification_draft("acc_holiday_instagram_01", "vnt_holiday_commerce_pilot_2026", "t",
                                                 bindings_doc=_ig_doc(), internal_ids=lambda: rows)
    assert r["state"] == "BLOCKED" and r["outcome"] == reason
    assert not [c for c in fake.calls if c[0] == "POST"]


def test_goclear_and_rayscentro_never_bind(tmp_path):
    doc = pa.load_bindings()
    rows = [_row("i1", "17841480265043148", "Clear Credentials", "goclearonline"),
            _row("i2", "17841480265043148", "Renamed", "renamed"),              # forbidden by id alone
            _row("i3", "131069194210954", "Clear Credentials", "", provider="facebook"),
            _row("i4", "17841400171252786", "Rayscentro", "rayscentro")]
    r = pa.verify_bindings(rows, doc, path=None)
    assert r["bound"] == []
    reasons = {u["id"]: u["reason"] for u in r["unbound"]}
    assert reasons == {"i1": "FORBIDDEN_IDENTITY", "i2": "FORBIDDEN_IDENTITY", "i3": "FORBIDDEN_IDENTITY",
                       "i4": "NO_EXACT_NEXUS_BINDING"}


def test_parse_internal_id_rows_keeps_pipes_in_name():
    rows = pa.parse_internal_id_rows("a|instagram|1|user|f|f|t|Name | With Pipe\nbad|row\n")
    assert rows == [{"id": "a", "provider": "instagram", "internal_id": "1", "profile": "user", "deleted": False,
                     "disabled": False, "in_between_steps": True, "name": "Name | With Pipe"}]


def test_describe_auth_url_reports_scopes_and_publish_flag():
    u = ("https://www.tiktok.com/v2/auth/authorize/?client_key=abc&redirect_uri="
         "https%3A%2F%2Fpostiz-auth.goclearonline.cc%2Fintegrations%2Fsocial%2Ftiktok&state=s&response_type=code"
         "&scope=user.info.basic%2Cuser.info.profile%2Cvideo.upload")
    d = pa.describe_auth_url("tiktok", 200, u)
    assert d["redirect_uri"] == "https://postiz-auth.goclearonline.cc/integrations/social/tiktok"
    assert d["requested_scopes"] == ["user.info.basic", "user.info.profile", "video.upload"]
    assert d["publish_scope_requested"] is False and d["third_party_redirect"] is False and d["oauth_ready"] is True
    d = pa.describe_auth_url("tiktok", 200, u.replace("video.upload", "video.upload%2Cvideo.publish"))
    assert d["publish_scope_requested"] is True


def test_tiktok_draft_settings_never_direct_post():
    st = pa.DRAFT_PROVIDER_SETTINGS["tiktok"]
    assert st["content_posting_method"] == "UPLOAD" and st["privacy_level"] == "SELF_ONLY"
    assert not any(st[k] for k in ("duet", "stitch", "comment", "brand_content_toggle", "brand_organic_toggle"))


def test_tiktok_binding_is_open_id_primary():
    b = next(x for x in pa.load_bindings()["bindings"] if x["channel_account_id"] == "acc_holiday_tiktok_01")
    assert b["venture_id"] == "vnt_holiday_commerce_pilot_2026"
    assert b["expected_external_id"] == b["tiktok_open_id"].replace("-", "")
    assert b["sandbox_target_username"] == "nexusaiwealth" and b["expected_username"] is None
    assert "holidayritualmugs" not in json.dumps(pa.load_bindings())
