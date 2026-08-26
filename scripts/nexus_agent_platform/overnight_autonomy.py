"""Bounded overnight autonomy contracts for Hermes and Executive Portfolio.

This module is deliberately deterministic.  It records decision facts and
evidence references, never hidden reasoning, and has no production, outreach,
trading, shell, or approval authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from nexus_agent_platform.phase15.common import ROOT, atomic_write_json, utc_now

OVERNIGHT_ID = "NEXUS_OVERNIGHT_2026_08_25"
CAMPAIGN_PATH = ROOT / "data/runtime/nexus_overnight_campaign.json"
TRACE_DIR = ROOT / "reports/runtime/hermes_decision_traces"
IDEA_PATH = ROOT / "data/runtime/hermes_idea_inbox.jsonl"
NOTIFIER_PATH = ROOT / "data/runtime/hermes_true_gate_notifications.jsonl"
CERT_DIR = ROOT / "reports/certification"

MODEL_REGISTRY = {
    "DETERMINISTIC_LOCAL": {"provider": "local", "model": "rules", "enabled": True},
    "PRIMARY_REASONER": {"provider": "configured_primary", "model": "UNKNOWN", "enabled": False},
    "RESEARCH_REASONER": {"provider": "alpha", "model": "existing_alpha_path", "enabled": True},
    "INTEGRITY_CRITIC": {"provider": "configured_critic", "model": "UNKNOWN", "enabled": False},
    "CODING_WORKER": {"provider": "existing_builder", "model": "Codex", "enabled": True},
    "FALLBACK_REASONER": {"provider": "local", "model": "rules", "enabled": True},
}


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def record_decision_trace(*, surface: str, message: str, intent: str, goal: str,
                          authority_result: str, evidence_sources: Iterable[str] = (),
                          reasoning_mode: str = "DETERMINISTIC_LOCAL",
                          model_route: str = "DETERMINISTIC_LOCAL",
                          specialist_route: str = "NONE", approval_required: bool = False,
                          approval_id: str | None = None, human_gate_type: str = "NONE",
                          executor: str = "NONE", verification_status: str = "NOT_RUN",
                          final_status: str = "RECORDED", ray_action_required: str = "NONE") -> Dict[str, Any]:
    trace = {
        "trace_id": f"hermes_trace_{_fingerprint((surface, message, utc_now()))}",
        "timestamp": utc_now(), "surface": surface,
        "input_fingerprint": _fingerprint(message), "intent": intent, "goal": goal,
        "authority_result": authority_result, "evidence_sources": list(evidence_sources),
        "evidence_freshness": "READ_AT_TRACE_TIME", "reasoning_mode": reasoning_mode,
        "model_route": model_route, "specialist_route": specialist_route,
        "critic_triggered": False, "critic_result_ref": None,
        "approval_required": approval_required, "approval_id": approval_id,
        "human_gate_type": human_gate_type, "executor": executor,
        "execution_receipt": None, "verification_status": verification_status,
        "final_status": final_status, "ray_action_required": ray_action_required,
    }
    path = TRACE_DIR / f"{trace['trace_id']}.json"
    atomic_write_json(path, trace)
    return trace


def route_model(task_type: str, *, sensitivity: str = "internal", need_dissent: bool = False,
                changed: bool = False) -> Dict[str, Any]:
    task = task_type.lower()
    if not changed and task in {"status", "approvals", "runtime_truth", "portfolio"}:
        role = "DETERMINISTIC_LOCAL"
    elif task in {"implementation", "repair", "source"}:
        role = "CODING_WORKER"
    elif task in {"research", "forex", "creative_research"}:
        role = "RESEARCH_REASONER"
    elif need_dissent:
        role = "INTEGRITY_CRITIC"
    else:
        role = "PRIMARY_REASONER"
    return {"role": role, **MODEL_REGISTRY[role], "reason": "deterministic-first bounded route", "sensitivity": sensitivity,
            "critic_action_authority": "NONE" if role == "INTEGRITY_CRITIC" else "NOT_APPLICABLE"}


def integrity_critic_review(summary: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a local structured critic fixture; no external model is invoked."""
    text = json.dumps(summary, sort_keys=True, default=str)
    forbidden = re.compile(r"token|secret|password|api[_ -]?key|client[_ -]?(?:name|email|ssn)|runtime\.env", re.I)
    if forbidden.search(text):
        return {"status": "BLOCKED_INPUT_SENSITIVITY", "action_authority": "NONE"}
    return {"status": "NOT_CONFIGURED", "action_authority": "NONE", "agreement": "UNKNOWN",
            "confidence": 0.0, "primary_objection": "Live critic provider is not configured.",
            "assumptions": [], "missing_evidence": ["critic_provider"], "contradictions": [],
            "alternate_explanation": "Deterministic local evidence remains authoritative.",
            "risk": "UNKNOWN", "recommended_check": "Configure a governed critic provider before live use."}


def capture_idea(text: str, *, source: str = "telegram") -> Dict[str, Any]:
    idea_text = re.sub(r"^\s*(?:IDEA\s*:\s*|idea\s+)", "", text, flags=re.I).strip()
    normalized = re.sub(r"\W+", " ", idea_text.lower()).strip()
    existing = []
    if IDEA_PATH.exists():
        for line in IDEA_PATH.read_text(encoding="utf-8").splitlines():
            try:
                existing.append(json.loads(line))
            except ValueError:
                continue
    duplicate = next((row for row in existing if row.get("normalized") == normalized and normalized), None)
    idea_id = f"idea_{_fingerprint((normalized, len(existing)))}"
    row = {"idea_id": idea_id, "text": idea_text[:2000], "normalized": normalized,
           "created_at": utc_now(), "source": source, "category": "UNCLASSIFIED",
           "business": "UNKNOWN", "potential_value": "UNKNOWN", "research_needed": True,
           "dependencies": [], "risk": "UNKNOWN", "status": "DUPLICATE" if duplicate else "CAPTURED",
           "duplicate_of": duplicate.get("idea_id") if duplicate else None,
           "portfolio_objective_id": None, "notes": "Capture does not start execution."}
    _append_jsonl(IDEA_PATH, row)
    return row


def list_ideas(limit: int = 5) -> Dict[str, Any]:
    rows = []
    if IDEA_PATH.exists():
        for line in IDEA_PATH.read_text(encoding="utf-8").splitlines():
            try: rows.append(json.loads(line))
            except ValueError: pass
    return {"count": len(rows), "newest": rows[-limit:],
            "research_ready": sum(1 for row in rows if row.get("status") == "NEEDS_RESEARCH"),
            "promoted": sum(1 for row in rows if row.get("status") == "PROMOTED_TO_OBJECTIVE")}


def arm_overnight_campaign(*, now: str | None = None) -> Dict[str, Any]:
    started = now or utc_now()
    try:
        local_now = datetime.now(ZoneInfo("America/Phoenix")) if now is None else datetime.fromisoformat(started).astimezone(ZoneInfo("America/Phoenix"))
        next_morning = (local_now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        end = next_morning.isoformat()
    except ValueError:
        end = "2026-08-26T08:00:00-07:00"
    campaign = {"campaign_id": OVERNIGHT_ID, "status": "ARMED", "started_at": started,
                "priority_window_end": end, "scheduler": "EXISTING_PHASE15_ONLY",
                "manual_scheduler_trigger": "NO", "production_mutation": "NO",
                "ray_interruption_policy": "TRUE_GATES_ONLY", "objectives": [
                    "reliability.voice_release_recovery", "reliability.mission_control_freshness",
                    "reliability.hermes_approval_health", "product.experience_2",
                    "product.nexus_completion_audit", "product.goclear_creative_rebuild",
                    "business.goclear_revenue", "intelligence.forex_foundation",
                    "intelligence.creative", "intelligence.model_control",
                    "intelligence.integrity_critic", "maintenance.idea_inbox",
                ], "evidence": "ARMED_ONLY; no work is fabricated"}
    atomic_write_json(CAMPAIGN_PATH, campaign)
    return campaign


def audit_portfolio_dispatches(*, receipt_dir: Path = ROOT / "reports/phase16a/execution_receipts") -> Dict[str, Any]:
    """Produce an evidence-only audit of portfolio dispatch claims."""
    rows = []
    for path in receipt_dir.glob("*.json") if receipt_dir.exists() else []:
        row = _read_json(path, {})
        if not isinstance(row, dict):
            continue
        downstream = row.get("mission_id") or row.get("work_order_id") or row.get("downstream_id")
        rows.append({"objective_id": row.get("objective_id"), "selected_at": row.get("selected_at"), "reported_dispatch_state": row.get("dispatch_status"), "real_downstream_record_exists": bool(downstream), "downstream_type": "mission" if row.get("mission_id") else "work_order" if row.get("work_order_id") else "request" if row.get("downstream_id") else "NONE", "downstream_id": downstream, "executor_started": bool(row.get("started_at")), "executor_completed": bool(row.get("completed_at")), "result_receipt": bool(row.get("receipt_refs")), "material_change": bool(row.get("material_change")), "truthful_final_state": row.get("execution_state", "UNKNOWN"), "source_receipt": str(path)})
    summary = {"generated_at": utc_now(), "rows": rows, "reported_dispatches": sum(row["reported_dispatch_state"] in {"DISPATCHED", "DISPATCH_QUEUED"} for row in rows), "real_downstream_records": sum(row["real_downstream_record_exists"] for row in rows), "synthetic_false_dispatches": sum(row["reported_dispatch_state"] == "DISPATCHED" and not row["real_downstream_record_exists"] for row in rows), "material_progress": sum(row["material_change"] for row in rows), "source": "persisted portfolio execution receipts only"}
    path = ROOT / "reports/phase16a/overnight_dispatch_audit.json"
    atomic_write_json(path, summary)
    return summary


def campaign_status() -> Dict[str, Any]:
    return _read_json(CAMPAIGN_PATH, {"status": "NOT_ARMED", "campaign_id": OVERNIGHT_ID})


def refresh_campaign_lifecycle(*, now: datetime | None = None) -> Dict[str, Any]:
    campaign = campaign_status()
    if campaign.get("status") == "ARMED":
        try:
            end = datetime.fromisoformat(str(campaign.get("priority_window_end")))
            current = now or datetime.now(end.tzinfo or timezone.utc)
            if current >= end:
                campaign = {**campaign, "status": "WINDOW_COMPLETE", "window_completed_at": current.isoformat()}
                atomic_write_json(CAMPAIGN_PATH, campaign)
        except (TypeError, ValueError):
            pass
    return campaign


def arm_catchup_campaign(*, now: datetime | None = None) -> Dict[str, Any]:
    local = now or datetime.now(ZoneInfo("America/Phoenix"))
    end = local.replace(hour=18, minute=0, second=0, microsecond=0)
    if local >= end:
        end = end + timedelta(days=1)
    prior = campaign_status()
    history = list(prior.get("campaign_history") or [])
    if prior.get("campaign_id") and prior.get("campaign_id") != "NEXUS_CATCHUP_2026_08_26":
        history.append(prior)
    campaign = {"campaign_id": "NEXUS_CATCHUP_2026_08_26", "status": "ARMED", "started_at": local.isoformat(), "priority_window_end": end.isoformat(), "scheduler": "EXISTING_PHASE15_ONLY", "manual_scheduler_trigger": "NO", "production_mutation": "NO", "objectives": ["reliability.voice_release_recovery", "product.experience_2", "business.goclear_revenue", "intelligence.forex_foundation", "intelligence.creative", "intelligence.model_control", "product.nexus_completion_audit", "reliability.mission_control_freshness", "product.goclear_creative_rebuild"], "evidence": "ARMED_ONLY; no work is fabricated", "campaign_history": history}
    atomic_write_json(CAMPAIGN_PATH, campaign)
    return campaign


def build_completion_audit(*, root: Path = ROOT) -> Dict[str, Any]:
    domains = ["Core Continuous Loop", "Active Operator", "Recovery", "Hermes Telegram", "Hermes brain/routing", "Mission Control", "governed approvals", "work orders", "receipts", "Product Evolution", "Builder/Codex", "autonomous release recovery", "Executive Portfolio", "Alpha research", "opportunity/revenue", "SEO/growth", "Creative Studio", "Creative Intelligence", "Voice", "Nova", "Experience 2.0", "Trading research", "Model Control", "Integrity Critic", "client portal", "Admin", "GoClear business workflows", "security/governance", "deployment governance", "observability", "cost control"]
    evidence = {"portfolio": (root / "reports/phase16a/executive_portfolio_latest.json").exists(),
                "telegram": (root / "reports/runtime/nexus_hermes_telegram_heartbeat_latest.json").exists(),
                "approval": (root / "data/governed/approvals.jsonl").exists(),
                "voice": (root / "reports/product_evolution/telegram-20260824172054-077bf5a7.json").exists()}
    sections = {}
    for domain in domains:
        status = "IMPLEMENTED_UNPROVEN" if domain in {"Hermes Telegram", "Executive Portfolio", "governed approvals"} else "PARTIAL"
        if domain == "Integrity Critic": status = "NOT_STARTED"
        if domain == "Voice" and evidence["voice"]: status = "WAITING_HUMAN"
        sections[domain] = {"classification": status, "evidence": [], "evidence_timestamp": utc_now(),
                            "commit_lineage": "CURRENT_CHECKOUT", "last_test": "FOCUSED_TESTS_ONLY",
                            "runtime_proof": "UNKNOWN", "human_proof": "NOT_REQUIRED" if status != "WAITING_HUMAN" else "REQUIRED",
                            "remaining_blocker": "Evidence depth or human gate required", "next_autonomous_action": "Continue bounded evidence collection",
                            "next_ray_action": "Microphone/release gate only" if status == "WAITING_HUMAN" else "NONE"}
    material_fingerprint = _fingerprint([(name, row["classification"]) for name, row in sections.items()])
    existing = _read_json(CERT_DIR / "nexus_completion_audit_latest.json", {})
    if isinstance(existing, dict) and existing.get("material_fingerprint") == material_fingerprint:
        return {**existing, "refresh": "NO_CHANGE", "checked_at": utc_now()}
    audit = {"audit_id": "NEXUS_COMPLETION_AUDIT_V1", "generated_at": utc_now(),
             "material_fingerprint": material_fingerprint, "sections": sections,
             "summary": {"certified": 0, "implemented_unproven": sum(v["classification"] == "IMPLEMENTED_UNPROVEN" for v in sections.values()),
                         "partial": sum(v["classification"] == "PARTIAL" for v in sections.values()),
                         "waiting_human": sum(v["classification"] == "WAITING_HUMAN" for v in sections.values()),
                         "blocked": 0, "deferred_or_not_started": sum(v["classification"] == "NOT_STARTED" for v in sections.values())},
             "status": "PARTIAL", "source": "bounded evidence audit; documentation is not completion proof"}
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(CERT_DIR / "nexus_completion_audit_latest.json", audit)
    lines = ["# NEXUS COMPLETION AUDIT V1", "", f"Generated: {audit['generated_at']}", "", "Evidence-driven status: PARTIAL", ""]
    lines.extend(f"- {name}: {row['classification']}" for name, row in sections.items())
    (CERT_DIR / "nexus_completion_audit_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit


def morning_report(*, portfolio_path: Path = ROOT / "reports/phase16a/executive_portfolio_latest.json") -> str:
    portfolio = _read_json(portfolio_path, {})
    plan = portfolio.get("plan", {}) if isinstance(portfolio, dict) else {}
    execution = plan.get("execution", {}) if isinstance(plan, dict) else {}
    ideas = list_ideas()
    audit = _read_json(CERT_DIR / "nexus_completion_audit_latest.json", {})
    summary = audit.get("summary", {})
    campaign = campaign_status()
    receipts = []
    receipt_dir = ROOT / "reports/phase16a/execution_receipts"
    for path in receipt_dir.glob("*.json") if receipt_dir.exists() else []:
        row = _read_json(path, {})
        if isinstance(row, dict) and row.get("cycle_id"):
            receipts.append(row)
    dispatched = [row for row in receipts if row.get("mission_id") or row.get("work_order_id") or row.get("downstream_id")]
    progress = [row for row in receipts if row.get("material_change") is True]
    blocked = [row for row in receipts if row.get("execution_state") == "BLOCKED"]
    return "\n".join(["NEXUS MORNING REPORT", "", f"Overnight window: {campaign.get('started_at', 'UNKNOWN')} → {campaign.get('priority_window_end', 'UNKNOWN')}", f"Natural downstream handoffs: {len(dispatched)} | material progress: {len(progress)} | blocked: {len(blocked)}",
        "", f"COMPLETED\n- {', '.join(execution.get('completed', [])) or 'None evidenced'}",
        f"MATERIAL PROGRESS\n- {', '.join(execution.get('materially_advanced', [])) or ('Evidence receipts: ' + str(len(progress)) if progress else 'None evidenced')}",
        f"VOICE\n- See /portfolio; human microphone/release gate remains separate",
        "FOREX\n- Research-only objective remains governed", "CREATIVE 2.0\n- Research/architecture objective remains governed",
        "MODEL CONTROL\n- Deterministic routing architecture active", "EXPERIENCE 2.0\n- Evidence-dependent", "GOCLEAR\n- Internal revenue work remains enabled; outreach blocked",
        f"NEXUS CERTIFICATION\n- Certified: {summary.get('certified', 0)} | Partial: {summary.get('partial', 0)} | Blocked: {summary.get('blocked', 0)} | Waiting human: {summary.get('waiting_human', 0)}",
        f"IDEAS\n- captured: {ideas['count']} | research-ready: {ideas['research_ready']} | promoted: {ideas['promoted']}",
        "RAY NEEDS TO DO\n- NONE unless a new exact human gate is reported", "", "Use /portfolio, /approvals, or /ideas for detail."])


def notify_true_gate(gate: Mapping[str, Any], sender: Any) -> Dict[str, Any]:
    fingerprint = _fingerprint({key: gate.get(key) for key in ("gate_type", "approval_id", "human_gate_id", "objective_id", "release_id", "candidate_sha", "state")})
    seen = []
    if NOTIFIER_PATH.exists():
        for line in NOTIFIER_PATH.read_text(encoding="utf-8").splitlines():
            try: seen.append(json.loads(line).get("fingerprint"))
            except ValueError: pass
    if fingerprint in seen:
        return {"status": "DUPLICATE_SUPPRESSED", "fingerprint": fingerprint}
    text = "\n".join(["NEXUS NEEDS RAY", f"Objective: {gate.get('objective', 'UNKNOWN')}", f"Why this requires you: {gate.get('reason', 'human-only gate')}", f"Evidence: {gate.get('evidence', 'UNKNOWN')}", f"Exact action: {gate.get('exact_action', 'Review the pending gate.')}", f"Expires: {gate.get('expires_at', 'UNKNOWN')}", "Everything else continues autonomously."])
    delivered = bool(sender(text))
    _append_jsonl(NOTIFIER_PATH, {"fingerprint": fingerprint, "created_at": utc_now(), "delivered": delivered, "gate_type": gate.get("gate_type")})
    return {"status": "SENT" if delivered else "DELIVERY_FAILED", "fingerprint": fingerprint}
