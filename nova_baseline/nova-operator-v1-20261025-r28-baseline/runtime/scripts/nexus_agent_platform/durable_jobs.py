"""Bounded durable job model and local certification store for Nexus V1.

Production persistence is defined by the companion Supabase migration.  The
SQLite implementation is deliberately adapter-shaped and is used by local
certification and offline development; it provides the same atomic transitions.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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
RESEARCH_TYPES = {"RESEARCH_INTAKE", "RESEARCH_GAP_VERIFY", "RESEARCH_RUNTIME_INSPECT", "RESEARCH_ROOM_ADVISOR", "MARKETING_RESEARCH_GAP_VERIFY", "NOTEBOOKLM_RESEARCH", "PROACTIVE_DISCOVERY", "CONTENT_INTELLIGENCE", "MARKET_HEARTBEAT"}
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
REAL_WORLD_V2_TYPES = {"REAL_WORLD_V2_GOAL"}
V5_OWNER_RESEARCH_TYPES = {"RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY"}
NOVA_COMMUNICATION_TYPES = {"NOVA_RESOURCE_ALERT_RETRY"}
NOVA_RESEARCH_RESULT_NOTICE_TYPES = {"NOVA_RESEARCH_RESULT_NOTICE"}
NOVA_SYSTEMS_RESULT_NOTICE_TYPES = {"NOVA_SYSTEMS_RESULT_NOTICE"}
NOVA_ALPHA_RESULT_NOTICE_TYPES = {"NOVA_ALPHA_RESULT_NOTICE"}
NOVA_ALPHA_ASSIGNMENT_NOTICE_TYPES = {"NOVA_ALPHA_ASSIGNMENT_NOTICE"}
NEEDLE_RESEARCH_TYPES = {"NEEDLE_RESEARCH_READINESS_VERIFY", "NEEDLE_RESEARCH_TARGETED_REPAIR"}
NOVA_V6_COMMUNICATION_TYPES = {"V6_NOVA_MILESTONE"}
V5_INTEGRATION_CHECK_TYPES = {"V5_REMOTE_STACK_HEALTH_CHECK", "V5_OPENCODE_MODEL_BENCHMARK", "V5_TRADING_MARKET_SCAN"}
V6_INTEGRATION_CHECK_TYPES = {"V6_OANDA_PRACTICE_SCAN"}
NEXUS_DEPARTMENT_QUERY_TYPES = {"NEXUS_DEPARTMENT_QUERY"}
NOVA_CONTROL_ACTION_TYPES = {"NOVA_CREATIVE_ASSET", "NOVA_BOUNDED_CODING_TASK"}
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
                governance_context: dict[str, Any] | None = None, job_id: str | None = None) -> Job:
        if not department or not job_type or max_attempts < 1:
            raise ValueError("INVALID_JOB_CONTRACT")
        budget=budget_envelope or DEFAULT_JOB_BUDGET
        max_attempts=min(max_attempts,max(1,int(budget.get("max_retries",3))))
        now = _iso(); key = idempotency_key or _canonical_hash([department, job_type, payload_ref, parent_job_id])
        job_id = job_id or "job_" + uuid.uuid4().hex
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

    def claim_by_id(self, job_id: str, worker_id: str, *, lease_seconds: int = 300) -> Job | None:
        now=utcnow(); stamp=_iso(now); expiry=_iso(now+timedelta(seconds=max(15,lease_seconds)))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cur=db.execute("UPDATE jobs SET state='CLAIMED',claimed_by=?,claimed_at=?,lease_until=?,attempt_count=attempt_count+1 WHERE job_id=? AND state IN ('READY','FAILED_RETRYABLE') AND scheduled_at<=? AND attempt_count<max_attempts",
                (worker_id,stamp,expiry,job_id,stamp))
            if cur.rowcount != 1:
                db.execute("COMMIT"); return None
            row=db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            db.execute("COMMIT")
            return self._job(row)

    def transition(self, job_id: str, state: str, *, worker_id: str | None = None, lease_seconds: int = 300,
                   error_code: str | None = None, error_summary: str | None = None) -> Job:
        if state not in STATES: raise ValueError("INVALID_JOB_STATE")
        now = utcnow(); fields: dict[str, Any] = {"state": state}
        if state == "RUNNING": fields.update(started_at=_iso(now), lease_until=_iso(now + timedelta(seconds=max(15,lease_seconds))))
        if state in {"COMPLETED","BLOCKED","CANCELLED"}: fields.update(completed_at=_iso(now), lease_until=None)
        if state == "WAITING": fields.update(lease_until=None,claimed_by=None)
        if state == "BLOCKED": fields.update(last_error_code=(error_code or "JOB_BLOCKED")[:100],last_error_summary=(error_summary or "")[:500])
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

    def requeue_for_repair(self, job_id: str, *, reason: str) -> Job:
        """Safely make the same unreceipted failed job claimable after repair."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT state,attempt_count,max_attempts,receipt_ref,result_hash FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None: db.execute("ROLLBACK"); raise JobError("JOB_NOT_FOUND")
            if row["state"] not in {"BLOCKED","FAILED_RETRYABLE","READY"} or row["receipt_ref"] or row["result_hash"]:
                db.execute("ROLLBACK"); raise JobError("JOB_NOT_REPAIR_REQUEUEABLE")
            if int(row["attempt_count"]) >= int(row["max_attempts"]):
                db.execute("ROLLBACK"); raise JobError("JOB_RETRY_CAPACITY_EXHAUSTED")
            db.execute("UPDATE jobs SET state='READY',scheduled_at=?,claimed_by=NULL,claimed_at=NULL,lease_until=NULL,started_at=NULL,completed_at=NULL,last_error_code=NULL,last_error_summary=? WHERE job_id=?",
                       (_iso(),f"Repair retry: {reason}"[:500],job_id))
            result=db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone(); db.execute("COMMIT")
            return self._job(result)

    def reopen_after_repair(self, job_id: str, *, reason: str,
                            budget_updates: dict[str, int] | None = None) -> Job:
        """Open a new bounded execution window for the same local durable job."""
        allowed={"max_tokens":50_000,"max_requests":500,"max_response_bytes":8_000_000}
        updates=budget_updates or {}
        if any(key not in allowed or int(value)<1 or int(value)>allowed[key] for key,value in updates.items()):
            raise JobError("REPAIR_BUDGET_UPDATE_OUT_OF_RANGE")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None: db.execute("ROLLBACK"); raise JobError("JOB_NOT_FOUND")
            if row["state"] not in {"BLOCKED","FAILED_RETRYABLE","WAITING"} or row["receipt_ref"] or row["result_hash"]:
                db.execute("ROLLBACK"); raise JobError("JOB_REPAIR_REOPEN_NOT_ALLOWED")
            context=json.loads(row["governance_context"] or "{}")
            windows=list(context.get("repair_retry_windows") or [])
            windows.append({"attempt_count":row["attempt_count"],"max_attempts":row["max_attempts"],
                "last_error_code":row["last_error_code"],"last_error_summary":row["last_error_summary"],
                "closed_at":_iso(),"reason":str(reason)[:500]})
            context["repair_retry_windows"]=windows[-10:]
            context["repair_attempt_total"]=max(int(context.get("repair_attempt_total",0) or 0),len(windows)-1)+1
            budget=json.loads(row["budget_envelope"] or "{}")
            budget.update({key:int(value) for key,value in updates.items()})
            db.execute("UPDATE jobs SET state='READY',attempt_count=0,scheduled_at=?,claimed_by=NULL,claimed_at=NULL,lease_until=NULL,started_at=NULL,completed_at=NULL,last_error_code=NULL,last_error_summary=?,budget_envelope=?,governance_context=? WHERE job_id=?",
                (_iso(),f"Reopened after repair: {reason}"[:500],json.dumps(budget),json.dumps(context),job_id))
            result=db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone(); db.execute("COMMIT")
            return self._job(result)

    def set_governance_context(self, job_id: str, value: dict[str, Any]) -> None:
        with self._connect() as db:
            cur=db.execute("UPDATE jobs SET governance_context=? WHERE job_id=?",(json.dumps(value),job_id))
            if cur.rowcount!=1: raise JobError("JOB_NOT_FOUND")

    def bind_parent_job(self, job_id: str, parent_job_id: str) -> None:
        with self._connect() as db:
            cur=db.execute("UPDATE jobs SET parent_job_id=? WHERE job_id=? AND state NOT IN ('COMPLETED','CANCELLED')",(parent_job_id,job_id))
            if cur.rowcount!=1: raise JobError("JOB_PARENT_BIND_REJECTED")

    def ensure_retry_capacity(self, job_id: str, max_attempts: int) -> None:
        with self._connect() as db:
            cur=db.execute("UPDATE jobs SET max_attempts=? WHERE job_id=? AND max_attempts<? AND state NOT IN ('COMPLETED','CANCELLED')",
                (int(max_attempts),job_id,int(max_attempts)))
            if cur.rowcount not in {0,1}: raise JobError("JOB_RETRY_CAPACITY_UPDATE_FAILED")

    def ensure_request_capacity(self, job_id: str, max_requests: int) -> None:
        if not 1 <= int(max_requests) <= 120: raise JobError("JOB_REQUEST_CAPACITY_OUT_OF_RANGE")
        with self._connect() as db:
            row=db.execute("SELECT state,receipt_ref,budget_envelope FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None: raise JobError("JOB_NOT_FOUND")
            if row["receipt_ref"] or row["state"] in {"COMPLETED","CANCELLED"}: raise JobError("JOB_BUDGET_IMMUTABLE")
            budget=json.loads(row["budget_envelope"] or "{}")
            if int(budget.get("max_requests",120)) < int(max_requests):
                budget["max_requests"]=int(max_requests)
                db.execute("UPDATE jobs SET budget_envelope=? WHERE job_id=?",(json.dumps(budget),job_id))

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

    def list_research_parent_jobs(self, limit: int = 500) -> list[Job]:
        with self._connect() as db:
            rows=db.execute("SELECT * FROM jobs WHERE department='RESEARCH' AND job_type='RESEARCH_INTAKE' ORDER BY created_at DESC LIMIT ?",
                            (max(1,min(1000,int(limit))),)).fetchall()
        jobs=[self._job(row) for row in rows]
        return [job for job in jobs if isinstance(job.governance_context,dict)
                and isinstance(job.governance_context.get("research_parent_state"),dict)]

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
                governance_context: dict[str, Any] | None = None, job_id: str | None = None) -> Job:
        budget=budget_envelope or DEFAULT_JOB_BUDGET
        max_attempts=min(max_attempts,max(1,int(budget.get("max_retries",3))))
        key=idempotency_key or _canonical_hash([department,job_type,payload_ref,parent_job_id])
        body={"job_id":job_id or "job_"+uuid.uuid4().hex,"department":department,"job_type":job_type,"priority":priority,
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

    def recover_resource_waiters(self) -> dict[str, int]:
        """Reset elapsed daily circuits and resume matching durable waiters."""
        reset=self._request("rpc/nexus_reset_daily_budget_hard_stops","POST",{},"return=representation")
        resumed=self._request("rpc/nexus_resume_resource_waiting_jobs","POST",{},"return=representation")
        def count(value, key):
            if isinstance(value,list):
                return int(value[0].get(key,0) or 0) if value else 0
            return int(value or 0)
        return {"policies_reset":count(reset,"nexus_reset_daily_budget_hard_stops"),
                "jobs_resumed":count(resumed,"nexus_resume_resource_waiting_jobs")}

    def claim(self, worker_id: str, *, lease_seconds: int = 300, now: datetime | None = None) -> Job | None:
        rows = self._request("rpc/nexus_claim_durable_job", "POST", {"p_worker_id": worker_id, "p_lease_seconds": lease_seconds}, "return=representation")
        return self._job(rows[0]) if rows else None

    def claim_by_id(self, job_id: str, worker_id: str, *, lease_seconds: int = 300) -> Job | None:
        try:
            rows=self._request("rpc/nexus_claim_durable_job_by_id", "POST",
                {"p_job_id":job_id,"p_worker_id":worker_id,"p_lease_seconds":lease_seconds},"return=representation")
            return self._job(rows[0]) if rows else None
        except RuntimeError as exc:
            if "PGRST202" not in str(exc):
                raise
            # Never fall back to generic claim: it can lease an unrelated,
            # higher-priority owner job and mutate its attempt counter. The
            # additive by-ID RPC is required for scoped dispatch.
            raise JobError("ATOMIC_CLAIM_BY_ID_RPC_REQUIRED") from exc

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
        elif state == "BLOCKED":
            patch.update(last_error_code=(error_code or "WORKER_ERROR")[:100],
                         last_error_summary=(error_summary or "")[:500])
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

    def set_governance_context(self, job_id: str, value: dict[str, Any]) -> None:
        rows=self._request(f"nexus_durable_jobs?job_id=eq.{quote(job_id,safe='')}","PATCH",
            {"governance_context":value},"return=representation")
        if not rows: raise JobError("JOB_CONTEXT_UPDATE_REJECTED")

    def requeue_for_repair(self, job_id: str, *, reason: str) -> Job:
        """Atomically clear stale lease fields before retrying the same failed job."""
        current=self.get(job_id)
        if current is None: raise JobError("JOB_NOT_FOUND")
        if current.state not in {"BLOCKED","FAILED_RETRYABLE","READY"} or current.receipt_ref or current.result_hash:
            raise JobError("JOB_NOT_REPAIR_REQUEUEABLE")
        if current.state == "READY" and current.lease_until:
            raise JobError("JOB_STILL_LEASED")
        if current.attempt_count >= current.max_attempts: raise JobError("JOB_RETRY_CAPACITY_EXHAUSTED")
        patch={"state":"READY","scheduled_at":_iso(),"claimed_by":None,"claimed_at":None,
               "lease_until":None,"started_at":None,"completed_at":None,"last_error_code":None,
               "last_error_summary":f"Repair retry: {reason}"[:500]}
        rows=self._request(f"nexus_durable_jobs?job_id=eq.{quote(job_id,safe='')}&state=eq.{current.state}&receipt_ref=is.null&result_hash=is.null",
                           "PATCH",patch,"return=representation")
        if not rows: raise JobError("JOB_REPAIR_REQUEUE_CONFLICT")
        return self._job(rows[0])

    def reopen_after_repair(self, job_id: str, *, reason: str,
                            budget_updates: dict[str, int] | None = None) -> Job:
        """Open a fresh bounded retry window after a verified provider/software repair.

        The same job, lineage, and checkpoint remain authoritative. Prior
        attempts are retained in governance_context before the per-window
        counter resets, so retry exhaustion is never hidden.
        """
        allowed = {"max_tokens": 50_000, "max_requests": 120, "max_response_bytes": 2_000_000}
        updates = budget_updates or {}
        if any(key not in allowed or int(value) < 1 or int(value) > allowed[key]
               for key, value in updates.items()):
            raise JobError("REPAIR_BUDGET_UPDATE_OUT_OF_RANGE")
        current = self.get(job_id)
        if current is None: raise JobError("JOB_NOT_FOUND")
        if current.state not in {"BLOCKED", "FAILED_RETRYABLE", "WAITING"} or current.receipt_ref or current.result_hash:
            raise JobError("JOB_REPAIR_REOPEN_NOT_ALLOWED")
        envelope = dict(current.budget_envelope or DEFAULT_JOB_BUDGET)
        prior = {"attempt_count": current.attempt_count, "max_attempts": current.max_attempts,
            "last_error_code": current.last_error_code, "last_error_summary": current.last_error_summary,
            "closed_at": _iso(), "reason": str(reason)[:500]}
        envelope.update({key: int(value) for key, value in updates.items()})
        context = dict(current.governance_context or {})
        windows = list(context.get("repair_retry_windows") or [])
        windows.append(prior)
        context["repair_retry_windows"] = windows[-10:]
        context["repair_attempt_total"] = max(
            int(context.get("repair_attempt_total", 0) or 0), len(windows) - 1
        ) + 1
        now = _iso()
        patch = {"state": "READY", "attempt_count": 0, "scheduled_at": now,
            "claimed_by": None, "claimed_at": None, "lease_until": None, "started_at": None,
            "completed_at": None, "last_error_code": None,
            "last_error_summary": f"Reopened after repair: {reason}"[:500],
            "budget_envelope": envelope, "governance_context": context}
        rows = self._request(f"nexus_durable_jobs?job_id=eq.{quote(job_id,safe='')}&state=eq.{current.state}&receipt_ref=is.null&result_hash=is.null",
            "PATCH", patch, "return=representation")
        if not rows: raise JobError("JOB_REPAIR_REOPEN_CONFLICT")
        return self._job(rows[0])

    def bind_parent_job(self, job_id: str, parent_job_id: str) -> None:
        rows=self._request(f"nexus_durable_jobs?job_id=eq.{quote(job_id,safe='')}&state=not.in.(COMPLETED,CANCELLED)","PATCH",
            {"parent_job_id":parent_job_id},"return=representation")
        if not rows: raise JobError("JOB_PARENT_BIND_REJECTED")

    def ensure_retry_capacity(self, job_id: str, max_attempts: int) -> None:
        current=self.get(job_id)
        if current is None: raise JobError("JOB_NOT_FOUND")
        if current.max_attempts>=max_attempts or current.state in {"COMPLETED","CANCELLED"}: return
        rows=self._request(f"nexus_durable_jobs?job_id=eq.{quote(job_id,safe='')}&state=not.in.(COMPLETED,CANCELLED)","PATCH",
            {"max_attempts":int(max_attempts)},"return=representation")
        if not rows: raise JobError("JOB_RETRY_CAPACITY_UPDATE_REJECTED")

    def ensure_request_capacity(self, job_id: str, max_requests: int) -> None:
        if not 1 <= int(max_requests) <= 120: raise JobError("JOB_REQUEST_CAPACITY_OUT_OF_RANGE")
        current=self.get(job_id)
        if current is None: raise JobError("JOB_NOT_FOUND")
        if current.receipt_ref or current.state in {"COMPLETED","CANCELLED"}: raise JobError("JOB_BUDGET_IMMUTABLE")
        budget=dict(current.budget_envelope or {})
        if int(budget.get("max_requests",120)) >= int(max_requests): return
        budget["max_requests"]=int(max_requests)
        rows=self._request(f"nexus_durable_jobs?job_id=eq.{quote(job_id,safe='')}","PATCH",
            {"budget_envelope":budget},"return=representation")
        if not rows: raise JobError("JOB_REQUEST_CAPACITY_UPDATE_REJECTED")

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

    def list_research_parent_jobs(self, limit: int = 500) -> list[Job]:
        # Parent state is stored in the existing governance_context column; no
        # parallel durable store or schema migration is introduced.
        rows=self._request(f"nexus_durable_jobs?department=eq.RESEARCH&job_type=eq.RESEARCH_INTAKE&select={self.JOB_COLUMNS}&order=created_at.desc&limit={max(1,min(1000,int(limit)))}")
        jobs=[self._job(row) for row in rows]
        return [job for job in jobs if isinstance(job.governance_context,dict)
                and isinstance(job.governance_context.get("research_parent_state"),dict)]

    def health(self) -> dict[str, Any]:
        value=self._request("rpc/nexus_durable_job_health","POST",{},"return=representation")
        return value if isinstance(value,dict) else (value[0] if value else {"counts":{}})


def default_store():
    # Explicit local certification runs must not load or select production queue
    # credentials.  The isolated SQLite adapter mirrors durable transitions.
    if os.environ.get("NEXUS_DURABLE_JOBS_LOCAL", "").lower() in {"1", "true", "yes"}:
        return DurableJobStore(os.environ.get("NEXUS_DURABLE_JOBS_DB", DEFAULT_DB))
    try:
        sys.path.insert(0,str(ROOT / "scripts/ops"))
        from nexus_runtime_env import load_runtime_env
        # launchd invokes this entry point without sourcing runtime.env. Load
        # only the backend queue credentials explicitly required here.
        load_runtime_env(allowed_keys={"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"})
    except (ImportError,OSError): pass
    if (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")) and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return SupabaseJobStore()
    raise RuntimeError("SUPABASE_DURABLE_QUEUE_NOT_CONFIGURED")


def classify(job: Job) -> set[str]:
    text = f"{job.job_type} {job.department}".upper()
    categories = {"total"}
    if "RESEARCH" in text or job.job_type in RESEARCH_TYPES: categories.add("research")
    if "BROWSER" in text or "NOTEBOOKLM" in text: categories.add("browser")
    lightweight_internal = (job.governance_context or {}).get("resource_class") == "LIGHTWEIGHT_INTERNAL"
    if not lightweight_internal and any(marker in text for marker in HEAVY_MARKERS): categories.add("heavy")
    return categories


def _resource_heavy_process(name: str, args: str) -> bool:
    """Recognize actual heavy workers without matching Chromium project names."""
    name = (name or "").lower()
    args = (args or "").lower()
    # Chrome Remote Desktop includes `org.chromium.chromoting.json` in its
    # command line. It is a remote access daemon, not a browser workload.
    if "remoting_me2me_host" in name or "chromeremotedesktophost" in args:
        return False
    if any(marker in args or marker in name for marker in
           ("playwright", "ffmpeg", "creative_asset", "large_model")):
        return True
    browser = name in {"chrome", "google chrome", "chromium", "chromium-browser"}
    if not browser:
        browser = bool(re.search(r"/(?:google chrome|chrome|chromium)(?:\s|$)", args))
    return browser and any(flag in args for flag in
                           ("--headless", "--remote-debugging-port", "--remote-debugging-pipe"))


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
                name=(proc.info.get("name") or "").lower()
                args=" ".join(proc.info.get("cmdline") or []).lower()
                if _resource_heavy_process(name, args):
                    active+=1
            except (psutil.Error,TypeError):
                continue
        return (memory.available < 2 * 1024**3 or memory.percent >= 90 or
                swap.percent >= 50 or load >= max(4.0, psutil.cpu_count() * 1.5) or active >= 1)
    except ImportError:
        # macOS installs of the canonical worker may omit optional psutil.
        # Use native host telemetry instead of converting a missing library
        # into a permanent blanket hold. Ordinary interactive Chrome windows
        # are excluded; only headless/automation Chrome blocks heavy work.
        if sys.platform != "darwin":
            return True
        try:
            vm = subprocess.run(["/usr/bin/vm_stat"], capture_output=True, text=True, timeout=3, check=True).stdout
            page_size = int(re.search(r"page size of (\d+) bytes", vm).group(1))
            pages = {}
            for label in ("Pages free", "Pages inactive", "Pages speculative"):
                match = re.search(rf"^{re.escape(label)}:\s+([0-9,]+)", vm, re.M)
                pages[label] = int(match.group(1).replace(",", "")) if match else 0
            total_bytes = int(subprocess.run(["/usr/sbin/sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=3, check=True).stdout.strip())
            available_bytes = sum(pages.values()) * page_size
            swap_text = subprocess.run(["/usr/sbin/sysctl", "vm.swapusage"],
                capture_output=True, text=True, timeout=3, check=True).stdout
            swap = re.search(r"used\s*=\s*([0-9.]+)([KMG])", swap_text)
            total = re.search(r"total\s*=\s*([0-9.]+)([KMG])", swap_text)
            scale = {"K":1024, "M":1024**2, "G":1024**3}
            swap_percent = (float(swap.group(1))*scale[swap.group(2)] /
                            max(1.0,float(total.group(1))*scale[total.group(2)])*100) if swap and total else 100.0
            process_text = subprocess.run(["/bin/ps", "-axo", "command="],
                capture_output=True, text=True, timeout=3, check=True).stdout.lower()
            active = 0
            for line in process_text.splitlines():
                executable = line.strip().split(maxsplit=1)
                name = Path(executable[0]).name if executable else ""
                if _resource_heavy_process(name, line):
                    active += 1
            load = os.getloadavg()[0]
            cpus = os.cpu_count() or 1
            return (available_bytes < 2 * 1024**3 or available_bytes / max(1,total_bytes) <= 0.10
                    or swap_percent >= 50 or load >= max(4.0, cpus * 1.5) or active >= 1)
        except Exception:
            return True
    except Exception:
        return True


def dispatch_once(store: DurableJobStore, *, launch: bool = True, worker_id: str | None = None,
                  allowed_job_ids: set[str] | None = None,
                  allowed_job_sources: set[str] | None = None) -> dict[str, int]:
    if isinstance(store, SupabaseJobStore):
        try:
            store.recover_resource_waiters()
        except RuntimeError as exc:
            # Let dispatch proceed during additive migration rollout; the
            # canonical controller retries recovery on its next tick.
            if "PGRST202" not in str(exc):
                raise
    worker_id = worker_id or f"dispatcher-{os.getpid()}"
    active = store.health()["active_worker_count"]
    active_jobs: list[Job] = []
    if hasattr(store, "active"):
        active_jobs = store.active()
    else:
        with store._connect() as db: active_jobs = [store._job(row) for row in db.execute("SELECT * FROM jobs WHERE state IN ('CLAIMED','RUNNING')").fetchall()]
    counts = {name: sum(name in classify(job) for job in active_jobs) for name in WORKER_LIMITS}
    started = 0
    candidates = store.list_ready(50)
    if allowed_job_ids is not None:
        candidates = [job for job in candidates if job.job_id in allowed_job_ids]
    if allowed_job_sources is not None:
        candidates = [job for job in candidates if str((job.governance_context or {}).get("source") or "") in allowed_job_sources]
    for candidate in candidates:
        cats = classify(candidate)
        if active >= WORKER_LIMITS["total"] or any(counts[key] >= WORKER_LIMITS[key] for key in cats): continue
        if "heavy" in cats and resource_pressure(): continue
        job = store.claim_by_id(candidate.job_id, worker_id) if (allowed_job_ids is not None or allowed_job_sources is not None) else store.claim(worker_id)
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
    if job_type in NEEDLE_RESEARCH_TYPES: return "NEEDLE_RESEARCH"
    if job_type == "RESEARCH_ROOM_ADVISOR": return "RESEARCH_ROOM_ADVISOR"
    if job_type in RESEARCH_TYPES: return "RESEARCH"
    if job_type in FEEDER_TYPES: return "FEEDER"
    if job_type in HANDOFF_TYPES: return "HANDOFF"
    if job_type in FINANCE_TYPES: return "FINANCE"
    if job_type in COMPANY_CERTIFICATION_TYPES: return "COMPANY_CERTIFICATION"
    if job_type in REAL_WORLD_V2_TYPES: return "REAL_WORLD_V2"
    if job_type in V5_OWNER_RESEARCH_TYPES: return "V5_OWNER_RESEARCH"
    if job_type in NOVA_COMMUNICATION_TYPES: return "NOVA_COMMUNICATION"
    if job_type in NOVA_RESEARCH_RESULT_NOTICE_TYPES: return "NOVA_COMMUNICATION"
    if job_type in NOVA_SYSTEMS_RESULT_NOTICE_TYPES: return "NOVA_COMMUNICATION"
    if job_type in NOVA_ALPHA_RESULT_NOTICE_TYPES: return "NOVA_COMMUNICATION"
    if job_type in NOVA_ALPHA_ASSIGNMENT_NOTICE_TYPES: return "NOVA_COMMUNICATION"
    if job_type in NOVA_V6_COMMUNICATION_TYPES: return "NOVA_V6_COMMUNICATION"
    if job_type in V5_INTEGRATION_CHECK_TYPES: return "V5_INTEGRATION_CHECK"
    if job_type in V6_INTEGRATION_CHECK_TYPES: return "V6_INTEGRATION_CHECK"
    if job_type in NOVA_CONTROL_ACTION_TYPES: return "NOVA_CONTROL_ACTION"
    if (job_type in NEXUS_DEPARTMENT_QUERY_TYPES
            or job_type.startswith("NEXUS_DEPARTMENT_QUERY_V5_")
            or job_type.startswith("NEXUS_DEPARTMENT_QUERY_V6_")): return "DEPARTMENT_QUERY"
    if job_type.startswith("NEXUS_NOTEBOOKLM_DISCOVERY_V5_") or job_type == "NEXUS_NOTEBOOKLM_RUNTIME_CANARY": return "NOTEBOOKLM_DISCOVERY"
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
