"""Section 31B bounded Instagram Reel publisher (21 contracts)."""
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

import facebook_live_publisher as fb  # noqa: E402
import instagram_live_publisher as ig  # noqa: E402

REAL_IG_REQUEST = ROOT / "dist/creative/holiday_instagram_bounded_publish_v2_approval_request.json"
REAL_FB_REQUEST = ROOT / "dist/creative/holiday_facebook_bounded_publish_approval_request.json"
IG_REQ_ID = json.loads(REAL_IG_REQUEST.read_text())["approval_request_id"]
FB_REQ_ID = "apr_req_e2b7a33fbaf04fc6"
FAKE_TOKEN = "EAAFAKE_IG_TOKEN_must_never_print"
IGID = "17841480885973564"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    import nexus_agent_platform.supabase_decision_consumer as sdc
    monkeypatch.setattr(sdc, "sync_approval", lambda approval: None)
    reqdir = tmp_path / "creative"
    reqdir.mkdir()
    req = json.loads(REAL_IG_REQUEST.read_text())
    for entry in (req["video"], req["video"]["provider_derivative"]):
        dst = reqdir / Path(entry["path"]).name
        dst.write_bytes((ROOT / entry["path"]).read_bytes())
        entry["path"] = str(dst)
    req["request_hash"] = ig.compute_request_hash(req)
    (reqdir / "ig_approval_request.json").write_text(json.dumps(req))
    fbreq = json.loads(REAL_FB_REQUEST.read_text())
    for entry in (fbreq["media"], fbreq["media"]["provider_derivative"]):
        dst = reqdir / Path(entry["path"]).name
        dst.write_bytes((ROOT / entry["path"]).read_bytes())
        entry["path"] = str(dst)
    fbreq["request_hash"] = fb.compute_request_hash(fbreq)
    (reqdir / "fb_approval_request.json").write_text(json.dumps(fbreq))
    monkeypatch.setattr(fb, "REQUESTS_DIR", reqdir)
    monkeypatch.setattr(fb, "ROOT", tmp_path)
    return {"req": req, "path": reqdir / "ig_approval_request.json", "dir": reqdir}


def owner_io(**over):
    def read_line(prompt):
        return "APPROVE " + prompt.split("'APPROVE ")[1].split("'")[0]
    base = dict(env={"USER": "raymonddavis"}, stdin_isatty=lambda: True, stdout_isatty=lambda: True,
                read_line=read_line, read_secret=lambda p: "pw", verify_password=lambda pw: (pw == "pw", "OK"),
                tty_name=lambda: "/dev/ttys001")
    base.update(over)
    return fb.OwnerIO(**base)


def approve_ig(**over):
    return ig.approve(IG_REQ_ID, io_=owner_io(**over), out=lambda *a: None)


def good_hosted(url, sha):
    return {"http_status": 200, "content_type": "video/mp4", "sha256": sha, "sha256_match": True, "fetchable": True}


class FakeIG:
    def __init__(self, token, caption, *, statuses=("IN_PROGRESS", "FINISHED"), linked_ig=IGID,
                 create=(200, {"id": "C1"}), publish=(200, {"id": "M1"}), create_transport=False,
                 publish_transport=False, media_caption=None, media_product_type="REELS"):
        assert token == FAKE_TOKEN
        self.version = "v23.0"
        self.caption = caption
        self.statuses = list(statuses)
        self.linked_ig = linked_ig
        self.create, self.publish = create, publish
        self.create_transport, self.publish_transport = create_transport, publish_transport
        self.media_caption = caption if media_caption is None else media_caption
        self.media_product_type = media_product_type
        self.calls = []
        self.creates = self.publishes = 0

    def get(self, path, fields):
        self.calls.append(("GET", path))
        if path == fb.HOLIDAY_PAGE_ID:
            return 200, {"id": path, "instagram_business_account": {"id": self.linked_ig, "username": "the612amritual"}}
        if path == "C1":
            code = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return 200, {"id": "C1", "status_code": code, "status": code}
        if path == "M1":
            return 200, {"id": "M1", "caption": self.media_caption, "media_type": "VIDEO",
                         "media_product_type": self.media_product_type, "permalink": "https://www.instagram.com/reel/ABC/",
                         "timestamp": "2026-11-13T00:00:00+0000", "owner": {"id": IGID}, "username": "the612amritual",
                         "media_url": "https://cdn/x.mp4", "shortcode": "ABC"}
        if path == f"{IGID}/media":
            return 200, {"data": []}
        return 404, {"error": {"code": 100}}

    def post_form(self, path, fields):
        self.calls.append(("POST", path))
        if path == f"{IGID}/media":
            assert fields["media_type"] == "REELS" and fields["caption"] == self.caption
            assert fields["video_url"].startswith("https://")
            if self.create_transport:
                raise fb.GraphTransportError("TimeoutError")
            self.creates += 1
            return self.create
        if path == f"{IGID}/media_publish":
            assert fields["creation_id"] == "C1"
            if self.publish_transport:
                raise fb.GraphTransportError("TimeoutError")
            self.publishes += 1
            return self.publish
        raise AssertionError(path)


def run(env, hosted=good_hosted, **kw):
    holder = {}
    def factory(t):
        holder["g"] = FakeIG(t, env["req"]["caption"], **kw)
        return holder["g"]
    out = io.StringIO()
    try:
        res = ig.publish(IG_REQ_ID, graph_factory=factory, token_provider=lambda: FAKE_TOKEN,
                         public_video_checker=hosted, sleep=lambda s: None,
                         out=lambda *a: out.write(" ".join(map(str, a)) + "\n"))
    except fb.PublishRefused as e:
        res = {"refused": str(e)}
    return res, holder.get("g"), out.getvalue()


def mutate(env, fn):
    req = json.loads(env["path"].read_text())
    fn(req)
    env["path"].write_text(json.dumps(req))


def tx_state(env):
    return (fb.latest_transaction(env["req"]["idempotency_key"]) or {}).get("state")


# 1
def test_01_instagram_request_generated(env):
    _, req = fb.find_request(IG_REQ_ID)
    assert req["platform"] == "INSTAGRAM" and req["post_format"] == "REELS"
    assert req["instagram_account_id"] == IGID and req["max_external_posts"] == 1
    assert ig.verify_request(req) == []
    real = json.loads(REAL_IG_REQUEST.read_text())
    assert real["status"] == "WAITING_FOR_RAY_APPROVAL" and real["idempotency_key"] != json.loads(REAL_FB_REQUEST.read_text())["idempotency_key"]


# 2
def test_02_facebook_approval_cannot_authorize_instagram(env):
    fb.approve(FB_REQ_ID, io_=owner_io(), out=lambda *a: None)
    assert ig._latest_approvals_for(IG_REQ_ID) == []
    res, g, _ = run(env)
    assert "APPROVAL_REQUIRED" in res["refused"] and g is None


# 3
def test_03_request_hash_binds_video_bytes(env):
    h1 = ig.compute_request_hash(env["req"])
    p = Path(env["req"]["video"]["provider_derivative"]["path"])
    p.write_bytes(p.read_bytes() + b"x")
    assert ig.compute_request_hash(env["req"]) != h1


# 4 / 5 / 6
@pytest.mark.parametrize("change", ["caption", "video", "account"])
def test_04_05_06_changes_invalidate_approval(env, change):
    approve_ig()
    if change == "caption":
        mutate(env, lambda r: r.__setitem__("caption", r["caption"] + " Limited time!"))
    elif change == "video":
        p = Path(env["req"]["video"]["provider_derivative"]["path"])
        p.write_bytes(p.read_bytes()[:-10])
    else:
        mutate(env, lambda r: r.__setitem__("instagram_account_id", "17841480265043148"))
    assert ig.approval_status(IG_REQ_ID)["approval_status"] == "INVALIDATED"
    res, g, _ = run(env)
    assert "REQUEST_INVALID" in res["refused"] and g is None


# 7
def test_07_owner_command_supports_instagram(env):
    lines = []
    res = ig.approve(IG_REQ_ID, io_=owner_io(), out=lines.append)
    text = "\n".join(lines)
    for needle in ("INSTAGRAM Reel on @the612amritual", IGID, "Caption:", env["req"]["caption"],
                   "Video:", "Campaign URL:", "Max posts:    1", "Purpose:", "plain text"):
        assert needle in text
    rec = ig._latest_approvals_for(IG_REQ_ID)[0]
    assert rec["action_id"] == ig.ACTION_ID and rec["input_summary"]["request_hash"] == env["req"]["request_hash"]
    assert rec["input_summary"]["public_video_sha256"] == env["req"]["public_video_sha256"]
    assert ig.approval_status(IG_REQ_ID)["approval_status"] == "APPROVED" and res["status"] == "APPROVED"


# 8
def test_08_agent_cannot_self_approve(env):
    with pytest.raises(fb.PublishRefused, match="AGENT_SESSION_DETECTED"):
        approve_ig(env={"CLAUDECODE": "1"})
    with pytest.raises(fb.PublishRefused, match="NO_INTERACTIVE_TTY"):
        approve_ig(stdout_isatty=lambda: False)
    with pytest.raises(fb.PublishRefused, match="OWNER_VERIFICATION_FAILED"):
        approve_ig(read_secret=lambda p: "nope")
    from nexus_agent_platform.governed import actions_api, approvals
    r = actions_api.create_approval_request(action_id=ig.ACTION_ID, input_summary={
        "request_id": IG_REQ_ID, "request_hash": env["req"]["request_hash"],
        "owner_attestation": {"method": fb.ATTESTATION_METHOD}})
    aid = (r.get("approval") or {}).get("approval_id") or (r.get("approval") or {}).get("id") or r.get("approval_id")
    approvals.resolve_approval(aid, "approve", resolved_by="ray")
    res, g, _ = run(env)
    assert "APPROVAL_NOT_FROM_OWNER_CLI" in res["refused"] and g is None


# 9
def test_09_public_media_url_validates(env):
    sha = env["req"]["public_video_sha256"]
    class Resp(io.BytesIO):
        status = 200
        headers = {"Content-Type": "video/mp4"}
        def __enter__(self): return self
        def __exit__(self, *a): return False
    body = Path(env["req"]["video"]["provider_derivative"]["path"]).read_bytes()
    with mock.patch.object(ig.urllib.request, "urlopen", return_value=Resp(body)):
        assert ig.check_public_video("https://x/v.mp4", sha)["fetchable"] is True
    with mock.patch.object(ig.urllib.request, "urlopen", return_value=Resp(body + b"tamper")):
        assert ig.check_public_video("https://x/v.mp4", sha)["fetchable"] is False
    approve_ig()
    res, g, _ = run(env, hosted=lambda u, s: {"fetchable": False, "http_status": 403})
    assert "PUBLIC_VIDEO_NOT_FETCHABLE_OR_CHANGED" in res["refused"] and g is None and tx_state(env) is None


# 10 / 11
def test_10_11_holiday_credential_resolves_goclear_rejected():
    goclear = mock.Mock(credential_id="credential.meta.social.goclear.prod.v1", status=mock.Mock(value="AVAILABLE"))
    with mock.patch.object(fb.ccp, "resolve_credential", return_value=goclear):
        with pytest.raises(fb.PublishRefused, match="TARGET_CREDENTIAL_LOCK_VIOLATION"):
            fb.resolve_holiday_page_token()
    holiday = mock.Mock(credential_id=fb.HOLIDAY_CREDENTIAL_ID, status=mock.Mock(value="AVAILABLE"))
    import os
    def apply(cid):
        os.environ["HOLIDAY_META_PAGE_ACCESS_TOKEN"] = FAKE_TOKEN
    with mock.patch.object(fb.ccp, "resolve_credential", return_value=holiday), \
         mock.patch.object(fb.ccp, "apply_to_process", side_effect=apply):
        os.environ.pop("HOLIDAY_META_PAGE_ACCESS_TOKEN", None)
        assert fb.resolve_holiday_page_token() == FAKE_TOKEN
        assert "HOLIDAY_META_PAGE_ACCESS_TOKEN" not in os.environ


# 12
def test_12_wrong_instagram_account_rejected(env):
    approve_ig()
    res, g, _ = run(env, linked_ig="17841480265043148")
    assert "TARGET_ACCOUNT_LOCK_VIOLATION" in res["refused"] and g.creates == 0 and tx_state(env) is None


# 13
def test_13_existing_transaction_prevents_duplicate_container(env):
    approve_ig()
    fb.persistence.append_record(fb.TX_COLLECTION, {"idempotency_key": env["req"]["idempotency_key"], "state": ig.S_CREATING})
    res, g, _ = run(env)
    assert "DUPLICATE_OR_AMBIGUOUS_TRANSACTION" in res["refused"] and g is None


def test_13b_known_container_is_resumed_not_recreated(env):
    approve_ig()
    fb.persistence.append_record(fb.TX_COLLECTION, {"idempotency_key": env["req"]["idempotency_key"],
                                                    "state": ig.S_PROCESSING, "media_container_id": "C1",
                                                    "distribution_job_id": env["req"]["distribution_job_id"]})
    res, g, out = run(env)
    assert res["result"] == "PUBLISHED" and g.creates == 0 and g.publishes == 1 and "RESUMING" in out


# 14 / 18 / 19 (happy path) — exactly one container + one publish, read-back, receipt, no secret
def test_14_18_19_single_publish_readback_receipt_no_secret(env):
    approve_ig()
    res, g, out = run(env)
    assert res["result"] == "PUBLISHED" and g.creates == 1 and g.publishes == 1
    assert ("GET", "M1") in g.calls
    assert res["instagram_media_id"] == "M1" and res["media_container_id"] == "C1" and res["readback_verified"]
    receipts = fb.persistence.read_records(fb.RECEIPT_COLLECTION)
    assert len(receipts) == 1
    for k in ("publish_receipt_id", "approval_id", "approval_request_id", "request_hash", "idempotency_key", "venture_id",
              "campaign_id", "distribution_job_id", "channel_account_id", "platform", "instagram_account_id",
              "video_asset_id", "video_sha256", "public_video_url", "media_container_id", "instagram_media_id",
              "permalink", "provider_http_status", "published_at", "readback_verified", "final_job_state", "retry_count"):
        assert k in receipts[0]
    states = [r["state"] for r in reversed(fb.persistence.read_records(fb.TX_COLLECTION))]
    assert states == [ig.S_CREATING, ig.S_PROCESSING, ig.S_PROCESSING, ig.S_PROCESSING, ig.S_READY,
                      ig.S_PUBLISHING, ig.S_ACCEPTED, ig.S_PUBLISHED] or \
        [s for i, s in enumerate(states) if i == 0 or s != states[i - 1]] == \
        [ig.S_CREATING, ig.S_PROCESSING, ig.S_READY, ig.S_PUBLISHING, ig.S_ACCEPTED, ig.S_PUBLISHED]
    store = "".join(p.read_text() for p in Path(fb.persistence.governed_data_dir()).glob("*.jsonl"))
    assert FAKE_TOKEN not in store and FAKE_TOKEN not in out and FAKE_TOKEN not in json.dumps(res)
    assert ig._latest_approvals_for(IG_REQ_ID)[0]["status"] == "consumed"
    # replay: existing success receipt prevents second publish
    res2, g2, _ = run(env)
    assert res2.get("result") == "ALREADY_PUBLISHED" and g2 is None
    assert len(fb.persistence.read_records(fb.RECEIPT_COLLECTION)) == 1


# 15
def test_15_ambiguous_container_outcome_blocks_retry(env):
    approve_ig()
    res, g, _ = run(env, create_transport=True)
    assert ig.S_CREATE_UNKNOWN in res["refused"] and tx_state(env) == ig.S_CREATE_UNKNOWN
    res2, g2, _ = run(env)
    assert "DUPLICATE_OR_AMBIGUOUS_TRANSACTION" in res2["refused"] and g2 is None


# 16
def test_16_ambiguous_publish_outcome_blocks_retry(env):
    approve_ig()
    res, g, _ = run(env, publish_transport=True)
    assert ig.S_PUBLISH_UNKNOWN in res["refused"] and tx_state(env) == ig.S_PUBLISH_UNKNOWN
    res2, g2, _ = run(env)
    assert "DUPLICATE_OR_AMBIGUOUS_TRANSACTION" in res2["refused"] and g2 is None


# 17
def test_17_container_must_be_finished_before_publish(env):
    approve_ig()
    res, g, _ = run(env, statuses=("IN_PROGRESS", "ERROR"))
    assert ig.S_CONTAINER_FAILED in res["refused"] and g.publishes == 0
    approve_ig()  # (approval still valid; container failure published nothing)
    res2, g2, _ = run(env)
    assert "PRIOR_ATTEMPT_CONTAINER_FAILED" in res2["refused"] and g2 is None


def test_17b_still_processing_exits_without_publishing(env, monkeypatch):
    monkeypatch.setattr(ig, "POLL_MAX_ATTEMPTS", 3)
    approve_ig()
    res, g, _ = run(env, statuses=("IN_PROGRESS",))
    assert "CONTAINER_STILL_PROCESSING" in res["refused"] and g.publishes == 0 and tx_state(env) == ig.S_PROCESSING


# 18b
def test_18b_readback_mismatch_not_certified(env):
    approve_ig()
    res, g, _ = run(env, media_caption="something else")
    assert ig.S_READBACK_FAILED in res["refused"] and tx_state(env) == ig.S_READBACK_FAILED
    assert fb.persistence.read_records(fb.RECEIPT_COLLECTION) == []
    res2, g2, _ = run(env, media_product_type="FEED")
    assert "DUPLICATE_OR_AMBIGUOUS_TRANSACTION" in res2["refused"]


# 20 / 21
def test_20_21_no_instagram_published_and_facebook_unchanged():
    gov = ROOT / "data" / "governed"
    txs = [json.loads(l) for l in (gov / "distribution_transactions.jsonl").read_text().splitlines() if l.strip()]
    receipts = [json.loads(l) for l in (gov / "distribution_publish_receipts.jsonl").read_text().splitlines() if l.strip()]
    # After the 2026-11-12 certification exactly ONE Instagram Reel was published.
    ig_receipts = [r for r in receipts if r.get("platform") == "INSTAGRAM"]
    assert len(ig_receipts) <= 1
    if ig_receipts:
        assert ig_receipts[0]["instagram_media_id"] == "18017879462954773"
        assert ig_receipts[0]["readback_verified"] is True and ig_receipts[0]["simulated"] is False
    fb_receipts = [r for r in receipts if r.get("platform") == "FACEBOOK"]
    assert len(fb_receipts) == 1 and fb_receipts[0]["publish_receipt_id"] == "rcpt_pub_e3a1aae0dda7ee39"
    assert fb_receipts[0]["meta_post_id"] == "1722332634511930_1182879984073759"
    fbreq = json.loads(REAL_FB_REQUEST.read_text())
    assert fbreq["request_hash"] == fb.compute_request_hash(fbreq) == fb_receipts[0]["approval_hash"]
    ig_approvals = [json.loads(l) for l in (gov / "approvals.jsonl").read_text().splitlines()
                    if l.strip() and ig.ACTION_ID in l]
    assert {a["id"] for a in ig_approvals} <= {"appr_e9ab343220a74906936ec8a8a2224450"}


# Truth correction: superseded request can never be approved or published
def test_22_superseded_request_refused_and_new_caption_truthful(env):
    old = json.loads((ROOT / "dist/creative/holiday_instagram_bounded_publish_approval_request.json").read_text())
    assert old["status"] == "SUPERSEDED" and old["superseded_by"] == IG_REQ_ID
    assert any("REQUEST_SUPERSEDED" in p for p in ig.verify_request(old))
    (env["dir"] / "old_approval_request.json").write_text(json.dumps(old))
    with pytest.raises(fb.PublishRefused, match="REQUEST_SUPERSEDED"):
        ig.approve(old["approval_request_id"], io_=owner_io(), out=lambda *a: None)
    with pytest.raises(fb.PublishRefused, match="REQUEST_SUPERSEDED"):
        ig.publish(old["approval_request_id"], graph_factory=lambda t: (_ for _ in ()).throw(AssertionError("no graph")),
                   token_provider=lambda: FAKE_TOKEN, public_video_checker=good_hosted, out=lambda *a: None)
    new = env["req"]
    assert "link in bio" not in new["caption"].lower()
    assert new["campaign_url"] in new["caption"] and "copy this address" in new["caption"]
    assert new["idempotency_key"] != old["idempotency_key"] and new["request_hash"] != old["request_hash"]
    assert new["video"] == {**old["video"], **{k: new["video"][k] for k in ("path",)}} or \
        new["video"]["provider_derivative"]["sha256"] == old["video"]["provider_derivative"]["sha256"]
    assert new["public_video_url"] == old["public_video_url"] and new["max_external_posts"] == 1
