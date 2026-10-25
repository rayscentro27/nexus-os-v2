"""Default-deny resource and spend governance for bounded Nexus jobs.

This module contains no provider credentials and never starts provider work. A
worker must reserve an explicit envelope before calling a billable adapter.
SQLite is the local certification adapter; hosted persistence is in the paired
Supabase migration and RPC adapter below.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data/runtime/resource_spend_governor.sqlite3"
STATES = {"NORMAL", "ELEVATED", "THROTTLED", "HARD_STOP", "HUMAN_APPROVAL_REQUIRED", "DISABLED"}
CERTIFICATION_STATES = {"NOT_TESTED", "MOCK_PASS", "LOCAL_REAL_PASS", "DATABASE_REAL_PASS", "EXTERNAL_REAL_PASS", "END_TO_END_REAL_PASS", "FAILED", "BLOCKED"}
PROVIDERS = (
    "SUPABASE", "ORACLE", "OLLAMA", "OPENAI_CODEX", "MODAL", "OPENROUTER", "TELEGRAM", "FAL_AI", "KAGGLE",
    "HUGGING_FACE", "BROWSER_EXTERNAL_SERVICES", "EMAIL_PROVIDER", "SOCIAL_MEDIA_EXTERNAL_ACTIONS",
)
DIMENSIONS = ("requests", "operations", "bytes", "tokens", "gpu_seconds", "runtime_seconds", "storage_bytes", "emails", "browser_actions", "api_calls", "resource_creations", "cost")
DEFAULT_LIMITS = {"rate": {"requests": 0, "operations": 0, "window_seconds": 60},
                  "usage": {key: 0 for key in DIMENSIONS if key != "cost"},
                  "money": {"per_job": 0, "per_day": 0, "per_month": 0}}
JOB_ENVELOPE = {"max_requests":120,"max_response_bytes":2_000_000,"max_tokens":12_000,
                "max_gpu_seconds":0,"max_runtime_seconds":900,"max_resource_creations":0,
                "max_estimated_cost":0.0,"max_retries":3}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def idempotency_key(job_id: str, provider: str, purpose: str) -> str:
    return hashlib.sha256(f"{job_id}:{provider.upper()}:{purpose}".encode()).hexdigest()


def sanitize(value: Any) -> Any:
    if isinstance(value,dict):
        clean={}
        for key,item in value.items():
            name=str(key).lower()
            secret=any(x in name for x in ("api_key","access_token","auth_token","secret","credential","password","authorization","transcript","pii","email_address","phone_number"))
            if name in {"token","tokens_value"}: secret=True
            if not secret: clean[key]=sanitize(item)
        return clean
    if isinstance(value,list): return [sanitize(item) for item in value]
    return value


class GovernanceDenied(RuntimeError):
    def __init__(self, state: str, code: str):
        super().__init__(code)
        self.state, self.code = state, code


class LocalGovernorStore:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS policies (
              provider TEXT NOT NULL, service TEXT NOT NULL, job_type TEXT NOT NULL, budget_period TEXT NOT NULL,
              autonomous_usage_allowed INTEGER NOT NULL DEFAULT 0, autonomous_spend_allowed INTEGER NOT NULL DEFAULT 0,
              soft_limits TEXT NOT NULL, hard_limits TEXT NOT NULL, concurrency_limit INTEGER NOT NULL DEFAULT 0,
              resource_creation_limit INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'DISABLED',
              approval_required INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
              PRIMARY KEY(provider,service,job_type,budget_period), CHECK(state IN ('NORMAL','ELEVATED','THROTTLED','HARD_STOP','HUMAN_APPROVAL_REQUIRED','DISABLED'))
            );
            CREATE TABLE IF NOT EXISTS reservations (
              reservation_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, provider TEXT NOT NULL, service TEXT NOT NULL,
              job_type TEXT NOT NULL, budget_period TEXT NOT NULL, job_id TEXT NOT NULL, estimate TEXT NOT NULL,
              actual TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL, created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL, reconciled_at TEXT
            );
            CREATE INDEX IF NOT EXISTS governor_reservations_scope_idx ON reservations(provider,service,job_type,budget_period,status);
            CREATE TABLE IF NOT EXISTS incidents (incident_id TEXT PRIMARY KEY, provider TEXT, job_id TEXT, project_id TEXT,
              code TEXT NOT NULL, threshold TEXT, observed TEXT, action TEXT NOT NULL, unrelated_work_continued INTEGER,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS footprints (job_id TEXT PRIMARY KEY, correlation_id TEXT, project_id TEXT,
              department TEXT, job_type TEXT, payload TEXT NOT NULL, receipt_hash TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS certifications (certification_id TEXT PRIMARY KEY, capability TEXT NOT NULL,
              status TEXT NOT NULL, project_id TEXT, job_id TEXT, evidence_ref TEXT, provider TEXT, host TEXT,
              cost REAL, result TEXT NOT NULL, updated_at TEXT NOT NULL,
              CHECK(status IN ('NOT_TESTED','MOCK_PASS','LOCAL_REAL_PASS','DATABASE_REAL_PASS','EXTERNAL_REAL_PASS','END_TO_END_REAL_PASS','FAILED','BLOCKED')));
            CREATE TABLE IF NOT EXISTS resources (resource_key TEXT PRIMARY KEY, job_id TEXT NOT NULL, provider TEXT NOT NULL,
              purpose TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            for provider in PROVIDERS:
                for period in ("DAILY", "MONTHLY"):
                    db.execute("INSERT OR IGNORE INTO policies(provider,service,job_type,budget_period,soft_limits,hard_limits,state,approval_required,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                               (provider, "*", "*", period, json.dumps(DEFAULT_LIMITS), json.dumps(DEFAULT_LIMITS), "DISABLED", 1, now()))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try: yield db
        finally: db.close()

    def reset_due_daily_budget_hard_stops(self) -> int:
        """Reset only prior-UTC-day hard stops opened by a budget incident."""
        boundary=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).isoformat()
        changed=0
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows=db.execute("SELECT * FROM policies WHERE budget_period='DAILY' AND state='HARD_STOP'").fetchall()
            for policy in rows:
                try: limits=json.loads(policy["hard_limits"])
                except (TypeError,ValueError): continue
                cap=(limits.get("usage") or {}).get("bytes")
                if not cap: continue
                incidents=db.execute("SELECT threshold FROM incidents WHERE provider=? AND code='BUDGET_HARD_LIMIT' AND created_at=? AND created_at<?",
                    (policy["provider"],policy["updated_at"],boundary)).fetchall()
                matched=False
                for incident in incidents:
                    try: matched = json.loads(incident["threshold"] or "null")=={"bytes":cap}
                    except (TypeError,ValueError): matched=False
                    if matched: break
                if matched:
                    db.execute("UPDATE policies SET state='NORMAL',updated_at=? WHERE provider=? AND service=? AND job_type=? AND budget_period=?",
                        (now(),policy["provider"],policy["service"],policy["job_type"],policy["budget_period"]))
                    changed+=1
            db.execute("COMMIT")
        return changed

    def set_policy(self, provider: str, service: str = "*", job_type: str = "*", budget_period: str = "DAILY", *,
                   autonomous_usage_allowed: bool = False, autonomous_spend_allowed: bool = False,
                   soft_limits: dict | None = None, hard_limits: dict | None = None, concurrency_limit: int = 0,
                   resource_creation_limit: int = 0, state: str = "NORMAL", approval_required: bool = True) -> None:
        provider = provider.upper()
        if state not in STATES: raise ValueError("INVALID_GOVERNOR_STATE")
        with self.connect() as db:
            db.execute("""INSERT INTO policies VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(provider,service,job_type,budget_period)
              DO UPDATE SET autonomous_usage_allowed=excluded.autonomous_usage_allowed,autonomous_spend_allowed=excluded.autonomous_spend_allowed,
              soft_limits=excluded.soft_limits,hard_limits=excluded.hard_limits,concurrency_limit=excluded.concurrency_limit,
              resource_creation_limit=excluded.resource_creation_limit,state=excluded.state,approval_required=excluded.approval_required,updated_at=excluded.updated_at""",
              (provider,service,job_type,budget_period,int(autonomous_usage_allowed),int(autonomous_spend_allowed),
               json.dumps(soft_limits or DEFAULT_LIMITS,separators=(",",":")),json.dumps(hard_limits or DEFAULT_LIMITS,separators=(",",":")),
               concurrency_limit,resource_creation_limit,state,int(approval_required),now()))

    def ensure_policy(self, provider: str, service: str, job_type: str, budget_period: str, *,
                      autonomous_usage_allowed: bool, autonomous_spend_allowed: bool,
                      soft_limits: dict, hard_limits: dict, concurrency_limit: int = 1,
                      resource_creation_limit: int = 0, state: str = "NORMAL",
                      approval_required: bool = False) -> bool:
        """Create a scoped policy once without reopening an existing stop or edit."""
        provider = provider.upper()
        if state not in STATES: raise ValueError("INVALID_GOVERNOR_STATE")
        with self.connect() as db:
            cur = db.execute("""INSERT OR IGNORE INTO policies
              (provider,service,job_type,budget_period,autonomous_usage_allowed,autonomous_spend_allowed,
               soft_limits,hard_limits,concurrency_limit,resource_creation_limit,state,approval_required,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (provider,service,job_type,budget_period,int(autonomous_usage_allowed),int(autonomous_spend_allowed),
               json.dumps(soft_limits,separators=(",",":")),json.dumps(hard_limits,separators=(",",":")),
               concurrency_limit,resource_creation_limit,state,int(approval_required),now()))
            return cur.rowcount == 1

    def resolve_policy(self, provider: str, service: str, job_type: str, budget_period: str = "DAILY") -> dict[str, Any] | None:
        """Return the policy the reserve path would select, including its scope."""
        provider = provider.upper()
        with self.connect() as db:
            row = db.execute("""SELECT * FROM policies WHERE provider=? AND service IN (?, '*')
                AND job_type IN (?, '*') AND budget_period=?
                ORDER BY (service='*'),(job_type='*') LIMIT 1""",
                (provider, service, job_type, budget_period.upper())).fetchone()
        if not row:
            return None
        value = dict(row)
        value["autonomous_usage_allowed"] = bool(value["autonomous_usage_allowed"])
        value["autonomous_spend_allowed"] = bool(value["autonomous_spend_allowed"])
        value["wildcard_fallback_used"] = value["service"] == "*" or value["job_type"] == "*"
        return value

    def reserve(self, provider: str, service: str, job_type: str, job_id: str, estimate: dict[str, float], *,
                purpose: str = "execution", project_id: str | None = None) -> dict:
        provider = provider.upper(); key = idempotency_key(job_id, provider, purpose)
        period = "MONTHLY" if str(estimate.get("budget_period", "DAILY")).upper() == "MONTHLY" else "DAILY"
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM reservations WHERE idempotency_key=?",(key,)).fetchone()
            if old:
                self._incident(db,provider,job_id,project_id,"RESERVATION_REPLAY_DENIED",old["estimate"],estimate,"DO_NOT_REPEAT_EXTERNAL_ACTION")
                db.execute("COMMIT")
                raise GovernanceDenied("HARD_STOP","RESERVATION_REPLAY_DENIED")
            row = db.execute("SELECT * FROM policies WHERE provider=? AND service IN (?, '*') AND job_type IN (?, '*') AND budget_period=? ORDER BY (service='*'),(job_type='*') LIMIT 1",
                             (provider,service,job_type,period)).fetchone()
            if row is None:
                self._incident(db,provider,job_id,project_id,"UNKNOWN_PAID_PROVIDER",None,estimate,"HUMAN_APPROVAL_REQUIRED")
                db.execute("COMMIT"); raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","UNKNOWN_PAID_PROVIDER")
            if row["state"] == "HARD_STOP":
                self._incident(db,provider,job_id,project_id,"PROVIDER_HARD_STOP",row["hard_limits"],estimate,"STOP_AFFECTED_JOB")
                db.execute("COMMIT"); raise GovernanceDenied("HARD_STOP","PROVIDER_HARD_STOP")
            if row["state"] == "DISABLED" or not row["autonomous_usage_allowed"]:
                self._incident(db,provider,job_id,project_id,"USAGE_NOT_AUTHORIZED",row["hard_limits"],estimate,"HUMAN_APPROVAL_REQUIRED")
                db.execute("COMMIT"); raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","USAGE_NOT_AUTHORIZED")
            if estimate.get("billable") and estimate.get("cost") is None:
                self._incident(db,provider,job_id,project_id,"COST_ESTIMATE_UNAVAILABLE",row["hard_limits"],estimate,"HUMAN_APPROVAL_REQUIRED")
                db.execute("COMMIT"); raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","COST_ESTIMATE_UNAVAILABLE")
            if float(estimate.get("cost",0)) > 0 and not row["autonomous_spend_allowed"]:
                self._incident(db,provider,job_id,project_id,"SPEND_NOT_AUTHORIZED",row["hard_limits"],estimate,"HUMAN_APPROVAL_REQUIRED")
                db.execute("COMMIT"); raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","SPEND_NOT_AUTHORIZED")
            job_rows=db.execute("SELECT estimate,actual FROM reservations WHERE job_id=? AND status IN ('ACTIVE','RECONCILED')",(job_id,)).fetchall()
            job_used={}
            for prior_job in job_rows:
                values=json.loads(prior_job["actual"] or "{}") or json.loads(prior_job["estimate"] or "{}")
                for dim,value in values.items():
                    if dim not in {"billable","budget_period","job_budget"}: job_used[dim]=job_used.get(dim,0)+float(value)
            envelope=dict(JOB_ENVELOPE)
            try: envelope.update({k:v for k,v in json.loads(os.environ.get("NEXUS_JOB_BUDGET","{}")).items() if k in envelope})
            except (ValueError,TypeError,AttributeError): pass
            env={"requests":"max_requests","bytes":"max_response_bytes","tokens":"max_tokens","gpu_seconds":"max_gpu_seconds","runtime_seconds":"max_runtime_seconds","resource_creations":"max_resource_creations","cost":"max_estimated_cost"}
            for dim,key_name in env.items():
                cap=float(envelope[key_name]); requested=float(estimate.get(dim,0) or 0)
                if cap==0 and requested>0 or cap>0 and job_used.get(dim,0)+requested>cap:
                    self._incident(db,provider,job_id,project_id,"JOB_BUDGET_LIMIT",{key_name:cap},{dim:job_used.get(dim,0)+requested},"STOP_AFFECTED_JOB")
                    db.execute("COMMIT"); raise GovernanceDenied("HARD_STOP",f"JOB_BUDGET_LIMIT:{dim}")
            active = db.execute("SELECT count(*) n FROM reservations WHERE provider=? AND status='ACTIVE'",(provider,)).fetchone()["n"]
            if row["concurrency_limit"] and active >= row["concurrency_limit"]:
                self._incident(db,provider,job_id,project_id,"CONCURRENCY_LIMIT",row["concurrency_limit"],active,"THROTTLE")
                db.execute("COMMIT"); raise GovernanceDenied("THROTTLED","CONCURRENCY_LIMIT")
            hard = json.loads(row["hard_limits"])
            used = {}
            db.execute("UPDATE reservations SET status='RELEASED',reconciled_at=? WHERE provider=? AND status='ACTIVE' AND julianday(expires_at)<=julianday('now')",(now(),provider))
            prior = db.execute("SELECT estimate,actual FROM reservations WHERE provider=? AND service=? AND job_type=? AND budget_period=? AND status IN ('ACTIVE','RECONCILED')",
                               (provider,service,job_type,period)).fetchall()
            for entry in prior:
                for dimension, amount in json.loads(entry["actual"]).items(): used[dimension] = used.get(dimension,0)+float(amount)
                if not json.loads(entry["actual"]):
                    for dimension, amount in json.loads(entry["estimate"]).items(): used[dimension] = used.get(dimension,0)+float(amount)
            rate=hard.get("rate",{}); rate_window=max(1,int(rate.get("window_seconds",60)))
            recent=db.execute("SELECT estimate,actual FROM reservations WHERE provider=? AND status IN ('ACTIVE','RECONCILED') AND julianday(created_at)>=julianday('now',?)",(provider,f"-{rate_window} seconds")).fetchall()
            for dimension in ("requests","operations"):
                cap=float(rate.get(dimension,0) or 0)
                if cap:
                    recent_used=sum(float(json.loads(r["actual"] or "{}").get(dimension,json.loads(r["estimate"] or "{}").get(dimension,0))) for r in recent)
                    if recent_used+float(estimate.get(dimension,0))>cap:
                        self._incident(db,provider,job_id,project_id,"RATE_LIMIT",cap,{dimension:recent_used+float(estimate.get(dimension,0))},"THROTTLE")
                        db.execute("COMMIT"); raise GovernanceDenied("THROTTLED",f"RATE_LIMIT:{dimension}")
            money=hard.get("money",{}); per_job=float(money.get("per_job",0) or 0)
            if per_job and float(estimate.get("cost",0))>per_job:
                self._incident(db,provider,job_id,project_id,"JOB_COST_LIMIT",per_job,estimate,"HARD_STOP")
                db.execute("COMMIT"); raise GovernanceDenied("HARD_STOP","JOB_COST_LIMIT")
            flat_hard = dict(hard.get("usage",{}))
            flat_hard["cost"] = money.get("per_day" if period=="DAILY" else "per_month",0)
            for dimension, amount in estimate.items():
                if dimension in {"billable","budget_period","job_budget"}: continue
                cap=float(flat_hard.get(dimension,0) or 0)
                if cap and used.get(dimension,0)+float(amount)>cap:
                    self._incident(db,provider,job_id,project_id,"BUDGET_HARD_LIMIT",cap,{dimension:amount,"current":used.get(dimension,0)},"HARD_STOP")
                    db.execute("UPDATE policies SET state='HARD_STOP',updated_at=? WHERE provider=? AND service=? AND job_type=? AND budget_period=?",(now(),provider,row["service"],row["job_type"],period))
                    db.execute("COMMIT"); raise GovernanceDenied("HARD_STOP",f"BUDGET_HARD_LIMIT:{dimension}")
            rid="reserve_"+uuid.uuid4().hex
            created=now()
            db.execute("INSERT INTO reservations(reservation_id,idempotency_key,provider,service,job_type,budget_period,job_id,estimate,status,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now','+6 hours'))",
                       (rid,key,provider,service,job_type,period,job_id,json.dumps(estimate,separators=(",",":")),"ACTIVE",created))
            db.execute("COMMIT")
            return {"reservation_id":rid,"idempotency_key":key,"provider":provider,"job_id":job_id,"estimate":estimate,"status":"ACTIVE"}

    def reconcile(self, reservation_id: str, actual: dict[str, float]) -> None:
        with self.connect() as db:
            cur=db.execute("UPDATE reservations SET actual=?,status='RECONCILED',reconciled_at=? WHERE reservation_id=? AND status='ACTIVE'",(json.dumps(actual,separators=(",",":")),now(),reservation_id))
            if cur.rowcount != 1: raise GovernanceDenied("BLOCKED","RESERVATION_NOT_ACTIVE")

    def release(self, reservation_id: str) -> bool:
        with self.connect() as db:
            cur=db.execute("UPDATE reservations SET status='RELEASED',reconciled_at=? WHERE reservation_id=? AND status='ACTIVE'",(now(),reservation_id))
            return cur.rowcount == 1

    def resource_create(self, job_id: str, provider: str, purpose: str, *, job_type: str = "UNKNOWN_RESOURCE_CREATE", max_per_job: int = 0, max_per_day: int = 0) -> str:
        key=idempotency_key(job_id,provider,purpose)
        envelope=dict(JOB_ENVELOPE)
        try: envelope.update({k:v for k,v in json.loads(os.environ.get("NEXUS_JOB_BUDGET","{}")).items() if k in envelope})
        except (ValueError,TypeError,AttributeError): pass
        if int(envelope["max_resource_creations"])<=0:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                self._incident(db,provider,job_id,None,"RESOURCE_CREATION_NOT_AUTHORIZED",{"max_resource_creations":0},{"purpose":purpose},"HUMAN_APPROVAL_REQUIRED")
                db.execute("COMMIT")
            raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","RESOURCE_CREATION_NOT_AUTHORIZED")
        max_per_job=min(max_per_job,int(envelope["max_resource_creations"]))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM resources WHERE resource_key=?",(key,)).fetchone(): db.execute("COMMIT"); return key
            policy=db.execute("SELECT * FROM policies WHERE provider=? AND service='resource_creation' AND job_type IN (?, '*') AND budget_period='DAILY' ORDER BY (job_type='*') LIMIT 1",(provider.upper(),job_type)).fetchone()
            if not policy or policy["state"]!="NORMAL" or not policy["autonomous_usage_allowed"] or not policy["autonomous_spend_allowed"]:
                self._incident(db,provider,job_id,None,"RESOURCE_CREATION_NOT_AUTHORIZED",None,{"purpose":purpose},"HUMAN_APPROVAL_REQUIRED")
                db.execute("COMMIT"); raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","RESOURCE_CREATION_NOT_AUTHORIZED")
            job_n=db.execute("SELECT count(*) n FROM resources WHERE job_id=? AND state='ACTIVE'",(job_id,)).fetchone()["n"]
            day_n=db.execute("SELECT count(*) n FROM resources WHERE provider=? AND created_at>=date('now')",(provider.upper(),)).fetchone()["n"]
            if (max_per_job and job_n>=max_per_job) or (max_per_day and day_n>=max_per_day):
                self._incident(db,provider,job_id,None,"RESOURCE_CREATION_LIMIT",{"per_job":max_per_job,"per_day":max_per_day},{"job":job_n,"day":day_n},"REJECT_CREATION")
                db.execute("COMMIT"); raise GovernanceDenied("HARD_STOP","RESOURCE_CREATION_LIMIT")
            db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?)",(key,job_id,provider.upper(),purpose,"ACTIVE",now())); db.execute("COMMIT")
        return key

    def record_footprint(self, footprint: dict) -> str:
        clean=sanitize(footprint)
        raw=json.dumps(clean,sort_keys=True,separators=(",",":"),default=str)
        digest=hashlib.sha256(raw.encode()).hexdigest()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO footprints(job_id,correlation_id,project_id,department,job_type,payload,receipt_hash,created_at) VALUES(?,?,?,?,?,?,?,?)",
                       (clean["job_id"],clean.get("correlation_id"),clean.get("project_id"),clean.get("department"),clean.get("job_type"),raw,digest,now()))
        return digest

    def record_incident(self, provider: str, job_id: str, code: str, action: str,
                        *, project_id: str | None = None, threshold: Any = None, observed: Any = None) -> None:
        with self.connect() as db:
            self._incident(db, provider, job_id, project_id, code, threshold, observed, action)

    def certify(self, capability: str, status: str, **evidence: Any) -> None:
        if status not in CERTIFICATION_STATES: raise ValueError("INVALID_CERTIFICATION_STATUS")
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO certifications VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       ("cert_"+hashlib.sha256(capability.encode()).hexdigest()[:20],capability,status,evidence.get("project_id"),evidence.get("job_id"),evidence.get("evidence_ref"),evidence.get("provider"),evidence.get("host"),evidence.get("cost"),json.dumps(sanitize(evidence),separators=(",",":"),default=str),now()))

    def summary(self) -> dict:
        with self.connect() as db:
            policies=[dict(r) for r in db.execute("SELECT provider,service,state,autonomous_usage_allowed,autonomous_spend_allowed,approval_required FROM policies WHERE service='*' AND job_type='*' ORDER BY provider,budget_period")]
            reservations=[dict(r) for r in db.execute("SELECT provider,budget_period,status,estimate,actual FROM reservations WHERE created_at>=datetime('now','-31 days') LIMIT 1000")]
            incidents=[dict(r) for r in db.execute("SELECT provider,job_id,code,action,created_at FROM incidents ORDER BY created_at DESC LIMIT 20")]
            providers=[]
            for policy in policies:
                if policy["provider"] in {x["provider"] for x in providers}: continue
                rows=[r for r in reservations if r["provider"]==policy["provider"]]
                def usage(period,status):
                    result={}
                    for r in rows:
                        if r["budget_period"]!=period or (status and r["status"]!=status): continue
                        values=json.loads(r["actual"] or "{}") or json.loads(r["estimate"] or "{}")
                        for dim,value in values.items():
                            if dim not in {"billable","budget_period"}: result[dim]=result.get(dim,0)+float(value)
                    return result
                providers.append({"provider":policy["provider"],"state":policy["state"],"autonomous_usage_allowed":bool(policy["autonomous_usage_allowed"]),"autonomous_spend_allowed":bool(policy["autonomous_spend_allowed"]),"approval_required":bool(policy["approval_required"]),"daily_usage":usage("DAILY","RECONCILED"),"monthly_usage":usage("MONTHLY","RECONCILED"),"reserved_usage":usage("DAILY","ACTIVE"),"active_paid_jobs":sum(1 for r in rows if r["status"]=="ACTIVE" and float(json.loads(r["estimate"]).get("cost",0) or 0)>0)})
            active=sum(1 for r in reservations if r["status"]=="ACTIVE")
        return {"providers":providers,"recent_incidents":incidents,"active_reservations":active}

    @staticmethod
    def _incident(db,provider,job_id,project_id,code,threshold,observed,action):
        db.execute("INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?,?,?)",("inc_"+uuid.uuid4().hex,provider,job_id,project_id,code,json.dumps(threshold,default=str),json.dumps(observed,default=str),action,None,now()))


def default_store():
    local_path=os.environ.get("NEXUS_GOVERNOR_DB")
    if local_path: return LocalGovernorStore(local_path)
    try:
        sys.path.insert(0,str(ROOT / "scripts/ops"))
        from nexus_runtime_env import load_runtime_env
        load_runtime_env()
    except (ImportError,OSError): pass
    if (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")) and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return SupabaseGovernorStore()
    return LocalGovernorStore(DEFAULT_DB)


def authorize_paid_action(provider: str, service: str, job_type: str, job_id: str, estimate: dict[str,float], *, purpose="execution"):
    """Reservation gate. Unknown providers and unconfigured spend are denied."""
    store=default_store()
    return store.reserve(provider,service,job_type,job_id,estimate,purpose=purpose)


class SupabaseGovernorStore:
    """Compact hosted adapter. Mutations use service role; no provider secrets are persisted."""
    def _request(self,path,method="GET",body=None,prefer="return=minimal"):
        from nexus_agent_platform.feeder_runtime import _request
        return _request(path,method,body,prefer)

    def set_policy(self, provider: str, service: str, job_type: str, budget_period: str, *,
                   autonomous_usage_allowed: bool, autonomous_spend_allowed: bool = False,
                   soft_limits: dict | None = None, hard_limits: dict | None = None,
                   concurrency_limit: int = 1, resource_creation_limit: int = 0,
                   state: str = "NORMAL", approval_required: bool = True) -> dict:
        """Upsert one narrowly scoped governed provider policy."""
        if state not in STATES or budget_period not in {"DAILY","MONTHLY"}:
            raise ValueError("INVALID_GOVERNOR_POLICY")
        body={"provider":provider.upper(),"service":service,"job_type":job_type,
              "budget_period":budget_period,"autonomous_usage_allowed":bool(autonomous_usage_allowed),
              "autonomous_spend_allowed":bool(autonomous_spend_allowed),"soft_limits":soft_limits or DEFAULT_LIMITS,
              "hard_limits":hard_limits or DEFAULT_LIMITS,"concurrency_limit":int(concurrency_limit),
              "resource_creation_limit":int(resource_creation_limit),"state":state,
              "approval_required":bool(approval_required),"updated_at":now()}
        rows=self._request("nexus_resource_policies?on_conflict=provider,service,job_type,budget_period",
            "POST",body,"resolution=merge-duplicates,return=representation")
        if not rows: raise GovernanceDenied("BLOCKED","RESOURCE_POLICY_UPSERT_REJECTED")
        return rows[0]

    def ensure_policy(self, provider: str, service: str, job_type: str, budget_period: str, *,
                      autonomous_usage_allowed: bool, autonomous_spend_allowed: bool,
                      soft_limits: dict, hard_limits: dict, concurrency_limit: int = 1,
                      resource_creation_limit: int = 0, state: str = "NORMAL",
                      approval_required: bool = False) -> bool:
        """Insert a scoped policy only if absent; never reopen an existing stop."""
        if state not in STATES or budget_period not in {"DAILY", "MONTHLY"}:
            raise ValueError("INVALID_GOVERNOR_POLICY")
        body={"provider":provider.upper(),"service":service,"job_type":job_type,
              "budget_period":budget_period,"autonomous_usage_allowed":bool(autonomous_usage_allowed),
              "autonomous_spend_allowed":bool(autonomous_spend_allowed),"soft_limits":soft_limits,
              "hard_limits":hard_limits,"concurrency_limit":int(concurrency_limit),
              "resource_creation_limit":int(resource_creation_limit),"state":state,
              "approval_required":bool(approval_required),"updated_at":now()}
        rows=self._request("nexus_resource_policies?on_conflict=provider,service,job_type,budget_period",
            "POST",body,"resolution=ignore-duplicates,return=representation")
        return bool(rows)

    def resolve_policy(self, provider: str, service: str, job_type: str, budget_period: str = "DAILY") -> dict[str, Any] | None:
        """Resolve policy with the same precedence as nexus_reserve_resource_budget_v2.

        The health RPC intentionally reports wildcard rows only. Query the four
        possible scopes directly so operators can verify the row reserve will
        actually select without changing the SQL governor contract.
        """
        base = (f"nexus_resource_policies?provider=eq.{provider.upper()}"
                f"&budget_period=eq.{budget_period.upper()}"
                "&select=provider,service,job_type,budget_period,state,autonomous_usage_allowed,"
                "autonomous_spend_allowed,approval_required,soft_limits,hard_limits,concurrency_limit,"
                "resource_creation_limit,updated_at&limit=1")
        scopes = ((service, job_type), (service, "*"), ("*", job_type), ("*", "*"))
        for selected_service, selected_job_type in scopes:
            rows = self._request(base + f"&service=eq.{selected_service}&job_type=eq.{selected_job_type}") or []
            if rows:
                value = dict(rows[0])
                value["wildcard_fallback_used"] = selected_service == "*" or selected_job_type == "*"
                return value
        return None

    def correct_invalid_url_preflight(self, reservation_id: str, *, job_id: str) -> dict:
        """Correct estimated usage for a GET rejected locally before any socket call."""
        rows=self._request(f"nexus_resource_reservations?reservation_id=eq.{reservation_id}&job_id=eq.{job_id}&select=reservation_id,provider,service,estimate,actual,status")
        if not rows: raise GovernanceDenied("BLOCKED","PREFLIGHT_RESERVATION_NOT_FOUND")
        row=rows[0]
        estimate=row.get("estimate") or {}; actual=row.get("actual") or {}
        if (row.get("provider")!="PUBLIC_WEB" or str(row.get("service") or "")!=""
                or row.get("status")!="RECONCILED" or actual.get("bytes")!=estimate.get("bytes")
                or int(estimate.get("requests",0))!=1):
            raise GovernanceDenied("BLOCKED","PREFLIGHT_RESERVATION_NOT_PROVABLY_LOCAL")
        corrected={**actual,"bytes":0,"requests":0,"api_calls":0,"cost":0,
                   "correction_reason":"invalid empty URL rejected before network request"}
        updated=self._request(f"nexus_resource_reservations?reservation_id=eq.{reservation_id}&job_id=eq.{job_id}&status=eq.RECONCILED",
            "PATCH",{"actual":corrected},"return=representation")
        if not updated: raise GovernanceDenied("BLOCKED","PREFLIGHT_RESERVATION_CORRECTION_REJECTED")
        return {"reservation_id":reservation_id,"job_id":job_id,"corrected_actual":corrected}

    def correct_cumulative_worker_snapshots(self, job_id: str) -> dict:
        """Turn known per-attempt cumulative worker snapshots into actual deltas."""
        rows=self._request(f"nexus_resource_reservations?job_id=eq.{job_id}&provider=eq.SUPABASE&service=eq.durable_worker&select=reservation_id,estimate,actual,status,created_at&order=created_at.asc")
        previous={"requests":0,"bytes":0}; corrected=[]
        for row in rows:
            actual=row.get("actual") or {}
            if row.get("status")!="RECONCILED" or not isinstance(actual,dict):
                raise GovernanceDenied("BLOCKED","WORKER_SNAPSHOT_REPAIR_STATE_INVALID")
            current={key:int(actual.get(key,0) or 0) for key in previous}
            if any(current[key]<previous[key] for key in previous):
                raise GovernanceDenied("BLOCKED","WORKER_SNAPSHOT_SEQUENCE_NOT_MONOTONIC")
            delta={key:current[key]-previous[key] for key in previous}
            replacement={**actual,**delta,"cost":float(actual.get("cost",0) or 0),
                         "correction_reason":"cumulative per-job egress snapshot converted to per-attempt usage"}
            updated=self._request(f"nexus_resource_reservations?reservation_id=eq.{row['reservation_id']}&job_id=eq.{job_id}&status=eq.RECONCILED",
                                  "PATCH",{"actual":replacement},"return=representation")
            if not updated: raise GovernanceDenied("BLOCKED","WORKER_SNAPSHOT_REPAIR_REJECTED")
            corrected.append({"reservation_id":row["reservation_id"],"delta":delta})
            previous=current
        return {"job_id":job_id,"corrected_count":len(corrected),"reservations":corrected,
                "cumulative_actual":previous}

    def reset_due_daily_budget_hard_stops(self) -> int:
        """Recover only budget circuits whose matching UTC window has expired.

        The database function checks the incident that opened the circuit and
        leaves manual, health, and other hard stops untouched.
        """
        rows=self._request("rpc/nexus_reset_daily_budget_hard_stops","POST",{},"return=representation")
        if isinstance(rows,list) and rows:
            value=rows[0]
            return int(value.get("nexus_reset_daily_budget_hard_stops",value.get("count",0)) if isinstance(value,dict) else value)
        if isinstance(rows,dict):
            return int(rows.get("nexus_reset_daily_budget_hard_stops",rows.get("count",0)))
        return int(rows or 0)

    def reserve(self,provider,service,job_type,job_id,estimate,*,purpose="execution",project_id=None):
        period=str(estimate.get("budget_period","DAILY")).upper()
        envelope=dict(JOB_ENVELOPE)
        try: envelope.update({k:v for k,v in json.loads(os.environ.get("NEXUS_JOB_BUDGET","{}")).items() if k in envelope})
        except (ValueError,TypeError,AttributeError): pass
        remote_estimate={**estimate,"job_budget":envelope}
        rows=self._request("rpc/nexus_reserve_resource_budget_v2","POST",{"p_provider":provider,"p_service":service,"p_job_type":job_type,"p_budget_period":period,"p_job_id":job_id,"p_estimate":remote_estimate,"p_purpose":purpose},"return=representation")
        result=rows[0] if isinstance(rows,list) and rows else rows
        if not result or not result.get("allowed"):
            raise GovernanceDenied((result or {}).get("state","HUMAN_APPROVAL_REQUIRED"),(result or {}).get("code","RESERVATION_DENIED"))
        if result.get("idempotent_replay"):
            self.record_incident(provider,job_id,"RESERVATION_REPLAY_DENIED","DO_NOT_REPEAT_EXTERNAL_ACTION",project_id=project_id,observed=estimate)
            raise GovernanceDenied("HARD_STOP","RESERVATION_REPLAY_DENIED")
        return result

    def reconcile(self,reservation_id,actual):
        rows=self._request(f"nexus_resource_reservations?reservation_id=eq.{reservation_id}&status=eq.ACTIVE","PATCH",{"actual":actual,"status":"RECONCILED","reconciled_at":now()},"return=representation")
        if not rows: raise GovernanceDenied("BLOCKED","RESERVATION_NOT_ACTIVE")

    def release(self,reservation_id):
        rows=self._request(f"nexus_resource_reservations?reservation_id=eq.{reservation_id}&status=eq.ACTIVE","PATCH",{"status":"RELEASED","reconciled_at":now()},"return=representation")
        return bool(rows)

    def resource_create(self,job_id,provider,purpose,*,job_type="UNKNOWN_RESOURCE_CREATE",max_per_job=0,max_per_day=0):
        envelope=dict(JOB_ENVELOPE)
        try: envelope.update({k:v for k,v in json.loads(os.environ.get("NEXUS_JOB_BUDGET","{}")).items() if k in envelope})
        except (ValueError,TypeError,AttributeError): pass
        limit=int(envelope["max_resource_creations"])
        if limit<=0: raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED","RESOURCE_CREATION_NOT_AUTHORIZED")
        max_per_job=min(max_per_job,limit)
        rows=self._request("rpc/nexus_reserve_resource_creation","POST",{"p_job_id":job_id,"p_provider":provider.upper(),"p_purpose":purpose,"p_job_type":job_type,"p_max_per_job":max_per_job,"p_max_per_day":max_per_day},"return=representation")
        result=rows[0] if isinstance(rows,list) and rows else rows
        if not result or not result.get("allowed"): raise GovernanceDenied((result or {}).get("state","HARD_STOP"),(result or {}).get("code","RESOURCE_CREATION_DENIED"))
        return result["resource_key"]

    def record_footprint(self,footprint):
        clean=sanitize(footprint)
        raw=json.dumps(clean,sort_keys=True,separators=(",",":"),default=str); digest=hashlib.sha256(raw.encode()).hexdigest()
        row={"job_id":clean["job_id"],"correlation_id":clean.get("correlation_id"),"project_id":clean.get("project_id"),"department":clean.get("department"),"job_type":clean.get("job_type"),"footprint":clean,"receipt_hash":digest,"created_at":now()}
        self._request("nexus_job_footprints?on_conflict=job_id","POST",row,"resolution=merge-duplicates,return=minimal")
        return digest

    def record_incident(self,provider,job_id,code,action,*,project_id=None,threshold=None,observed=None):
        row={"incident_id":"inc_"+hashlib.sha256(f"{provider}:{job_id}:{code}".encode()).hexdigest()[:28],
             "provider":provider,"job_id":job_id,"project_id":project_id,"code":code,
             "threshold":sanitize(threshold),"observed":sanitize(observed),"action":action,
             "unrelated_work_continued":True,"created_at":now()}
        self._request("nexus_resource_incidents?on_conflict=incident_id","POST",row,"resolution=merge-duplicates,return=minimal")

    def certify(self,capability,status,**evidence):
        if status not in CERTIFICATION_STATES: raise ValueError("INVALID_CERTIFICATION_STATUS")
        cid="cert_"+hashlib.sha256(capability.encode()).hexdigest()[:20]
        evidence=sanitize(evidence)
        row={"certification_id":cid,"capability":capability,"status":status,"project_id":evidence.get("project_id"),"job_id":evidence.get("job_id"),"evidence_ref":evidence.get("evidence_ref"),"provider":evidence.get("provider"),"host":evidence.get("host"),"estimated_cost":evidence.get("estimated_cost"),"actual_cost":evidence.get("actual_cost"),"result":evidence,"updated_at":now()}
        self._request("nexus_certification_ledger?on_conflict=certification_id","POST",row,"resolution=merge-duplicates,return=minimal")

    def summary(self):
        value=self._request("rpc/nexus_resource_governor_health","POST",{},"return=representation")
        result = value if isinstance(value,dict) else (value[0] if value else {"providers":[],"recent_incidents":[]})
        # The health RPC is a provider overview over wildcard policy rows. Keep
        # scoped Research authorization visible alongside it; otherwise a
        # wildcard DISABLED default is easily mistaken for the effective policy.
        resolver = getattr(self, "resolve_policy", None)
        if resolver:
            result["policy_resolutions"] = {
                "research_notebooklm_daily": resolver("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY"),
                "research_notebooklm_monthly": resolver("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "MONTHLY"),
                "research_supabase_daily": resolver("SUPABASE", "durable_worker", "RESEARCH_GAP_VERIFY", "DAILY"),
                "needle_model_daily": resolver("OPENAI_CODEX", "subscription_model", "NEEDLE_RESEARCH_READINESS_VERIFY", "DAILY"),
            }
        return result
