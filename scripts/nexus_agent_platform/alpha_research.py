"""Governed, evidence-first Alpha research intelligence.

This module extends the existing Alpha advisor with a bounded research-job
contract.  It consumes canonical Nexus evidence artifacts; it does not fetch
the web, call Modal, write work orders, or make consequential decisions.
Those capabilities remain behind their existing Nexus adapters and authority
gates.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from nexus_agent_platform.evidence_ingestion import DEFAULT_HANDOFF, DEFAULT_RECEIPTS, DEFAULT_RUNTIME as DEFAULT_EVIDENCE_RUNTIME, normalize_text

SCHEMA_VERSION = "nexus.alpha-research-job.v1"
PACK_SCHEMA_VERSION = "nexus.alpha-research-pack.v1"
RECEIPT_SCHEMA_VERSION = "nexus.alpha-research-receipt.v1"
DEFAULT_RUNTIME = Path(__file__).resolve().parents[2] / "data/runtime/alpha_research"
DEFAULT_REPORTS = Path(__file__).resolve().parents[2] / "reports/runtime/alpha_research"

RESEARCH_TYPES = {
    "MARKET_RESEARCH", "COMPETITOR_RESEARCH", "BUSINESS_OPPORTUNITY_RESEARCH",
    "AFFILIATE_RESEARCH", "FUNDING_PROGRAM_RESEARCH", "GRANT_RESEARCH",
    "SEO_RESEARCH", "PRODUCT_SERVICE_RESEARCH", "PRICING_RESEARCH",
    "TECHNOLOGY_RESEARCH", "OPEN_SOURCE_RESEARCH", "INDUSTRY_TREND_RESEARCH",
    "CONTENT_RESEARCH", "TRADING_RESEARCH",
}
STATUSES = {"COMPLETE", "PARTIAL", "INSUFFICIENT_EVIDENCE", "BLOCKED", "FAILED"}
FRESHNESS = {"CURRENT", "AGING", "STALE", "UNKNOWN"}
QUALITY = {"PRIMARY", "AUTHORITATIVE", "HIGH_QUALITY_SECONDARY", "SECONDARY", "COMMUNITY", "UNVERIFIED"}

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"(?i)\b(?:ssn|social security|credit report|bank account|routing number)\b"),
    re.compile(r"(?i)\b(?:client vault|private client communication|credit application record)\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]"),
    re.compile(r"(?i)(?:runtime\.env|\.env|supabase service key|stripe secret)"),
)


class AlphaResearchError(ValueError):
    """Expected, safe-to-display research contract failure."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _contains_sensitive(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, ensure_ascii=True) if not isinstance(value, str) else value
    return any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS)


def _limits(value: Optional[dict]) -> dict:
    source = dict(value or {})
    result = {
        "max_sources": min(max(int(source.get("max_sources", 10)), 1), 25),
        "max_evidence_jobs": min(max(int(source.get("max_evidence_jobs", 5)), 0), 10),
        "max_model_calls": min(max(int(source.get("max_model_calls", 8)), 0), 20),
        "max_runtime_seconds": min(max(int(source.get("max_runtime_seconds", 120)), 1), 600),
        "max_output_chars": min(max(int(source.get("max_output_chars", 100_000)), 1_000), 500_000),
    }
    return result


def build_research_job(*, objective: str, research_type: str = "MARKET_RESEARCH",
                       business_context: Optional[dict] = None, scope: Optional[dict] = None,
                       source_policy: Optional[dict] = None, freshness_requirement: str = "CURRENT",
                       limits: Optional[dict] = None, requested_by: str = "ray",
                       tenant_context: Optional[dict] = None, job_id: Optional[str] = None) -> dict:
    job = {
        "schema_version": SCHEMA_VERSION,
        "research_job_id": job_id or _id("alpha-research"),
        "objective": normalize_text(str(objective or "")),
        "research_type": str(research_type or "").upper(),
        "business_context": business_context or {"scope": "public_business_context"},
        "scope": scope or {},
        "constraints": {"consequential_action": False, "pii_allowed": False, "external_publish": False},
        "source_policy": source_policy or {"public_only": True, "evidence_first": True},
        "freshness_requirement": str(freshness_requirement or "CURRENT").upper(),
        "limits": _limits(limits),
        "cost_budget": {"model_calls": _limits(limits)["max_model_calls"], "remote_cpu_jobs": _limits(limits)["max_evidence_jobs"]},
        "requested_by": requested_by,
        "tenant_context": tenant_context or {"scope": "founder_admin", "tenant_id": None},
        "created_at": _now(),
    }
    validate_research_job(job)
    return job


def validate_research_job(job: dict) -> tuple[bool, str]:
    if not isinstance(job, dict) or job.get("schema_version") != SCHEMA_VERSION:
        raise AlphaResearchError("unsupported-research-job-schema")
    if not isinstance(job.get("objective"), str) or len(job["objective"].strip()) < 8:
        raise AlphaResearchError("missing-research-objective")
    if not isinstance(job.get("research_job_id"), str) or not job["research_job_id"]:
        raise AlphaResearchError("missing-research-job-id")
    if job.get("research_type") not in RESEARCH_TYPES:
        raise AlphaResearchError("unsupported-research-type")
    if job.get("freshness_requirement") not in FRESHNESS:
        raise AlphaResearchError("unsupported-freshness-requirement")
    if not isinstance(job.get("tenant_context"), dict):
        raise AlphaResearchError("missing-tenant-context")
    if _contains_sensitive({"objective": job["objective"], "scope": job.get("scope"), "business_context": job.get("business_context")}):
        raise AlphaResearchError("SAFETY_BLOCKED: sensitive-client-context")
    limits = job.get("limits")
    if not isinstance(limits, dict) or not 1 <= int(limits.get("max_sources", 0)) <= 25:
        raise AlphaResearchError("invalid-source-limit")
    return True, "ok"


def build_research_plan(job: dict) -> dict:
    validate_research_job(job)
    objective = job["objective"]
    return {
        "research_job_id": job["research_job_id"],
        "objective": objective,
        "key_questions": [
            f"What public evidence directly answers: {objective}?",
            "Which claims are corroborated, disputed, or still unknown?",
            "What is the evidence freshness and source quality?",
        ],
        "source_classes": ["official/public primary sources", "canonical Nexus evidence", "high-quality secondary sources"],
        "freshness_requirement": job["freshness_requirement"],
        "stopping_conditions": ["questions answered with bounded evidence", "source limit reached", "remaining gap cannot be safely resolved"],
        "limits": job["limits"],
    }


def _freshness(item: dict, requirement: str) -> str:
    value = (item.get("freshness") or item.get("source", {}).get("freshness") or "UNKNOWN").upper()
    if value in FRESHNESS:
        return value
    retrieved = item.get("source", {}).get("retrieved_at")
    if not retrieved:
        return "UNKNOWN"
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(retrieved.replace("Z", "+00:00"))).total_seconds()
        return "CURRENT" if age <= 7 * 86400 else ("AGING" if age <= 30 * 86400 else "STALE")
    except (TypeError, ValueError):
        return "UNKNOWN"


def _source_record(evidence: dict, *, quality: str = "UNVERIFIED") -> dict:
    source = evidence.get("source") or {}
    integrity = evidence.get("integrity") or {}
    return {
        "evidence_id": evidence.get("evidence_id"),
        "source_type": source.get("source_type"),
        "reference": source.get("final_url") or source.get("original_reference") or source.get("requested_url"),
        "title": (evidence.get("content") or {}).get("title"),
        "source_hash": integrity.get("source_hash"),
        "material_hash": integrity.get("material_hash"),
        "quality": quality if quality in QUALITY else "UNVERIFIED",
        "retrieved_at": source.get("retrieved_at") or (evidence.get("execution") or {}).get("completed_at"),
        "freshness": _freshness(evidence, "CURRENT"),
        "provenance": source.get("provenance", {}),
    }


def _claim(spec: dict, evidence_by_id: dict, freshness_requirement: str) -> dict:
    refs = list(dict.fromkeys(spec.get("evidence_refs") or []))
    if not refs or any(ref not in evidence_by_id for ref in refs):
        return {**spec, "confidence": "UNSUPPORTED", "evidence_refs": refs, "status": "UNSUPPORTED"}
    confidence = str(spec.get("confidence", "MEDIUM")).upper()
    if confidence not in {"HIGH", "MEDIUM", "LOW", "UNSUPPORTED"}:
        confidence = "LOW"
    freshness = [evidence_by_id[ref]["freshness"] for ref in refs]
    if freshness_requirement == "CURRENT" and all(value == "STALE" for value in freshness):
        confidence = "LOW"
    return {"claim": normalize_text(str(spec.get("claim", ""))), "claim_type": spec.get("claim_type", "DERIVED_ANALYSIS"), "confidence": confidence, "evidence_refs": refs, "source_count": len(refs), "source_quality": spec.get("source_quality", "UNVERIFIED"), "freshness": freshness, "contradictions": spec.get("contradictions", []), "notes": spec.get("notes", ""), "status": "SUPPORTED" if spec.get("claim") else "UNSUPPORTED"}


def run_alpha_research(job: dict, evidence: Iterable[dict], *, claim_specs: Optional[Iterable[dict]] = None,
                       opportunities: Optional[Iterable[dict]] = None, risks: Optional[Iterable[str]] = None,
                       unknowns: Optional[Iterable[str]] = None, contradictions: Optional[Iterable[dict]] = None,
                       cost_usage: Optional[dict] = None, runtime_root: Optional[Path] = None) -> dict:
    validate_research_job(job)
    started = _now()
    evidence_list = list(evidence)
    limit = job["limits"]["max_sources"]
    if len(evidence_list) > limit:
        evidence_list = evidence_list[:limit]
    valid_evidence = [item for item in evidence_list if isinstance(item, dict) and item.get("schema_version") == "nexus.evidence.v1" and item.get("status") in {"SUCCESS", "DUPLICATE", "NO_CHANGE"}]
    if len(valid_evidence) != len(evidence_list):
        status = "PARTIAL" if valid_evidence else "INSUFFICIENT_EVIDENCE"
    else:
        status = "COMPLETE" if valid_evidence else "INSUFFICIENT_EVIDENCE"
    source_rows = [_source_record(item) for item in valid_evidence]
    evidence_by_id = {row["evidence_id"]: row for row in source_rows if row.get("evidence_id")}
    claims = [_claim(spec, evidence_by_id, job["freshness_requirement"]) for spec in (claim_specs or [])]
    supported = [item for item in claims if item.get("status") == "SUPPORTED"]
    if claims and not supported:
        status = "INSUFFICIENT_EVIDENCE"
    elif claims and len(supported) < len(claims):
        status = "PARTIAL"
    pack = {
        "schema_version": PACK_SCHEMA_VERSION, "research_job_id": job["research_job_id"], "objective": job["objective"], "status": status,
        "executive_summary": f"Bounded Alpha research completed with {len(valid_evidence)} accepted evidence source(s) and {len(supported)} supported claim(s).",
        "plan": build_research_plan(job), "findings": supported, "claims": claims,
        "opportunities": [{**item, "execution_status": "NOT_EXECUTED", "advisory": True} for item in (opportunities or [])],
        "risks": list(risks or []), "unknowns": list(unknowns or []), "contradictions": list(contradictions or []),
        "sources": source_rows, "evidence_refs": [row["evidence_id"] for row in source_rows],
        "freshness": {"requirement": job["freshness_requirement"], "sources": [row["freshness"] for row in source_rows]},
        "cost_usage": cost_usage or {"classification": "UNKNOWN", "model_calls": 0, "remote_cpu_jobs": 0}, "created_at": _now(),
    }
    report = render_report(pack)
    report_hash = hashlib.sha256(report.encode("utf-8")).hexdigest()
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION, "receipt_id": _id("alpha-receipt"), "research_job_id": job["research_job_id"],
        "objective": job["objective"], "status": status, "started_at": started, "completed_at": _now(),
        "source_count": len(source_rows), "evidence_count": len(evidence_by_id), "model_usage": pack["cost_usage"],
        "remote_worker_usage": {"jobs": pack["cost_usage"].get("remote_cpu_jobs", 0)}, "research_pack_ref": f"alpha-pack:{job['research_job_id']}",
        "report_ref": f"alpha-report:{report_hash}", "opportunity_candidate_count": len(pack["opportunities"]), "error_classification": None if status in {"COMPLETE", "PARTIAL"} else status,
    }
    root = runtime_root or DEFAULT_RUNTIME
    reports = (root / "reports") if runtime_root else DEFAULT_REPORTS
    root.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    (root / f"{job['research_job_id']}.json").write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (reports / f"{job['research_job_id']}.md").write_text(report, encoding="utf-8")
    (root / f"{job['research_job_id']}.receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    heartbeat = {"capability": "alpha_research", "status": "HEALTHY" if status in {"COMPLETE", "PARTIAL"} else "DEGRADED", "last_run": receipt["completed_at"], "last_success": receipt["completed_at"] if status in {"COMPLETE", "PARTIAL"} else None, "last_result": status, "research_job_id": job["research_job_id"], "receipt_id": receipt["receipt_id"], "source_count": len(source_rows), "evidence_count": len(evidence_by_id), "browser_evidence_used": bool(pack["cost_usage"].get("remote_cpu_jobs")), "freshness": pack["freshness"], "optional": True, "core_health_dependency": False, "consequential_action_performed": False, "updated_at": _now()}
    heartbeat_path = Path(__file__).resolve().parents[2] / "reports/runtime/nexus_alpha_research_heartbeat_latest.json"
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True); heartbeat_path.write_text(json.dumps(heartbeat, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"job": job, "plan": pack["plan"], "pack": pack, "report": report, "receipt": receipt, "heartbeat": heartbeat}


def run_alpha_browser_research(*, objective: str, research_type: str, url: str,
                               requested_by: str = "ray", tenant_context: Optional[dict] = None,
                               claim: Optional[str] = None, provider: Any = None,
                               runtime_root: Optional[Path] = None) -> dict:
    """Run one bounded Alpha job from Nexus-accepted browser evidence."""
    from nexus_agent_platform.alpha_evidence_bridge import request_research_evidence

    job = build_research_job(objective=objective, research_type=research_type, requested_by=requested_by, tenant_context=tenant_context)
    evidence_root = (runtime_root / "evidence") if runtime_root else None
    acquired = request_research_evidence(
        url=url, job_id=job["research_job_id"], tenant_context=job["tenant_context"],
        limits={"timeout_seconds": job["limits"]["max_runtime_seconds"]}, provider=provider,
        root=evidence_root or DEFAULT_EVIDENCE_RUNTIME,
        receipt_dir=(evidence_root / "receipts") if evidence_root else DEFAULT_RECEIPTS,
        handoff=(evidence_root / "intake_events.jsonl") if evidence_root else DEFAULT_HANDOFF,
    )
    if acquired.get("status") not in {"SUCCESS", "DUPLICATE", "NO_CHANGE"}:
        return {"job": job, "status": acquired.get("status", "DEPENDENCY_UNAVAILABLE"), "remote_result": acquired.get("remote_result"), "heartbeat": status_from_runtime()}
    item = acquired["evidence"]
    canonical = {
        "schema_version": "nexus.evidence.v1", "evidence_id": item["evidence_id"], "job_id": job["research_job_id"],
        "status": item["status"], "source": {"source_type": item["source_type"], "original_reference": item["original_source"], "retrieved_at": item["retrieved_at"]},
        "integrity": {"material_hash": item["material_hash"], "source_hash": item.get("source_hash")},
        "content": {"normalized_text_or_markdown": item["text"]},
    }
    claim_specs = [{"claim": claim or item["text"][:500], "claim_type": "DIRECT_EVIDENCE", "confidence": "MEDIUM", "evidence_refs": [item["evidence_id"]], "source_quality": "UNVERIFIED"}]
    result = run_alpha_research(job, [canonical], claim_specs=claim_specs, cost_usage={"classification": "UNKNOWN", "model_calls": 0, "remote_cpu_jobs": 1}, runtime_root=runtime_root)
    result["bridge"] = {"status": acquired["status"], "artifact_ref": item["artifact_ref"], "original_source": item["original_source"]}
    return result


def render_report(pack: dict) -> str:
    lines = [f"# Alpha Research Report\n", f"**Objective:** {pack['objective']}", f"**Status:** {pack['status']}", "", "## Executive Summary", pack["executive_summary"], "", "## Key Findings"]
    lines += [f"- {row['claim']} ({row['confidence']}; evidence: {', '.join(row['evidence_refs'])})" for row in pack["findings"]] or ["- No supported findings; evidence is insufficient."]
    lines += ["", "## Opportunities"] + [f"- {row.get('opportunity_title', row.get('title', 'Candidate'))} — advisory only; execution status: NOT_EXECUTED" for row in pack["opportunities"]]
    lines += ["", "## Risks", *[f"- {row}" for row in pack["risks"]], "", "## Unknowns", *[f"- {row}" for row in pack["unknowns"]], "", "## Contradictions", *[f"- {row}" for row in pack["contradictions"]], "", "## Sources"]
    lines += [f"- {row.get('title') or row.get('reference')} — {row.get('reference')} ({row.get('quality')}, {row.get('freshness')})" for row in pack["sources"]] or ["- None"]
    lines += ["", "## Research Limits", "Bounded public-evidence research. Recommendations are advisory; no external action was executed."]
    return "\n".join(lines) + "\n"


def status_from_runtime(path: Optional[Path] = None) -> dict:
    path = path or (Path(__file__).resolve().parents[2] / "reports/runtime/nexus_alpha_research_heartbeat_latest.json")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "NOT_ENABLED", "reason": "No Alpha research heartbeat recorded", "optional": True, "core_health_dependency": False}
    return {"status": str(value.get("status", "UNKNOWN")).upper(), "last_updated": value.get("updated_at") or value.get("last_run"), "last_result": value.get("last_result"), "last_research_job": value.get("research_job_id"), "source_count": value.get("source_count", 0), "evidence_count": value.get("evidence_count", 0), "freshness": value.get("freshness", {}), "optional": True, "core_health_dependency": False}
