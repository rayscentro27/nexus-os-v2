"""Governed operating loop persistence — bounded local store.

Append-only JSONL collections under ``data/governed/`` (gitignored). Each record
is immutable once written; a new record supersedes the previous one for stateful
entities (approvals, work orders). This gives restart persistence without
introducing a new database system.

Paths are overridable via ``NEXUS_GOVERNED_DATA_DIR`` for tests.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from nexus_agent_platform.runtime.paths import nexus_data_path

COLLECTIONS = ("approvals", "work_orders", "recommendations", "audit", "queue", "research_requests", "research_questions", "youtube_claim_validations", "youtube_follow_ups", "youtube_follow_up_executions", "youtube_asr_jobs", "ui_skills_receipts", "result_feedback", "opportunities", "revenue_observations", "revenue_snapshots", "growth_experiments", "marketing_funnels", "marketing_events", "marketing_projects", "marketing_handoffs", "marketing_evaluations", "marketing_experiments", "creative_briefs", "creative_assets", "creative_receipts", "creative_concepts", "creative_feedback", "creative_preference_profiles", "creative_references", "creative_campaigns", "creative_territories", "creative_jobs", "creative_ai", "creative_media", "creative_reviews", "creative_learning", "finance_resource_ledger", "finance_cost_receipts", "finance_revenue", "finance_learning", "finance_economic_requests", "engagement_messages", "customer_signals", "company_handoffs", "specialists", "specialist_permissions", "skill_assignments", "goals", "loop_state", "metrics", "improvement_candidates", "trading_strategies", "business_ideas", "business_research", "business_receipts", "commercial_policies", "launch_candidates", "outcomes", "trading_experiments", "trading_journal", "trading_learning", "trading_paper_observations", "trading_replays", "trading_portfolios", "trading_mcp_audits", "trading_source_registry", "trading_strategy_dna", "trading_experiment_ledger", "trading_candidate_queue", "trading_source_quality", "trading_discovery_receipts", "knowledge_refreshes", "alpha_source_registry", "alpha_theme_registry", "alpha_content", "alpha_claims", "alpha_research", "alpha_discovery_queue", "alpha_outcomes", "alpha_evaluations", "adaptive_diagnoses", "adaptive_variants", "adaptive_learning", "adaptive_runs", "research_v2_sources", "research_v2_claims", "research_v2_methods", "research_v2_opportunities", "research_v2_strategies", "research_v2_questions", "research_v2_investigations", "research_v2_follow_ups", "research_v2_alpha_reviews", "research_v2_plans", "research_v2_reputations", "research_v2_handoffs", "research_v2_comparisons", "research_v2_packages", "research_v2_missions", "research_v2_mission_items", "research_v2_mission_reports", "research_v2_review_queue", "company_cycles")

# Trading completion records are deliberately kept in the same governed append-only
# store while remaining additive to the historical collection tuple.
EXTRA_COLLECTIONS = {"trading_champion_board", "trading_cost_models", "trading_options_watch", "trading_degradation", "trading_recommendations", "trading_multi_mode", "trading_instruments", "trading_runtime_states", "trading_events", "trading_outcome_observations", "research_runtime_states", "research_lanes", "research_discovery_clusters", "research_opportunity_synthesis", "research_intelligence_intake", "research_market_intelligence", "research_market_watch", "research_special_projects", "research_recovery_incidents", "research_stage_receipts", "alpha_health_states", "alpha_decision_receipts", "alpha_rejection_history", "alpha_decision_overrides", "systems_health_states", "systems_services", "systems_incidents", "systems_recovery_receipts", "systems_ai_analyses", "certification_experiments", "labs_candidates", "labs_experiments", "labs_model_capabilities", "labs_health_states", "upgrade_requests", "upgrade_decisions", "upgrade_health_states", "upgrade_rollback_receipts", "finance_truth_snapshots", "finance_project_economics", "finance_goal_snapshots", "finance_alerts", "finance_service_cost_baseline", "finance_token_rollups", "finance_certification_carryover", "customer_service_cases", "customer_service_case_events", "customer_service_followups", "customer_service_escalations", "customer_service_health", "marketing_opportunities", "marketing_campaigns", "marketing_leads", "marketing_health", "marketing_certification_carryover", "creative_tasks", "creative_provider_receipts", "creative_health", "creative_certification_carryover", "creative_prompt_architect_receipts"}


def governed_data_dir() -> Path:
    override = os.environ.get("NEXUS_GOVERNED_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return nexus_data_path("governed")


def collection_path(name: str) -> Path:
    if name not in COLLECTIONS and name not in EXTRA_COLLECTIONS:
        raise ValueError(f"Unknown governed collection: {name}")
    return governed_data_dir() / f"{name}.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _ensure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600)
    os.chmod(path, 0o600)


def append_record(collection: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Append an immutable record to the collection."""
    path = collection_path(collection)
    _ensure(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return record


def read_records(collection: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read all records, most recent last. Returns newest-first ordering."""
    path = collection_path(collection)
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit is not None:
        records = records[-limit:]
    return list(reversed(records))


def get_record(collection: str, record_id: str, key: str = "id") -> Optional[Dict[str, Any]]:
    """Return the newest record matching id, or None."""
    for record in read_records(collection):
        if record.get(key) == record_id:
            return record
    return None


def latest_record(collection: str) -> Optional[Dict[str, Any]]:
    records = read_records(collection, limit=1)
    return records[0] if records else None


def write_snapshot(collection: str, records: List[Dict[str, Any]]) -> Path:
    """Write a deterministic snapshot of a collection (superseded records included)."""
    path = governed_data_dir() / f"{collection}_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collection": collection,
        "generated_at": _now(),
        "record_count": len(records),
        "records": records,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def emit_audit_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Append an audit trail event (no sensitive message contents)."""
    record = {
        "event_id": new_id("aud"),
        "created_at": _now(),
        **event,
    }
    return append_record("audit", record)


def read_audit(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    return read_records("audit", limit=limit)
