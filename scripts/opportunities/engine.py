"""Durable commercial opportunity library and deterministic scoring primitives.

This is the authority for opportunity state. Research and upstream registries
remain separate evidence sources; this module never writes into their stores.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
SCORE_VERSION = "nexus-opportunity-score-v1"
DB_PATH = Path.home() / ".nexus/state/opportunities/opportunities.sqlite3"

OPPORTUNITY_TYPES = {
    "AFFILIATE", "CONSULTING", "SERVICE", "DIGITAL_PRODUCT", "SAAS",
    "LEAD_GENERATION", "PROCUREMENT", "ECOMMERCE", "CONTENT_MONETIZATION",
    "PARTNERSHIP", "LICENSING_API", "SPONSORSHIP", "MARKETPLACE", "OTHER",
}
DELIVERY_MODELS = {
    "ONLINE_ONLY", "LOCAL_SERVICE", "MOBILE_SERVICE", "HYBRID",
    "PHYSICAL_LOCATION", "REMOTE_SERVICE", "MARKETPLACE", "PARTNER_FULFILLED",
}
SOURCE_TYPES = {
    "RESEARCH_R10", "NOVA_MANUAL", "RAY_MANUAL", "OPENAFFILIATE", "GITHUB",
    "PROCUREMENT", "SOCIAL_DISCOVERY", "SEO_DEMAND", "OTHER",
}
VERIFICATION_STATES = {"VERIFIED", "PARTIAL", "UNVERIFIED", "CONFLICTING"}
CLAIM_TYPES = {
    "COMMISSION_RATE", "COOKIE_DURATION", "MARKET_DEMAND", "ESTIMATED_MARGIN",
    "STARTUP_COST", "CUSTOMER_NEED", "COMPETITION", "APPROVAL_REQUIREMENTS",
    "PAYMENT_TERMS", "LEGAL_RESTRICTION", "TRAFFIC_REQUIREMENT", "EXPECTED_CONVERSION",
    "LAB_PARTNER_REQUIREMENT", "REFERRAL_PARTNER_REQUIREMENT", "LOCAL_DEMAND",
    "REGULATORY_REQUIREMENT",
}
RISK_TYPES = {
    "FINANCIAL", "LEGAL_COMPLIANCE", "PRIVACY", "SECURITY", "CREDENTIAL",
    "PLATFORM_DEPENDENCY", "REPUTATION", "PAID_ADVERTISING", "TECHNICAL_COMPLEXITY",
    "CAPITAL_INTENSITY", "REGULATORY", "LOCAL_MARKET_DEPENDENCY", "PARTNER_DEPENDENCY",
}
STATUSES = {
    "DISCOVERED", "NORMALIZED", "NEEDS_RESEARCH", "RESEARCH_PENDING", "READY_TO_SCORE",
    "SCORED", "UNDER_REVIEW", "EXPERIMENT_PENDING", "ACTIVE", "COMPLETED",
    "ARCHIVED", "REJECTED",
}
RECOMMENDATIONS = {
    "REJECT", "WATCH", "RESEARCH_MORE", "VALIDATE", "TEST", "BUILD", "APPLY", "LAUNCH", "SCALE",
}
WEIGHTS = {
    "revenue_potential_score": 20,
    "monetization_probability_score": 15,
    "time_to_revenue_score": 15,
    "capability_fit_score": 15,
    "audience_fit_score": 10,
    "startup_cost_efficiency_score": 10,
    "automation_potential_score": 5,
    "competitive_barrier_score": 5,
    "evidence_quality_score": 5,
}
LOCAL_DELIVERY = {"LOCAL_SERVICE", "MOBILE_SERVICE", "HYBRID", "PHYSICAL_LOCATION"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
 opportunity_id TEXT PRIMARY KEY,
 dedupe_key TEXT UNIQUE NOT NULL,
 title TEXT NOT NULL,
 candidate_identity TEXT NOT NULL,
 identity_json TEXT NOT NULL DEFAULT '{}',
 opportunity_type TEXT NOT NULL CHECK(opportunity_type IN (
  'AFFILIATE','CONSULTING','SERVICE','DIGITAL_PRODUCT','SAAS','LEAD_GENERATION',
  'PROCUREMENT','ECOMMERCE','CONTENT_MONETIZATION','PARTNERSHIP','LICENSING_API',
  'SPONSORSHIP','MARKETPLACE','OTHER')),
 subcategory TEXT,
 summary TEXT NOT NULL,
 target_customer TEXT,
 revenue_model TEXT,
 revenue_details_json TEXT,
 startup_cost_estimate REAL,
 time_to_first_revenue_days INTEGER,
 capability_fit TEXT,
 audience_fit TEXT,
 automation_potential TEXT,
 status TEXT NOT NULL CHECK(status IN (
  'DISCOVERED','NORMALIZED','NEEDS_RESEARCH','RESEARCH_PENDING','READY_TO_SCORE',
  'SCORED','UNDER_REVIEW','EXPERIMENT_PENDING','ACTIVE','COMPLETED','ARCHIVED','REJECTED')),
 recommendation TEXT CHECK(recommendation IS NULL OR recommendation IN (
  'REJECT','WATCH','RESEARCH_MORE','VALIDATE','TEST','BUILD','APPLY','LAUNCH','SCALE')),
 overall_score REAL CHECK(overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 100)),
 confidence TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 last_evaluated_at TEXT,
 next_review_at TEXT,
 owner_engine TEXT NOT NULL DEFAULT 'opportunities',
 source_count INTEGER NOT NULL DEFAULT 0,
 delivery_model TEXT CHECK(delivery_model IS NULL OR delivery_model IN (
  'ONLINE_ONLY','LOCAL_SERVICE','MOBILE_SERVICE','HYBRID','PHYSICAL_LOCATION',
  'REMOTE_SERVICE','MARKETPLACE','PARTNER_FULFILLED')),
 online_offline_mix TEXT,
 geographic_scope TEXT,
 physical_presence_required INTEGER,
 customer_interaction_mode TEXT,
 inventory_required TEXT,
 equipment_required TEXT,
 licensed_partner_required INTEGER,
 partner_type TEXT,
 facility_required INTEGER,
 vehicle_required INTEGER,
 local_marketing_dependency TEXT,
 referral_partner_dependency TEXT,
 regulatory_complexity TEXT,
 scalability_model TEXT,
 asset_light_score REAL,
 partner_fulfilled INTEGER,
 assessment_json TEXT
);
CREATE TABLE IF NOT EXISTS opportunity_sources (
 source_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
 source_type TEXT NOT NULL CHECK(source_type IN (
  'RESEARCH_R10','NOVA_MANUAL','RAY_MANUAL','OPENAFFILIATE','GITHUB',
  'PROCUREMENT','SOCIAL_DISCOVERY','SEO_DEMAND','OTHER')),
 source_name TEXT,
 source_reference TEXT,
 source_external_id TEXT,
 source_observed_at TEXT,
 raw_summary TEXT,
 verification_state TEXT NOT NULL CHECK(verification_state IN ('VERIFIED','PARTIAL','UNVERIFIED','CONFLICTING')),
 metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_opportunity_sources_owner ON opportunity_sources(opportunity_id,source_type);
CREATE INDEX IF NOT EXISTS idx_opportunity_sources_external ON opportunity_sources(source_type,source_external_id);
CREATE TABLE IF NOT EXISTS opportunity_evidence (
 evidence_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
 claim_type TEXT NOT NULL CHECK(claim_type IN (
  'COMMISSION_RATE','COOKIE_DURATION','MARKET_DEMAND','ESTIMATED_MARGIN','STARTUP_COST',
  'CUSTOMER_NEED','COMPETITION','APPROVAL_REQUIREMENTS','PAYMENT_TERMS','LEGAL_RESTRICTION',
  'TRAFFIC_REQUIREMENT','EXPECTED_CONVERSION','LAB_PARTNER_REQUIREMENT',
  'REFERRAL_PARTNER_REQUIREMENT','LOCAL_DEMAND','REGULATORY_REQUIREMENT')),
 claim TEXT,
 evidence_value TEXT,
 evidence_quality TEXT,
 source_id TEXT REFERENCES opportunity_sources(source_id),
 verified_by TEXT,
 verified_at TEXT,
 expires_at TEXT,
 conflict_state TEXT
);
CREATE INDEX IF NOT EXISTS idx_opportunity_evidence_owner ON opportunity_evidence(opportunity_id,claim_type);
CREATE TABLE IF NOT EXISTS opportunity_scores (
 score_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
 revenue_potential_score REAL,
 monetization_probability_score REAL,
 time_to_revenue_score REAL,
 capability_fit_score REAL,
 audience_fit_score REAL,
 startup_cost_efficiency_score REAL,
 automation_potential_score REAL,
 competitive_barrier_score REAL,
 evidence_quality_score REAL,
 asset_light_bonus REAL,
 overall_score REAL NOT NULL CHECK(overall_score >= 0 AND overall_score <= 100),
 confidence TEXT,
 scoring_version TEXT NOT NULL,
 assumptions_json TEXT,
 scored_at TEXT NOT NULL,
 scored_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_opportunity_scores_history ON opportunity_scores(opportunity_id,scored_at);
CREATE TABLE IF NOT EXISTS opportunity_risks (
 risk_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
 risk_type TEXT NOT NULL CHECK(risk_type IN (
  'FINANCIAL','LEGAL_COMPLIANCE','PRIVACY','SECURITY','CREDENTIAL','PLATFORM_DEPENDENCY',
  'REPUTATION','PAID_ADVERTISING','TECHNICAL_COMPLEXITY','CAPITAL_INTENSITY',
  'REGULATORY','LOCAL_MARKET_DEPENDENCY','PARTNER_DEPENDENCY')),
 severity TEXT,
 description TEXT,
 mitigation TEXT,
 requires_ray_approval INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'OPEN'
);
CREATE INDEX IF NOT EXISTS idx_opportunity_risks_owner ON opportunity_risks(opportunity_id);
CREATE TABLE IF NOT EXISTS opportunity_history (
 event_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
 event_type TEXT NOT NULL,
 previous_state TEXT,
 new_state TEXT,
 actor TEXT,
 reason TEXT,
 metadata_json TEXT,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunity_history_owner ON opportunity_history(opportunity_id,created_at);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _clean_text(value: Any, limit: int = 2000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _truth(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if value in (0, 1):
        return int(value)
    raise ValueError("boolean_field_must_be_true_false_or_null")


def _db_path(path: str | Path | None) -> Path:
    return Path(path).expanduser() if path is not None else DB_PATH


@contextmanager
def _connect(path: str | Path | None = None, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
    db_path = _db_path(path)
    if readonly:
        con = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=4)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(db_path.parent, 0o700)
        except OSError:
            pass
        con = sqlite3.connect(db_path, timeout=8)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=8000")
    try:
        yield con
        if not readonly:
            con.commit()
    except BaseException:
        if not readonly:
            con.rollback()
        raise
    finally:
        con.close()


def initialize(path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(path)
    with _connect(db_path) as con:
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError("OPPORTUNITIES_SCHEMA_NEWER_THAN_RUNTIME")
        con.executescript(SCHEMA)
        con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass
    return {"status": "READY", "schema_version": SCHEMA_VERSION, "database_path": str(db_path)}


def _fetch_opportunity(con: sqlite3.Connection, opportunity_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM opportunities WHERE opportunity_id=?", (opportunity_id,)).fetchone()


def _resolve_id(con: sqlite3.Connection, opportunity_id: str = "", title: str = "") -> str | None:
    reference = _clean_text(opportunity_id, 128)
    if reference:
        row = _fetch_opportunity(con, reference)
        if row:
            return reference
    name = _clean_text(title, 240).casefold()
    if name:
        rows = con.execute("SELECT opportunity_id FROM opportunities WHERE lower(title)=? ORDER BY updated_at DESC LIMIT 2",
                           (name,)).fetchall()
        if len(rows) == 1:
            return str(rows[0]["opportunity_id"])
    return None


def resolve_reference(opportunity_id: str = "", title: str = "", *,
                      database_path: str | Path | None = None) -> str | None:
    """Resolve an exact internal reference or unique title for tool composition."""
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        return _resolve_id(con, opportunity_id, title)


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _domain(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlsplit(text if "://" in text else "https://" + text)
    return (parsed.hostname or "").lower().removeprefix("www.")


def _identity(data: dict[str, Any]) -> dict[str, str]:
    name = _norm(_clean_text(data.get("candidate_name") or data.get("partner_program_id") or data.get("title"), 240))
    domain = _domain(str(data.get("website") or data.get("source_reference") or ""))
    return {
        "name": name,
        "type": str(data.get("opportunity_type") or "").upper(),
        "source_type": str(data.get("source_type") or "OTHER").upper(),
        "external_id": _clean_text(data.get("source_external_id"), 200).casefold(),
        "domain": domain,
        "partner_program_id": _norm(_clean_text(data.get("partner_program_id"), 200)),
        "geography": _norm(_clean_text(data.get("geographic_scope"), 160))
            if str(data.get("delivery_model") or "").upper() in LOCAL_DELIVERY or
               str(data.get("online_offline_mix") or "").upper() not in {"", "ONLINE_ONLY"} else "",
    }


def _dedupe_key(identity: dict[str, str]) -> str:
    material = "|".join(identity.get(key, "") for key in
                        ("name", "type", "source_type", "external_id", "domain", "partner_program_id", "geography"))
    return hashlib.sha256(material.encode()).hexdigest()


def _find_duplicate(con: sqlite3.Connection, identity: dict[str, str], dedupe_key: str) -> str | None:
    row = con.execute("SELECT opportunity_id FROM opportunities WHERE dedupe_key=?", (dedupe_key,)).fetchone()
    if row:
        return str(row[0])
    for key in ("external_id", "partner_program_id"):
        value = identity.get(key)
        if value and key == "external_id":
            row = con.execute(
                "SELECT s.opportunity_id FROM opportunity_sources s WHERE s.source_type=? AND lower(s.source_external_id)=? LIMIT 1",
                (identity.get("source_type"), _clean_text(value, 300)),
            ).fetchone()
            if row:
                return str(row[0])
    if identity.get("partner_program_id"):
        for row in con.execute("SELECT opportunity_id,identity_json FROM opportunities WHERE opportunity_type=?",
                               (identity["type"],)):
            prior = json.loads(row["identity_json"] or "{}")
            if prior.get("partner_program_id") == identity["partner_program_id"] and (
                    not prior.get("geography") or not identity.get("geography") or
                    prior.get("geography") == identity.get("geography")):
                return str(row["opportunity_id"])
    if identity.get("domain"):
        rows = con.execute(
            "SELECT opportunity_id,identity_json FROM opportunities WHERE candidate_identity=? AND opportunity_type=?",
            (identity["name"], identity["type"]),
        ).fetchall()
        for row in rows:
            prior = json.loads(row["identity_json"] or "{}")
            if prior.get("domain") == identity["domain"] and (
                    not prior.get("geography") or not identity.get("geography") or
                    prior.get("geography") == identity.get("geography")):
                return str(row["opportunity_id"])
    return None


def _source(con: sqlite3.Connection, opportunity_id: str, data: dict[str, Any]) -> str | None:
    source_type = str(data.get("source_type") or "OTHER").upper()
    if source_type not in SOURCE_TYPES:
        raise ValueError("unsupported_source_type")
    verification = str(data.get("verification_state") or "UNVERIFIED").upper()
    if verification not in VERIFICATION_STATES:
        raise ValueError("unsupported_verification_state")
    if source_type == "GITHUB" and verification == "VERIFIED":
        raise ValueError("GITHUB_OPPORTUNITY_CLAIMS_REQUIRE_RESEARCH_VERIFICATION")
    external = _clean_text(data.get("source_external_id"), 300) or None
    if external:
        existing = con.execute(
            "SELECT source_id FROM opportunity_sources WHERE opportunity_id=? AND source_type=? AND source_external_id=?",
            (opportunity_id, source_type, external),
        ).fetchone()
        if existing:
            return str(existing[0])
    source_id = "src_" + uuid.uuid4().hex
    con.execute(
        """INSERT INTO opportunity_sources
        (source_id,opportunity_id,source_type,source_name,source_reference,source_external_id,
         source_observed_at,raw_summary,verification_state,metadata_json)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (source_id, opportunity_id, source_type, _clean_text(data.get("source_name"), 200) or None,
         _clean_text(data.get("source_reference"), 1000) or None, external, now(),
         _clean_text(data.get("source_summary"), 2000) or None, verification,
         _json(data.get("source_metadata") or {})),
    )
    con.execute("UPDATE opportunities SET source_count=(SELECT count(*) FROM opportunity_sources WHERE opportunity_id=?),updated_at=? WHERE opportunity_id=?",
                (opportunity_id, now(), opportunity_id))
    return source_id


def _history(con: sqlite3.Connection, opportunity_id: str, event_type: str,
             previous: str | None = None, new: str | None = None, reason: str = "",
             metadata: dict[str, Any] | None = None, actor: str = "NEXUS_OPPORTUNITIES") -> None:
    con.execute(
        "INSERT INTO opportunity_history VALUES (?,?,?,?,?,?,?,?,?)",
        ("evt_" + uuid.uuid4().hex, opportunity_id, event_type, previous, new,
         _clean_text(actor, 100), _clean_text(reason, 1000) or None, _json(metadata or {}), now()),
    )


def _add_risks(con: sqlite3.Connection, opportunity_id: str, risks: list[dict[str, Any]]) -> None:
    for risk in risks[:20]:
        kind = str(risk.get("risk_type") or "").upper()
        if kind not in RISK_TYPES:
            raise ValueError("unsupported_risk_type")
        description = _clean_text(risk.get("description"), 1200)
        if con.execute("SELECT 1 FROM opportunity_risks WHERE opportunity_id=? AND risk_type=? AND description=?",
                       (opportunity_id, kind, description)).fetchone():
            continue
        con.execute(
            """INSERT INTO opportunity_risks
            (risk_id,opportunity_id,risk_type,severity,description,mitigation,requires_ray_approval,status)
            VALUES (?,?,?,?,?,?,?,?)""",
            ("risk_" + uuid.uuid4().hex, opportunity_id, kind,
             _clean_text(risk.get("severity"), 40).upper() or "UNKNOWN",
             description, _clean_text(risk.get("mitigation"), 1200) or None,
             int(bool(risk.get("requires_ray_approval"))), "OPEN"),
        )


def submit(data: dict[str, Any], *, database_path: str | Path | None = None) -> dict[str, Any]:
    title = _clean_text(data.get("title"), 240)
    summary = _clean_text(data.get("summary"), 4000)
    kind = str(data.get("opportunity_type") or "").upper()
    if not title or not summary or kind not in OPPORTUNITY_TYPES:
        return {"status": "REJECTED", "reason": "TITLE_SUMMARY_AND_SUPPORTED_TYPE_REQUIRED"}
    delivery = str(data.get("delivery_model") or "").upper() or None
    if delivery and delivery not in DELIVERY_MODELS:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_DELIVERY_MODEL"}
    source_type = str(data.get("source_type") or "OTHER").upper()
    if source_type not in SOURCE_TYPES:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_SOURCE_TYPE"}
    verification = str(data.get("verification_state") or "UNVERIFIED").upper()
    if verification not in VERIFICATION_STATES:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_VERIFICATION_STATE"}
    if source_type == "GITHUB" and verification == "VERIFIED":
        return {"status": "REJECTED", "reason": "GITHUB_OPPORTUNITY_CLAIMS_REQUIRE_RESEARCH_VERIFICATION"}
    startup = data.get("startup_cost_estimate")
    days = data.get("time_to_first_revenue_days")
    if startup is not None and (float(startup) < 0 or float(startup) > 1_000_000_000):
        return {"status": "REJECTED", "reason": "STARTUP_COST_OUT_OF_BOUNDS"}
    if days is not None and (int(days) < 0 or int(days) > 36500):
        return {"status": "REJECTED", "reason": "TIME_TO_REVENUE_OUT_OF_BOUNDS"}
    identity = _identity(data)
    dedupe = _dedupe_key(identity)
    oid = "opp_" + uuid.uuid4().hex
    timestamp = now()
    details = data.get("revenue_details")
    if details is not None and not isinstance(details, dict):
        return {"status": "REJECTED", "reason": "REVENUE_DETAILS_MUST_BE_AN_OBJECT"}
    columns = {
        "opportunity_id": oid, "dedupe_key": dedupe, "title": title,
        "candidate_identity": identity["name"], "identity_json": _json(identity),
        "opportunity_type": kind, "subcategory": _clean_text(data.get("subcategory"), 160) or None,
        "summary": summary, "target_customer": _clean_text(data.get("target_customer"), 1000) or None,
        "revenue_model": _clean_text(data.get("revenue_model"), 500) or None,
        "revenue_details_json": _json(details) if details is not None else None,
        "startup_cost_estimate": float(startup) if startup is not None else None,
        "time_to_first_revenue_days": int(days) if days is not None else None,
        "capability_fit": _clean_text(data.get("capability_fit"), 500) or None,
        "audience_fit": _clean_text(data.get("audience_fit"), 500) or None,
        "automation_potential": _clean_text(data.get("automation_potential"), 500) or None,
        "status": str(data.get("status") or "NORMALIZED").upper(),
        "recommendation": None, "overall_score": None, "confidence": None,
        "created_at": timestamp, "updated_at": timestamp, "last_evaluated_at": None,
        "next_review_at": None, "owner_engine": "opportunities", "source_count": 0,
        "delivery_model": delivery, "online_offline_mix": _clean_text(data.get("online_offline_mix"), 80) or None,
        "geographic_scope": _clean_text(data.get("geographic_scope"), 240) or None,
        "physical_presence_required": _truth(data.get("physical_presence_required")),
        "customer_interaction_mode": _clean_text(data.get("customer_interaction_mode"), 120) or None,
        "inventory_required": _clean_text(data.get("inventory_required"), 100) or None,
        "equipment_required": _clean_text(data.get("equipment_required"), 1000) or None,
        "licensed_partner_required": _truth(data.get("licensed_partner_required")),
        "partner_type": _clean_text(data.get("partner_type"), 200) or None,
        "facility_required": _truth(data.get("facility_required")),
        "vehicle_required": _truth(data.get("vehicle_required")),
        "local_marketing_dependency": _clean_text(data.get("local_marketing_dependency"), 80) or None,
        "referral_partner_dependency": _clean_text(data.get("referral_partner_dependency"), 80) or None,
        "regulatory_complexity": _clean_text(data.get("regulatory_complexity"), 80) or None,
        "scalability_model": _clean_text(data.get("scalability_model"), 500) or None,
        "asset_light_score": float(data["asset_light_score"]) if data.get("asset_light_score") is not None else None,
        "partner_fulfilled": _truth(data.get("partner_fulfilled")),
        "assessment_json": None,
    }
    if columns["status"] not in STATUSES:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_INITIAL_STATUS"}
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path) as con:
        existing = _find_duplicate(con, identity, dedupe)
        if existing:
            source_id = _source(con, existing, data)
            _history(con, existing, "SOURCE_ATTACHED", reason="Candidate matched an existing commercial identity.",
                     metadata={"source_type": source_type, "verification_state": verification})
            return {"status": "DUPLICATE_REUSED", "opportunity_id": existing, "source_id": source_id,
                    "duplicate": True, "created": False}
        names = list(columns)
        con.execute(f"INSERT INTO opportunities ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                    [columns[name] for name in names])
        source_id = _source(con, oid, data)
        _add_risks(con, oid, data.get("risks") or [])
        _history(con, oid, "OPPORTUNITY_SUBMITTED", new=columns["status"], reason="Candidate normalized and recorded.",
                 metadata={"source_type": source_type, "verification_state": verification})
    return {"status": columns["status"], "opportunity_id": oid, "source_id": source_id,
            "duplicate": False, "created": True, "title": title}


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    value = dict(row)
    for key in ("revenue_details_json", "identity_json", "assessment_json"):
        raw = value.pop(key, None)
        value[key.removesuffix("_json")] = json.loads(raw) if raw else None
    return value


def _public(value: Any, *, include_internal_ids: bool = False) -> Any:
    hidden = {"opportunity_id", "dedupe_key", "source_id", "source_external_id", "evidence_id", "score_id",
              "risk_id", "event_id", "history_id", "research_job_id", "durable_job_id",
              "work_id", "objective_id", "receipt_id", "request_id", "research_source_id",
              "research_objective_id", "research_work_id", "research_receipt_id",
              "candidate_identity", "identity"}
    if isinstance(value, dict):
        result = {key: _public(item, include_internal_ids=include_internal_ids)
                  for key, item in value.items() if include_internal_ids or key.casefold() not in hidden}
        return result
    if isinstance(value, list):
        return [_public(item, include_internal_ids=include_internal_ids) for item in value]
    if isinstance(value, str) and not include_internal_ids:
        value = re.sub(r"\b(?:opp|src|ev|score|risk|evt)_[a-f0-9]{32}\b", "[internal reference]", value)
        value = re.sub(r"\b(?:job|sysjob|sysrcpt|receipt|nova_research|nova_research_work)_[A-Za-z0-9_-]{8,}\b",
                       "[internal reference]", value)
    return value


def get(opportunity_id: str = "", title: str = "", *, database_path: str | Path | None = None,
        include_internal_ids: bool = False) -> dict[str, Any] | None:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid = _resolve_id(con, opportunity_id, title)
        if not oid:
            return None
        value = _row(_fetch_opportunity(con, oid)) or {}
        value["sources"] = [dict(row) for row in con.execute(
            "SELECT * FROM opportunity_sources WHERE opportunity_id=? ORDER BY source_observed_at", (oid,))]
        for source in value["sources"]:
            raw_metadata = source.pop("metadata_json", None)
            source["metadata"] = json.loads(raw_metadata) if raw_metadata else {}
        value["evidence"] = [dict(row) for row in con.execute(
            "SELECT * FROM opportunity_evidence WHERE opportunity_id=? ORDER BY verified_at", (oid,))]
        value["scores"] = [dict(row) for row in con.execute(
            "SELECT * FROM opportunity_scores WHERE opportunity_id=? ORDER BY scored_at DESC", (oid,))]
        value["risks"] = [dict(row) for row in con.execute(
            "SELECT * FROM opportunity_risks WHERE opportunity_id=? ORDER BY risk_type", (oid,))]
        value["history"] = [dict(row) for row in con.execute(
            "SELECT * FROM opportunity_history WHERE opportunity_id=? ORDER BY created_at", (oid,))]
        for event in value["history"]:
            raw_metadata = event.pop("metadata_json", None)
            event["metadata"] = json.loads(raw_metadata) if raw_metadata else {}
    return _public(value, include_internal_ids=include_internal_ids)


def list_opportunities(*, status: str = "", opportunity_type: str = "", delivery_model: str = "",
                       limit: int = 20, database_path: str | Path | None = None,
                       include_internal_ids: bool = False) -> list[dict[str, Any]]:
    initialize(database_path)
    clauses: list[str] = []
    params: list[Any] = []
    for column, value, allowed in (("status", status, STATUSES), ("opportunity_type", opportunity_type, OPPORTUNITY_TYPES),
                                   ("delivery_model", delivery_model, DELIVERY_MODELS)):
        clean = str(value or "").upper()
        if clean:
            if clean not in allowed:
                raise ValueError(f"unsupported_{column}")
            clauses.append(f"{column}=?")
            params.append(clean)
    params.append(max(1, min(int(limit), 100)))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with _connect(database_path, readonly=True) as con:
        rows = con.execute(f"SELECT * FROM opportunities{where} ORDER BY updated_at DESC LIMIT ?", params).fetchall()
    return [_public(_row(row), include_internal_ids=include_internal_ids) or {} for row in rows]


def search(query: str = "", *, opportunity_type: str = "", delivery_model: str = "",
           geographic_scope: str = "", limit: int = 20,
           database_path: str | Path | None = None) -> list[dict[str, Any]]:
    initialize(database_path)
    clauses: list[str] = []
    params: list[Any] = []
    clean_query = _clean_text(query, 160)
    if clean_query:
        # Escape LIKE wildcards so free-text search cannot broaden the requested match.
        escaped = clean_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(title LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\' OR candidate_identity LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%"] * 3)
    for column, value, allowed in (("opportunity_type", opportunity_type, OPPORTUNITY_TYPES),
                                   ("delivery_model", delivery_model, DELIVERY_MODELS)):
        selected = str(value or "").upper()
        if selected:
            if selected not in allowed:
                raise ValueError(f"unsupported_{column}")
            clauses.append(f"{column}=?")
            params.append(selected)
    if geographic_scope:
        clauses.append("geographic_scope LIKE ?")
        params.append(f"%{_clean_text(geographic_scope, 160)}%")
    params.append(max(1, min(int(limit), 100)))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with _connect(database_path, readonly=True) as con:
        rows = con.execute(f"SELECT * FROM opportunities{where} ORDER BY overall_score DESC, updated_at DESC LIMIT ?", params).fetchall()
    return [_public(_row(row)) or {} for row in rows]


def status(*, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        total = con.execute("SELECT count(*) FROM opportunities").fetchone()[0]
        by_status = {str(row[0]): int(row[1]) for row in con.execute(
            "SELECT status,count(*) FROM opportunities GROUP BY status")}
        by_type = {str(row[0]): int(row[1]) for row in con.execute(
            "SELECT opportunity_type,count(*) FROM opportunities GROUP BY opportunity_type")}
        latest = con.execute("SELECT max(last_evaluated_at) FROM opportunities").fetchone()[0]
    return {"status": "OK", "opportunity_count": int(total), "by_status": by_status,
            "by_type": by_type, "last_evaluation_at": latest, "schema_version": SCHEMA_VERSION}


def top(limit: int = 5, *, database_path: str | Path | None = None) -> list[dict[str, Any]]:
    initialize(database_path)
    amount = max(1, min(int(limit), 25))
    with _connect(database_path, readonly=True) as con:
        rows = con.execute(
            """SELECT * FROM opportunities WHERE overall_score IS NOT NULL
            AND status NOT IN ('ARCHIVED','REJECTED','COMPLETED')
            ORDER BY overall_score DESC, coalesce(asset_light_score,0) DESC, updated_at DESC LIMIT ?""",
            (amount,),
        ).fetchall()
    return [_public(_row(row)) or {} for row in rows]


def latest(*, database_path: str | Path | None = None) -> dict[str, Any] | None:
    rows = list_opportunities(limit=1, database_path=database_path)
    return rows[0] if rows else None


def score_history_count(opportunity_id: str, *, database_path: str | Path | None = None) -> int:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        row = con.execute("SELECT count(*) FROM opportunity_scores WHERE opportunity_id=?", (opportunity_id,)).fetchone()
        return int(row[0])


def score(opportunity_id: str, dimensions: dict[str, Any], *, confidence: str = "",
          assumptions: dict[str, Any] | None = None, scored_by: str = "NEXUS_OPPORTUNITIES",
          database_path: str | Path | None = None) -> dict[str, Any]:
    values: dict[str, float | None] = {}
    weighted = 0.0
    available_weight = 0
    for field, weight in WEIGHTS.items():
        raw = dimensions.get(field)
        if raw is None or raw == "":
            values[field] = None
            continue
        number = float(raw)
        if not 0 <= number <= 10:
            return {"status": "REJECTED", "reason": f"{field}_must_be_0_to_10"}
        values[field] = number
        weighted += number * weight
        available_weight += weight
    if not available_weight:
        return {"status": "REJECTED", "reason": "AT_LEAST_ONE_SCORE_DIMENSION_REQUIRED"}
    total = min(100.0, max(0.0, weighted / available_weight * 10.0))
    confidence_value = str(confidence or "").upper()
    if confidence_value not in {"LOW", "MEDIUM", "HIGH"}:
        known = sum(value is not None for value in values.values())
        confidence_value = "HIGH" if known == len(WEIGHTS) and (values.get("evidence_quality_score") or 0) >= 7 else \
                           "MEDIUM" if known >= 6 else "LOW"
    asset = dimensions.get("asset_light_bonus")
    asset_bonus = min(10.0, max(0.0, float(asset or 0)))
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        row = _fetch_opportunity(con, oid)
        prior_status = str(row["status"])
        timestamp = now()
        score_id = "score_" + uuid.uuid4().hex
        con.execute(
            """INSERT INTO opportunity_scores
            (score_id,opportunity_id,revenue_potential_score,monetization_probability_score,
             time_to_revenue_score,capability_fit_score,audience_fit_score,startup_cost_efficiency_score,
             automation_potential_score,competitive_barrier_score,evidence_quality_score,asset_light_bonus,
             overall_score,confidence,scoring_version,assumptions_json,scored_at,scored_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (score_id, oid, *(values[key] for key in WEIGHTS), asset_bonus, total, confidence_value,
             SCORE_VERSION, _json(assumptions or {}), timestamp, _clean_text(scored_by, 100)),
        )
        if confidence_value == "LOW":
            recommendation = "RESEARCH_MORE"
            new_status = "NEEDS_RESEARCH"
        else:
            recommendation = "TEST" if total >= 70 else "VALIDATE" if total >= 55 else "WATCH" if total >= 40 else "REJECT"
            new_status = "SCORED"
        con.execute("UPDATE opportunities SET overall_score=?,confidence=?,recommendation=?,status=?,updated_at=?,last_evaluated_at=? WHERE opportunity_id=?",
                    (total, confidence_value, recommendation, new_status, timestamp, timestamp, oid))
        _history(con, oid, "SCORED", previous=prior_status, new=new_status,
                 reason="Deterministic weighted score recorded; previous score history retained.",
                 metadata={"score": total, "confidence": confidence_value, "scoring_version": SCORE_VERSION})
    return {"status": new_status, "recommendation": recommendation, "overall_score": round(total, 2),
            "confidence": confidence_value, "asset_light_bonus": round(asset_bonus, 2),
            "scoring_version": SCORE_VERSION, "score_id": score_id, "opportunity_id": oid}


def _required_evidence(kind: str, delivery: str | None) -> set[str]:
    common = {"CUSTOMER_NEED", "MARKET_DEMAND", "STARTUP_COST"}
    if kind == "AFFILIATE":
        return {"COMMISSION_RATE", "APPROVAL_REQUIREMENTS", "PAYMENT_TERMS", "TRAFFIC_REQUIREMENT",
                "EXPECTED_CONVERSION", "ESTIMATED_MARGIN"}
    if kind in {"SERVICE", "CONSULTING", "PARTNERSHIP", "PROCUREMENT"}:
        result = common | {"COMPETITION", "LEGAL_RESTRICTION"}
        if delivery in LOCAL_DELIVERY:
            result |= {"LOCAL_DEMAND", "REGULATORY_REQUIREMENT"}
        return result
    return common | {"COMPETITION", "ESTIMATED_MARGIN"}


def _assessment(row: sqlite3.Row, missing: list[str]) -> dict[str, Any]:
    title = str(row["title"])
    partner = bool(row["partner_fulfilled"])
    delivery = str(row["delivery_model"] or "UNSPECIFIED")
    cost = row["startup_cost_estimate"]
    estimated_cost: float | str = float(cost) if cost is not None else "UNKNOWN"
    return {
        "missing_evidence": missing,
        "30_days": {
            "goal": f"Validate the first evidence gaps for {title}",
            "expected_result": "Document source-backed customer, market, and operating assumptions.",
            "required_actions": ["Identify source evidence", "Confirm customer need",
                                 "List dependencies and any external approval boundary"],
            "estimated_cost": estimated_cost,
            "revenue_range": "UNKNOWN",
            "success_metric": f"{max(1, min(3, len(missing)))} priority evidence claims verified or explicitly unresolved",
        },
        "60_days": {
            "goal": "Validate unit economics and delivery feasibility",
            "expected_result": "Evidence-based cost, partner, regulatory, and acquisition assessment.",
            "required_actions": ["Verify startup and per-customer cost", "Confirm partner terms" if partner else "Confirm delivery requirements",
                                 "Assess customer acquisition and fulfillment constraints"],
            "estimated_cost": estimated_cost,
            "revenue_range": "UNKNOWN",
            "success_metric": "Documented contribution-margin inputs and delivery requirements",
        },
        "90_days": {
            "goal": "Decide whether a bounded experiment is justified",
            "expected_result": "A go/no-go recommendation with no unsupported revenue projection.",
            "required_actions": ["Compare evidence with investment and risk boundaries", "Prepare a bounded test only if justified"],
            "estimated_cost": estimated_cost,
            "revenue_range": "UNKNOWN",
            "success_metric": "Evidence-supported TEST, WATCH, RESEARCH_MORE, or REJECT recommendation",
        },
    }


def evaluate(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        row = _fetch_opportunity(con, oid)
        evidence = con.execute(
            "SELECT claim_type,evidence_quality,conflict_state FROM opportunity_evidence WHERE opportunity_id=?",
            (oid,),
        ).fetchall()
        reliable = {str(item["claim_type"]) for item in evidence
                    if str(item["evidence_quality"] or "").upper() in {"HIGH", "MEDIUM"}
                    and str(item["conflict_state"] or "").upper() not in {"CONFLICTING", "UNRESOLVED"}}
        missing = sorted(_required_evidence(str(row["opportunity_type"]), row["delivery_model"]) - reliable)
        previous = str(row["status"])
        state = "NEEDS_RESEARCH" if missing else "READY_TO_SCORE"
        recommendation = "RESEARCH_MORE" if missing else "VALIDATE"
        confidence = "LOW" if missing else "MEDIUM"
        plan = _assessment(row, missing)
        timestamp = now()
        con.execute(
            "UPDATE opportunities SET status=?,recommendation=?,confidence=?,assessment_json=?,updated_at=?,last_evaluated_at=? WHERE opportunity_id=?",
            (state, recommendation, confidence, _json(plan), timestamp, timestamp, oid),
        )
        if missing and str(row["delivery_model"] or "") in LOCAL_DELIVERY:
            risks = [
                {"risk_type": "LOCAL_MARKET_DEPENDENCY", "severity": "UNKNOWN",
                 "description": "Local demand and customer-acquisition evidence is not yet verified.",
                 "mitigation": "Request source-backed local demand and acquisition evidence."},
                {"risk_type": "REGULATORY", "severity": "UNKNOWN",
                 "description": "Applicable regulatory and insurance/documentation requirements need research.",
                 "mitigation": "Verify jurisdiction-specific requirements before any customer activity."},
            ]
            if bool(row["partner_fulfilled"]):
                risks.append({"risk_type": "PARTNER_DEPENDENCY", "severity": "UNKNOWN",
                              "description": "Partner capability, quality, pricing, and service-level terms are unverified.",
                              "mitigation": "Verify partner qualifications, capacity, costs, and customer ownership terms."})
            _add_risks(con, oid, risks)
        _history(con, oid, "EVALUATED", previous=previous, new=state,
                 reason="Evidence sufficiency evaluated; unknowns remain unknown.",
                 metadata={"missing_evidence": missing, "assessment": plan})
    return {"status": state, "recommendation": recommendation, "confidence": confidence,
            "missing_evidence": missing, "assessment": plan}


def attach_evidence(opportunity_id: str, evidence: dict[str, Any], *, database_path: str | Path | None = None) -> dict[str, Any]:
    claim_type = str(evidence.get("claim_type") or "").upper()
    quality = str(evidence.get("evidence_quality") or "UNKNOWN").upper()
    if claim_type not in CLAIM_TYPES:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_CLAIM_TYPE"}
    if quality not in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_EVIDENCE_QUALITY"}
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        source_id = None
        if any(evidence.get(key) for key in ("source_type", "source_name", "source_reference", "source_external_id")):
            source_id = _source(con, oid, evidence)
        evidence_id = "ev_" + uuid.uuid4().hex
        verified_at = _clean_text(evidence.get("verified_at"), 80) or (now() if evidence.get("verified_by") else None)
        con.execute(
            """INSERT INTO opportunity_evidence
            (evidence_id,opportunity_id,claim_type,claim,evidence_value,evidence_quality,source_id,
             verified_by,verified_at,expires_at,conflict_state)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (evidence_id, oid, claim_type, _clean_text(evidence.get("claim"), 1000) or None,
             _clean_text(evidence.get("evidence_value"), 3000) or None, quality, source_id,
             _clean_text(evidence.get("verified_by"), 160) or None, verified_at,
             _clean_text(evidence.get("expires_at"), 80) or None,
             _clean_text(evidence.get("conflict_state"), 80).upper() or "NONE"),
        )
        _history(con, oid, "EVIDENCE_ATTACHED", reason=f"{claim_type} evidence attached.",
                 metadata={"claim_type": claim_type, "evidence_quality": quality})
    return {"status": "ATTACHED", "evidence_id": evidence_id}


def update_state(opportunity_id: str, new_state: str, reason: str, *,
                 recommendation: str = "", database_path: str | Path | None = None) -> dict[str, Any]:
    state = str(new_state or "").upper()
    rec = str(recommendation or "").upper()
    if state not in STATUSES:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_STATE"}
    if rec and rec not in RECOMMENDATIONS:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_RECOMMENDATION"}
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        row = _fetch_opportunity(con, oid)
        previous = str(row["status"])
        if previous == state and (not rec or rec == row["recommendation"]):
            return {"status": state, "changed": False}
        timestamp = now()
        con.execute("UPDATE opportunities SET status=?,recommendation=coalesce(?,recommendation),updated_at=? WHERE opportunity_id=?",
                    (state, rec or None, timestamp, oid))
        _history(con, oid, "STATE_CHANGED", previous, state, reason,
                 {"recommendation": rec or row["recommendation"]})
    return {"status": state, "changed": True}



def accept_research_handoff(opportunity_id: str, handoff: dict[str, Any], *,
                            research_work_id: str = "",
                            database_path: str | Path | None = None) -> dict[str, Any]:
    """Validate and persist one condensed Research handoff on the same opportunity.

    The Research contract owns the required output list. Detailed evidence stays
    in Research's local authority; this function stores only the condensed
    package and an acceptance/rejection receipt in the existing opportunity DB.
    """
    from research.notebook_completion_contracts import BUSINESS_OPPORTUNITY_DELIVERABLES

    if not isinstance(handoff, dict) or len(_json(handoff).encode("utf-8")) > 24000:
        return {"status": "REJECTED", "reason": "BOUNDED_HANDOFF_OBJECT_REQUIRED"}
    if str(handoff.get("from_engine") or handoff.get("FROM_ENGINE") or "").upper() != "RESEARCH":
        return {"status": "REJECTED", "reason": "RESEARCH_SENDER_REQUIRED"}
    if str(handoff.get("to_engine") or handoff.get("TO_ENGINE") or "").upper() != "BUSINESS_OPPORTUNITIES":
        return {"status": "REJECTED", "reason": "BUSINESS_OPPORTUNITIES_RECEIVER_REQUIRED"}
    deliverables = handoff.get("deliverables") or handoff.get("DELIVERABLES") or {}
    if not isinstance(deliverables, dict):
        deliverables = {}
    missing: list[str] = []
    for field in BUSINESS_OPPORTUNITY_DELIVERABLES:
        value = deliverables.get(field)
        if not isinstance(value, dict):
            missing.append(field)
            continue
        state = str(value.get("status") or "").upper()
        summary = str(value.get("summary") or "").strip()
        if state == "COMPLETE":
            sources = value.get("sources")
            if not summary or not isinstance(sources, list) or not sources:
                missing.append(field)
        elif state == "EXTERNAL_BOUNDARY":
            required = ("boundary_type", "information_required", "why_public_research_cannot_resolve_it",
                        "decision_impact", "next_external_action")
            sources = value.get("sources_attempted")
            if any(not str(value.get(key) or "").strip() for key in required) or not isinstance(sources, list) or not sources:
                missing.append(field)
        else:
            missing.append(field)
    material_requirements = ("VIABLE_BUSINESS_MODELS", "TARGET_CUSTOMERS", "CUSTOMER_NEED",
        "MARKET_DEMAND", "COMPETITION", "COMPETITOR_PRICING", "PRICING_INPUTS",
        "STARTUP_COST_INPUTS", "OPERATING_COST_INPUTS", "PARTNERS_AND_SUPPLIERS",
        "REGULATORY_REQUIREMENTS", "LEGAL_RESTRICTIONS", "CUSTOMER_ACQUISITION_CHANNELS",
        "REFERRAL_CHANNELS", "TECHNOLOGY_REQUIREMENTS", "RISKS", "SOURCE_CONFIDENCE",
        "EXTERNAL_BOUNDARIES")
    for field in material_requirements:
        value = deliverables.get(field)
        if field not in missing and isinstance(value, dict) and value.get("status") not in {"COMPLETE", "EXTERNAL_BOUNDARY"}:
            missing.append(field)
    missing = sorted(set(missing))
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        row = _fetch_opportunity(con, oid)
        digest = hashlib.sha256(_json(handoff).encode("utf-8")).hexdigest()
        prior = con.execute("SELECT event_type,metadata_json FROM opportunity_history WHERE opportunity_id=? "
            "AND event_type IN ('RESEARCH_HANDOFF_ACCEPTED','RESEARCH_HANDOFF_REJECTED') ORDER BY created_at DESC",
            (oid,)).fetchall()
        for event in prior:
            try:
                metadata = json.loads(event["metadata_json"] or "{}")
            except ValueError:
                metadata = {}
            if metadata.get("handoff_sha256") == digest and metadata.get("research_work_id") == research_work_id:
                return {"status": event["event_type"].replace("RESEARCH_HANDOFF_", ""),
                    "already_recorded": True, "missing_requirements": metadata.get("missing_requirements", []),
                    "opportunity_title": row["title"]}
        accepted = not missing
        previous = str(row["status"])
        next_state = "UNDER_REVIEW" if accepted else previous
        compact = {key: handoff.get(key) for key in ("case_id", "summary_version", "executive_summary",
            "source_confidence", "evidence_quality", "local_detail_pointer", "evidence_count", "generated_at")}
        _history(con, oid, "RESEARCH_HANDOFF_ACCEPTED" if accepted else "RESEARCH_HANDOFF_REJECTED",
            previous, next_state, "Receiver-side validation of the current Research Deliverable Contract.",
            {"handoff_sha256": digest, "research_work_id": research_work_id,
             "missing_requirements": missing, "handoff_summary": compact,
             "accepted": accepted, "current_stage": "BUSINESS_OPPORTUNITIES" if accepted else "RESEARCH"})
        if accepted:
            con.execute("UPDATE opportunities SET status=?,updated_at=? WHERE opportunity_id=?",
                (next_state, now(), oid))
        return {"status": "ACCEPTED" if accepted else "REJECTED",
            "already_recorded": False, "opportunity_title": row["title"],
            "missing_requirements": missing, "current_stage": "BUSINESS_OPPORTUNITIES" if accepted else "RESEARCH",
            "research_work_id": research_work_id}

def request_research(opportunity_id: str, missing_evidence: list[str], *,
                     database_path: str | Path | None = None) -> dict[str, Any]:
    claims = sorted({str(value).upper() for value in missing_evidence})
    if not claims or len(claims) > 12 or not set(claims) <= CLAIM_TYPES:
        return {"status": "REJECTED", "reason": "SUPPORTED_MISSING_EVIDENCE_CLAIMS_REQUIRED"}
    db_path = _db_path(database_path)
    initialize(db_path)
    with _connect(db_path, readonly=True) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        row = _fetch_opportunity(con, oid)
        sources = con.execute(
            "SELECT source_external_id,metadata_json FROM opportunity_sources WHERE opportunity_id=? AND source_type='RESEARCH_R10'",
            (oid,),
        ).fetchall()
        for source in sources:
            try:
                metadata = json.loads(source["metadata_json"] or "{}")
            except ValueError:
                metadata = {}
            if set(metadata.get("requested_claims") or []) == set(claims):
                return {"status": "RESEARCH_PENDING", "already_requested": True,
                        "opportunity_title": row["title"]}
        title = str(row["title"])
        summary = str(row["summary"])
        delivery = str(row["delivery_model"] or "UNSPECIFIED")
        location = str(row["geographic_scope"] or "not specified")
    from research.notebook_completion_contracts import BUSINESS_OPPORTUNITY_DELIVERABLES
    deliverables = ", ".join(BUSINESS_OPPORTUNITY_DELIVERABLES)
    question = (
        f"Complete NEXUS_RESEARCH_DELIVERABLE_V1 for this same Nexus business opportunity: {title}. "
        f"Context: {summary}. Delivery: {delivery}; geography: {location}. "
        f"Investigate the named evidence gaps: {', '.join(claims)}. "
        f"Deliver all 25 fields: {deliverables}. "
        "Use the original source only as a starting point; pursue approved official/public/vendor/GitHub Remote sources. "
        "Cite URLs, dates, jurisdiction, source quality/confidence, alternatives, conflicts, and source attempts. "
        "Do not fabricate. Missing obtainable facts require same-assignment continuation, not terminal insufficiency. "
        "Mark a remaining unknown external only with the required outside actor/action and sources already attempted. "
        "No provider contact, signup, paid activation, spend, or unsupported revenue projection."
    )
    if len(question) > 1600:
        raise ValueError("RESEARCH_DELIVERABLE_REQUEST_EXCEEDS_EXISTING_ASSIGNMENT_BOUND")
    result = _request_research(title, question)
    if not isinstance(result, dict) or result.get("status") not in {"queued", "idempotent_existing"}:
        return {"status": "RESEARCH_REQUEST_FAILED", "reason": str((result or {}).get("error") or (result or {}).get("status") or "UNKNOWN")}
    objective_id = str(result.get("objective_id") or "")
    if not objective_id:
        return {"status": "RESEARCH_REQUEST_FAILED", "reason": "EXISTING_RESEARCH_INTERFACE_RETURNED_NO_OBJECTIVE_REFERENCE"}
    with _connect(db_path) as con:
        source_id = _source(con, oid, {"source_type": "RESEARCH_R10", "source_name": "Current Nexus Research MCP",
            "source_reference": "current Research R10 / Research MCP R5", "source_external_id": objective_id,
            "source_summary": question, "verification_state": "UNVERIFIED",
            "source_metadata": {"requested_claims": claims, "research_state": result.get("durable_job_state")}})
        previous = str(_fetch_opportunity(con, oid)["status"])
        con.execute("UPDATE opportunities SET status='RESEARCH_PENDING',recommendation='RESEARCH_MORE',updated_at=? WHERE opportunity_id=?",
                    (now(), oid))
        _history(con, oid, "RESEARCH_REQUESTED", previous, "RESEARCH_PENDING",
                 "Bounded missing-evidence request routed through the existing Nexus Research assignment interface.",
                 {"requested_claims": claims, "research_source_id": source_id})
    return {"status": "RESEARCH_PENDING", "already_requested": False, "opportunity_title": title,
            "requested_claims": claims}


def _request_research(objective: str, question: str) -> dict[str, Any]:
    # Call the current governed Nexus MCP Research assignment path. It owns the
    # existing Research queue and persists Research jobs through its authority.
    from services.nexus_mcp.server import _action_call, _assign_research
    return _action_call("nexus_assign_research", _assign_research, {
        "objective": objective, "question": question, "priority": 5,
        "parent_request_id": "", "followup_department": "", "requested_intent": "RESEARCH_MISSION",
    })


def evidence(opportunity_id: str, *, database_path: str | Path | None = None) -> list[dict[str, Any]]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return []
        rows = [dict(row) for row in con.execute(
            "SELECT claim_type,claim,evidence_value,evidence_quality,verified_by,verified_at,expires_at,conflict_state "
            "FROM opportunity_evidence WHERE opportunity_id=? ORDER BY claim_type,verified_at", (oid,))]
    return rows


def scorecard(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any] | None:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return None
        row = con.execute("SELECT * FROM opportunity_scores WHERE opportunity_id=? ORDER BY scored_at DESC LIMIT 1",
                          (oid,)).fetchone()
    if not row:
        return None
    value = dict(row)
    value.pop("opportunity_id", None)
    value.pop("score_id", None)
    value["assumptions"] = json.loads(value.pop("assumptions_json") or "{}")
    return value


def needs_research(limit: int = 20, *, database_path: str | Path | None = None) -> list[dict[str, Any]]:
    return list_opportunities(status="NEEDS_RESEARCH", limit=limit, database_path=database_path) + \
        list_opportunities(status="RESEARCH_PENDING", limit=limit, database_path=database_path)


def history(opportunity_id: str, limit: int = 50, *,
            database_path: str | Path | None = None) -> list[dict[str, Any]]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid = _resolve_id(con, opportunity_id)
        if not oid:
            return []
        rows = [dict(row) for row in con.execute(
            "SELECT event_type,previous_state,new_state,actor,reason,metadata_json,created_at "
            "FROM opportunity_history WHERE opportunity_id=? ORDER BY created_at DESC LIMIT ?",
            (oid, max(1, min(int(limit), 200))))]
    for row in rows:
        row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
    return rows


def health(*, database_path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(database_path)
    try:
        initialize(db_path)
        with _connect(db_path, readonly=True) as con:
            integrity = str(con.execute("PRAGMA quick_check").fetchone()[0])
            version = int(con.execute("PRAGMA user_version").fetchone()[0])
            count = int(con.execute("SELECT count(*) FROM opportunities").fetchone()[0])
            last_evaluation = con.execute("SELECT max(last_evaluated_at) FROM opportunities").fetchone()[0]
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        integrity, version, count, last_evaluation = "ERROR", None, None, None
        db_error = type(exc).__name__
    else:
        db_error = None
    adapter_status = "UNKNOWN"
    try:
        from scripts.opportunities.source_adapters.openaffiliate import health as openaffiliate_health
        adapter_status = openaffiliate_health()["status"]
    except Exception:
        adapter_status = "UNAVAILABLE"
    research_status = "UNKNOWN"
    try:
        from urllib.request import urlopen
        with urlopen("http://127.0.0.1:18766/health", timeout=2) as response:
            research_status = "PASS" if response.status == 200 else f"HTTP_{response.status}"
    except Exception as exc:
        research_status = f"UNAVAILABLE_{type(exc).__name__}"
    mcp_status = "UNKNOWN"
    try:
        from services.nexus_mcp.server import mcp
        names = {tool.name for tool in mcp._tool_manager.list_tools()}
        expected = {"opportunities_health", "opportunities_status", "opportunities_submit",
                    "opportunities_score", "opportunities_request_research"}
        mcp_status = "PASS" if expected <= names else "INCOMPLETE"
    except Exception:
        mcp_status = "UNAVAILABLE"
    return {"status": "PASS" if integrity == "ok" and version == SCHEMA_VERSION and mcp_status in {"PASS", "UNKNOWN"} else "DEGRADED",
            "sqlite_integrity": integrity, "schema_version": version, "record_count": count,
            "source_adapter_status": adapter_status, "research_interface_status": research_status,
            "nexus_mcp_exposure": mcp_status, "last_evaluation_at": last_evaluation,
            "database_path": str(db_path), "error_class": db_error}


# ---------------------------------------------------------------------------
# Commercial synthesis layer (additive).
#
# Business Opportunities owns commercial synthesis only. These builders derive
# unit economics, break-even, scenario, timing, low-capital-test, and the
# structured Marketing handoff from inputs that already exist on the same
# opportunity: the stored commercial inputs in revenue_details_json, the
# opportunity columns, reliable attached evidence, and recorded risks. They
# NEVER invent an unsupported number. When an input is absent the exact missing
# research input is named in MISSING_INPUTS and the output field stays UNKNOWN.
# Every assumed value carries an explicit label. No new table, queue, MCP,
# release, or Research cycle is involved; every call is read-only.
# ---------------------------------------------------------------------------

UNKNOWN = "UNKNOWN"

# Canonical commercial input keys accepted inside revenue_details_json. Plain
# keys are treated as supported; the same keys nested under "assumptions" are
# treated as explicitly assumed. Research-owned evidence values are a fallback.
_MISSING_RESEARCH_INPUT = {
    "SELLING_PRICE_OR_REVENUE_PER_CONVERSION": "Research PRICING_INPUTS / COMPETITOR_PRICING",
    "VARIABLE_COST_PER_UNIT_OR_CONVERSION": "Research OPERATING_COST_INPUTS",
    "AFFILIATE_COMMISSION_OR_REFERRAL_VALUE": "Research PRICING_INPUTS / AFFILIATE_RESELLER_WHITE_LABEL_OPTIONS",
    "CUSTOMER_ACQUISITION_COST_ASSUMPTION": "Research CUSTOMER_ACQUISITION_CHANNELS cost evidence",
    "ONGOING_FIXED_COST": "Research OPERATING_COST_INPUTS",
    "FIXED_STARTUP_COST": "Research STARTUP_COST_INPUTS",
    "CONVERSION_RATE": "Research EXPECTED_CONVERSION / market conversion evidence",
    "TRAFFIC_OR_LEADS": "Research CUSTOMER_ACQUISITION_CHANNELS demand/traffic evidence",
}

_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUM_RE.search(str(value).replace(",", ""))
    return float(match.group()) if match else None


def _as_rate(value: Any) -> float | None:
    """Normalise a conversion/margin value to a 0-1 fraction without inventing one."""
    number = _num(value)
    if number is None:
        return None
    if isinstance(value, str) and "%" in value:
        return number / 100.0
    return number / 100.0 if number > 1 else number


def _reliable_evidence(con: sqlite3.Connection, oid: str) -> dict[str, str]:
    rows = con.execute(
        "SELECT claim_type,evidence_value,evidence_quality,conflict_state "
        "FROM opportunity_evidence WHERE opportunity_id=?", (oid,)).fetchall()
    index: dict[str, str] = {}
    for row in rows:
        if str(row["evidence_quality"] or "").upper() in {"HIGH", "MEDIUM"} \
                and str(row["conflict_state"] or "").upper() not in {"CONFLICTING", "UNRESOLVED"} \
                and row["claim_type"] not in index:
            index[str(row["claim_type"])] = row["evidence_value"]
    return index


def _pick(details: dict[str, Any], evidence: dict[str, str], keys: list[str],
          *, ev_claim: str = "", rate: bool = False) -> tuple[float | None, str | None]:
    convert = _as_rate if rate else _num
    assumptions = details.get("assumptions") if isinstance(details.get("assumptions"), dict) else {}
    for source_label, store in (("DETAILS_SUPPORTED", details), ("DETAILS_ASSUMED", assumptions)):
        for key in keys:
            if key in store and store[key] not in (None, ""):
                value = convert(store[key])
                if value is not None:
                    return value, source_label
    if ev_claim and ev_claim in evidence:
        value = convert(evidence[ev_claim])
        if value is not None:
            return value, "EVIDENCE"
    return None, None


def _fmt(value: float | None, digits: int = 4) -> Any:
    return round(value, digits) if isinstance(value, (int, float)) else UNKNOWN


def _load(con: sqlite3.Connection, opportunity_id: str) -> tuple[str | None, sqlite3.Row | None, dict, dict]:
    oid = _resolve_id(con, opportunity_id)
    if not oid:
        return None, None, {}, {}
    row = _fetch_opportunity(con, oid)
    try:
        details = json.loads(row["revenue_details_json"] or "{}")
    except (ValueError, TypeError):
        details = {}
    if not isinstance(details, dict):
        details = {}
    return oid, row, details, _reliable_evidence(con, oid)


def _unit_economics(row: sqlite3.Row, details: dict, evidence: dict) -> dict[str, Any]:
    missing: list[str] = []
    assumptions: list[str] = []

    def record(field: str, value: float | None, label: str | None) -> float | None:
        if value is None:
            missing.append(f"{field} (needs {_MISSING_RESEARCH_INPUT.get(field, 'Research evidence')})")
        elif label in {"DETAILS_ASSUMED", "EVIDENCE"} or label == "DETAILS_SUPPORTED":
            assumptions.append(f"{field}={_fmt(value, 4)} [{label}]")
        return value

    price, p_src = _pick(details, evidence, ["selling_price", "price", "revenue_per_conversion", "average_revenue"])
    var, v_src = _pick(details, evidence, ["variable_cost_per_unit", "variable_cost"])
    commission, c_src = _pick(details, evidence, ["affiliate_commission", "referral_value", "commission"], ev_claim="COMMISSION_RATE")
    cac, cac_src = _pick(details, evidence, ["customer_acquisition_cost", "cac"])
    ongoing, o_src = _pick(details, evidence, ["ongoing_fixed_cost", "monthly_fixed_cost"])
    startup = row["startup_cost_estimate"]
    startup = float(startup) if startup is not None else None

    price = record("SELLING_PRICE_OR_REVENUE_PER_CONVERSION", price, p_src)
    var = record("VARIABLE_COST_PER_UNIT_OR_CONVERSION", var, v_src)
    if commission is not None:
        assumptions.append(f"AFFILIATE_COMMISSION_OR_REFERRAL_VALUE={_fmt(commission)} [{c_src}]")
    cac = record("CUSTOMER_ACQUISITION_COST_ASSUMPTION", cac, cac_src)
    if startup is None:
        missing.append(f"FIXED_STARTUP_COST (needs {_MISSING_RESEARCH_INPUT['FIXED_STARTUP_COST']})")
    else:
        assumptions.append(f"FIXED_STARTUP_COST={_fmt(startup)} [COLUMN]")
    ongoing = record("ONGOING_FIXED_COST", ongoing, o_src)

    gross_profit = price - var if price is not None and var is not None else None
    gross_margin = (gross_profit / price * 100.0) if gross_profit is not None and price else None
    if gross_margin is None:
        margin_ev, m_src = _pick(details, evidence, ["gross_margin_percent"], ev_claim="ESTIMATED_MARGIN")
        if margin_ev is not None:
            gross_margin = margin_ev
            assumptions.append(f"GROSS_MARGIN_PERCENT={_fmt(margin_ev, 2)} [{m_src}]")
    if gross_profit is not None and cac is not None:
        contribution = gross_profit - cac
        contribution_note = "gross_profit_minus_cac"
    elif gross_profit is not None:
        contribution = gross_profit
        contribution_note = "equals_gross_profit_cac_unknown"
    else:
        contribution = None
        contribution_note = "unavailable"

    return {
        "SELLING_PRICE_OR_REVENUE_PER_CONVERSION": _fmt(price),
        "VARIABLE_COST_PER_UNIT_OR_CONVERSION": _fmt(var),
        "GROSS_PROFIT_PER_UNIT_OR_CONVERSION": _fmt(gross_profit),
        "GROSS_MARGIN_PERCENT": _fmt(gross_margin, 2),
        "AFFILIATE_COMMISSION_OR_REFERRAL_VALUE": _fmt(commission),
        "CUSTOMER_ACQUISITION_COST_ASSUMPTION": _fmt(cac),
        "CONTRIBUTION_MARGIN": _fmt(contribution),
        "CONTRIBUTION_MARGIN_BASIS": contribution_note,
        "FIXED_STARTUP_COST": _fmt(startup),
        "ONGOING_FIXED_COST": _fmt(ongoing),
        "KEY_ASSUMPTIONS": assumptions,
        "MISSING_INPUTS": sorted(set(missing)),
        "_contribution": contribution,
        "_price": price,
        "_startup": startup,
        "_ongoing": ongoing,
    }


def _conversion_rate(details: dict, evidence: dict) -> tuple[float | None, str | None]:
    return _pick(details, evidence, ["conversion_rate"], ev_claim="EXPECTED_CONVERSION", rate=True)


def _scenario_calc(scenario: Any) -> dict[str, Any] | None:
    if not isinstance(scenario, dict):
        return None
    traffic = _num(scenario.get("traffic"))
    conv = _as_rate(scenario.get("conversion_rate"))
    avg = _num(scenario.get("average_revenue") if scenario.get("average_revenue") is not None
               else scenario.get("average_commission"))
    var = _num(scenario.get("variable_cost"))
    marketing = _num(scenario.get("marketing_cost"))
    label = "EVIDENCE_BACKED" if scenario.get("evidence_backed") else "ASSUMED"
    out: dict[str, Any] = {
        "ASSUMPTION_LABEL": label, "TRAFFIC": _fmt(traffic, 2), "CONVERSION_RATE": _fmt(conv, 6),
        "AVERAGE_REVENUE_OR_COMMISSION": _fmt(avg, 2), "VARIABLE_COST": _fmt(var, 2),
        "MARKETING_COST": _fmt(marketing, 2),
    }
    gaps = [name for name, value in (("TRAFFIC", traffic), ("CONVERSION_RATE", conv),
                                     ("AVERAGE_REVENUE_OR_COMMISSION", avg)) if value is None]
    if gaps:
        out.update({"EXPECTED_CONVERSIONS": UNKNOWN, "ESTIMATED_REVENUE": UNKNOWN,
                    "ESTIMATED_COST": UNKNOWN, "ESTIMATED_NET_RESULT": UNKNOWN, "MISSING_INPUTS": gaps})
        return out
    conversions = traffic * conv
    revenue = conversions * avg
    cost = conversions * (var or 0.0) + (marketing or 0.0)
    out.update({"EXPECTED_CONVERSIONS": round(conversions, 2), "ESTIMATED_REVENUE": round(revenue, 2),
                "ESTIMATED_COST": round(cost, 2), "ESTIMATED_NET_RESULT": round(revenue - cost, 2)})
    return out


def unit_economics(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        result = _unit_economics(row, details, evidence)
    return {key: value for key, value in result.items() if not key.startswith("_")}


def break_even(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    import math
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        econ = _unit_economics(row, details, evidence)
        contribution, price, startup, ongoing = econ["_contribution"], econ["_price"], econ["_startup"], econ["_ongoing"]
        conv, _ = _conversion_rate(details, evidence)
        missing = list(econ["MISSING_INPUTS"])
        be_units = be_revenue = be_traffic = UNKNOWN
        fixed_total = None
        if startup is not None:
            fixed_total = startup + (ongoing or 0.0)
        if fixed_total is not None and isinstance(contribution, (int, float)) and contribution > 0:
            units = math.ceil(fixed_total / contribution)
            be_units = units
            if price is not None:
                be_revenue = round(units * price, 2)
            if conv and conv > 0:
                be_traffic = math.ceil(units / conv)
            else:
                missing.append("TRAFFIC_OR_LEADS (needs Research EXPECTED_CONVERSION to convert units into required traffic)")
        elif isinstance(contribution, (int, float)) and contribution <= 0:
            missing.append("CONTRIBUTION_MARGIN is non-positive; break-even is not achievable at the supplied economics")

        scenarios_in = details.get("scenarios") if isinstance(details.get("scenarios"), dict) else {}
        scenario_out: dict[str, Any] = {}
        for name in ("downside", "base", "upside"):
            calc = _scenario_calc(scenarios_in.get(name))
            if calc is None:
                scenario_out[name.upper() + "_SCENARIO"] = {
                    "STATUS": UNKNOWN,
                    "NOTE": "Provide labeled scenario inputs (traffic, conversion_rate, average_revenue, "
                            "variable_cost, marketing_cost) or Research-supported rates; none fabricated.",
                }
            else:
                scenario_out[name.upper() + "_SCENARIO"] = calc
    return {
        "BREAK_EVEN_UNITS_OR_CONVERSIONS": be_units,
        "BREAK_EVEN_REVENUE": be_revenue,
        "BREAK_EVEN_TRAFFIC_OR_LEADS": be_traffic,
        "FIXED_COST_BASIS": _fmt(fixed_total, 2),
        "CONTRIBUTION_MARGIN": econ["CONTRIBUTION_MARGIN"],
        **scenario_out,
        "KEY_ASSUMPTIONS": econ["KEY_ASSUMPTIONS"],
        "MISSING_INPUTS": sorted(set(missing)),
        "DISCLAIMER": "Scenarios are labeled estimates, not guarantees.",
    }


def revenue_scenarios(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        plan = _assessment(row, sorted(json.loads(row["assessment_json"] or "{}").get("missing_evidence", []))
                           if row["assessment_json"] else [])
        base = details.get("scenarios", {}).get("base") if isinstance(details.get("scenarios"), dict) else None
        down = details.get("scenarios", {}).get("downside") if isinstance(details.get("scenarios"), dict) else None
        up = details.get("scenarios", {}).get("upside") if isinstance(details.get("scenarios"), dict) else None
        windows: dict[str, Any] = {}
        for days, months, key in ((30, 1, "30_DAY_REVENUE_SCENARIO"),
                                  (60, 2, "60_DAY_REVENUE_SCENARIO"),
                                  (90, 3, "90_DAY_REVENUE_SCENARIO")):
            block = plan.get(f"{days}_days", {})
            entry: dict[str, Any] = {
                "ASSUMPTIONS": [], "REQUIRED_ACTIONS": block.get("required_actions", []),
                "EXPECTED_TRAFFIC_OR_LEADS": UNKNOWN, "EXPECTED_CONVERSIONS": UNKNOWN,
                "REVENUE_RANGE": UNKNOWN, "EXPECTED_COST": UNKNOWN, "EXPECTED_NET_RESULT": UNKNOWN,
                "SUCCESS_METRIC": block.get("success_metric", UNKNOWN),
            }
            base_calc = _scenario_calc(
                {**base, "traffic": _num((base or {}).get("traffic")) * months} if base and _num((base or {}).get("traffic")) is not None else base)
            if base_calc and base_calc.get("ESTIMATED_REVENUE") != UNKNOWN:
                low = base_calc["ESTIMATED_REVENUE"]
                high = low
                for edge, mult in ((down, months), (up, months)):
                    edge_calc = _scenario_calc(
                        {**edge, "traffic": _num((edge or {}).get("traffic")) * mult} if edge and _num((edge or {}).get("traffic")) is not None else edge)
                    if edge_calc and edge_calc.get("ESTIMATED_REVENUE") != UNKNOWN:
                        low = min(low, edge_calc["ESTIMATED_REVENUE"])
                        high = max(high, edge_calc["ESTIMATED_REVENUE"])
                entry.update({
                    "ASSUMPTIONS": [f"base monthly inputs scaled x{months} [{base_calc['ASSUMPTION_LABEL']}]"],
                    "EXPECTED_TRAFFIC_OR_LEADS": base_calc["TRAFFIC"],
                    "EXPECTED_CONVERSIONS": base_calc["EXPECTED_CONVERSIONS"],
                    "REVENUE_RANGE": [round(low, 2), round(high, 2)],
                    "EXPECTED_COST": base_calc["ESTIMATED_COST"],
                    "EXPECTED_NET_RESULT": base_calc["ESTIMATED_NET_RESULT"],
                })
            else:
                entry["MISSING_INPUTS"] = ["Labeled base/downside/upside scenario inputs or Research-supported "
                                          "traffic + conversion + average revenue; no projection fabricated."]
            windows[key] = entry
    windows["DISCLAIMER"] = "Ranges are labeled estimates. UNKNOWN is returned where evidence is insufficient."
    return windows


def _dependency_lists(con: sqlite3.Connection, oid: str, details: dict) -> dict[str, list]:
    risks = con.execute("SELECT risk_type,description,requires_ray_approval FROM opportunity_risks "
                        "WHERE opportunity_id=?", (oid,)).fetchall()
    ray = [str(r["risk_type"]) for r in risks if int(r["requires_ray_approval"] or 0) == 1]
    ray += [str(x) for x in (details.get("ray_approvals") or [])]
    external = [str(r["risk_type"]) for r in risks
                if str(r["risk_type"]) in {"PARTNER_DEPENDENCY", "REGULATORY", "LOCAL_MARKET_DEPENDENCY", "LEGAL_COMPLIANCE"}]
    external += [str(x) for x in (details.get("external_dependencies") or [])]
    return {"ray": sorted(set(ray)), "external": sorted(set(external))}


def _range(value: Any) -> Any:
    if isinstance(value, dict) and "min" in value and "max" in value:
        return [_num(value["min"]), _num(value["max"])]
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return [_num(value[0]), _num(value[1])]
    number = _num(value)
    return [number, number] if number is not None else UNKNOWN


def time_to_launch(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        deps = _dependency_lists(con, oid, details)
    est = _range(details.get("time_to_launch_days"))
    requirements = [str(x) for x in (details.get("launch_requirements") or [])]
    assumptions = [f"{k}={v} [DETAILS_ASSUMED]" for k, v in (details.get("launch_assumptions") or {}).items()]
    return {
        "ESTIMATED_TIME_TO_LAUNCH": {"ESTIMATED_RANGE_DAYS": est,
                                     "NEXUS_CONTROLLED_WORK_DAYS": _range(details.get("nexus_launch_days")),
                                     "EXTERNAL_WAITING_DAYS": _range(details.get("external_wait_days"))},
        "MINIMUM_LAUNCH_REQUIREMENTS": requirements or ["UNKNOWN (needs Research TECHNOLOGY_REQUIREMENTS / "
                                                        "REGULATORY_REQUIREMENTS to enumerate launch prerequisites)"],
        "DEPENDENCIES": [str(x) for x in (details.get("dependencies") or [])] or deps["external"] or ["UNKNOWN"],
        "RAY_APPROVALS_REQUIRED": deps["ray"],
        "EXTERNAL_DEPENDENCIES": deps["external"] or ["NONE_RECORDED"],
        "ASSUMPTIONS": assumptions,
        "NOTE": "Nexus-controlled work and external waiting time are reported separately; estimate, not a commitment.",
    }


def time_to_first_revenue(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        deps = _dependency_lists(con, oid, details)
        column_days = row["time_to_first_revenue_days"]
    est = _range(details.get("time_to_first_revenue_days")) if details.get("time_to_first_revenue_days") is not None \
        else (_range(column_days) if column_days is not None else UNKNOWN)
    conv, _ = _conversion_rate(details, evidence)
    traffic_req = _num(details.get("required_traffic")) or (evidence.get("TRAFFIC_REQUIREMENT"))
    confidence = str(details.get("confidence") or row["confidence"] or "LOW").upper()
    missing = []
    if est == UNKNOWN:
        missing.append("ESTIMATED_TIME_TO_FIRST_REVENUE (needs time_to_first_revenue_days or Research demand/velocity evidence)")
    if traffic_req is None:
        missing.append("REQUIRED_TRAFFIC_OR_LEAD_EVENT (needs Research CUSTOMER_ACQUISITION_CHANNELS / EXPECTED_CONVERSION)")
    return {
        "ESTIMATED_TIME_TO_FIRST_REVENUE": {"ESTIMATED_RANGE_DAYS": est},
        "REQUIRED_TRAFFIC_OR_LEAD_EVENT": traffic_req if traffic_req is not None else UNKNOWN,
        "DEPENDENCIES": deps["external"] or ["NONE_RECORDED"],
        "ASSUMPTIONS": [f"conversion_rate={_fmt(conv, 6)}"] if conv is not None else [],
        "CONFIDENCE": confidence,
        "MISSING_INPUTS": missing,
        "NOTE": "This is an estimate, not a guarantee.",
    }


def low_capital_test(opportunity_id: str, *, database_path: str | Path | None = None) -> dict[str, Any]:
    """Organic-first bounded test. Preserves ORGANIC_FIRST -> PROVE_INTEREST ->
    SMALL_PAID_TEST_IF_JUSTIFIED -> SCALE_ONLY_WITH_EVIDENCE."""
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        be = break_even(oid, database_path=database_path)
    test = details.get("low_capital_test") if isinstance(details.get("low_capital_test"), dict) else {}
    traffic_target = test.get("traffic_target", be.get("BREAK_EVEN_TRAFFIC_OR_LEADS", UNKNOWN))
    conversion_target = test.get("conversion_target", be.get("BREAK_EVEN_UNITS_OR_CONVERSIONS", UNKNOWN))
    return {
        "OBJECTIVE": test.get("objective", f"Prove organic interest for {row['title']} before any paid spend"),
        "CASH_REQUIRED": test.get("cash_required", 0),
        "CASH_REQUIRED_BASIS": "ORGANIC_FIRST ($0 organic validation unless an input overrides)",
        "NEXUS_TIME_REQUIRED": test.get("nexus_time_required", "BOUNDED [ASSUMED]"),
        "ASSETS_REQUIRED": test.get("assets_required", ["Offer/landing surface", "Conversion tracking"]),
        "TRAFFIC_TARGET": traffic_target,
        "CONVERSION_TARGET": conversion_target,
        "SUCCESS_METRIC": test.get("success_metric", "Evidence of real interest at or above the break-even conversion signal"),
        "FAILURE_METRIC": test.get("failure_metric", "No qualified interest within the test window"),
        "TEST_DURATION": test.get("test_duration", "14-30 days [ASSUMED]"),
        "NEXT_ACTION_IF_SUCCESS": "SMALL_PAID_TEST_IF_JUSTIFIED within PAID_TEST_LIMIT",
        "NEXT_ACTION_IF_FAILURE": "REJECT or RESEARCH_MORE; do not scale",
        "PAID_TEST_LIMIT": test.get("paid_test_limit", UNKNOWN),
        "PHILOSOPHY": "ORGANIC_FIRST -> PROVE_INTEREST -> SMALL_PAID_TEST_IF_JUSTIFIED -> SCALE_ONLY_WITH_EVIDENCE",
    }


def commercial_synthesis(opportunity_id: str, *, database_path: str | Path | None = None,
                         include_internal_ids: bool = False) -> dict[str, Any]:
    """Consolidated commercial synthesis for one opportunity.

    Pure composition of the existing authoritative builders; performs no
    calculation of its own and fabricates nothing. Unknowns stay UNKNOWN and
    missing evidence stays named in MISSING_INPUTS.
    """
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
    econ = unit_economics(oid, database_path=database_path)
    be = break_even(oid, database_path=database_path)
    windows = revenue_scenarios(oid, database_path=database_path)
    ttl = time_to_launch(oid, database_path=database_path)
    ttfr = time_to_first_revenue(oid, database_path=database_path)
    test = low_capital_test(oid, database_path=database_path)

    missing: list[str] = []
    for part in (econ, be, ttfr):
        missing.extend(part.get("MISSING_INPUTS", []))
    for window in ("30_DAY_REVENUE_SCENARIO", "60_DAY_REVENUE_SCENARIO", "90_DAY_REVENUE_SCENARIO"):
        missing.extend(windows.get(window, {}).get("MISSING_INPUTS", []))

    package = {
        "OPPORTUNITY_ID": oid,
        "MONETIZATION_MODEL": {
            "RECOMMENDED_MONETIZATION_MODEL": row["revenue_model"] or UNKNOWN,
            "ALTERNATIVE_MONETIZATION_MODELS": details.get("alternative_models", []),
        },
        "UNIT_ECONOMICS": econ,
        "BREAK_EVEN_MODEL": {k: be[k] for k in ("BREAK_EVEN_UNITS_OR_CONVERSIONS", "BREAK_EVEN_REVENUE",
                                                "BREAK_EVEN_TRAFFIC_OR_LEADS", "FIXED_COST_BASIS")},
        "DOWNSIDE_BASE_UPSIDE_SCENARIOS": {k: be[k] for k in ("DOWNSIDE_SCENARIO", "BASE_SCENARIO", "UPSIDE_SCENARIO")},
        "30_DAY_REVENUE_SCENARIO": windows["30_DAY_REVENUE_SCENARIO"],
        "60_DAY_REVENUE_SCENARIO": windows["60_DAY_REVENUE_SCENARIO"],
        "90_DAY_REVENUE_SCENARIO": windows["90_DAY_REVENUE_SCENARIO"],
        "ESTIMATED_TIME_TO_LAUNCH": ttl["ESTIMATED_TIME_TO_LAUNCH"],
        "ESTIMATED_TIME_TO_FIRST_REVENUE": ttfr["ESTIMATED_TIME_TO_FIRST_REVENUE"],
        "LOW_CAPITAL_TEST": test,
        "COMMERCIAL_RECOMMENDATION": row["recommendation"] or "RESEARCH_MORE",
        "MISSING_INPUTS": sorted(set(missing)),
        "EXTERNAL_BOUNDARIES": ttl["EXTERNAL_DEPENDENCIES"],
    }
    return _public(package, include_internal_ids=include_internal_ids)


def marketing_handoff(opportunity_id: str, *, database_path: str | Path | None = None,
                      include_internal_ids: bool = True) -> dict[str, Any]:
    """Condensed cross-engine Business Opportunities -> Marketing package.

    Local SQLite stays authoritative; this is a coordination package only. No raw
    Research evidence, transcript, large source content, retry history, or detailed
    intermediate calculation is included, and nothing is written to Supabase.
    """
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        oid, row, details, evidence = _load(con, opportunity_id)
        if not oid:
            return {"status": "NOT_FOUND"}
        deps = _dependency_lists(con, oid, details)
    econ = unit_economics(oid, database_path=database_path)
    be = break_even(oid, database_path=database_path)
    windows = revenue_scenarios(oid, database_path=database_path)
    ttl = time_to_launch(oid, database_path=database_path)
    ttfr = time_to_first_revenue(oid, database_path=database_path)
    test = low_capital_test(oid, database_path=database_path)

    missing: list[str] = []
    for part in (econ, be, ttfr):
        missing.extend(part.get("MISSING_INPUTS", []))
    for window in ("30_DAY_REVENUE_SCENARIO", "60_DAY_REVENUE_SCENARIO", "90_DAY_REVENUE_SCENARIO"):
        missing.extend(windows.get(window, {}).get("MISSING_INPUTS", []))

    package = {
        "OPPORTUNITY_ID": oid,
        "WHAT_WE_ARE_MONETIZING": row["title"],
        "WHY_NOW": details.get("why_now", UNKNOWN),
        "TARGET_CUSTOMER": row["target_customer"] or UNKNOWN,
        "CUSTOMER_NEED": details.get("customer_need", UNKNOWN),
        "VALUE_PROPOSITION": details.get("value_proposition", UNKNOWN),
        "RECOMMENDED_MONETIZATION_MODEL": row["revenue_model"] or UNKNOWN,
        "ALTERNATIVE_MONETIZATION_MODELS": details.get("alternative_models", []),
        "PRODUCT_SERVICE_PRICE": econ.get("SELLING_PRICE_OR_REVENUE_PER_CONVERSION", UNKNOWN),
        "UNIT_ECONOMICS": econ,
        "BREAK_EVEN_MODEL": {k: be[k] for k in ("BREAK_EVEN_UNITS_OR_CONVERSIONS", "BREAK_EVEN_REVENUE",
                                                "BREAK_EVEN_TRAFFIC_OR_LEADS", "FIXED_COST_BASIS")},
        "DOWNSIDE_BASE_UPSIDE_SCENARIOS": {k: be[k] for k in ("DOWNSIDE_SCENARIO", "BASE_SCENARIO", "UPSIDE_SCENARIO")},
        "30_DAY_REVENUE_SCENARIO": windows["30_DAY_REVENUE_SCENARIO"],
        "60_DAY_REVENUE_SCENARIO": windows["60_DAY_REVENUE_SCENARIO"],
        "90_DAY_REVENUE_SCENARIO": windows["90_DAY_REVENUE_SCENARIO"],
        "ESTIMATED_TIME_TO_LAUNCH": ttl["ESTIMATED_TIME_TO_LAUNCH"],
        "ESTIMATED_TIME_TO_FIRST_REVENUE": ttfr["ESTIMATED_TIME_TO_FIRST_REVENUE"],
        "BRAND_FUNDED_DEMAND": details.get("brand_funded_demand", UNKNOWN),
        "PRIMARY_CHANNEL_OPPORTUNITIES": details.get("channels", []),
        "LOW_CAPITAL_TEST": test,
        "PAID_TEST_LIMIT": test.get("PAID_TEST_LIMIT", UNKNOWN),
        "MARKETING_REQUIREMENTS": details.get("marketing_requirements", ["TBD by Marketing engine"]),
        "CREATIVE_REQUIREMENTS": details.get("creative_requirements", ["TBD by Marketing engine"]),
        "PRIMARY_RISKS": [str(x) for x in (details.get("primary_risks") or [])] or deps["external"],
        "EXTERNAL_BOUNDARIES": ttl["EXTERNAL_DEPENDENCIES"],
        "MISSING_INPUTS": sorted(set(missing)),
        "COMMERCIAL_RECOMMENDATION": row["recommendation"] or "RESEARCH_MORE",
        "LOCAL_SQLITE_IS_AUTHORITATIVE": "YES",
        "SUPABASE_IS_COORDINATION_LAYER": "YES",
        "RAW_RESEARCH_SENT_TO_SUPABASE": "NO",
        "HANDOFF_READY": not missing,
        "GENERATED_AT": now(),
    }
    return _public(package, include_internal_ids=include_internal_ids)

