#!/usr/bin/env python3
"""Bounded, owner-approved Instagram Reel live publisher (Section 31B).

Reuses the Facebook bounded-publish infrastructure (facebook_live_publisher):
owner-presence check, governed approvals, governed transaction/receipt
collections + lock, Graph client, canonical Holiday credential resolution.

Flow (Instagram API with Facebook Login, Page access token):
  POST /{ig-id}/media (media_type=REELS, video_url, caption)  -> container id
  GET  /{container}?fields=status_code,status                  -> poll FINISHED
  POST /{ig-id}/media_publish (creation_id)                    -> media id
  GET  /{media-id}?fields=...                                  -> read-back

State machine (persisted before every provider call):
  CONTAINER_CREATING -> CONTAINER_PROCESSING -> READY_TO_PUBLISH -> PUBLISHING
  -> PROVIDER_ACCEPTED -> PUBLISHED
Ambiguous: CONTAINER_CREATE_UNKNOWN, PUBLISH_OUTCOME_UNKNOWN, READBACK_FAILED
(never auto-retried; `reconcile` investigates read-only). A known container is
resumed, never duplicated.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts", ROOT / "scripts" / "distribution"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import facebook_live_publisher as fb  # noqa: E402  (shared infrastructure)
from facebook_live_publisher import PublishRefused  # noqa: E402
from nexus_agent_platform.governed import approvals, persistence  # noqa: E402

ACTION_ID = "distribution.instagram.bounded_publish"
HOLIDAY_IG_ID = "17841480885973564"
HOLIDAY_IG_USERNAME = "the612amritual"
HOLIDAY_IG_CHANNEL_ACCOUNT_ID = "acc_holiday_instagram_01"
FORBIDDEN_IG_IDS = frozenset({"17841480265043148"})  # @goclearonline
POLL_INTERVAL_SECONDS = 5
POLL_MAX_ATTEMPTS = 60  # ~5 minutes; then exit and resume the SAME container later

S_CREATING = "CONTAINER_CREATING"
S_CREATE_UNKNOWN = "CONTAINER_CREATE_UNKNOWN"
S_CREATE_REJECTED = "CONTAINER_CREATE_REJECTED"
S_PROCESSING = "CONTAINER_PROCESSING"
S_CONTAINER_FAILED = "CONTAINER_FAILED"
S_READY = "READY_TO_PUBLISH"
S_PUBLISHING = "PUBLISHING"
S_PUBLISH_UNKNOWN = "PUBLISH_OUTCOME_UNKNOWN"
S_PUBLISH_REJECTED = "PUBLISH_REJECTED"
S_ACCEPTED = "PROVIDER_ACCEPTED"
S_READBACK_FAILED = "READBACK_FAILED"
S_PUBLISHED = "PUBLISHED"
BLOCKING_STATES = frozenset({S_CREATING, S_CREATE_UNKNOWN, S_PUBLISHING, S_PUBLISH_UNKNOWN, S_ACCEPTED, S_READBACK_FAILED})
RESUMABLE_STATES = frozenset({S_PROCESSING, S_READY})
RETRYABLE_WITH_FLAG = frozenset({S_CREATE_REJECTED, S_CONTAINER_FAILED, S_PUBLISH_REJECTED})

PROTECTED_FIELDS = (
    "approval_request_id", "venture_id", "campaign_id", "distribution_job_id", "platform",
    "channel_account_id", "instagram_account_id", "instagram_username", "post_format", "caption",
    "campaign_url", "share_to_feed", "public_video_url", "max_external_posts", "certification_purpose",
    "certification_run_id", "idempotency_key",
)


# --------------------------------------------------------------------------
# Request (immutable, hash-bound to live video bytes)
# --------------------------------------------------------------------------

def compute_request_hash(req: Dict[str, Any]) -> str:
    video = req.get("video") or {}
    deriv = video.get("provider_derivative") or {}
    live = {}
    for label, entry in (("source", video), ("derivative", deriv)):
        p = entry.get("path")
        live[label] = fb._sha256_file(fb._resolve_path(p)) if p and fb._resolve_path(p).exists() else "MISSING"
    protected = {k: req.get(k) for k in PROTECTED_FIELDS}
    protected["video"] = {
        "asset_id": video.get("asset_id"), "path": video.get("path"),
        "derivative_asset_id": deriv.get("asset_id"), "derivative_path": deriv.get("path"),
        "declared_public_sha256": req.get("public_video_sha256"),
        "live_source_sha256": live["source"], "live_derivative_sha256": live["derivative"],
    }
    return fb._sha256_bytes(json.dumps(protected, sort_keys=True, separators=(",", ":")).encode())


def expected_idempotency_key(req: Dict[str, Any]) -> str:
    parts = [req.get("venture_id"), req.get("campaign_id"), req.get("platform"), req.get("channel_account_id"),
             (req.get("video") or {}).get("asset_id"), req.get("approval_request_id"), req.get("certification_run_id")]
    return "idem_" + fb._sha256_bytes("|".join(str(p) for p in parts).encode())[:24]


def verify_request(req: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    if req.get("status") == "SUPERSEDED" or req.get("superseded_by"):
        problems.append(f"REQUEST_SUPERSEDED by {req.get('superseded_by')} (cannot be approved or published)")
    if req.get("request_hash") != compute_request_hash(req):
        problems.append("REQUEST_HASH_MISMATCH (protected field or video changed)")
    video = req.get("video") or {}
    deriv = video.get("provider_derivative") or {}
    for label, entry in (("source", video), ("derivative", deriv)):
        p = entry.get("path")
        if not p or not fb._resolve_path(p).exists():
            problems.append(f"VIDEO_MISSING:{label}")
        elif entry.get("sha256") != fb._sha256_file(fb._resolve_path(p)):
            problems.append(f"VIDEO_SHA_MISMATCH:{label}")
    if req.get("public_video_sha256") != deriv.get("sha256"):
        problems.append("PUBLIC_VIDEO_NOT_BOUND_TO_DERIVATIVE")
    if not str(req.get("public_video_url", "")).startswith("https://"):
        problems.append("PUBLIC_VIDEO_URL_NOT_HTTPS")
    if req.get("platform") != "INSTAGRAM":
        problems.append("PLATFORM_NOT_INSTAGRAM")
    if req.get("post_format") != "REELS":
        problems.append("POST_FORMAT_NOT_REELS")
    if req.get("instagram_account_id") != HOLIDAY_IG_ID or req.get("instagram_account_id") in FORBIDDEN_IG_IDS:
        problems.append("TARGET_ACCOUNT_LOCK_VIOLATION")
    if req.get("instagram_username") != HOLIDAY_IG_USERNAME:
        problems.append("TARGET_USERNAME_LOCK_VIOLATION")
    if req.get("channel_account_id") != HOLIDAY_IG_CHANNEL_ACCOUNT_ID:
        problems.append("CHANNEL_ACCOUNT_LOCK_VIOLATION")
    if req.get("venture_id") != fb.HOLIDAY_VENTURE_ID:
        problems.append("VENTURE_LOCK_VIOLATION")
    if req.get("max_external_posts") != 1:
        problems.append("MAX_EXTERNAL_POSTS_NOT_1")
    if req.get("idempotency_key") != expected_idempotency_key(req):
        problems.append("IDEMPOTENCY_KEY_MISMATCH")
    if len(req.get("caption") or "") > 2200 or (req.get("caption") or "").count("#") > 30:
        problems.append("CAPTION_EXCEEDS_INSTAGRAM_LIMITS")
    return problems


def check_public_video(url: str, expected_sha256: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch the hosted video like Meta would and confirm it is exactly the approved bytes."""
    req = urllib.request.Request(url, headers={"User-Agent": "facebookexternalhit/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=fb.ccp._get_ssl_context()) as resp:
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            status = resp.status
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, "fetchable": False}
    except Exception as e:
        return {"http_status": None, "fetchable": False, "error": type(e).__name__}
    sha = hashlib.sha256(body).hexdigest()
    return {"http_status": status, "content_type": ctype, "bytes": len(body), "sha256": sha,
            "sha256_match": sha == expected_sha256,
            "fetchable": status == 200 and ctype.startswith("video/mp4") and sha == expected_sha256}


# --------------------------------------------------------------------------
# Approval (same owner command, Instagram binding)
# --------------------------------------------------------------------------

BINDING_KEYS = ("idempotency_key", "instagram_account_id", "channel_account_id", "venture_id", "platform",
                "public_video_url", "public_video_sha256")


def _latest_approvals_for(request_id: str) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for rec in persistence.read_records("approvals"):
        if rec.get("id") in seen:
            continue
        seen.add(rec.get("id"))
        if rec.get("action_id") == ACTION_ID and (rec.get("input_summary") or {}).get("request_id") == request_id:
            out.append(rec)
    return out


def approval_problems(approval: Dict[str, Any], req: Dict[str, Any]) -> List[str]:
    problems = []
    reason = approvals.is_approval_valid_for(approval, ACTION_ID, None)
    if reason:
        problems.append(f"APPROVAL_NOT_VALID: {reason}")
    inputs = approval.get("input_summary") or {}
    if approval.get("requested_by") != fb.REQUESTER or approval.get("resolved_by") != fb.OWNER:
        problems.append("APPROVAL_NOT_FROM_OWNER_CLI")
    if (inputs.get("owner_attestation") or {}).get("method") != fb.ATTESTATION_METHOD:
        problems.append("OWNER_ATTESTATION_MISSING")
    current = compute_request_hash(req)
    if inputs.get("request_hash") != current or req.get("request_hash") != current:
        problems.append("APPROVAL_INVALIDATED: request changed after approval")
    for key in BINDING_KEYS:
        if inputs.get(key) != req.get(key):
            problems.append(f"APPROVAL_BINDING_MISMATCH:{key}")
    if inputs.get("max_external_posts") != 1:
        problems.append("APPROVAL_BINDING_MISMATCH:max_external_posts")
    return problems


def approval_status(request_id: str) -> Dict[str, Any]:
    path, req = fb.find_request(request_id)
    req_problems = verify_request(req)
    recs = _latest_approvals_for(request_id)
    out = {"approval_request_id": request_id, "platform": "INSTAGRAM", "request_path": str(path.relative_to(fb.ROOT)),
           "request_hash": req.get("request_hash"), "request_intact": not req_problems,
           "request_problems": req_problems, "idempotency_key": req.get("idempotency_key")}
    if req.get("status") == "SUPERSEDED" or req.get("superseded_by"):
        out["approval_status"] = "SUPERSEDED"
        out["superseded_by"] = req.get("superseded_by")
        return out
    if not recs:
        out["approval_status"] = "WAITING_FOR_RAY_APPROVAL"
        return out
    rec = recs[0]
    out.update(approval_id=rec.get("id"), approved_at=rec.get("resolved_at"))
    status = str(rec.get("status")).upper()
    if status == "APPROVED":
        probs = approval_problems(rec, req)
        status = "INVALIDATED" if any("INVALIDATED" in p or "BINDING" in p for p in probs) else \
            ("EXPIRED" if approvals.approval_is_expired(rec) else ("APPROVED" if not probs else "INVALID"))
        out["approval_problems"] = probs
    out["approval_status"] = status
    return out


def approve(request_id: str, io_: Optional[fb.OwnerIO] = None, out=print) -> Dict[str, Any]:
    io_ = io_ or fb.OwnerIO.real()
    path, req = fb.find_request(request_id)
    problems = verify_request(req)
    if problems:
        raise PublishRefused("APPROVAL_REFUSED: " + "; ".join(problems))
    for rec in _latest_approvals_for(request_id):
        if str(rec.get("status")) in ("approved", "consumed") and not approval_problems(rec, req):
            out(f"ALREADY_APPROVED approval_id={rec['id']} (no new approval recorded)")
            return {"status": "ALREADY_APPROVED", "approval_id": rec["id"]}
    deriv = req["video"]["provider_derivative"]
    out("\n=== NEXUS BOUNDED INSTAGRAM REEL PUBLISH — OWNER APPROVAL ===")
    out(f"Request:      {req['approval_request_id']}  (hash {req['request_hash'][:16]})")
    out(f"Venture:      {req['venture_id']}   Campaign: {req['campaign_id']}")
    out(f"Platform:     INSTAGRAM Reel on @{req['instagram_username']} ({req['instagram_account_id']})  account {req['channel_account_id']}")
    out(f"Video:        {deriv['path']}  sha256 {deriv['sha256'][:16]}  ({req['video'].get('summary', '')})")
    out(f"Hosted at:    {req['public_video_url']}")
    out(f"Campaign URL: {req['campaign_url']}  (not clickable in Instagram captions)")
    out(f"Max posts:    {req['max_external_posts']}   Purpose: {req['certification_purpose']}")
    out("Caption:\n---\n" + req["caption"] + "\n---")
    for note in req.get("review_notes", []):
        out("Note:         " + note)
    out("Limitation:   " + req.get("rollback_limitations", ""))
    out("Approving records consent only; it does NOT publish.")
    attestation = fb.owner_presence_check(req, io_)
    summary = {
        "request_id": req["approval_request_id"], "request_hash": req["request_hash"],
        **{k: req[k] for k in BINDING_KEYS}, "campaign_id": req["campaign_id"],
        "max_external_posts": req["max_external_posts"], "certification_scope": "INSTAGRAM_ONLY",
        "certification_run_id": req["certification_run_id"], "owner_attestation": attestation,
    }
    pending = approvals.create_approval_request(
        action_id=ACTION_ID, requested_by=fb.REQUESTER, requested_for=fb.OWNER, input_summary=summary,
        action_summary=f"Publish exactly 1 Instagram Reel to @{req['instagram_username']} ({req['instagram_account_id']})",
        evidence_refs=[str(path.relative_to(fb.ROOT))], ttl_seconds=fb.APPROVAL_TTL_SECONDS)
    res = approvals.resolve_approval(pending["id"], "approve", resolved_by=fb.OWNER,
                                     feedback=f"owner CLI approval ({fb.ATTESTATION_METHOD})")
    if not res.get("approved"):
        raise PublishRefused(f"APPROVAL_NOT_RECORDED: {res.get('status')}")
    try:
        from nexus_agent_platform.supabase_decision_consumer import sync_approval
        sync_approval(approvals.get_approval(pending["id"]) or {})
    except Exception:
        pass
    out(f"\nAPPROVAL_RECORDED approval_id={pending['id']} expires_at={pending['expires_at']}")
    out("EXTERNAL_CONTENT_PUBLISHED=NO (approval only)")
    return {"status": "APPROVED", "approval_id": pending["id"], "expires_at": pending["expires_at"]}


# --------------------------------------------------------------------------
# Publish
# --------------------------------------------------------------------------

def _approved_for(req: Dict[str, Any]) -> Dict[str, Any]:
    recs = _latest_approvals_for(req["approval_request_id"])
    if not recs:
        raise PublishRefused("APPROVAL_REQUIRED: WAITING_FOR_RAY_APPROVAL")
    probs = approval_problems(recs[0], req)
    if probs:
        raise PublishRefused("APPROVAL_GATE_BLOCKED: " + "; ".join(probs))
    return recs[0]


def _verify_target(graph: fb.MetaGraphClient) -> None:
    status, page = graph.get(fb.HOLIDAY_PAGE_ID, "id,instagram_business_account{id,username}")
    ig = (page or {}).get("instagram_business_account") or {}
    if status != 200 or ig.get("id") != HOLIDAY_IG_ID or ig.get("id") in FORBIDDEN_IG_IDS \
            or ig.get("username") != HOLIDAY_IG_USERNAME:
        raise PublishRefused(f"TARGET_ACCOUNT_LOCK_VIOLATION: credential's linked IG is {ig.get('id')} (HTTP {status})")


def _poll_container(graph: fb.MetaGraphClient, tx: Dict[str, Any], sleep: Callable[[float], None]) -> Dict[str, Any]:
    cid = tx["media_container_id"]
    last = None
    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        status, body = graph.get(cid, "id,status_code,status")
        code = (body or {}).get("status_code")
        if status == 200 and code != last:
            tx = fb._write_tx(tx, container_status_code=code, container_status=body.get("status"), poll_attempts=attempt)
            last = code
        if code == "FINISHED":
            return fb._write_tx(tx, state=S_READY, container_status_code=code)
        if code in ("ERROR", "EXPIRED"):
            fb._write_tx(tx, state=S_CONTAINER_FAILED, container_status_code=code, error=body.get("status"))
            raise PublishRefused(f"{S_CONTAINER_FAILED}: container {cid} is {code} ({body.get('status')}); not publishing")
        if code == "PUBLISHED":
            fb._write_tx(tx, state=S_PUBLISH_UNKNOWN, container_status_code=code,
                         error="container already PUBLISHED but no media id recorded")
            raise PublishRefused(f"{S_PUBLISH_UNKNOWN}: container {cid} already PUBLISHED; run reconcile")
        sleep(POLL_INTERVAL_SECONDS)
    raise PublishRefused(f"CONTAINER_STILL_PROCESSING: {cid} not FINISHED after {POLL_MAX_ATTEMPTS} polls; "
                         "re-run publish to resume the SAME container (no new container will be created)")


def publish(request_id: str, *, graph_factory: Callable[[str], fb.MetaGraphClient] = fb.MetaGraphClient,
            token_provider: Callable[[], str] = fb.resolve_holiday_page_token,
            public_video_checker: Callable[[str, str], Dict[str, Any]] = check_public_video,
            sleep: Callable[[float], None] = time.sleep, allow_new_container_after_failure: bool = False,
            out=print) -> Dict[str, Any]:
    with fb._tx_lock():
        _, req = fb.find_request(request_id)
        problems = verify_request(req)
        if problems:
            raise PublishRefused("REQUEST_INVALID: " + "; ".join(problems))
        idem = req["idempotency_key"]
        tx = fb.latest_transaction(idem)
        state = (tx or {}).get("state")
        if state == S_PUBLISHED:
            out(f"EXISTING_SUCCESS_RECEIPT={tx.get('publish_receipt_id')} INSTAGRAM_MEDIA_ID={tx.get('instagram_media_id')} (not sending)")
            return {"result": "ALREADY_PUBLISHED", **tx}
        if state in BLOCKING_STATES:
            raise PublishRefused(f"DUPLICATE_OR_AMBIGUOUS_TRANSACTION: {idem} is {state}; run reconcile — no automatic retry")
        if state in RETRYABLE_WITH_FLAG and not allow_new_container_after_failure:
            raise PublishRefused(f"PRIOR_ATTEMPT_{state}: {tx.get('error')}; nothing was published; "
                                 "re-run with explicit --new-container-after-failure")
        approval = _approved_for(req)
        published = [t for t in fb.transactions_for_job(req["distribution_job_id"]) if t.get("state") == S_PUBLISHED]
        if len(published) >= int(req["max_external_posts"]):
            raise PublishRefused("MAX_EXTERNAL_POSTS_REACHED")

        deriv = req["video"]["provider_derivative"]
        hosted = public_video_checker(req["public_video_url"], deriv["sha256"])
        if not hosted.get("fetchable"):
            raise PublishRefused(f"PUBLIC_VIDEO_NOT_FETCHABLE_OR_CHANGED: {hosted}")

        token = token_provider()
        graph = graph_factory(token)
        del token
        _verify_target(graph)

        if state in RESUMABLE_STATES and tx.get("media_container_id"):
            out(f"RESUMING existing container {tx['media_container_id']} (state {state}); no new container")
        else:
            retry_count = (tx.get("retry_count", 0) + 1) if tx else 0
            base = {
                "idempotency_key": idem, "approval_request_id": req["approval_request_id"],
                "approval_id": approval["id"], "approval_hash": req["request_hash"],
                "venture_id": req["venture_id"], "campaign_id": req["campaign_id"],
                "distribution_job_id": req["distribution_job_id"], "channel_account_id": req["channel_account_id"],
                "platform": "INSTAGRAM", "instagram_account_id": HOLIDAY_IG_ID,
                "video_asset_id": req["video"]["asset_id"], "derivative_asset_id": deriv["asset_id"],
                "video_sha256": deriv["sha256"], "public_video_url": req["public_video_url"],
                "caption_hash": fb._sha256_bytes(req["caption"].encode()), "retry_count": retry_count,
                "graph_api_version": graph.version, "public_video_check": hosted,
            }
            tx = fb._write_tx(base, state=S_CREATING, started_at=fb.utc_now())  # persisted BEFORE Meta call
            try:
                status, body = graph.post_form(f"{HOLIDAY_IG_ID}/media", {
                    "media_type": "REELS", "video_url": req["public_video_url"], "caption": req["caption"],
                    "share_to_feed": "true" if req.get("share_to_feed", True) else "false"})
            except fb.GraphTransportError as e:
                fb._write_tx(tx, state=S_CREATE_UNKNOWN, error=f"TRANSPORT:{e}")
                raise PublishRefused(f"{S_CREATE_UNKNOWN}: no response creating container ({e}); run reconcile")
            if status == 200 and body.get("id"):
                tx = fb._write_tx(tx, state=S_PROCESSING, media_container_id=body["id"], container_http_status=status)
            elif status >= 500:
                fb._write_tx(tx, state=S_CREATE_UNKNOWN, container_http_status=status, error=body.get("error"))
                raise PublishRefused(f"{S_CREATE_UNKNOWN}: HTTP {status}; run reconcile")
            else:
                fb._write_tx(tx, state=S_CREATE_REJECTED, container_http_status=status, error=body.get("error"))
                raise PublishRefused(f"{S_CREATE_REJECTED}: HTTP {status} {body.get('error')}")

        if tx["state"] == S_PROCESSING:
            tx = _poll_container(graph, tx, sleep)
        if tx["state"] != S_READY:
            raise PublishRefused(f"CONTAINER_NOT_READY: {tx['state']}")

        tx = fb._write_tx(tx, state=S_PUBLISHING, publish_started_at=fb.utc_now())  # persisted BEFORE publish
        try:
            status, body = graph.post_form(f"{HOLIDAY_IG_ID}/media_publish", {"creation_id": tx["media_container_id"]})
        except fb.GraphTransportError as e:
            fb._write_tx(tx, state=S_PUBLISH_UNKNOWN, error=f"TRANSPORT:{e}", provider_request_outcome="NO_RESPONSE")
            raise PublishRefused(f"{S_PUBLISH_UNKNOWN}: no response from media_publish ({e}); run reconcile")
        if status == 200 and body.get("id"):
            tx = fb._write_tx(tx, state=S_ACCEPTED, provider_http_status=status, instagram_media_id=body["id"],
                              provider_request_outcome="ACCEPTED")
        elif status >= 500 or status == 200:
            fb._write_tx(tx, state=S_PUBLISH_UNKNOWN, provider_http_status=status, error=body.get("error"),
                         provider_request_outcome="AMBIGUOUS")
            raise PublishRefused(f"{S_PUBLISH_UNKNOWN}: HTTP {status}; run reconcile")
        else:
            cstatus, cbody = graph.get(tx["media_container_id"], "status_code")
            if (cbody or {}).get("status_code") == "PUBLISHED":
                fb._write_tx(tx, state=S_PUBLISH_UNKNOWN, provider_http_status=status, error=body.get("error"))
                raise PublishRefused(f"{S_PUBLISH_UNKNOWN}: HTTP {status} but container PUBLISHED; run reconcile")
            fb._write_tx(tx, state=S_PUBLISH_REJECTED, provider_http_status=status, error=body.get("error"),
                         provider_request_outcome="REJECTED")
            raise PublishRefused(f"{S_PUBLISH_REJECTED}: HTTP {status} {body.get('error')}")

        return _finish_with_readback(graph, tx, req, approval, out)


def verify_readback(graph: fb.MetaGraphClient, media_id: str, req: Dict[str, Any]) -> Dict[str, Any]:
    status, m = graph.get(media_id, "id,caption,media_type,media_product_type,permalink,timestamp,owner,username,media_url,shortcode")
    r = {"media_http_status": status, "media_exists": status == 200 and m.get("id") == media_id}
    owner = (m.get("owner") or {}).get("id")
    r["instagram_account_id_match"] = bool(r["media_exists"] and (owner == HOLIDAY_IG_ID or
                                                                  (not owner and m.get("username") == HOLIDAY_IG_USERNAME)))
    r["caption_match"] = (m.get("caption") or "").strip() == req["caption"].strip()
    r["media_type_match"] = m.get("media_type") == "VIDEO" and m.get("media_product_type") == "REELS"
    r["video_present"] = r["media_type_match"] and bool(m.get("media_url") or m.get("permalink"))
    r["created_time"] = m.get("timestamp")
    r["permalink"] = m.get("permalink")
    r["shortcode"] = m.get("shortcode")
    r["readback_verified"] = all(r[k] for k in ("media_exists", "instagram_account_id_match", "caption_match",
                                                "media_type_match", "video_present")) and bool(r["created_time"] and r["permalink"])
    return r


def _finish_with_readback(graph, tx, req, approval, out) -> Dict[str, Any]:
    rb = verify_readback(graph, tx["instagram_media_id"], req)
    if not rb["readback_verified"]:
        fb._write_tx(tx, state=S_READBACK_FAILED, readback=rb, readback_verified=False)
        raise PublishRefused(f"{S_READBACK_FAILED}: {json.dumps(rb)}")
    receipt_id = "rcpt_pub_" + fb._sha256_bytes(f"{tx['idempotency_key']}:{tx['instagram_media_id']}".encode())[:16]
    deriv = req["video"]["provider_derivative"]
    receipt = {
        "publish_receipt_id": receipt_id, "approval_id": approval["id"], "approval_request_id": req["approval_request_id"],
        "request_hash": req["request_hash"], "idempotency_key": tx["idempotency_key"], "venture_id": req["venture_id"],
        "campaign_id": req["campaign_id"], "distribution_job_id": req["distribution_job_id"],
        "channel_account_id": req["channel_account_id"], "platform": "INSTAGRAM", "instagram_account_id": HOLIDAY_IG_ID,
        "video_asset_id": req["video"]["asset_id"], "derivative_asset_id": deriv["asset_id"],
        "video_sha256": deriv["sha256"], "public_video_url": req["public_video_url"],
        "media_container_id": tx["media_container_id"], "instagram_media_id": tx["instagram_media_id"],
        "permalink": rb["permalink"], "provider_http_status": tx.get("provider_http_status"),
        "published_at": rb["created_time"], "readback": rb, "readback_verified": True,
        "final_job_state": S_PUBLISHED, "retry_count": tx.get("retry_count", 0), "recorded_at": fb.utc_now(),
        "simulated": False,
    }
    persistence.append_record(fb.RECEIPT_COLLECTION, receipt)
    tx = fb._write_tx(tx, state=S_PUBLISHED, readback=rb, readback_verified=True, permalink=rb["permalink"],
                      publish_receipt_id=receipt_id, published_at=rb["created_time"])
    try:
        from types import SimpleNamespace
        from distribution_foundation import PublishReceipt
        from social_publishing_engine import SocialPublishingMemory
        pr = PublishReceipt(publish_receipt_id=receipt_id, distribution_job_id=req["distribution_job_id"],
                            venture_id=req["venture_id"], campaign_id=req["campaign_id"],
                            channel_account_id=req["channel_account_id"], platform="INSTAGRAM",
                            external_post_id=tx["instagram_media_id"], published_at=rb["created_time"] or fb.utc_now(),
                            media_asset_ids=[req["video"]["asset_id"], deriv["asset_id"]],
                            copy_hash=tx["caption_hash"], target_url=req.get("campaign_url"),
                            provider_response_reference=f"ig_container:{tx['media_container_id']}",
                            external_url=rb["permalink"])
        job = SimpleNamespace(distribution_job_id=req["distribution_job_id"], venture_id=req["venture_id"],
                              campaign_id=req["campaign_id"], product_id="prod_stoneware_mug_14oz",
                              channel_account_id=req["channel_account_id"], platform="INSTAGRAM")
        SocialPublishingMemory.record_publication(pr, job)
    except Exception as exc:
        persistence.emit_audit_event({"type": "social_memory_lineage_failed", "receipt": receipt_id, "error": str(exc)[:200]})
    approvals.mark_approval_consumed(approval["id"])
    out(f"PUBLISHED INSTAGRAM_MEDIA_ID={tx['instagram_media_id']} PERMALINK={rb['permalink']} RECEIPT={receipt_id}")
    return {"result": "PUBLISHED", **receipt}


def reconcile(request_id: str, *, graph_factory: Callable[[str], fb.MetaGraphClient] = fb.MetaGraphClient,
              token_provider: Callable[[], str] = fb.resolve_holiday_page_token, out=print) -> Dict[str, Any]:
    """Investigate an ambiguous attempt WITHOUT creating containers or publishing."""
    with fb._tx_lock():
        _, req = fb.find_request(request_id)
        tx = fb.latest_transaction(req["idempotency_key"])
        state = (tx or {}).get("state")
        if state not in BLOCKING_STATES:
            return {"result": "NOTHING_TO_RECONCILE", "state": state}
        graph = graph_factory(token_provider())
        if tx.get("instagram_media_id"):
            approval = _latest_approvals_for(req["approval_request_id"])[0]
            return _finish_with_readback(graph, tx, req, approval, out)
        status, media = graph.get(f"{HOLIDAY_IG_ID}/media", "id,caption,timestamp,media_product_type")
        since = (tx.get("started_at") or "")[:19]
        matches = [m for m in (media.get("data") or []) if (m.get("caption") or "").strip() == req["caption"].strip()
                   and (m.get("timestamp") or "") >= since]
        if len(matches) == 1:
            tx = fb._write_tx(tx, instagram_media_id=matches[0]["id"], reconciled=True)
            approval = _latest_approvals_for(req["approval_request_id"])[0]
            return _finish_with_readback(graph, tx, req, approval, out)
        if len(matches) > 1:
            out(f"RECONCILE: {len(matches)} matching media found; left as {state} for owner review")
            return {"result": "UNRESOLVED_MULTIPLE", "state": state, "matches": len(matches)}
        cid = tx.get("media_container_id")
        if cid:
            cstatus, cbody = graph.get(cid, "status_code,status")
            code = (cbody or {}).get("status_code")
            if code == "FINISHED" and state in (S_PUBLISHING, S_PUBLISH_UNKNOWN):
                fb._write_tx(tx, state=S_READY, reconciled=True, container_status_code=code)
                out(f"RECONCILE: container {cid} FINISHED and no media published; state -> {S_READY} (publish may resume)")
                return {"result": "SAFE_TO_RESUME", "state": S_READY}
            out(f"RECONCILE: no media found; container {cid} is {code}; left as {state}")
            return {"result": "UNRESOLVED", "state": state, "container_status_code": code}
        out(f"RECONCILE: no media and no container id recorded; left as {state} for owner review")
        return {"result": "UNRESOLVED", "state": state}
