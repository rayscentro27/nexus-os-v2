"""Bounded durable job model and local certification store for Nexus V1.

Production persistence is defined by the companion Supabase migration.  The
SQLite implementation is deliberately adapter-shaped and is used by local
certification and offline development; it provides the same atomic transitions.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data/runtime/nexus_durable_jobs.sqlite3"
STATES = {"QUEUED", "READY", "CLAIMED", "RUNNING", "WAITING", "COMPLETED", "FAILED_RETRYABLE", "BLOCKED", "CANCELLED"}
RESEARCH_TYPES = {"RESEARCH_GAP_VERIFY", "MARKETING_RESEARCH_GAP_VERIFY", "NOTEBOOKLM_RESEARCH", "PROACTIVE_DISCOVERY", "CONTENT_INTELLIGENCE", "MARKET_HEARTBEAT"}
FEEDER_TYPES = {"BUSINESS_OPPORTUNITY_FEEDER", "BUSINESS_FUNDING_FEEDER", "BUSINESS_CREATION_BANKABILITY_FEEDER", "FOREX_INDICATOR_STRATEGY_FEEDER", "OPTIONS_STRATEGY_FEEDER", "RAY_NOVA_OPPORTUNITY_INTAKE", "FEEDER_RESEARCH_CONTINUATION"}
HANDOFF_TYPES = {"FORMAL_HANDOFF", "HANDOFF_DELIVERY", "PULSE_HANDOFF"}
MARKETING_CREATIVE_TYPES = {
    "MARKETING_STRATEGY", "MARKETING_RESEARCH_REQUEST", "MARKETING_CAMPAIGN_BUILD",
    "CREATIVE_BRIEF_BUILD", "CREATIVE_ASSET_GENERATE", "CREATIVE_ASSET_REVISE",
    "CREATIVE_QA", "MARKETING_ASSET_REVIEW", "MARKETING_PUBLISH_PREP",
    "CONTROLLED_EMAIL_SEND", "CONTROLLED_SOCIAL_POST", "LANDING_PAGE_BUILD",
    "LANDING_PAGE_VERIFY", "PERFORMANCE_COLLECT", "MARKETING_PERFORMANCE_ANALYZE",
    "MARKETING_FINANCE_REVIEW_RESULT", "RESEARCH_MARKETING_TEST_HANDOFF",
}
FINANCE_TYPES = {"FINANCE_CAMPAIGN_REVIEW"}
DOCUMENT_ANALYSIS_TYPES = {"CREDIT_REPORT_ANALYSIS"}
COMPANY_CERTIFICATION_TYPES = {"CERTIFICATION_RESEARCH_SYNTHESIS", "CERTIFICATION_ATLAS_ANALYSIS", "CERTIFICATION_FUNDING_REVIEW", "CERTIFICATION_NOVA_SUMMARY", "CERTIFICATION_TRADING_BACKTEST"}
WORKER_LIMITS = {"total": 2, "research": 1, "browser": 1, "heavy": 1}
HEAVY_MARKERS = ("NOTEBOOKLM", "BROWSER", "FFMPEG", "VIDEO", "MEDIA", "LARGE_MODEL", "CREATIVE", "GPU", "CREDIT_REPORT_ANALYSIS")
DEFAULT_JOB_BUDGET = {"max_requests":120,"max_response_bytes":2_000_000,"max_tokens":12_000,"max_gpu_seconds":0,
                      "max_runtime_seconds":900,"max_resource_creations":0,"max_estimated_cost":0.0,"max_retries":3}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class Job:
    job_id: str
    department: str
    job_type: str
    priority: int = 50
    state: str = "READY"
    scheduled_at: str = ""
    claimed_at: str | None = None
    lease_until: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    payload_ref: str | None = None
    parent_job_id: str | None = None
    correlation_id: str = ""
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    last_error_code: str | None = None
    last_error_summary: str | None = None
    receipt_ref: str | None = None
    claimed_by: str | None = None
    idempotency_key: str = ""
    result_hash: str | None = None
    budget_envelope: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    client_id: str | None = None
    source_document_id: str | None = None
    governance_context: dict[str, Any] = field(default_factory=dict)


class JobError(RuntimeError):
    pass


class DurableJobStore:
    """Transactional SQLite adapter used offline; transitions mirror SQL RPCs."""
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
              job_id TEXT PRIMARY KEY, department TEXT NOT NULL, job_type TEXT NOT NULL,
              priority INTEGER NOT NULL, state TEXT NOT NULL, scheduled_at TEXT NOT NULL,
              claimed_at TEXT, lease_until TEXT, attempt_count INTEGER NOT NULL DEFAULT 0,
              max_attempts INTEGER NOT NULL DEFAULT 3, payload_ref TEXT, parent_job_id TEXT,
              correlation_id TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT,
              completed_at TEXT, last_error_code TEXT, last_error_summary TEXT, receipt_ref TEXT,
              claimed_by TEXT, idempotency_key TEXT NOT NULL UNIQUE, result_hash TEXT, budget_envelope TEXT NOT NULL DEFAULT '{"max_requests":120,"max_response_bytes":2000000,"max_tokens":12000,"max_gpu_seconds":0,"max_runtime_seconds":900,"max_resource_creations":0,"max_estimated_cost":0.0,"max_retries":3}'
              ,tenant_id TEXT, client_id TEXT, source_document_id TEXT, governance_context TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS jobs_ready_idx ON jobs(state, scheduled_at, priority DESC, created_at);
            CREATE TABLE IF NOT EXISTS receipts (
              receipt_ref TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE, result_hash TEXT NOT NULL,
              created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );
            CREATE TABLE IF NOT EXISTS schedules (
              schedule_id TEXT PRIMARY KEY, department TEXT NOT NULL, job_type TEXT NOT NULL,
              payload_ref TEXT, priority INTEGER NOT NULL DEFAULT 50, enabled INTEGER NOT NULL DEFAULT 1,
              interval_seconds INTEGER, next_run_at TEXT NOT NULL, correlation_id TEXT
            );
            """)
            columns={row[1] for row in db.execute("PRAGMA table_info(jobs)")}
            if "budget_envelope" not in columns: db.execute("ALTER TABLE jobs ADD COLUMN budget_envelope TEXT NOT NULL DEFAULT '{\"max_requests\":120,\"max_response_bytes\":2000000,\"max_tokens\":12000,\"max_gpu_seconds\":0,\"max_runtime_seconds\":900,\"max_resource_creations\":0,\"max_estimated_cost\":0.0,\"max_retries\":3}'")
            for name, definition in (("tenant_id", "TEXT"), ("client_id", "TEXT"), ("source_document_id", "TEXT"), ("governance_context", "TEXT NOT NULL DEFAULT '{}'")):
                if name not in columns: db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            yield db
        finally:
            db.close()

    def enqueue(self, department: str, job_type: str, *, priority: int = 50, scheduled_at: str | None = None,
                payload_ref: str | None = None, parent_job_id: str | None = None, correlation_id: str | None = None,
                max_attempts: int = 3, idempotency_key: str | None = None, budget_envelope: dict[str,Any] | None = None,
                tenant_id: str | None = None, client_id: str | None = None, source_document_id: str | None = None,
                governance_context: dict[str, Any] | None = None) -> Job:
        if not department or not job_type or max_attempts < 1:
            raise ValueError("INVALID_JOB_CONTRACT")
        budget=budget_envelope or DEFAULT_JOB_BUDGET
        max_attempts=min(max_attempts,max(1,int(budget.get("max_retries",3))))
        now = _iso(); key = idempotency_key or _canonical_hash([department, job_type, payload_ref, parent_job_id])
        job_id = "job_" + uuid.uuid4().hex
        with self._connect() as db:
            db.execute("""INSERT OR IGNORE INTO jobs
              (job_id,department,job_type,priority,state,scheduled_at,max_attempts,payload_ref,parent_job_id,correlation_id,created_at,idempotency_key,budget_envelope,tenant_id,client_id,source_document_id,governance_context)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (job_id, department, job_type, int(priority), "READY", scheduled_at or now, max_attempts,
               payload_ref, parent_job_id, correlation_id or uuid.uuid4().hex, now, key,json.dumps(budget),tenant_id,client_id,source_document_id,json.dumps(governance_context or {})))
            row = db.execute("SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
            return self._job(row)

    def add_schedule(self, schedule_id: str, department: str, job_type: str, *, next_run_at: str,
                     interval_seconds: int | None = None, payload_ref: str | None = None,
                     priority: int = 50, enabled: bool = True) -> None:
        with self._connect() as db:
            db.execute("""INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?,?)
              ON CONFLICT(schedule_id) DO UPDATE SET department=excluded.department,job_type=excluded.job_type,
              payload_ref=excluded.payload_ref,priority=excluded.priority,enabled=excluded.enabled,
              interval_seconds=excluded.interval_seconds,next_run_at=excluded.next_run_at""",
              (schedule_id, department, job_type, payload_ref, priority, int(enabled), interval_seconds,
               next_run_at, uuid.uuid4().hex))

    def scheduler_once(self, now: datetime | None = None) -> int:
        now = now or utcnow(); stamp = _iso(now); made = 0
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT * FROM schedules WHERE enabled=1 AND next_run_at<=? ORDER BY next_run_at LIMIT 50", (stamp,)).fetchall()
            for row in rows:
                key = f"schedule:{row['schedule_id']}:{row['next_run_at']}"
                job_id = "job_" + uuid.uuid4().hex
                cursor = db.execute("""INSERT OR IGNORE INTO jobs
                  (job_id,department,job_type,priority,state,scheduled_at,max_attempts,payload_ref,correlation_id,created_at,idempotency_key)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (job_id,row['department'],row['job_type'],row['priority'],"READY",row['next_run_at'],3,row['payload_ref'],row['correlation_id'] or uuid.uuid4().hex,stamp,key))
                made += cursor.rowcount
                next_run = _iso(now + timedelta(seconds=row['interval_seconds'])) if row['interval_seconds'] else stamp
                db.execute("UPDATE schedules SET next_run_at=?,enabled=? WHERE schedule_id=?", (next_run,int(bool(row['interval_seconds'])),row['schedule_id']))
            db.execute("COMMIT")
        return made

    def claim(self, worker_id: str, *, lease_seconds: int = 300, now: datetime | None = None) -> Job | None:
        now = now or utcnow(); stamp = _iso(now); expiry = _iso(now + timedelta(seconds=max(15, lease_seconds)))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT job_id FROM jobs WHERE state IN ('READY','FAILED_RETRYABLE') AND scheduled_at<=? AND attempt_count<max_attempts ORDER BY priority DESC,scheduled_at,created_at LIMIT 1", (stamp,)).fetchone()
            if row is None:
                db.execute("COMMIT"); return None
            cur = db.execute("UPDATE jobs SET state='CLAIMED',claimed_by=?,claimed_at=?,lease_until=?,attempt_count=attempt_count+1 WHERE job_id=? AND state IN ('READY','FAILED_RETRYABLE')", (worker_id,stamp,expiry,row['job_id']))
            if cur.rowcount != 1:
                db.execute("ROLLBACK"); return None
            result = db.execute("SELECT * FROM jobs WHERE job_id=?", (row['job_id'],)).fetchone()
            db.execute("COMMIT")
            return self._job(result)

    def transition(self, job_id: str, state: str, *, worker_id: str | None = None, lease_seconds: int = 300,
                   error_code: str | None = None, error_summary: str | None = None) -> Job:
        if state not in STATES: raise ValueError("INVALID_JOB_STATE")
        now = utcnow(); fields: dict[str, Any] = {"state": state}
        if state == "RUNNING": fields.update(started_at=_iso(now), lease_until=_iso(now + timedelta(seconds=max(15,lease_seconds))))
        if state in {"COMPLETED","BLOCKED","CANCELLED"}: fields.update(completed_at=_iso(now), lease_until=None)
        if state == "WAITING": fields.update(lease_until=None,claimed_by=None)
        if state == "FAILED_RETRYABLE":
            fields.update(lease_until=None,completed_at=None,last_error_code=(error_code or "WORKER_ERROR")[:100],last_error_summary=(error_summary or "")[:500])
        if worker_id is not None: fields["claimed_by"] = worker_id
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state,claimed_by,attempt_count,max_attempts FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None: db.execute("ROLLBACK"); raise JobError("JOB_NOT_FOUND")
            if worker_id and row["claimed_by"] != worker_id: db.execute("ROLLBACK"); raise JobError("LEASE_OWNER_MISMATCH")
            if row["state"] in {"COMPLETED","CANCELLED"}: db.execute("ROLLBACK"); raise JobError("JOB_TERMINAL")
            if state == "FAILED_RETRYABLE" and row["attempt_count"] >= row["max_attempts"]:
                fields.update(state="BLOCKED", completed_at=_iso())
            elif state == "FAILED_RETRYABLE":
                delay=min(3600,60*(2**max(0,int(row["attempt_count"])-1)))
                fields.update(scheduled_at=_iso(now+timedelta(seconds=delay)))
            setters = ",".join(f"{key}=?" for key in fields)
            db.execute(f"UPDATE jobs SET {setters} WHERE job_id=?", (*fields.values(),job_id))
            result = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone(); db.execute("COMMIT")
            return self._job(result)

    def renew(self, job_id: str, worker_id: str, *, lease_seconds: int = 300) -> bool:
        with self._connect() as db:
            cur = db.execute("UPDATE jobs SET lease_until=? WHERE job_id=? AND claimed_by=? AND state IN ('CLAIMED','RUNNING') AND lease_until>?", (_iso(utcnow()+timedelta(seconds=max(15,lease_seconds))),job_id,worker_id,_iso()))
            return cur.rowcount == 1

    def recover_expired(self, now: datetime | None = None, *, backoff_seconds: int = 60) -> int:
        stamp = _iso(now or utcnow()); next_run = _iso((now or utcnow()) + timedelta(seconds=max(30,backoff_seconds)))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT job_id,attempt_count,max_attempts FROM jobs WHERE state IN ('CLAIMED','RUNNING') AND lease_until<=?", (stamp,)).fetchall()
            for row in rows:
                state = "FAILED_RETRYABLE" if row["attempt_count"] < row["max_attempts"] else "BLOCKED"
                scheduled = next_run if state == "FAILED_RETRYABLE" else stamp
                completed = stamp if state == "BLOCKED" else None
                db.execute("UPDATE jobs SET state=?,scheduled_at=?,completed_at=?,claimed_by=NULL,claimed_at=NULL,lease_until=NULL,last_error_code='LEASE_EXPIRED',last_error_summary='Worker lease expired; recovered safely' WHERE job_id=?", (state,scheduled,completed,row['job_id']))
            db.execute("COMMIT")
            return len(rows)

    def complete(self, job_id: str, worker_id: str, result: Any, *, receipt_ref: str | None = None) -> str:
        digest = _canonical_hash(result); receipt = receipt_ref or "receipt_" + uuid.uuid4().hex
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state,claimed_by,result_hash FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None: db.execute("ROLLBACK"); raise JobError("JOB_NOT_FOUND")
            if row["state"] == "COMPLETED":
                db.execute("COMMIT"); return db.execute("SELECT receipt_ref FROM jobs WHERE job_id=?",(job_id,)).fetchone()[0]
            if row["claimed_by"] != worker_id or row["state"] not in {"CLAIMED","RUNNING"}: db.execute("ROLLBACK"); raise JobError("LEASE_OWNER_MISMATCH")
            db.execute("INSERT INTO receipts VALUES(?,?,?,?)", (receipt,job_id,digest,_iso()))
            db.execute("UPDATE jobs SET state='COMPLETED',completed_at=?,lease_until=NULL,receipt_ref=?,result_hash=? WHERE job_id=?", (_iso(),receipt,digest,job_id))
            db.execute("COMMIT"); return receipt

    def get(self, job_id: str) -> Job | None:
        with self._connect() as db: row = db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
        return self._job(row) if row else None

    def list_ready(self, limit: int = 20) -> list[Job]:
        with self._connect() as db: rows = db.execute("SELECT * FROM jobs WHERE state IN ('READY','FAILED_RETRYABLE') AND scheduled_at<=? ORDER BY priority DESC,scheduled_at LIMIT ?",(_iso(),max(1,min(100,limit)))).fetchall()
        return [self._job(row) for row in rows]

    def health(self) -> dict[str, Any]:
        with self._connect() as db:
            counts = {row["state"]: row["n"] for row in db.execute("SELECT state,count(*) n FROM jobs GROUP BY state")}
            oldest = db.execute("SELECT min(created_at) FROM jobs WHERE state IN ('QUEUED','READY')").fetchone()[0]
            expired = db.execute("SELECT count(*) FROM jobs WHERE state IN ('CLAIMED','RUNNING') AND lease_until<=?",(_iso(),)).fetchone()[0]
            today = utcnow().date().isoformat()
            completed = db.execute("SELECT count(*) FROM jobs WHERE state='COMPLETED' AND completed_at>=?",(today,)).fetchone()[0]
            retry = db.execute("SELECT coalesce(sum(attempt_count),0) FROM jobs").fetchone()[0]
        age = max(0,int((utcnow()-datetime.fromisoformat(oldest)).total_seconds())) if oldest else 0
        return {"counts":counts,"expired_leases":expired,"oldest_queued_age_seconds":age,"jobs_completed_today":completed,"retry_count":retry,"active_worker_count":counts.get("CLAIMED",0)+counts.get("RUNNING",0)}

    @staticmethod
    def _job(row: sqlite3.Row) -> Job:
        value=dict(row)
        try: value["budget_envelope"]=json.loads(value.get("budget_envelope") or "{}")
        except (ValueError,TypeError): value["budget_envelope"]={}
        try: value["governance_context"]=json.loads(value.get("governance_context") or "{}")
        except (ValueError,TypeError): value["governance_context"]={}
        return Job(**value)


class SupabaseJobStore:
    """Production adapter using the service-role path and SQL claim RPC."""
    JOB_COLUMNS = "job_id,department,job_type,priority,state,scheduled_at,claimed_at,lease_until,attempt_count,max_attempts,payload_ref,parent_job_id,correlation_id,created_at,started_at,completed_at,last_error_code,last_error_summary,receipt_ref,claimed_by,idempotency_key,result_hash,budget_envelope,tenant_id,client_id,source_document_id,governance_context"
    def _request(self, path: str, method: str = "GET", body: Any = None, prefer: str = "return=minimal"):
        from nexus_agent_platform.feeder_runtime import _request
        return _request(path, method, body, prefer)

    @staticmethod
    def _job(row: dict | None) -> Job | None:
        if not row: return None
        value={field: row.get(field) for field in Job.__dataclass_fields__}
        value["budget_envelope"]=value.get("budget_envelope") or DEFAULT_JOB_BUDGET
        value["governance_context"]=value.get("governance_context") or {}
        return Job(**value)

    def scheduler_once(self, now: datetime | None = None) -> int:
        rows = self._request("rpc/nexus_schedule_durable_jobs", "POST", {}, "return=representation")
        return int(rows or 0) if not isinstance(rows, list) else int(rows[0].get("nexus_schedule_durable_jobs", 0) if rows else 0)

    def enqueue(self, department: str, job_type: str, *, priority: int = 50, scheduled_at: str | None = None,
                payload_ref: str | None = None, parent_job_id: str | None = None, correlation_id: str | None = None,
                max_attempts: int = 3, idempotency_key: str | None = None, budget_envelope: dict[str,Any] | None = None,
                tenant_id: str | None = None, client_id: str | None = None, source_document_id: str | None = None,
                governance_context: dict[str, Any] | None = None) -> Job:
        budget=budget_envelope or DEFAULT_JOB_BUDGET
        max_attempts=min(max_attempts,max(1,int(budget.get("max_retries",3))))
        key=idempotency_key or _canonical_hash([department,job_type,payload_ref,parent_job_id])
        body={"job_id":"job_"+uuid.uuid4().hex,"department":department,"job_type":job_type,"priority":priority,
              "state":"READY","scheduled_at":scheduled_at or _iso(),"max_attempts":max_attempts,"payload_ref":payload_ref,
              "parent_job_id":parent_job_id,"correlation_id":correlation_id or uuid.uuid4().hex,"idempotency_key":key,"budget_envelope":budget,
              "tenant_id":tenant_id,"client_id":client_id,"source_document_id":source_document_id,"governance_context":governance_context or {}}
        rows=self._request("nexus_durable_jobs?on_conflict=idempotency_key","POST",body,"resolution=ignore-duplicates,return=representation")
        if rows: return self._job(rows[0])
        found=self._request(f"nexus_durable_jobs?idempotency_key=eq.{key}&select={self.JOB_COLUMNS}&limit=1")
        if not found: raise JobError("JOB_DEDUPE_INSERT_FAILED")
        return self._job(found[0])

    def recover_expired(self, now: datetime | None = None, *, backoff_seconds: int = 60) -> int:
        rows = self._request("rpc/nexus_recover_expired_durable_jobs", "POST", {}, "return=representation")
        return int(rows or 0) if not isinstance(rows, list) else int(rows[0].get("nexus_recover_expired_durable_jobs", 0) if rows else 0)

    def claim(self, worker_id: str, *, lease_seconds: int = 300, now: datetime | None = None) -> Job | None:
        rows = self._request("rpc/nexus_claim_durable_job", "POST", {"p_worker_id": worker_id, "p_lease_seconds": lease_seconds}, "return=representation")
        return self._job(rows[0]) if rows else None

    def get(self, job_id: str) -> Job | None:
        rows = self._request(f"nexus_durable_jobs?job_id=eq.{job_id}&select={self.JOB_COLUMNS}&limit=1")
        return self._job(rows[0]) if rows else None

    def transition(self, job_id: str, state: str, *, worker_id: str | None = None, lease_seconds: int = 300,
                   error_code: str | None = None, error_summary: str | None = None) -> Job:
        if state not in STATES: raise ValueError("INVALID_JOB_STATE")
        current=self.get(job_id)
        if current is None: raise JobError("JOB_NOT_FOUND")
        exhausted = state == "FAILED_RETRYABLE" and current.attempt_count >= current.max_attempts
        if exhausted: state="BLOCKED"
        now = _iso(); patch: dict[str, Any] = {"state": state}
        if state == "RUNNING": patch.update(started_at=now, lease_until=_iso(utcnow()+timedelta(seconds=max(15,lease_seconds))))
        if state in {"COMPLETED","BLOCKED","CANCELLED"}: patch.update(completed_at=now,lease_until=None)
        if state == "WAITING": patch.update(lease_until=None,claimed_by=None)
        if state == "FAILED_RETRYABLE":
            delay=min(3600,60*(2**max(0,current.attempt_count-1)))
            patch.update(lease_until=None,completed_at=None,scheduled_at=_iso(utcnow()+timedelta(seconds=delay)),last_error_code=(error_code or "WORKER_ERROR")[:100],last_error_summary=(error_summary or "")[:500])
        elif exhausted:
            patch.update(completed_at=now,lease_until=None,last_error_code=(error_code or "WORKER_ERROR")[:100],last_error_summary=(error_summary or "")[:500])
        filt=f"job_id=eq.{job_id}"
        if worker_id: filt+=f"&claimed_by=eq.{worker_id}"
        # Starting a worker is a one-shot compare-and-set. Without this state
        # predicate two processes that both read CLAIMED could both enter the
        # workflow while sharing the dispatcher identity.
        state_filter="state=eq.CLAIMED" if state == "RUNNING" else "state=not.in.(COMPLETED,CANCELLED)"
        rows=self._request(f"nexus_durable_jobs?{filt}&{state_filter}","PATCH",patch,"return=representation")
        job=self._job(rows[0]) if rows else None
        if not job: raise JobError("JOB_TRANSITION_REJECTED")
        return job

    def complete(self, job_id: str, worker_id: str, result: Any, *, receipt_ref: str | None = None) -> str:
        digest=_canonical_hash(result); receipt=receipt_ref or "receipt_"+uuid.uuid4().hex
        current=self.get(job_id)
        if current and current.state=="COMPLETED" and current.receipt_ref: return current.receipt_ref
        rows=self._request(f"nexus_durable_jobs?job_id=eq.{job_id}&claimed_by=eq.{worker_id}&state=in.(CLAIMED,RUNNING)","PATCH",
            {"state":"COMPLETED","completed_at":_iso(),"lease_until":None,"receipt_ref":receipt,"result_hash":digest},"return=representation")
        if not rows: raise JobError("JOB_COMPLETION_REJECTED")
        return receipt

    def list_ready(self, limit: int = 20) -> list[Job]:
        # Encode the UTC offset so urlopen/PostgREST do not treat '+' as a space.
        due_at = quote(_iso(), safe="")
        rows=self._request(f"nexus_durable_jobs?state=in.(READY,FAILED_RETRYABLE)&scheduled_at=lte.{due_at}&select={self.JOB_COLUMNS}&order=priority.desc,scheduled_at.asc&limit={max(1,min(100,limit))}")
        return [self._job(row) for row in rows]

    def active(self) -> list[Job]:
        rows=self._request(f"nexus_durable_jobs?state=in.(CLAIMED,RUNNING)&select={self.JOB_COLUMNS}&limit=100")
        return [self._job(row) for row in rows]

    def health(self) -> dict[str, Any]:
        value=self._request("rpc/nexus_durable_job_health","POST",{},"return=representation")
        return value if isinstance(value,dict) else (value[0] if value else {"counts":{}})


def default_store():
    try:
        sys.path.insert(0,str(ROOT / "scripts/ops"))
        from nexus_runtime_env import load_runtime_env
        # launchd invokes this entry point without sourcing runtime.env. Load
        # only the backend queue credentials explicitly required here.
        load_runtime_env(allowed_keys={"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"})
    except (ImportError,OSError): pass
    if (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")) and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return SupabaseJobStore()
    if os.environ.get("NEXUS_DURABLE_JOBS_LOCAL", "").lower() in {"1", "true", "yes"}:
        return DurableJobStore()
    raise RuntimeError("SUPABASE_DURABLE_QUEUE_NOT_CONFIGURED")


def classify(job: Job) -> set[str]:
    text = f"{job.job_type} {job.department}".upper()
    categories = {"total"}
    if "RESEARCH" in text or job.job_type in RESEARCH_TYPES: categories.add("research")
    if "BROWSER" in text or "NOTEBOOKLM" in text: categories.add("browser")
    lightweight_internal = (job.governance_context or {}).get("resource_class") == "LIGHTWEIGHT_INTERNAL"
    if not lightweight_internal and any(marker in text for marker in HEAVY_MARKERS): categories.add("heavy")
    return categories


def resource_pressure() -> bool:
    """Conservative host preflight. Missing telemetry defers heavy work."""
    if os.environ.get("NEXUS_RESOURCE_PRESSURE", "").lower() in {"1","true","yes"}: return True
    try:
        import psutil  # optional, no new runtime dependency
        memory=psutil.virtual_memory()
        swap=psutil.swap_memory()
        load=psutil.getloadavg()[0]
        active=0
        for proc in psutil.process_iter(["name","cmdline"]):
            try:
                text=" ".join([proc.info.get("name") or "",*(proc.info.get("cmdline") or [])]).lower()
                if any(word in text for word in ("playwright","chromium","chrome","ffmpeg","creative_asset","large_model")):
                    active+=1
            except (psutil.Error,TypeError):
                continue
        return (memory.available < 2 * 1024**3 or memory.percent >= 90 or
                swap.percent >= 50 or load >= max(4.0, psutil.cpu_count() * 1.5) or active >= 1)
    except Exception:
        return True


def dispatch_once(store: DurableJobStore, *, launch: bool = True, worker_id: str | None = None) -> dict[str, int]:
    worker_id = worker_id or f"dispatcher-{os.getpid()}"
    active = store.health()["active_worker_count"]
    active_jobs: list[Job] = []
    if hasattr(store, "active"):
        active_jobs = store.active()
    else:
        with store._connect() as db: active_jobs = [store._job(row) for row in db.execute("SELECT * FROM jobs WHERE state IN ('CLAIMED','RUNNING')").fetchall()]
    counts = {name: sum(name in classify(job) for job in active_jobs) for name in WORKER_LIMITS}
    started = 0
    for candidate in store.list_ready(50):
        cats = classify(candidate)
        if active >= WORKER_LIMITS["total"] or any(counts[key] >= WORKER_LIMITS[key] for key in cats): continue
        if "heavy" in cats and resource_pressure(): continue
        job = store.claim(worker_id)
        if job is None: break
        if not launch:
            store.transition(job.job_id,"RUNNING",worker_id=worker_id)
        else:
            try:
                subprocess.Popen([sys.executable,str(ROOT/"scripts/nexus_agent_platform/job_worker_once.py"),"--job-id",job.job_id,"--worker-id",worker_id], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            except Exception as exc:
                store.transition(job.job_id,"FAILED_RETRYABLE",worker_id=worker_id,error_code="WORKER_LAUNCH_FAILED",error_summary=str(exc))
                continue
        active += 1; started += 1
        for key in cats: counts[key] += 1
    return {"started":started,"active":active,"ready":len(store.list_ready(100))}


def handler_route(job_type: str) -> str:
    if job_type in {"SYSTEMS_INTERNAL_CANARY", "SYSTEMS_FAILURE_CANARY"}: return "INTERNAL_CANARY"
    if job_type in DOCUMENT_ANALYSIS_TYPES: return "DOCUMENT_ANALYSIS"
    if job_type in RESEARCH_TYPES: return "RESEARCH"
    if job_type in FEEDER_TYPES: return "FEEDER"
    if job_type in HANDOFF_TYPES: return "HANDOFF"
    if job_type in FINANCE_TYPES: return "FINANCE"
    if job_type in COMPANY_CERTIFICATION_TYPES: return "COMPANY_CERTIFICATION"
    if job_type in MARKETING_CREATIVE_TYPES: return "MARKETING_CREATIVE"
    raise JobError("UNSUPPORTED_JOB_TYPE")


def create_next_job(store: DurableJobStore, parent: Job, *, department: str, job_type: str,
                    payload_ref: str | None, event_id: str) -> Job:
    """Called by a completed workflow event; deterministic key prevents repeats."""
    return store.enqueue(department, job_type, payload_ref=payload_ref, parent_job_id=parent.job_id,
                         correlation_id=parent.correlation_id, tenant_id=parent.tenant_id,
                         client_id=parent.client_id, source_document_id=parent.source_document_id,
                         governance_context=parent.governance_context,
                         idempotency_key=f"next:{parent.job_id}:{event_id}:{job_type}")
