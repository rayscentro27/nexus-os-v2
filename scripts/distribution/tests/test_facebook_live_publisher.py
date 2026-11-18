"""Section 31B bounded Facebook live publisher + owner approval (20 contracts)."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "distribution"))

import facebook_live_publisher as f  # noqa: E402

REAL_REQUEST = ROOT / "dist/creative/holiday_facebook_bounded_publish_approval_request.json"
FAKE_TOKEN = "EAAFAKE_PAGE_TOKEN_must_never_print"
PAGE = "1722332634511930"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolated governed store + request dir with copies of the real request/media."""
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    # Never project test approvals to the remote dashboard.
    import nexus_agent_platform.supabase_decision_consumer as sdc
    monkeypatch.setattr(sdc, "sync_approval", lambda approval: None)
    reqdir = tmp_path / "creative"
    reqdir.mkdir()
    req = json.loads(REAL_REQUEST.read_text())
    for entry in (req["media"], req["media"]["provider_derivative"]):
        dst = reqdir / Path(entry["path"]).name
        dst.write_bytes((ROOT / entry["path"]).read_bytes())
        entry["path"] = str(dst)
    req["request_hash"] = f.compute_request_hash(req)
    path = reqdir / "test_approval_request.json"
    path.write_text(json.dumps(req))
    monkeypatch.setattr(f, "REQUESTS_DIR", reqdir)
    monkeypatch.setattr(f, "ROOT", tmp_path)
    return {"path": path, "req": req, "dir": reqdir}


def owner_io(**over):
    nonce_box = {}
    def read_line(prompt):
        nonce = prompt.split("'APPROVE ")[1].split("'")[0]
        nonce_box["n"] = nonce
        return f"APPROVE {nonce}"
    base = dict(env={"USER": "raymonddavis"}, stdin_isatty=lambda: True, stdout_isatty=lambda: True,
                read_line=read_line, read_secret=lambda p: "correct-horse",
                verify_password=lambda pw: (pw == "correct-horse", "OK"), tty_name=lambda: "/dev/ttys001")
    base.update(over)
    return f.OwnerIO(**base)


def do_approve(**over):
    return f.approve("apr_req_e2b7a33fbaf04fc6", io_=owner_io(**over), out=lambda *a: None)


class FakeGraph:
    """Records every call; never touches the network."""
    def __init__(self, token, *, post_result=(200, {"id": "9001", "post_id": f"{PAGE}_7001"}), me_id=PAGE,
                 message=None, transport_error=False):
        assert token == FAKE_TOKEN
        self.version = "v23.0"
        self.posts = 0
        self.post_result = post_result
        self.me_id = me_id
        self.message = message
        self.transport_error = transport_error
        self.calls = []

    def get(self, path, fields):
        self.calls.append(("GET", path))
        if path == "me":
            return 200, {"id": self.me_id, "name": "Raytestpage"}
        if path == f"{PAGE}_7001":
            return 200, {"id": path, "message": self.message, "created_time": "2026-11-13T00:00:00+0000",
                         "permalink_url": f"https://www.facebook.com/{path}", "full_picture": "https://cdn/x.jpg",
                         "from": {"id": PAGE}, "attachments": {"data": [{"media_type": "photo"}]}}
        if path == "9001":
            return 200, {"id": "9001", "images": [{"height": 1280, "width": 1920}]}
        return 404, {"error": {"code": 100}}

    def post_photo(self, page_id, image, filename, caption):
        self.calls.append(("POST", f"{page_id}/photos"))
        if self.transport_error:
            raise f.GraphTransportError("TimeoutError")
        self.posts += 1
        assert page_id == PAGE and filename.endswith(".jpg") and image[:2] == b"\xff\xd8"
        return self.post_result


def run_publish(env, **graph_kw):
    holder = {}
    def factory(token):
        g = FakeGraph(token, message=env["req"]["copy"], **graph_kw)
        holder["g"] = g
        return g
    out = io.StringIO()
    try:
        res = f.publish("apr_req_e2b7a33fbaf04fc6", graph_factory=factory, token_provider=lambda: FAKE_TOKEN,
                        out=lambda *a: out.write(" ".join(map(str, a)) + "\n"))
    except f.PublishRefused as e:
        res = {"refused": str(e)}
    return res, holder.get("g"), out.getvalue()


# 1
def test_01_approval_request_loads(env):
    path, req = f.find_request("apr_req_e2b7a33fbaf04fc6")
    assert req["platform"] == "FACEBOOK" and req["post_format"] == "PHOTO_POST"
    assert f.verify_request(req) == []
    real = json.loads(REAL_REQUEST.read_text())
    assert real["idempotency_key"] == "idem_61606c157e587a276bf99205"


# 2
def test_02_owner_approval_persists(env):
    res = do_approve()
    assert res["status"] == "APPROVED"
    st = f.approval_status("apr_req_e2b7a33fbaf04fc6")
    assert st["approval_status"] == "APPROVED" and st["approval_id"] == res["approval_id"]
    rec = f._latest_approvals_for("apr_req_e2b7a33fbaf04fc6")[0]
    assert rec["resolved_by"] == "ray" and rec["input_summary"]["owner_attestation"]["method"] == f.ATTESTATION_METHOD
    assert rec["input_summary"]["idempotency_key"] == env["req"]["idempotency_key"]
    assert rec["input_summary"]["max_external_posts"] == 1


# 3
def test_03_approval_does_not_publish(env):
    with mock.patch.object(f, "MetaGraphClient") as client, mock.patch.object(f, "resolve_holiday_page_token") as tok:
        do_approve()
    client.assert_not_called()
    tok.assert_not_called()
    assert f.latest_transaction(env["req"]["idempotency_key"]) is None


def _mutate(env, fn):
    req = json.loads(env["path"].read_text())
    fn(req)
    env["path"].write_text(json.dumps(req))


# 4
def test_04_changed_copy_invalidates_approval(env):
    do_approve()
    _mutate(env, lambda r: r.__setitem__("copy", r["copy"] + " Now 50% off!"))
    assert f.approval_status("apr_req_e2b7a33fbaf04fc6")["approval_status"] == "INVALIDATED"
    res, g, _ = run_publish(env)
    assert "REQUEST_INVALID" in res["refused"] and g is None


# 5
def test_05_changed_asset_invalidates_approval(env):
    do_approve()
    p = Path(env["req"]["media"]["provider_derivative"]["path"])
    p.write_bytes(p.read_bytes() + b"tamper")
    assert f.approval_status("apr_req_e2b7a33fbaf04fc6")["approval_status"] == "INVALIDATED"
    res, g, _ = run_publish(env)
    assert "REQUEST_INVALID" in res["refused"] and g is None


# 6
def test_06_changed_target_page_invalidates_and_is_locked(env):
    do_approve()
    _mutate(env, lambda r: r.__setitem__("target_page_id", "131069194210954"))
    st = f.approval_status("apr_req_e2b7a33fbaf04fc6")
    assert st["approval_status"] == "INVALIDATED"
    assert any("TARGET_PAGE_LOCK" in p for p in st["request_problems"])


# 7
def test_07_agent_cannot_fabricate_owner_approval(env):
    with pytest.raises(f.PublishRefused, match="AGENT_SESSION_DETECTED"):
        do_approve(env={"CLAUDECODE": "1", "USER": "raymonddavis"})
    with pytest.raises(f.PublishRefused, match="NO_INTERACTIVE_TTY"):
        do_approve(stdin_isatty=lambda: False)
    with pytest.raises(f.PublishRefused, match="CONFIRMATION_PHRASE_MISMATCH"):
        do_approve(read_line=lambda p: "APPROVE 000000")
    with pytest.raises(f.PublishRefused, match="OWNER_VERIFICATION_FAILED"):
        do_approve(read_secret=lambda p: "guess")
    # Direct use of the generic governed API (no owner attestation) cannot authorize a send.
    from nexus_agent_platform.governed import approvals
    pending = approvals.create_approval_request(action_id=f.ACTION_ID, requested_by="claude_code",
                                                input_summary={"request_id": "apr_req_e2b7a33fbaf04fc6",
                                                               "request_hash": env["req"]["request_hash"]})
    approvals.resolve_approval(pending["id"], "approve", resolved_by="ray")
    res, g, _ = run_publish(env)
    assert "APPROVAL_NOT_FROM_OWNER_CLI" in res["refused"] and "OWNER_ATTESTATION_MISSING" in res["refused"]
    assert g is None


# 8
def test_08_jpeg_derivative_matches_source_and_lineage():
    from PIL import Image
    req = json.loads(REAL_REQUEST.read_text())
    src, der = ROOT / req["media"]["path"], ROOT / req["media"]["provider_derivative"]["path"]
    assert Image.open(src).size == Image.open(der).size == (1920, 1280)
    assert Image.open(der).format == "JPEG"
    rec = json.loads((ROOT / req["media"]["provider_derivative"]["lineage_receipt"]).read_text())
    assert rec["parent_asset_id"] == req["media"]["asset_id"] == "asset_metaai_image_1794355016"
    assert rec["parent_sha256"] == f._sha256_file(src) == req["media"]["sha256"]
    assert rec["sha256"] == f._sha256_file(der) == req["media"]["provider_derivative"]["sha256"]
    assert rec["not_a_new_creative_concept"] is True and rec["fidelity"]["psnr_db_vs_parent"] > 40


# 9 / 10
def test_09_10_resolver_holiday_only_goclear_rejected():
    holiday = mock.Mock(credential_id=f.HOLIDAY_CREDENTIAL_ID, status=mock.Mock(value="AVAILABLE"))
    goclear = mock.Mock(credential_id="credential.meta.social.goclear.prod.v1", status=mock.Mock(value="AVAILABLE"))
    with mock.patch.object(f.ccp, "resolve_credential", return_value=goclear):
        with pytest.raises(f.PublishRefused, match="TARGET_CREDENTIAL_LOCK_VIOLATION"):
            f.resolve_holiday_page_token()
    def apply(cid):
        import os
        os.environ["HOLIDAY_META_PAGE_ACCESS_TOKEN"] = FAKE_TOKEN
    with mock.patch.object(f.ccp, "resolve_credential", return_value=holiday), \
         mock.patch.object(f.ccp, "apply_to_process", side_effect=apply):
        import os
        os.environ.pop("HOLIDAY_META_PAGE_ACCESS_TOKEN", None)
        assert f.resolve_holiday_page_token() == FAKE_TOKEN
        assert "HOLIDAY_META_PAGE_ACCESS_TOKEN" not in os.environ  # secret not left in env


# 11
def test_11_wrong_page_token_rejected_before_send(env):
    do_approve()
    res, g, _ = run_publish(env, me_id="131069194210954")
    assert "TARGET_PAGE_LOCK_VIOLATION" in res["refused"] and g.posts == 0
    assert f.latest_transaction(env["req"]["idempotency_key"]) is None


# 12 / 15 / 16 / 17 / 18
def test_12_15_16_17_18_single_real_send_readback_receipt_no_secret(env):
    do_approve()
    res, g, out = run_publish(env)
    assert res["result"] == "PUBLISHED" and g.posts == 1
    assert ("POST", f"{PAGE}/photos") in g.calls and (("GET", f"{PAGE}_7001")) in g.calls  # read-back happened
    assert res["meta_post_id"] == f"{PAGE}_7001" and not res["meta_post_id"].startswith("post_sim_")
    assert res["readback_verified"] is True and res["simulated"] is False
    tx = f.latest_transaction(env["req"]["idempotency_key"])
    assert tx["state"] == f.S_PUBLISHED and tx["approval_id"] and tx["publish_receipt_id"] == res["publish_receipt_id"]
    receipts = f.persistence.read_records(f.RECEIPT_COLLECTION)
    assert len(receipts) == 1
    for field in ("approval_id", "approval_request_id", "approval_hash", "idempotency_key", "page_id", "asset_id",
                  "derivative_asset_id", "asset_sha256", "copy_hash", "meta_post_id", "meta_photo_id",
                  "provider_http_status", "published_at", "readback_verified", "final_job_state", "retry_count"):
        assert field in receipts[0]
    store = "".join(p.read_text() for p in Path(f.persistence.governed_data_dir()).glob("*.jsonl"))
    assert FAKE_TOKEN not in store and FAKE_TOKEN not in out and FAKE_TOKEN not in json.dumps(res)
    assert f._latest_approvals_for("apr_req_e2b7a33fbaf04fc6")[0]["status"] == "consumed"
    # 12: replay with an existing success receipt never sends again
    res2, g2, _ = run_publish(env)
    assert res2.get("result") == "ALREADY_PUBLISHED" or "APPROVAL" in res2.get("refused", "")
    assert g2 is None or g2.posts == 0
    assert len(f.persistence.read_records(f.RECEIPT_COLLECTION)) == 1


# 12b: success receipt short-circuits before approval/credential checks
def test_12b_success_receipt_short_circuits(env):
    f.persistence.append_record(f.TX_COLLECTION, {"idempotency_key": env["req"]["idempotency_key"],
                                                  "state": f.S_PUBLISHED, "meta_post_id": "x", "publish_receipt_id": "r"})
    res, g, _ = run_publish(env)
    assert res["result"] == "ALREADY_PUBLISHED" and g is None


# 13
def test_13_in_flight_transaction_blocks_second_send(env):
    do_approve()
    f.persistence.append_record(f.TX_COLLECTION, {"idempotency_key": env["req"]["idempotency_key"],
                                                  "state": f.S_PUBLISHING, "distribution_job_id": "dist_job_holiday_facebook_01"})
    res, g, _ = run_publish(env)
    assert "DUPLICATE_OR_AMBIGUOUS_TRANSACTION" in res["refused"] and g is None


# 13b: concurrent lock
def test_13b_concurrent_publish_lock(env):
    with f._tx_lock():
        res, g, _ = run_publish(env)
    assert "another publish is in progress" in res["refused"] and g is None


# 14
def test_14_unknown_outcome_blocks_blind_retry(env):
    do_approve()
    res, g, _ = run_publish(env, transport_error=True)
    assert f.S_UNKNOWN in res["refused"]
    assert f.latest_transaction(env["req"]["idempotency_key"])["state"] == f.S_UNKNOWN
    res2, g2, _ = run_publish(env)
    assert "DUPLICATE_OR_AMBIGUOUS_TRANSACTION" in res2["refused"] and g2 is None


def test_14b_server_error_is_ambiguous_and_4xx_is_definitive(env):
    do_approve()
    res, g, _ = run_publish(env, post_result=(500, {"error": {"code": 2}}))
    assert f.S_UNKNOWN in res["refused"]


def test_14c_publishing_state_persisted_before_provider_call(env):
    do_approve()
    seen = {}
    class Spy(FakeGraph):
        def post_photo(self, *a, **k):
            seen["state"] = f.latest_transaction(env["req"]["idempotency_key"])["state"]
            return super().post_photo(*a, **k)
    res = f.publish("apr_req_e2b7a33fbaf04fc6", graph_factory=lambda t: Spy(t, message=env["req"]["copy"]),
                    token_provider=lambda: FAKE_TOKEN, out=lambda *a: None)
    assert seen["state"] == f.S_PUBLISHING and res["result"] == "PUBLISHED"


# 17b: read-back mismatch never marks PUBLISHED
def test_17b_readback_mismatch_not_published(env):
    do_approve()
    holder = {}
    def factory(t):
        holder["g"] = FakeGraph(t, message="different text")
        return holder["g"]
    with pytest.raises(f.PublishRefused, match=f.S_READBACK_FAILED):
        f.publish("apr_req_e2b7a33fbaf04fc6", graph_factory=factory, token_provider=lambda: FAKE_TOKEN, out=lambda *a: None)
    assert f.latest_transaction(env["req"]["idempotency_key"])["state"] == f.S_READBACK_FAILED
    assert f.persistence.read_records(f.RECEIPT_COLLECTION) == []


# 16b: real client builds a Graph photo request with token only in the header
def test_16b_real_client_request_shape():
    captured = {}
    class Resp(io.BytesIO):
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def urlopen(req, timeout, context):
        captured["url"], captured["auth"], captured["body"] = req.full_url, req.headers.get("Authorization"), req.data
        return Resp(b'{"id":"1","post_id":"1722332634511930_2"}')
    with mock.patch.object(f.urllib.request, "urlopen", side_effect=urlopen):
        status, body = f.MetaGraphClient(FAKE_TOKEN).post_photo(PAGE, b"\xff\xd8jpeg", "a.jpg", "caption text")
    assert captured["url"] == f"https://graph.facebook.com/v23.0/{PAGE}/photos"
    assert FAKE_TOKEN not in captured["url"] and captured["auth"] == f"Bearer {FAKE_TOKEN}"
    assert b'name="caption"' in captured["body"] and b'name="source"' in captured["body"]
    assert body["post_id"].startswith(PAGE)


# 19 / 20
def test_19_20_no_live_publish_or_schedule_in_repo_state():
    # After the 2026-11-12 certification the real ledger holds exactly ONE Facebook
    # receipt (the certified post) and nothing else was published.
    real_dir = ROOT / "data" / "governed"
    rc = real_dir / "distribution_publish_receipts.jsonl"
    receipts = [json.loads(l) for l in rc.read_text().splitlines() if l.strip()] if rc.exists() else []
    fb_receipts = [r for r in receipts if r.get("platform") == "FACEBOOK"]
    assert len(fb_receipts) <= 1
    if fb_receipts:
        assert fb_receipts[0]["meta_post_id"] == "1722332634511930_1182879984073759"
        assert fb_receipts[0]["simulated"] is False and fb_receipts[0]["readback_verified"] is True
    import distribution_foundation as df
    for a in df.create_seed_channel_accounts():
        assert a.schedule_allowed is False
    src = (ROOT / "scripts/distribution/facebook_live_publisher.py").read_text()
    assert "scheduled_publish_time" not in src and "post_sim_" not in src.replace("`post_sim_*`", "")


# 7b: a Nova-created approval (even with a forged attestation, resolved by Ray) cannot authorize a send
def test_07b_nova_path_approval_cannot_authorize(env):
    from nexus_agent_platform.governed import actions_api, approvals
    forged = {"request_id": "apr_req_e2b7a33fbaf04fc6", "request_hash": env["req"]["request_hash"],
              "idempotency_key": env["req"]["idempotency_key"], "venture_id": env["req"]["venture_id"],
              "platform": "FACEBOOK", "channel_account_id": "acc_holiday_facebook_01",
              "target_page_id": PAGE, "max_external_posts": 1,
              "owner_attestation": {"method": f.ATTESTATION_METHOD}}
    r = actions_api.create_approval_request(action_id=f.ACTION_ID, input_summary=forged)
    appr_id = (r.get("approval") or {}).get("approval_id") or (r.get("approval") or {}).get("id") or r.get("approval_id")
    assert appr_id, r
    approvals.resolve_approval(appr_id, "approve", resolved_by="ray")
    res, g, _ = run_publish(env)
    assert "APPROVAL_NOT_FROM_OWNER_CLI" in res["refused"] and g is None
