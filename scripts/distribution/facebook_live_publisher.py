#!/usr/bin/env python3
"""Bounded, owner-approved Facebook Page live publisher (Section 31B).

Replaces the simulation path (`publish_now_after_approval`, which fabricates
`post_sim_*` IDs) for certification sends. Reuses existing Nexus components:

* approval requests: dist/creative/*_approval_request.json (immutable, hashed)
* approvals: governed approval ledger (nexus_agent_platform.governed.approvals)
* transactions/receipts: governed append-only persistence (fsync'd JSONL)
* credential: canonical resolver (credential_control_plane)
* lineage: SocialPublishingMemory + PublishReceipt model

Safety properties:
* approval only via the owner-run CLI (interactive TTY + agent-session refusal
  + one-time nonce + macOS admin password check); hash-bound to the request
* any protected-field or media change invalidates approval
* PUBLISHING persisted (fsync) before contacting Meta; ambiguous outcomes are
  never auto-retried; a successful idempotency key never sends again
* hard locks: Holiday credential, Raytestpage ID, Holiday channel account
* tokens never printed, logged, persisted or placed in URLs
"""
from __future__ import annotations

import fcntl
import getpass
import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts", ROOT / "scripts" / "distribution"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from nexus_agent_platform import credential_control_plane as ccp  # noqa: E402
from nexus_agent_platform.governed import approvals, persistence  # noqa: E402

ACTION_ID = "distribution.facebook.bounded_publish"
REQUESTS_DIR = ROOT / "dist" / "creative"
GRAPH_VERSION = "v23.0"
GRAPH_BASE = "https://graph.facebook.com"

# Hard target locks (Part 11).
HOLIDAY_VENTURE_ID = "vnt_holiday_commerce_pilot_2026"
HOLIDAY_CREDENTIAL_ID = "credential.meta.social.holiday.prod.v1"
HOLIDAY_PAGE_ID = "1722332634511930"
HOLIDAY_CHANNEL_ACCOUNT_ID = "acc_holiday_facebook_01"
FORBIDDEN_CREDENTIAL_IDS = frozenset({"credential.meta.social.goclear.prod.v1", "credential.meta.social.prod.v1"})
FORBIDDEN_PAGE_IDS = frozenset({"131069194210954"})  # GoClear / Clear Credentials

TX_COLLECTION = "distribution_transactions"
RECEIPT_COLLECTION = "distribution_publish_receipts"
REQUESTER = "nexus.distribution.approval_request"
OWNER = "ray"
APPROVAL_TTL_SECONDS = 24 * 3600
ATTESTATION_METHOD = "INTERACTIVE_TTY+NONCE+MACOS_ADMIN_PASSWORD"

AGENT_ENV_MARKERS = (
    "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION",
    "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED", "CODEX_THREAD_ID", "CODEX_SESSION_ID", "CODEX_CI",
)

# Transaction states.
S_PUBLISHING = "PUBLISHING"
S_ACCEPTED = "PROVIDER_ACCEPTED"
S_UNKNOWN = "PUBLISH_OUTCOME_UNKNOWN"
S_REJECTED = "FAILED_PROVIDER_REJECTED"
S_READBACK_FAILED = "READBACK_FAILED"
S_PUBLISHED = "PUBLISHED"
BLOCKING_STATES = frozenset({S_PUBLISHING, S_ACCEPTED, S_UNKNOWN, S_READBACK_FAILED})


class PublishRefused(Exception):
    """Raised for any refusal; message is safe to print."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _resolve_path(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


# --------------------------------------------------------------------------
# Approval request (immutable, hash-bound)
# --------------------------------------------------------------------------

PROTECTED_FIELDS = (
    "approval_request_id", "venture_id", "campaign_id", "distribution_job_id", "platform",
    "channel_account_id", "target_page", "target_page_id", "post_format", "copy", "target_url",
    "max_external_posts", "certification_purpose", "certification_run_id", "idempotency_key",
)


def find_request(request_id: str, requests_dir: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
    base = requests_dir or REQUESTS_DIR
    for path in sorted(base.glob("*_approval_request.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("approval_request_id") == request_id:
            return path, data
    raise PublishRefused(f"REQUEST_NOT_FOUND: {request_id}")


def compute_request_hash(req: Dict[str, Any]) -> str:
    """Hash of every protected field plus the LIVE bytes of both media files."""
    media = req.get("media") or {}
    deriv = media.get("provider_derivative") or {}
    live = {}
    for label, entry in (("source", media), ("derivative", deriv)):
        p = entry.get("path")
        live[label] = _sha256_file(_resolve_path(p)) if p and _resolve_path(p).exists() else "MISSING"
    protected = {k: req.get(k) for k in PROTECTED_FIELDS}
    protected["media"] = {
        "asset_id": media.get("asset_id"), "path": media.get("path"),
        "derivative_asset_id": deriv.get("asset_id"), "derivative_path": deriv.get("path"),
        "live_source_sha256": live["source"], "live_derivative_sha256": live["derivative"],
    }
    return _sha256_bytes(json.dumps(protected, sort_keys=True, separators=(",", ":")).encode())


def expected_idempotency_key(req: Dict[str, Any]) -> str:
    parts = [req.get("venture_id"), req.get("campaign_id"), req.get("platform"), req.get("channel_account_id"),
             (req.get("media") or {}).get("asset_id"), req.get("approval_request_id"), req.get("certification_run_id")]
    return "idem_" + _sha256_bytes("|".join(str(p) for p in parts).encode())[:24]


def verify_request(req: Dict[str, Any]) -> List[str]:
    """Return a list of problems; empty means the request is intact and in-bounds."""
    problems: List[str] = []
    if req.get("status") == "SUPERSEDED":
        problems.append(f"REQUEST_SUPERSEDED_BY:{req.get('superseded_by')}")
    if req.get("request_hash") != compute_request_hash(req):
        problems.append("REQUEST_HASH_MISMATCH (protected field or media changed)")
    media = req.get("media") or {}
    deriv = media.get("provider_derivative") or {}
    for label, entry in (("source", media), ("derivative", deriv)):
        p = entry.get("path")
        if not p or not _resolve_path(p).exists():
            problems.append(f"MEDIA_MISSING:{label}")
        elif entry.get("sha256") != _sha256_file(_resolve_path(p)):
            problems.append(f"MEDIA_SHA_MISMATCH:{label}")
    if req.get("platform") != "FACEBOOK":
        problems.append("PLATFORM_NOT_FACEBOOK")
    if req.get("post_format") != "PHOTO_POST":
        problems.append("POST_FORMAT_NOT_PHOTO_POST")
    if req.get("target_page_id") != HOLIDAY_PAGE_ID or req.get("target_page_id") in FORBIDDEN_PAGE_IDS:
        problems.append("TARGET_PAGE_LOCK_VIOLATION")
    if req.get("channel_account_id") != HOLIDAY_CHANNEL_ACCOUNT_ID:
        problems.append("CHANNEL_ACCOUNT_LOCK_VIOLATION")
    if req.get("venture_id") != HOLIDAY_VENTURE_ID:
        problems.append("VENTURE_LOCK_VIOLATION")
    if req.get("max_external_posts") != 1:
        problems.append("MAX_EXTERNAL_POSTS_NOT_1")
    if req.get("idempotency_key") != expected_idempotency_key(req):
        problems.append("IDEMPOTENCY_KEY_MISMATCH")
    if req.get("target_url") and req["target_url"] not in (req.get("copy") or ""):
        problems.append("TARGET_URL_NOT_IN_COPY")
    return problems


# --------------------------------------------------------------------------
# Owner presence (self-approval prevention)
# --------------------------------------------------------------------------

@dataclass
class OwnerIO:
    env: Dict[str, str]
    stdin_isatty: Callable[[], bool]
    stdout_isatty: Callable[[], bool]
    read_line: Callable[[str], str]
    read_secret: Callable[[str], str]
    verify_password: Callable[[str], Tuple[bool, str]]
    tty_name: Callable[[], str]

    @classmethod
    def real(cls) -> "OwnerIO":
        return cls(env=dict(os.environ), stdin_isatty=sys.stdin.isatty, stdout_isatty=sys.stdout.isatty,
                   read_line=input, read_secret=getpass.getpass, verify_password=_verify_macos_admin_password,
                   tty_name=lambda: os.ttyname(sys.stdin.fileno()))


def _verify_macos_admin_password(password: str) -> Tuple[bool, str]:
    """Validate the local admin password via `sudo -v`; runs nothing as root.

    The password is passed on stdin (never argv). Cached sudo timestamps are
    cleared first and after, and passwordless sudo is rejected as non-proof.
    """
    subprocess.run(["sudo", "-k"], check=False, capture_output=True)
    nopass = subprocess.run(["sudo", "-n", "-v"], check=False, capture_output=True)
    if nopass.returncode == 0:
        subprocess.run(["sudo", "-k"], check=False, capture_output=True)
        return False, "PASSWORDLESS_SUDO_NOT_ACCEPTED_AS_OWNER_PROOF"
    proc = subprocess.run(["sudo", "-S", "-v", "-p", ""], input=password + "\n", text=True,
                          check=False, capture_output=True, timeout=30)
    subprocess.run(["sudo", "-k"], check=False, capture_output=True)
    return proc.returncode == 0, "OK" if proc.returncode == 0 else "PASSWORD_REJECTED"


def owner_presence_check(req: Dict[str, Any], io_: OwnerIO) -> Dict[str, Any]:
    markers = [m for m in AGENT_ENV_MARKERS if io_.env.get(m)]
    if markers:
        raise PublishRefused("AGENT_SESSION_DETECTED: run this command yourself in a normal Terminal window, "
                             "not through Claude Code/Codex (markers: " + ",".join(markers) + ")")
    if not (io_.stdin_isatty() and io_.stdout_isatty()):
        raise PublishRefused("NO_INTERACTIVE_TTY: owner approval must be typed at an interactive terminal")
    nonce = secrets.token_hex(3).upper()
    typed = io_.read_line(f"\nType exactly 'APPROVE {nonce}' to approve this ONE Facebook post: ").strip()
    if typed != f"APPROVE {nonce}":
        raise PublishRefused("CONFIRMATION_PHRASE_MISMATCH: approval not recorded")
    password = io_.read_secret("macOS password for this account (confirms you are the owner; not stored): ")
    ok, detail = io_.verify_password(password)
    del password
    if not ok:
        raise PublishRefused(f"OWNER_VERIFICATION_FAILED: {detail}")
    try:
        tty = io_.tty_name()
    except Exception:
        tty = "UNKNOWN_TTY"
    return {"method": ATTESTATION_METHOD, "os_user": io_.env.get("USER") or getpass.getuser(),
            "uid": os.getuid(), "tty": tty, "nonce": nonce, "verified_at": utc_now()}


# --------------------------------------------------------------------------
# Governed approval binding
# --------------------------------------------------------------------------

def _latest_approvals_for(request_id: str) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for rec in persistence.read_records("approvals"):  # newest first
        if rec.get("id") in seen:
            continue
        seen.add(rec.get("id"))
        if rec.get("action_id") == ACTION_ID and (rec.get("input_summary") or {}).get("request_id") == request_id:
            out.append(rec)
    return out


def approval_problems(approval: Dict[str, Any], req: Dict[str, Any]) -> List[str]:
    """Why this approval cannot authorize a send for this request (empty = valid)."""
    problems = []
    reason = approvals.is_approval_valid_for(approval, ACTION_ID, None)
    if reason:
        problems.append(f"APPROVAL_NOT_VALID: {reason}")
    inputs = approval.get("input_summary") or {}
    if approval.get("requested_by") != REQUESTER or approval.get("resolved_by") != OWNER:
        problems.append("APPROVAL_NOT_FROM_OWNER_CLI")
    att = inputs.get("owner_attestation") or {}
    if att.get("method") != ATTESTATION_METHOD:
        problems.append("OWNER_ATTESTATION_MISSING")
    current_hash = compute_request_hash(req)
    if inputs.get("request_hash") != current_hash or req.get("request_hash") != current_hash:
        problems.append("APPROVAL_INVALIDATED: request changed after approval")
    for key in ("idempotency_key", "target_page_id", "channel_account_id", "venture_id", "platform"):
        if inputs.get(key) != req.get(key):
            problems.append(f"APPROVAL_BINDING_MISMATCH:{key}")
    if inputs.get("max_external_posts") != 1:
        problems.append("APPROVAL_BINDING_MISMATCH:max_external_posts")
    return problems


def approval_status(request_id: str) -> Dict[str, Any]:
    """Read-only status for `nexus distribution approval-status`."""
    path, req = find_request(request_id)
    req_problems = verify_request(req)
    recs = _latest_approvals_for(request_id)
    out = {"approval_request_id": request_id, "request_path": str(path.relative_to(ROOT)),
           "request_hash": req.get("request_hash"), "request_intact": not req_problems,
           "request_problems": req_problems, "idempotency_key": req.get("idempotency_key")}
    if not recs:
        out["approval_status"] = "WAITING_FOR_RAY_APPROVAL"
        return out
    rec = recs[0]
    out["approval_id"] = rec.get("id")
    out["approved_at"] = rec.get("resolved_at")
    status = str(rec.get("status")).upper()
    if status == "APPROVED":
        probs = approval_problems(rec, req)
        status = "INVALIDATED" if any("INVALIDATED" in p or "BINDING" in p for p in probs) else \
            ("EXPIRED" if approvals.approval_is_expired(rec) else ("APPROVED" if not probs else "INVALID"))
        out["approval_problems"] = probs
    out["approval_status"] = status
    return out


def approve(request_id: str, io_: Optional[OwnerIO] = None, out=print) -> Dict[str, Any]:
    """Owner-run approval. Never publishes."""
    io_ = io_ or OwnerIO.real()
    path, req = find_request(request_id)
    problems = verify_request(req)
    if problems:
        raise PublishRefused("APPROVAL_REFUSED: " + "; ".join(problems))
    for rec in _latest_approvals_for(request_id):
        if str(rec.get("status")) in ("approved", "consumed") and not approval_problems(rec, req):
            out(f"ALREADY_APPROVED approval_id={rec['id']} (no new approval recorded)")
            return {"status": "ALREADY_APPROVED", "approval_id": rec["id"]}
    out("\n=== NEXUS BOUNDED FACEBOOK PUBLISH — OWNER APPROVAL ===")
    out(f"Request:      {req['approval_request_id']}  (hash {req['request_hash'][:16]})")
    out(f"Venture:      {req['venture_id']}   Campaign: {req['campaign_id']}")
    out(f"Platform:     FACEBOOK photo post on {req['target_page']} ({req['target_page_id']})  account {req['channel_account_id']}")
    out(f"Media:        {req['media']['provider_derivative']['path']}  sha256 {req['media']['provider_derivative']['sha256'][:16]}")
    out(f"Target URL:   {req['target_url']}")
    out(f"Max posts:    {req['max_external_posts']}   Purpose: {req['certification_purpose']}")
    out("Copy:\n---\n" + req["copy"] + "\n---")
    out("Limitation:   " + req.get("rollback_limitations", ""))
    out("Approving records consent only; it does NOT publish.")
    attestation = owner_presence_check(req, io_)
    pending = approvals.create_approval_request(
        action_id=ACTION_ID, requested_by=REQUESTER, requested_for=OWNER,
        input_summary={
            "request_id": req["approval_request_id"], "request_hash": req["request_hash"],
            "idempotency_key": req["idempotency_key"], "venture_id": req["venture_id"],
            "campaign_id": req["campaign_id"], "platform": req["platform"],
            "channel_account_id": req["channel_account_id"], "target_page_id": req["target_page_id"],
            "max_external_posts": req["max_external_posts"], "certification_scope": "FACEBOOK_ONLY",
            "certification_run_id": req["certification_run_id"], "owner_attestation": attestation},
        action_summary=f"Publish exactly 1 Facebook photo post to {req['target_page']} ({req['target_page_id']})",
        evidence_refs=[str(path.relative_to(ROOT))], ttl_seconds=APPROVAL_TTL_SECONDS)
    res = approvals.resolve_approval(pending["id"], "approve", resolved_by=OWNER,
                                     feedback=f"owner CLI approval ({ATTESTATION_METHOD})")
    if not res.get("approved"):
        raise PublishRefused(f"APPROVAL_NOT_RECORDED: {res.get('status')}")
    try:  # keep the dashboard projection in sync (best effort; local ledger is authoritative)
        from nexus_agent_platform.supabase_decision_consumer import sync_approval
        sync_approval(approvals.get_approval(pending["id"]) or {})
    except Exception:
        pass
    out(f"\nAPPROVAL_RECORDED approval_id={pending['id']} expires_at={pending['expires_at']}")
    out("EXTERNAL_CONTENT_PUBLISHED=NO (approval only)")
    return {"status": "APPROVED", "approval_id": pending["id"], "expires_at": pending["expires_at"]}


# --------------------------------------------------------------------------
# Transaction ledger (idempotency)
# --------------------------------------------------------------------------

@contextmanager
def _tx_lock() -> Iterator[None]:
    lock_path = persistence.governed_data_dir() / "distribution_transactions.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PublishRefused("DUPLICATE_OR_AMBIGUOUS_TRANSACTION: another publish is in progress")
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def latest_transaction(idempotency_key: str) -> Optional[Dict[str, Any]]:
    return persistence.get_record(TX_COLLECTION, idempotency_key, key="idempotency_key")


def _write_tx(tx: Dict[str, Any], **updates: Any) -> Dict[str, Any]:
    new = {**tx, **updates, "updated_at": utc_now()}
    persistence.append_record(TX_COLLECTION, new)
    return new


def transactions_for_job(job_id: str) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for rec in persistence.read_records(TX_COLLECTION):
        k = rec.get("idempotency_key")
        if k in seen:
            continue
        seen.add(k)
        if rec.get("distribution_job_id") == job_id:
            out.append(rec)
    return out


def publish_status(job_id: str) -> Dict[str, Any]:
    """Read-only status for `nexus distribution publish-status`."""
    txs = transactions_for_job(job_id)
    if not txs:
        return {"distribution_job_id": job_id, "final_job_state": "NO_TRANSACTION (READY_FOR_APPROVAL or APPROVED)"}
    tx = txs[0]
    keys = ("platform", "idempotency_key", "state", "approval_id", "approval_request_id", "meta_post_id", "meta_photo_id",
            "public_post_url", "media_container_id", "container_status_code", "instagram_media_id", "permalink",
            "provider_http_status", "readback_verified", "publish_receipt_id",
            "retry_count", "started_at", "updated_at", "error")
    return {"distribution_job_id": job_id, **{k: tx.get(k) for k in keys if k in tx or k in ("state",)}}


# --------------------------------------------------------------------------
# Meta Graph client (token only in Authorization header / POST body)
# --------------------------------------------------------------------------

class GraphTransportError(Exception):
    """No HTTP response received (timeout/connection) — outcome unknown."""


class MetaGraphClient:
    def __init__(self, token: str, version: str = GRAPH_VERSION, timeout: int = 60):
        self._token = token
        self.version = version
        self.timeout = timeout

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, str]] = None,
                 body: Optional[bytes] = None, content_type: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
        url = f"{GRAPH_BASE}/{self.version}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        if content_type:
            req.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ccp._get_ssl_context()) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read() or b"{}")
            except Exception:
                data = {}
            err = data.get("error") or {}
            return e.code, {"error": {"code": err.get("code"), "error_subcode": err.get("error_subcode"),
                                      "type": err.get("type"), "message": _redact(str(err.get("message", "")), self._token)[:300],
                                      "fbtrace_id": err.get("fbtrace_id")}}
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            raise GraphTransportError(type(e).__name__) from None

    def get(self, path: str, fields: str) -> Tuple[int, Dict[str, Any]]:
        return self._request("GET", path, params={"fields": fields})

    def post_form(self, path: str, fields: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
        """Form-encoded POST (token stays in the Authorization header)."""
        return self._request("POST", path, body=urllib.parse.urlencode(fields).encode(),
                             content_type="application/x-www-form-urlencoded")

    def post_photo(self, page_id: str, image: bytes, filename: str, caption: str) -> Tuple[int, Dict[str, Any]]:
        boundary = "nexus" + uuid.uuid4().hex
        buf = io.BytesIO()
        for name, value in (("caption", caption), ("published", "true")):
            buf.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode())
            buf.write(value.encode("utf-8") + b"\r\n")
        buf.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"{filename}\"\r\n"
                  f"Content-Type: image/jpeg\r\n\r\n".encode())
        buf.write(image + b"\r\n" + f"--{boundary}--\r\n".encode())
        return self._request("POST", f"{page_id}/photos", body=buf.getvalue(),
                             content_type=f"multipart/form-data; boundary={boundary}")


def _redact(text: str, token: Optional[str]) -> str:
    return text.replace(token, "[REDACTED]") if token else text


def resolve_holiday_page_token() -> str:
    """Canonical resolver path: capability -> credential id -> secure component."""
    res = ccp.resolve_credential(capability="facebook.publish", venture_id=HOLIDAY_VENTURE_ID)
    cred_id = getattr(res, "credential_id", None)
    status = getattr(getattr(res, "status", None), "value", str(getattr(res, "status", "")))
    if cred_id in FORBIDDEN_CREDENTIAL_IDS or cred_id != HOLIDAY_CREDENTIAL_ID:
        raise PublishRefused(f"TARGET_CREDENTIAL_LOCK_VIOLATION: resolver returned {cred_id}")
    if status != "AVAILABLE":
        raise PublishRefused(f"CREDENTIAL_NOT_AVAILABLE: {status}")
    entry = ccp.registry_entry(HOLIDAY_CREDENTIAL_ID)
    aliases = entry.get("canonical_aliases", {})
    names = [aliases.get("page_access_token"), *entry.get("legacy_aliases", {}).get("page_access_token", [])]
    before = {n: os.environ.get(n) for n in names + [aliases.get("page_id")] if n}
    try:
        ccp.apply_to_process(HOLIDAY_CREDENTIAL_ID)
        token = os.environ.get(aliases.get("page_access_token", ""), "")
    finally:
        for n, v in before.items():  # never leave the secret in the process env
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
    if not token:
        raise PublishRefused("CREDENTIAL_COMPONENT_MISSING: page_access_token")
    return token


# --------------------------------------------------------------------------
# Read-back verification
# --------------------------------------------------------------------------

def verify_readback(graph: MetaGraphClient, post_id: str, photo_id: Optional[str], req: Dict[str, Any]) -> Dict[str, Any]:
    status, post = graph.get(post_id, "id,message,created_time,permalink_url,full_picture,from{id,name},attachments{media_type}")
    result = {"post_http_status": status, "post_exists": status == 200 and post.get("id") == post_id}
    frm = (post.get("from") or {}).get("id")
    result["page_id_match"] = bool(result["post_exists"] and (frm == HOLIDAY_PAGE_ID or post_id.startswith(HOLIDAY_PAGE_ID + "_")))
    msg = (post.get("message") or "").strip()
    result["message_match"] = msg == req["copy"].strip()
    media_types = [a.get("media_type") for a in ((post.get("attachments") or {}).get("data") or [])]
    result["media_present"] = bool(post.get("full_picture")) or "photo" in media_types
    if photo_id:
        pstatus, photo = graph.get(photo_id, "id,from{id},images,created_time")
        result["photo_http_status"] = pstatus
        result["media_present"] = result["media_present"] and pstatus == 200 and bool(photo.get("images"))
    result["target_url_present_in_message"] = req["target_url"] in msg
    result["created_time"] = post.get("created_time")
    result["permalink_url"] = post.get("permalink_url")
    result["readback_verified"] = all(result[k] for k in ("post_exists", "page_id_match", "message_match",
                                                          "media_present", "target_url_present_in_message")) \
        and bool(result["created_time"])
    return result


# --------------------------------------------------------------------------
# Bounded publish
# --------------------------------------------------------------------------

def _approved_for(req: Dict[str, Any]) -> Dict[str, Any]:
    recs = _latest_approvals_for(req["approval_request_id"])
    if not recs:
        raise PublishRefused("APPROVAL_REQUIRED: WAITING_FOR_RAY_APPROVAL")
    rec = recs[0]
    probs = approval_problems(rec, req)
    if probs:
        raise PublishRefused("APPROVAL_GATE_BLOCKED: " + "; ".join(probs))
    return rec


def publish(request_id: str, *, graph_factory: Callable[[str], MetaGraphClient] = MetaGraphClient,
            token_provider: Callable[[], str] = resolve_holiday_page_token,
            allow_retry_after_rejection: bool = False, out=print) -> Dict[str, Any]:
    with _tx_lock():
        _, req = find_request(request_id)
        problems = verify_request(req)
        if problems:
            raise PublishRefused("REQUEST_INVALID: " + "; ".join(problems))
        idem = req["idempotency_key"]
        tx = latest_transaction(idem)
        if tx and tx.get("state") == S_PUBLISHED:
            out(f"EXISTING_SUCCESS_RECEIPT={tx.get('publish_receipt_id')} META_POST_ID={tx.get('meta_post_id')} (not sending)")
            return {"result": "ALREADY_PUBLISHED", **tx}
        if tx and tx.get("state") in BLOCKING_STATES:
            raise PublishRefused(f"DUPLICATE_OR_AMBIGUOUS_TRANSACTION: {idem} is {tx.get('state')}; "
                                 "investigate provider state (nexus distribution reconcile) — no automatic retry")
        if tx and tx.get("state") == S_REJECTED and not allow_retry_after_rejection:
            raise PublishRefused(f"PRIOR_SEND_REJECTED_BY_PROVIDER: {tx.get('error')}; re-run with explicit retry flag")
        approval = _approved_for(req)
        published = [t for t in transactions_for_job(req["distribution_job_id"]) if t.get("state") == S_PUBLISHED]
        if len(published) >= int(req["max_external_posts"]):
            raise PublishRefused("MAX_EXTERNAL_POSTS_REACHED")

        token = token_provider()
        graph = graph_factory(token)
        me_status, me = graph.get("me", "id,name")
        if me_status != 200 or me.get("id") != HOLIDAY_PAGE_ID:
            raise PublishRefused(f"TARGET_PAGE_LOCK_VIOLATION: credential resolves to {me.get('id')} (HTTP {me_status})")

        deriv = req["media"]["provider_derivative"]
        image = _resolve_path(deriv["path"]).read_bytes()
        if _sha256_bytes(image) != deriv["sha256"]:
            raise PublishRefused("MEDIA_SHA_MISMATCH at send time")
        retry_count = (tx.get("retry_count", 0) + 1) if tx else 0
        base = {
            "idempotency_key": idem, "approval_request_id": req["approval_request_id"],
            "approval_id": approval["id"], "approval_hash": req["request_hash"],
            "venture_id": req["venture_id"], "campaign_id": req["campaign_id"],
            "distribution_job_id": req["distribution_job_id"], "channel_account_id": req["channel_account_id"],
            "platform": "FACEBOOK", "page_id": HOLIDAY_PAGE_ID, "asset_id": req["media"]["asset_id"],
            "derivative_asset_id": deriv["asset_id"], "asset_sha256": deriv["sha256"],
            "copy_hash": _sha256_bytes(req["copy"].encode()), "target_url": req["target_url"],
            "retry_count": retry_count, "graph_api_version": graph.version,
        }
        tx = _write_tx(base, state=S_PUBLISHING, started_at=utc_now())  # persisted BEFORE contacting Meta

        try:
            http_status, body = graph.post_photo(HOLIDAY_PAGE_ID, image, Path(deriv["path"]).name, req["copy"])
        except GraphTransportError as e:
            tx = _write_tx(tx, state=S_UNKNOWN, error=f"TRANSPORT:{e}", provider_request_outcome="NO_RESPONSE")
            raise PublishRefused(f"{S_UNKNOWN}: no provider response ({e}); run reconcile before any retry")
        del token

        post_id, photo_id = body.get("post_id"), body.get("id")
        if http_status == 200 and post_id:
            tx = _write_tx(tx, state=S_ACCEPTED, provider_http_status=http_status, meta_post_id=post_id,
                           meta_photo_id=photo_id, provider_request_outcome="ACCEPTED")
        elif http_status >= 500 or http_status == 200 or (body.get("error") or {}).get("code") in (1, 2):
            tx = _write_tx(tx, state=S_UNKNOWN, provider_http_status=http_status, error=body.get("error"),
                           meta_photo_id=photo_id, provider_request_outcome="AMBIGUOUS")
            raise PublishRefused(f"{S_UNKNOWN}: HTTP {http_status}; run reconcile before any retry")
        else:
            _write_tx(tx, state=S_REJECTED, provider_http_status=http_status, error=body.get("error"),
                      provider_request_outcome="REJECTED")
            raise PublishRefused(f"{S_REJECTED}: HTTP {http_status} {body.get('error')}")

        return _finish_with_readback(graph, tx, req, approval, out)


def _finish_with_readback(graph: MetaGraphClient, tx: Dict[str, Any], req: Dict[str, Any],
                          approval: Dict[str, Any], out) -> Dict[str, Any]:
    rb = verify_readback(graph, tx["meta_post_id"], tx.get("meta_photo_id"), req)
    if not rb["readback_verified"]:
        _write_tx(tx, state=S_READBACK_FAILED, readback=rb, readback_verified=False)
        raise PublishRefused(f"{S_READBACK_FAILED}: {json.dumps(rb)}")
    url = rb.get("permalink_url") or f"https://www.facebook.com/{tx['meta_post_id']}"
    receipt_id = "rcpt_pub_" + _sha256_bytes(f"{tx['idempotency_key']}:{tx['meta_post_id']}".encode())[:16]
    receipt = {
        "publish_receipt_id": receipt_id, "approval_id": approval["id"],
        "approval_request_id": req["approval_request_id"], "approval_hash": req["request_hash"],
        "idempotency_key": tx["idempotency_key"], "venture_id": req["venture_id"], "campaign_id": req["campaign_id"],
        "distribution_job_id": req["distribution_job_id"], "channel_account_id": req["channel_account_id"],
        "platform": "FACEBOOK", "page_id": HOLIDAY_PAGE_ID, "asset_id": req["media"]["asset_id"],
        "derivative_asset_id": tx["derivative_asset_id"], "asset_sha256": tx["asset_sha256"],
        "copy_hash": tx["copy_hash"], "target_url": req["target_url"], "meta_post_id": tx["meta_post_id"],
        "meta_photo_id": tx.get("meta_photo_id"), "provider_http_status": tx.get("provider_http_status"),
        "public_post_url": url, "published_at": rb.get("created_time"), "readback": rb,
        "readback_verified": True, "final_job_state": S_PUBLISHED, "retry_count": tx.get("retry_count", 0),
        "recorded_at": utc_now(), "simulated": False,
    }
    persistence.append_record(RECEIPT_COLLECTION, receipt)
    tx = _write_tx(tx, state=S_PUBLISHED, readback=rb, readback_verified=True, public_post_url=url,
                   publish_receipt_id=receipt_id, published_at=rb.get("created_time"))
    try:
        from distribution_foundation import PublishReceipt
        from social_publishing_engine import SocialPublishingMemory
        pr = PublishReceipt(publish_receipt_id=receipt_id, distribution_job_id=req["distribution_job_id"],
                            venture_id=req["venture_id"], campaign_id=req["campaign_id"],
                            channel_account_id=req["channel_account_id"], platform="FACEBOOK",
                            external_post_id=tx["meta_post_id"], published_at=rb.get("created_time") or utc_now(),
                            media_asset_ids=[req["media"]["asset_id"], tx["derivative_asset_id"]],
                            copy_hash=tx["copy_hash"], target_url=req["target_url"],
                            provider_response_reference=f"meta_graph:{tx.get('meta_photo_id')}",
                            external_url=url)
        job = SimpleNamespace(distribution_job_id=req["distribution_job_id"], venture_id=req["venture_id"],
                              campaign_id=req["campaign_id"], product_id="prod_stoneware_mug_14oz",
                              channel_account_id=req["channel_account_id"], platform="FACEBOOK")
        SocialPublishingMemory.record_publication(pr, job)
    except Exception as exc:  # lineage is secondary; the governed receipt is authoritative
        persistence.emit_audit_event({"type": "social_memory_lineage_failed", "receipt": receipt_id, "error": str(exc)[:200]})
    approvals.mark_approval_consumed(approval["id"])
    out(f"PUBLISHED META_POST_ID={tx['meta_post_id']} URL={url} RECEIPT={receipt_id}")
    return {"result": "PUBLISHED", **receipt}


def reconcile(request_id: str, *, graph_factory: Callable[[str], MetaGraphClient] = MetaGraphClient,
              token_provider: Callable[[], str] = resolve_holiday_page_token, out=print) -> Dict[str, Any]:
    """Investigate an ambiguous/unverified send WITHOUT sending anything."""
    with _tx_lock():
        _, req = find_request(request_id)
        tx = latest_transaction(req["idempotency_key"])
        if not tx or tx.get("state") not in (S_UNKNOWN, S_ACCEPTED, S_READBACK_FAILED, S_PUBLISHING):
            return {"result": "NOTHING_TO_RECONCILE", "state": (tx or {}).get("state")}
        graph = graph_factory(token_provider())
        post_id = tx.get("meta_post_id")
        if not post_id:
            status, feed = graph.get(f"{HOLIDAY_PAGE_ID}/published_posts", "id,message,created_time")
            matches = [p for p in (feed.get("data") or []) if (p.get("message") or "").strip() == req["copy"].strip()
                       and (p.get("created_time") or "") >= (tx.get("started_at") or "")[:19]]
            if len(matches) != 1:
                out(f"RECONCILE: {len(matches)} matching posts found; state left as {tx['state']} for owner review")
                return {"result": "UNRESOLVED", "matches": len(matches), "state": tx["state"]}
            post_id = matches[0]["id"]
            tx = _write_tx(tx, meta_post_id=post_id, reconciled=True)
        approval = _latest_approvals_for(req["approval_request_id"])[0]
        return _finish_with_readback(graph, tx, req, approval, out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    if len(argv) < 3:
        print("Usage: nexus distribution approve|approval-status|publish|publish-status|reconcile <id>")
        return 1
    cmd, ident = argv[1], argv[2]
    try:
        if cmd == "publish-status":
            print(json.dumps(publish_status(ident), indent=2))
            return 0
        if cmd not in ("approve", "approval-status", "publish", "reconcile"):
            print(f"Unknown distribution command: {cmd}")
            return 1
        _, req = find_request(ident)
        if req.get("platform") == "INSTAGRAM":  # same owner CLI; platform-specific binding
            import instagram_live_publisher as ig
            if cmd == "approve":
                ig.approve(ident)
            elif cmd == "approval-status":
                print(json.dumps(ig.approval_status(ident), indent=2))
            elif cmd == "publish":
                res = ig.publish(ident, allow_new_container_after_failure="--new-container-after-failure" in argv)
                print(json.dumps({k: v for k, v in res.items() if k not in ("readback", "public_video_check")}, indent=2))
            else:
                print(json.dumps(ig.reconcile(ident), indent=2))
            return 0
        if req.get("platform") != "FACEBOOK":
            raise PublishRefused(f"UNSUPPORTED_PLATFORM: {req.get('platform')}")
        if cmd == "approve":
            approve(ident)
        elif cmd == "approval-status":
            print(json.dumps(approval_status(ident), indent=2))
        elif cmd == "publish":
            res = publish(ident, allow_retry_after_rejection="--retry-after-provider-rejection" in argv)
            print(json.dumps({k: v for k, v in res.items() if k != "readback"}, indent=2))
        else:
            print(json.dumps(reconcile(ident), indent=2))
    except PublishRefused as e:
        print(f"REFUSED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    # Run through the importable module so PublishRefused (and all state) has a
    # single identity shared with instagram_live_publisher.
    import facebook_live_publisher as _canonical
    raise SystemExit(_canonical.main(sys.argv))
