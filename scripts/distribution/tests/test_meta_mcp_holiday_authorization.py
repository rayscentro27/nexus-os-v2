"""Meta Social Technologies MCP integration + Holiday owner-authorization contracts."""
from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.parse
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "distribution"))

from nexus_agent_platform import credential_control_plane as ccp  # noqa: E402
import meta_holiday_owner_authorize as auth  # noqa: E402

HOLIDAY = "credential.meta.social.holiday.prod.v1"
GOCLEAR = "credential.meta.social.goclear.prod.v1"
REQUIRED = {"pages_show_list", "pages_read_engagement", "pages_manage_posts",
            "instagram_basic", "instagram_content_publish", "business_management"}
FAKE_SECRET = "FAKE_APP_SECRET_do_not_print"
FAKE_USER = "FAKE_USER_TOKEN_do_not_print"
FAKE_PAGE = "FAKE_PAGE_TOKEN_do_not_print"


def _registry():
    d = json.loads((ROOT / "configs/nexus_credential_registry.json").read_text())
    return d["credentials"] if isinstance(d, dict) else d


def test_existing_meta_app_reused_and_no_app_creation_path():
    q = urllib.parse.parse_qs(urllib.parse.urlparse(auth.consent_url("s")).query)
    assert q["client_id"] == ["1889438111704778"]
    assert set(q["scope"][0].split(",")) == REQUIRED
    assert q["response_type"] == ["code"]
    src = (ROOT / "scripts/distribution/meta_holiday_owner_authorize.py").read_text()
    assert "app_create" not in src and "business_create" not in src


def test_single_holiday_credential_and_goclear_unchanged():
    metas = [e for e in _registry() if e.get("provider") == "meta"]
    holiday = [e for e in metas if "vnt_holiday_commerce_pilot_2026" in e.get("venture_binding", [])]
    assert [e["credential_id"] for e in holiday] == [HOLIDAY]
    goclear = next(e for e in metas if e["credential_id"] == GOCLEAR)
    assert goclear["venture_binding"] == ["vnt_goclear_credit_2026"]
    assert goclear["status"] == "AVAILABLE"
    assert "131069194210954" in goclear["account_scope"]
    assert "1722332634511930" in next(e for e in metas if e["credential_id"] == HOLIDAY)["account_scope"]


def test_cross_venture_aliases_isolated():
    by_id = {e["credential_id"]: e for e in _registry()}
    h = set(by_id[HOLIDAY]["canonical_aliases"].values()) | {a for v in by_id[HOLIDAY].get("legacy_aliases", {}).values() for a in v}
    g = set(by_id[GOCLEAR]["canonical_aliases"].values()) | {a for v in by_id[GOCLEAR].get("legacy_aliases", {}).values() for a in v}
    assert not (h & g), "Holiday must never resolve GoClear secrets"


def test_meta_mcp_registered_as_developer_capability_not_social_credential():
    caps = json.loads((ROOT / "data/runtime/nexus_capability_registry.json").read_text())["capabilities"]
    cap = next(c for c in caps if c["capability_id"] == "meta.developer_platform.mcp")
    assert cap["authority_class"] == "developer_management"
    assert {"meta.app.inspect", "meta.permissions.inspect", "meta.docs.search"} <= set(cap["sub_capabilities"])
    assert not any(e["credential_id"].startswith("meta.developer") or "devtools" in e["credential_id"] for e in _registry())


def test_meta_developer_tasks_route_through_official_mcp_first():
    tools = json.loads((ROOT / "configs/nexus_tool_access_registry.json").read_text())["tools"]
    t = next(x for x in tools if x["tool_name"] == "meta_devtools_mcp")
    order = t["routing_policy"]["preference_order"]
    assert order[0] == "meta_devtools_mcp"
    assert order.index("meta_devtools_mcp") < order.index("manual_graph_api_explorer_instructions")
    assert "devtools_app_create" in t["blocked_commands"]
    assert t["endpoint"] == "https://mcp.facebook.com/devtools"


class _Resp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _validate(token, page_id, response=None, http_error=None):
    vals = {"page_access_token": token, "page_id": page_id}
    def urlopen(*a, **k):
        if http_error:
            raise http_error
        return _Resp(json.dumps(response).encode())
    with mock.patch.object(ccp, "_component_value", side_effect=lambda c, e, comp: vals.get(comp)), \
         mock.patch.object(ccp.urllib.request, "urlopen", side_effect=urlopen):
        return ccp.validate_credential_live(HOLIDAY)


def test_validator_missing_token_is_auth_failure():
    assert _validate(None, "1722332634511930").status == ccp.HealthCheckStatus.AUTH_FAILURE


def test_validator_rejects_wrong_page_and_accepts_bound_page():
    assert _validate(FAKE_PAGE, "1722332634511930", {"id": "131069194210954"}).status == ccp.HealthCheckStatus.AUTH_FAILURE
    ok = _validate(FAKE_PAGE, "1722332634511930", {"id": "1722332634511930", "name": "Raytestpage"})
    assert ok.status == ccp.HealthCheckStatus.PASS
    assert FAKE_PAGE not in ok.message


def test_validator_expired_token():
    err = urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b'{"error":{"code":190}}'))
    assert _validate(FAKE_PAGE, "1722332634511930", http_error=err).status == ccp.HealthCheckStatus.EXPIRED_OR_REVOKED


def _fake_graph(path, params):
    if path == "oauth/access_token":
        return {"access_token": FAKE_USER}
    if path == "debug_token":
        return {"data": {"app_id": "1889438111704778", "type": "USER", "is_valid": True,
                         "scopes": sorted(REQUIRED), "expires_at": 0,
                         "granular_scopes": [{"scope": "pages_show_list", "target_ids": ["1722332634511930"]}]}}
    if path == "me/accounts":
        return {"data": [
            {"id": "131069194210954", "name": "Clear Credentials", "access_token": "FAKE_GOCLEAR_PAGE_TOKEN", "tasks": ["MANAGE"]},
            {"id": "1722332634511930", "name": "Raytestpage", "access_token": FAKE_PAGE, "tasks": ["CREATE_CONTENT", "MANAGE"]},
        ]}
    if path == "1722332634511930":
        assert "tasks" not in params["fields"], "tasks is not a Page-node field"
        assert params["access_token"] == FAKE_PAGE
        return {"id": "1722332634511930", "name": "Raytestpage",
                "instagram_business_account": {"id": "17841400000000000", "username": "the612amritual"}}
    raise AssertionError(path)


def _run_authorize(graph):
    stored = {}
    def store(cid, comp, value, replace=False):
        stored[(cid, comp)] = value
        return {"stored": True, "status": "STORED", "values_included": False}
    out = io.StringIO()
    with mock.patch.object(auth.ccp, "_keychain_value", return_value=FAKE_SECRET), \
         mock.patch.object(auth.ccp, "store_keychain", side_effect=store), \
         mock.patch.object(auth, "_graph", side_effect=graph), \
         mock.patch.object(auth, "_receive_code", return_value={"code": "FAKE_CODE"}), \
         redirect_stdout(out):
        rc = auth.authorize(open_browser=False)
    return rc, out.getvalue(), stored


def test_other_page_only_is_target_page_not_granted_and_nothing_stored():
    def graph(path, params):
        if path == "me/accounts":
            return {"data": [{"id": "551901321641130", "name": "Phoenix Home Search",
                              "access_token": "FAKE_PHOENIX_TOKEN", "tasks": ["MANAGE"]}]}
        if path == "1722332634511930":
            raise AssertionError("must not query target Page without a granted token")
        return _fake_graph(path, params)
    rc, text, stored = _run_authorize(graph)
    assert rc == 7
    assert "TARGET_PAGE_NOT_GRANTED" in text and "Phoenix Home Search(551901321641130)" in text
    assert stored == {}
    assert "FAKE_PHOENIX_TOKEN" not in text and FAKE_USER not in text


def test_unsupported_tasks_field_falls_back_and_still_discovers_page_token():
    calls = []
    def graph(path, params):
        if path == "me/accounts":
            calls.append(params["fields"])
            if "tasks" in params["fields"]:
                return {"error": {"code": 100, "message": "(#100) Tried accessing nonexisting field (tasks)"}}
            return {"data": [{"id": "1722332634511930", "name": "Raytestpage", "access_token": FAKE_PAGE}]}
        return _fake_graph(path, params)
    rc, text, stored = _run_authorize(graph)
    assert rc == 0
    assert calls == ["id,name,access_token,tasks", "id,name,access_token"]
    assert "TASKS_FIELD_UNSUPPORTED=YES" in text and "PAGE_TASKS=UNREPORTED" in text
    assert stored[(HOLIDAY, "page_access_token")] == FAKE_PAGE
    assert FAKE_PAGE not in text


def test_exact_page_id_required_even_with_matching_name():
    def graph(path, params):
        if path == "me/accounts":
            return {"data": [{"id": "999", "name": "Raytestpage", "access_token": "FAKE_DUP"}]}
        return _fake_graph(path, params)
    rc, text, stored = _run_authorize(graph)
    assert rc == 7 and stored == {} and "TARGET_PAGE_NOT_GRANTED" in text


def test_paging_through_me_accounts_finds_target():
    def graph(path, params):
        if path == "me/accounts":
            if params.get("after") == "c1":
                return {"data": [{"id": "1722332634511930", "name": "Raytestpage", "access_token": FAKE_PAGE, "tasks": ["CREATE_CONTENT"]}]}
            return {"data": [{"id": "1", "name": "A", "access_token": "x"}],
                    "paging": {"cursors": {"after": "c1"}, "next": "https://graph.facebook.com/next"}}
        return _fake_graph(path, params)
    rc, _, stored = _run_authorize(graph)
    assert rc == 0 and (HOLIDAY, "page_access_token") in stored


def test_consent_url_forces_asset_reselection():
    q = urllib.parse.parse_qs(urllib.parse.urlparse(auth.consent_url("s")).query)
    assert q["auth_type"] == ["reauthorize"]


def test_authorize_flow_stores_in_keychain_and_never_prints_secrets():
    stored = {}
    def store(cid, comp, value, replace=False):
        stored[(cid, comp)] = value
        return {"stored": True, "status": "STORED", "values_included": False}
    out = io.StringIO()
    with mock.patch.object(auth.ccp, "_keychain_value", return_value=FAKE_SECRET), \
         mock.patch.object(auth.ccp, "store_keychain", side_effect=store), \
         mock.patch.object(auth, "_graph", side_effect=_fake_graph), \
         mock.patch.object(auth, "_receive_code", return_value={"code": "FAKE_CODE"}), \
         redirect_stdout(out):
        rc = auth.authorize(open_browser=False)
    text = out.getvalue()
    assert rc == 0
    assert stored[(HOLIDAY, "page_access_token")] == FAKE_PAGE
    assert all(cid == HOLIDAY for cid, _ in stored), "must never write GoClear"
    for s in (FAKE_SECRET, FAKE_USER, FAKE_PAGE, "FAKE_CODE"):
        assert s not in text
    assert "CONNECTED_PAIR_VERIFIED=YES" in text and "RAW_TOKEN_EXPOSED=NO" in text


def test_authorize_refuses_wrong_page_identity():
    def graph(path, params):
        if path == "me/accounts":
            return {"data": [{"id": "1722332634511930", "name": "Clear Credentials", "access_token": FAKE_PAGE}]}
        return _fake_graph(path, params)
    store = mock.Mock()
    with mock.patch.object(auth.ccp, "_keychain_value", return_value=FAKE_SECRET), \
         mock.patch.object(auth.ccp, "store_keychain", store), \
         mock.patch.object(auth, "_graph", side_effect=graph), \
         mock.patch.object(auth, "_receive_code", return_value={"code": "c"}), \
         redirect_stdout(io.StringIO()):
        assert auth.authorize(open_browser=False) == 8
    store.assert_not_called()


def test_authorize_without_app_secret_blocks_before_browser():
    with mock.patch.object(auth.ccp, "_keychain_value", return_value=None), \
         mock.patch.object(auth.webbrowser, "open") as wb, redirect_stdout(io.StringIO()):
        assert auth.authorize() == 2
    wb.assert_not_called()


def test_holiday_channel_bindings_follow_live_credential_and_keep_external_ids():
    import distribution_foundation as df
    accts = {a.channel_account_id: a for a in df.create_seed_channel_accounts()}
    fb, ig = accts["acc_holiday_facebook_01"], accts["acc_holiday_instagram_01"]
    assert fb.external_account_id == "1722332634511930" and fb.account_name == "Raytestpage"
    assert ig.external_account_id == "17841480885973564" and ig.account_name == "@the612amritual"
    for a in (fb, ig):
        assert a.venture_scope == ["vnt_holiday_commerce_pilot_2026"]
        assert a.credential_reference == HOLIDAY
        assert a.schedule_allowed is False
        assert a.approval_policy == "APPROVAL_REQUIRED"
        assert (a.auth_status, a.publish_allowed) == ("AUTHENTICATED", True)


def test_holiday_channel_bindings_fail_closed_when_credential_not_live(tmp_path):
    import distribution_foundation as df
    reg = json.loads((ROOT / "configs/nexus_credential_registry.json").read_text())
    entries = reg["credentials"] if isinstance(reg, dict) else reg
    for e in entries:
        if e["credential_id"] == HOLIDAY:
            e["status"] = "EXPIRED"
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(reg))
    with mock.patch.object(df, "CREDENTIAL_REGISTRY_PATH", p):
        accts = {a.channel_account_id: a for a in df.create_seed_channel_accounts()}
    for k in ("acc_holiday_facebook_01", "acc_holiday_instagram_01"):
        assert (accts[k].auth_status, accts[k].publish_allowed) == ("AUTH_REQUIRED", False)
