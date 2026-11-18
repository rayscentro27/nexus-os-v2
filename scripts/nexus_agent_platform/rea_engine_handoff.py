"""Nexus durable REA job -> Contabo REA harness (CONTABO_REA_HARNESS_ENVIRONMENT_R1).

Nexus stays authoritative. One durable job (job_type REA_EXECUTION) maps deterministically to exactly
one REA session (rea_<24 hex>) on the Contabo `nexus-rea` container, reached only through the
SSH-authenticated host wrapper `/opt/nexus-app-services/rea/bin/rea-job` (no published ports).

Linkage and receipts live in governance_context.rea_engine (no new authoritative store):
  NEXUS_JOB_ID, REA_SESSION_ID, HARNESS_SESSION_ID, TARGET, OBJECTIVE, CREATED_AT.

Cost policy: the job is created with spend_allowed=False / paid_provider_authorized=False. The harness
refuses MODEL mode unless its provider is READY and, when PAID, carries a Cost Governor approval ref.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

JOB_TYPE = "REA_EXECUTION"
DEPARTMENT = "REA"
SOURCE = "NEXUS_REA_REQUEST"
SCHEMA = "nexus.rea-request.v1"
ENGINE = "CONTABO_REA_HARNESS"
SSH_TARGET = os.environ.get("NEXUS_REA_SSH_TARGET", "nexus-contabo")
REMOTE_WRAPPER = "/opt/nexus-app-services/rea/bin/rea-job"
MODES = {"TOOL_CERT", "MODEL"}
# Per-assignment harness options (validated again on Contabo). Model/tool choice never requires adapter changes.
OPTION_KEYS = {"tool_profile", "model_mode", "model_key", "fallback_key", "model_profile", "required_context"}
NEXUS_JOB_RE = re.compile(r"^job_[0-9a-f]{32}$")
SID_RE = re.compile(r"^rea_[0-9a-f]{24}$")
LEASE_SECONDS = 900
RENEW_EVERY_SECONDS = 450
POLL_SECONDS = 15
MAX_WAIT_SECONDS = {"TOOL_CERT": 1500, "MODEL": 3600}
REMOTE_DOWN_GRACE_SECONDS = 600
RUNTIME_BUDGET_SECONDS = 3600 + 1200
MAX_RECEIPTS = 40
ACTIVE = {"SUBMITTED", "QUEUED_WAITING_FOR_SLOT", "RUNNING"}
COMPLETE = {"COMPLETED", "COMPLETED_WITH_LIMITATIONS"}
OUTPUT_CONTRACT = ["OBJECTIVE", "TARGET", "OBSERVED_BEHAVIOR", "WORKFLOWS", "FEATURES", "DATA_FLOW", "INTERFACES",
                   "DEPENDENCIES", "SECURITY_CONSIDERATIONS", "LIMITATIONS", "OPPORTUNITIES", "NEXUS_SPECIFIC_IMPROVEMENTS",
                   "ORIGINAL_IMPLEMENTATION_GUIDANCE", "DEVELOPMENT_DIRECTIVE", "EVIDENCE", "CONFIDENCE"]


class RemoteError(Exception):
    def __init__(self, code: str, retryable: bool = True):
        super().__init__(code)
        self.code, self.retryable = code, retryable


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def session_id_for(nexus_job_id: str) -> str:
    """Must match rea_harness.sid_for on Contabo."""
    return "rea_" + hashlib.sha256(("nexus-rea:" + nexus_job_id).encode()).hexdigest()[:24]


# ---------------------------------------------------------------- remote (SSH host wrapper only)

def remote_call(command: str, *, sid: str | None = None, payload: dict | None = None, timeout: int = 180) -> dict:
    args = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=15", SSH_TARGET,
            REMOTE_WRAPPER, command] + ([sid] if sid else [])
    try:
        proc = subprocess.run(args, input=json.dumps(payload) if payload is not None else None, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RemoteError("REA_REMOTE_TIMEOUT") from exc
    if proc.returncode == 255:
        raise RemoteError("REA_SSH_UNAVAILABLE")
    line = (proc.stdout.strip().splitlines() or [""])[-1]
    try:
        out = json.loads(line)
    except ValueError as exc:
        raise RemoteError("REA_REMOTE_OUTPUT_INVALID") from exc
    if not out.get("ok"):
        err = out.get("error") or {}
        raise RemoteError(str(err.get("code") or "REA_REMOTE_ERROR"), bool(err.get("retryable", True)))
    return out.get("data") or {}


# ---------------------------------------------------------------- request creation (Nexus-owned)

def _payload_dir() -> Path:
    from nexus_agent_platform.runtime.paths import nexus_research_state_path
    return nexus_research_state_path("runtime", "nexus_rea_requests")


def normalize_request(raw: dict) -> dict:
    mode = str(raw.get("mode") or "MODEL").upper()
    if mode not in MODES:
        raise ValueError("REA_MODE_INVALID")
    objective = " ".join(str(raw.get("objective") or "").split())[:4000]
    target = " ".join(str(raw.get("target") or "").split())[:1000]
    if not objective or not target:
        raise ValueError("REA_OBJECTIVE_AND_TARGET_REQUIRED")
    authorization = str(raw.get("authorization_ref") or "").strip()[:200] or None
    if mode == "MODEL" and not authorization:
        # Clean-room governance: a real analysis must name why the target is authorized.
        raise ValueError("REA_TARGET_AUTHORIZATION_REQUIRED")
    raw_opts = raw.get("options") if isinstance(raw.get("options"), dict) else {}
    unknown = set(raw_opts) - OPTION_KEYS
    if unknown:
        raise ValueError("REA_OPTION_UNKNOWN:" + ",".join(sorted(unknown))[:60])
    options = {k: (v if k == "required_context" else str(v)[:80]) for k, v in sorted(raw_opts.items()) if v not in (None, "")}
    return {"mode": mode, "objective": objective, "target": target, "authorization_ref": authorization, "options": options,
            "requested_by": str(raw.get("requested_by") or "RAY")[:40], "priority": int(raw.get("priority") or 60)}


def create_request(store, raw: dict) -> dict:
    from nexus_agent_platform.durable_jobs import DEFAULT_JOB_BUDGET
    req = normalize_request(raw)
    fp = _sha(req["mode"], req["objective"], req["target"], req["authorization_ref"], req["options"] or None)
    payload_path = _payload_dir() / f"{fp[:40]}.json"
    payload = {"schema_version": SCHEMA, **req, "request_fingerprint": fp}
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    if not payload_path.exists():
        tmp = payload_path.with_suffix(".tmp-" + uuid.uuid4().hex[:8])
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, payload_path)
    candidate = "job_" + uuid.uuid4().hex
    created_at = utcnow()
    context = {"source": SOURCE, "requestor": req["requested_by"], "request_fingerprint": fp,
               "external_actions_authorized": False, "external_actions_allowed": False,
               "spend_allowed": False, "paid_provider_authorized": False,
               "rea_engine": {"engine": ENGINE, "rea_session_id": None, "harness_session_id": None,
                              "target": req["target"], "objective": req["objective"][:500], "mode": req["mode"],
                              "created_at": created_at, "receipts": [_receipt("REA_REQUEST_CREATED", candidate, 0,
                                                                            {"payload_ref": str(payload_path)})]}}
    budget = dict(DEFAULT_JOB_BUDGET)
    budget["max_runtime_seconds"] = RUNTIME_BUDGET_SECONDS
    job = store.enqueue(DEPARTMENT, JOB_TYPE, priority=req["priority"], payload_ref=str(payload_path),
                        correlation_id="rea_" + fp[:24], max_attempts=3, idempotency_key="nexus-rea-request:" + fp[:40],
                        budget_envelope=budget, governance_context=context, job_id=candidate)
    eng = (job.governance_context or {}).get("rea_engine") or {}
    return {"status": "queued" if job.job_id == candidate else "existing", "nexus_job_id": job.job_id, "job_state": job.state,
            "rea_session_id": eng.get("rea_session_id") or session_id_for(job.job_id), "created_at": eng.get("created_at"),
            "mode": req["mode"]}


# ---------------------------------------------------------------- receipts in the existing durable row

def _receipt(event: str, nexus_job_id: str, attempt: int, fields: dict) -> dict:
    return {"receipt_id": "rearcpt_" + _sha(nexus_job_id, event, attempt, fields.get("key"))[:24], "event": event,
            "attempt": attempt, "at": utcnow(), **{k: v for k, v in fields.items() if k != "key" and v is not None}}


class Chain:
    def __init__(self, store, job_id: str, context: dict, attempt: int):
        self.store, self.job_id, self.attempt = store, job_id, attempt
        self.context = dict(context or {})
        self.engine = dict(self.context.get("rea_engine") or {"engine": ENGINE, "receipts": []})
        self.engine.setdefault("receipts", [])

    def has(self, event: str) -> bool:
        return any(r.get("event") == event for r in self.engine["receipts"])

    def record(self, event: str, *, once: bool = False, link: dict | None = None, **fields) -> None:
        if once and self.has(event):
            if link:
                self.engine.update(link)
                self._persist()
            return
        self.engine["receipts"].append(_receipt(event, self.job_id, self.attempt, fields))
        if len(self.engine["receipts"]) > MAX_RECEIPTS:
            self.engine["receipts"] = self.engine["receipts"][:1] + self.engine["receipts"][-(MAX_RECEIPTS - 1):]
        if link:
            self.engine.update(link)
        self._persist()

    def _persist(self) -> None:
        self.context["rea_engine"] = self.engine
        self.store.set_governance_context(self.job_id, self.context)


def _load_payload(job) -> dict:
    data = json.loads(Path(str(job.payload_ref or "")).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
        raise ValueError("REA_PAYLOAD_INVALID")
    return data


def validate_result(nexus_job_id: str, sid: str, result: dict) -> dict:
    problems = []
    if result.get("nexus_job_id") != nexus_job_id:
        problems.append("NEXUS_JOB_ID_MISMATCH")
    if result.get("rea_session_id") != sid:
        problems.append("REA_SESSION_ID_MISMATCH")
    if not result.get("harness_session_id"):
        problems.append("HARNESS_SESSION_ID_MISSING")
    contract = result.get("contract") if isinstance(result.get("contract"), dict) else {}
    missing = [k for k in OUTPUT_CONTRACT if k not in contract]
    if result.get("mode") == "TOOL_CERT":
        if result.get("harness_tool_layer") != "PASS":
            problems.append("HARNESS_TOOL_LAYER_NOT_PASS")
    elif missing:
        problems.append("OUTPUT_CONTRACT_INCOMPLETE")
    if float((result.get("cost") or {}).get("paid_cost_usd") or 0) > 0:
        problems.append("UNAUTHORIZED_COST")
    return {"valid": not problems, "problems": problems, "contract_missing": missing}


def summarize(result: dict) -> dict:
    keep = ("rea_session_id", "nexus_job_id", "harness_session_id", "target", "objective", "mode", "provider_mode", "model",
            "created_at", "started_at", "completed_at", "elapsed_seconds", "tool_call_count", "tools_used",
            "harness_tool_layer", "certification_checks", "artifacts", "cost", "contract_missing_keys", "harness_version")
    out = {k: result.get(k) for k in keep if k in result}
    contract = result.get("contract") if isinstance(result.get("contract"), dict) else {}
    out["development_directive"] = contract.get("DEVELOPMENT_DIRECTIVE")
    out["confidence"] = contract.get("CONFIDENCE")
    out["limitations"] = contract.get("LIMITATIONS")
    return out


# ---------------------------------------------------------------- execution (one leased attempt)

def execute(job, store, worker_id: str, *, call: Callable[..., dict] | None = None,
            sleep: Callable[[float], None] = time.sleep, monotonic: Callable[[], float] = time.monotonic) -> dict:
    call = call or remote_call
    fresh = store.get(job.job_id) or job
    chain = Chain(store, job.job_id, fresh.governance_context or {}, int(fresh.attempt_count or 0))
    payload = _load_payload(fresh)
    sid = chain.engine.get("rea_session_id")
    chain.record("REA_DISPATCH_CLAIMED", worker_id=worker_id, reattach=bool(sid), key=f"claim-{fresh.attempt_count}")
    if not sid:
        try:
            sub = call("submit", payload={"nexus_job_id": job.job_id, "mode": payload["mode"], "objective": payload["objective"],
                                          "target": payload["target"], "authorization_ref": payload.get("authorization_ref"),
                                          "created_at": chain.engine.get("created_at") or fresh.created_at,
                                          "options": payload.get("options") or {}})
        except RemoteError as exc:
            return {"status": "RETRY" if exc.retryable else "BLOCKED", "reason": "REA_SUBMIT_" + exc.code}
        sid = str(sub.get("rea_session_id") or "")
        if not SID_RE.fullmatch(sid) or sid != session_id_for(job.job_id):
            return {"status": "BLOCKED", "reason": "REA_SUBMIT_RESPONSE_INVALID"}
        chain.record("REA_SESSION_SUBMITTED", once=True, rea_session_id=sid, idempotent=bool(sub.get("idempotent")),
                     link={"rea_session_id": sid, "linked_at": utcnow()})
    deadline = monotonic() + MAX_WAIT_SECONDS.get(payload["mode"], 3600)
    last_renew = float("-inf")
    unreachable_since = None
    while True:
        try:
            st = call("status", sid=sid)
            unreachable_since = None
        except RemoteError as exc:
            st = {"status": "UNREACHABLE", "error": exc.code}
            unreachable_since = unreachable_since if unreachable_since is not None else monotonic()
            if monotonic() - unreachable_since >= REMOTE_DOWN_GRACE_SECONDS:
                return {"status": "RETRY", "reason": "REA_REMOTE_UNAVAILABLE", "rea_session_id": sid}
        state = str(st.get("status") or "").upper()
        if state == "RUNNING":
            chain.record("REA_SESSION_STARTED", once=True, rea_session_id=sid, started_at=st.get("started_at"))
        if state in COMPLETE or state == "FAILED" and st.get("harness_session_id"):
            try:
                result = call("result", sid=sid)
            except RemoteError as exc:
                return {"status": "RETRY", "reason": "REA_RESULT_" + exc.code, "rea_session_id": sid}
            check = validate_result(job.job_id, sid, result)
            chain.record("REA_SESSION_TERMINAL", once=True, rea_session_id=sid, rea_status=state,
                         link={"harness_session_id": result.get("harness_session_id")},
                         harness_session_id=result.get("harness_session_id"))
            if state not in COMPLETE or not check["valid"]:
                chain.record("REA_DURABLE_FAILED", rea_session_id=sid, reason="REA_RESULT_INVALID", problems=check["problems"])
                return {"status": "BLOCKED", "reason": "REA_RESULT_INVALID", "problems": check["problems"], "rea_session_id": sid}
            chain.record("REA_RESULT_VALIDATED", once=True, rea_session_id=sid, mode=result.get("mode"),
                         harness_tool_layer=result.get("harness_tool_layer"))
            summary = summarize(result)
            linkage = {"NEXUS_JOB_ID": job.job_id, "REA_SESSION_ID": sid, "HARNESS_SESSION_ID": result.get("harness_session_id"),
                       "TARGET": result.get("target"), "OBJECTIVE": result.get("objective"), "CREATED_AT": result.get("created_at")}
            return {"status": "COMPLETED", "rea_engine": {"engine": ENGINE, "rea_session_id": sid,
                                                          "harness_session_id": result.get("harness_session_id")},
                    "rea_result": summary, "summary": json.dumps(summary, default=str)[:6000], "evidence": linkage,
                    "evidence_class": "NEXUS_DURABLE_REA_RESULT"}
        if state == "WAITING_FOR_MODEL_ENDPOINT":
            chain.record("REA_WAITING_FOR_MODEL_ENDPOINT", once=True, rea_session_id=sid, reason=st.get("reason"))
            return {"status": "BLOCKED", "reason": "REA_MODEL_PROVIDER_NOT_READY", "rea_session_id": sid,
                    "provider_status": st.get("reason")}
        if state in {"FAILED", "BLOCKED", "CANCELLED", "NOT_FOUND"}:
            chain.record("REA_SESSION_TERMINAL", once=True, rea_session_id=sid, rea_status=state, reason=st.get("reason"))
            retry = bool(st.get("retryable")) and state == "FAILED"
            return {"status": "RETRY" if retry else "BLOCKED", "reason": "REA_" + str(st.get("reason") or state)[:80],
                    "rea_session_id": sid}
        if monotonic() >= deadline:
            return {"status": "RETRY", "reason": "REA_SESSION_WAIT_CAP", "rea_session_id": sid}
        if monotonic() - last_renew >= RENEW_EVERY_SECONDS:
            if not store.renew(job.job_id, worker_id, lease_seconds=LEASE_SECONDS):
                return {"status": "LEASE_LOST", "rea_session_id": sid}
            last_renew = monotonic()
        sleep(POLL_SECONDS)


def lookup(store, nexus_job_id: str) -> dict:
    if not NEXUS_JOB_RE.fullmatch(nexus_job_id):
        raise ValueError("NEXUS_JOB_ID_INVALID")
    job = store.get(nexus_job_id)
    if not job or job.job_type != JOB_TYPE:
        raise ValueError("REA_JOB_NOT_FOUND")
    eng = (job.governance_context or {}).get("rea_engine") or {}
    return {"nexus_job_id": job.job_id, "state": job.state, "rea_session_id": eng.get("rea_session_id"),
            "harness_session_id": eng.get("harness_session_id"), "target": eng.get("target"), "objective": eng.get("objective"),
            "created_at": eng.get("created_at"), "mode": eng.get("mode"),
            "receipts": [r.get("event") for r in eng.get("receipts") or []],
            "result_summary": (job.governance_context or {}).get("result_summary"),
            "receipt_ref": getattr(job, "receipt_ref", None), "result_hash": getattr(job, "result_hash", None)}


def fetch_result(store, nexus_job_id: str) -> dict:
    """Nexus-side retrieval of the full REA result: read it from the linked Contabo session (never a new run)
    and confirm it is the one this job completed with (rea_session_id + nexus_job_id linkage)."""
    info = lookup(store, nexus_job_id)
    sid = info.get("rea_session_id")
    if not sid or not SID_RE.fullmatch(sid):
        raise ValueError("REA_SESSION_NOT_LINKED")
    result = remote_call("result", sid=sid)
    check = validate_result(nexus_job_id, sid, result)
    return {"nexus_job_id": nexus_job_id, "state": info["state"], "rea_session_id": sid, "linkage_valid": check["valid"],
            "problems": check["problems"], "result_hash": info.get("result_hash"), "result": summarize(result)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("request")
    sub.add_parser("lookup").add_argument("nexus_job_id")
    sub.add_parser("result").add_argument("nexus_job_id")
    sub.add_parser("health")
    args = parser.parse_args(argv)
    os.environ.setdefault("NEXUS_DURABLE_EXECUTION_ID", f"rea-handoff-{args.cmd}-{os.getpid()}-{time.time_ns()}")
    try:
        if args.cmd == "health":
            out = remote_call("health")
        else:
            from nexus_agent_platform.durable_jobs import default_store
            store = default_store()
            if args.cmd == "request":
                out = create_request(store, json.loads(sys.stdin.read() or "{}"))
            elif args.cmd == "result":
                out = fetch_result(store, args.nexus_job_id)
            else:
                out = lookup(store, args.nexus_job_id)
        print(json.dumps({"ok": True, "data": out}, default=str))
        return 0
    except (ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": {"code": str(exc)[:80], "retryable": False}}))
        return 2
    except RemoteError as exc:
        print(json.dumps({"ok": False, "error": {"code": exc.code, "retryable": exc.retryable}}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
