#!/usr/bin/env python3
"""Build one report-backed Daily Brief from existing Nexus evidence.

This is an aggregation/read model. It does not call Supabase, invoke providers,
create approvals, contact clients, publish, or create another persistent agent.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"
RUNTIME_DIR = ROOT / "reports" / "runtime"
LOOP_DIR = ROOT / "data" / "runtime" / "nexus_loops"
BUILDER_DIR = ROOT / "data" / "runtime" / "builder_execution_ledger"

UNKNOWN = "UNKNOWN"
NOT_AVAILABLE = "NOT_AVAILABLE"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except ValueError:
                continue
    except OSError:
        pass
    return rows


def _source_ref(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _stable_id(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _latest_timestamp(values: Iterable[Any]) -> Optional[str]:
    parsed = [str(value) for value in values if value]
    return max(parsed) if parsed else None


def _load_sources() -> Dict[str, Any]:
    paths = {
        "pilot": REPORT_DIR / "end_to_end_pilot.json",
        "modernization_state": REPORT_DIR / "state.json",
        "revenue": RUNTIME_DIR / "revenue_dashboard_latest.json",
        "money_scoreboard": RUNTIME_DIR / "money_opportunity_scoreboard_latest.json",
        "blockers": RUNTIME_DIR / "global_blocker_resolution_matrix_latest.json",
        "approvals": RUNTIME_DIR / "ray_review_queue_latest.json",
        "client_attention": RUNTIME_DIR / "client_reminder_revenue_risk_latest.json",
        "marketing": RUNTIME_DIR / "nexus_active_operator_receipts/rcpt_marketing_content_pipeline_20260818T031526Z.json",
        "scheduler": RUNTIME_DIR / "scheduler_ui_status_latest.json",
        "loop_state": LOOP_DIR / "loop_state.json",
        "loop_ledger": LOOP_DIR / "execution_ledger.jsonl",
        "builder_ledger": BUILDER_DIR / "ledger.jsonl",
        "learning": REPORT_DIR / "learning_proposals.json",
        "workforce": REPORT_DIR / "workforce_certification.json",
    }
    loaded = {name: _read_json(path, {}) for name, path in paths.items() if name not in {"loop_ledger", "builder_ledger"}}
    loaded["loop_ledger"] = _read_jsonl(paths["loop_ledger"])
    loaded["builder_ledger"] = _read_jsonl(paths["builder_ledger"])
    loaded["paths"] = paths
    return loaded


def _build_cost_summary(sources: Dict[str, Any], pilot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    loop_rows = sources["loop_ledger"]
    builder_rows = sources["builder_ledger"]
    rows = loop_rows + builder_rows
    input_tokens = sum(int(row.get("input_tokens") or 0) for row in rows)
    output_tokens = sum(int(row.get("output_tokens") or 0) for row in rows)
    estimated_cost = sum(float(row.get("estimated_cost") or row.get("estimated_cost_usd") or 0.0) for row in rows)
    ai_calls = sum(int(row.get("ai_calls") or row.get("model_calls") or 0) for row in rows)
    deterministic = sum(1 for row in rows if row.get("ai_calls", 0) == 0 and row.get("ai_used") is not True)
    pilot_tokens = (pilot or {}).get("tokens") or {}
    successes = sum(1 for row in rows if row.get("result_status") in {"success", "pass"} or row.get("status") == "pass")
    return {
        "execution_records": len(rows),
        "successful_records": successes,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "provider_cost_usd": round(estimated_cost, 8),
        "ai_calls": ai_calls,
        "zero_token_executions": max(sum(1 for row in rows if row.get("zero_token_execution") is True), int(pilot_tokens.get("zero_token_operations") or 0)),
        "deterministic_execution_share": 1.0 if rows and ai_calls == 0 else (round(deterministic / len(rows), 4) if rows else UNKNOWN),
        "ai_execution_share": round(ai_calls / len(rows), 4) if rows else UNKNOWN,
        "local_compute_executions": int(pilot_tokens.get("local_compute_executions") or len(builder_rows)),
        "value_events": sum(int(row.get("value_events") or 0) for row in loop_rows),
        "cost_status": "LOCAL_COMPUTE_ONLY" if estimated_cost == 0 else "REPORT_BACKED_ESTIMATE",
    }


def build_daily_brief() -> Dict[str, Any]:
    sources = _load_sources()
    pilot = sources["pilot"] if isinstance(sources["pilot"], dict) else {}
    opportunity = pilot.get("opportunity") or {}
    revenue = sources["revenue"] if isinstance(sources["revenue"], dict) else {}
    scoreboard = sources["money_scoreboard"] if isinstance(sources["money_scoreboard"], dict) else {}
    blockers = sources["blockers"] if isinstance(sources["blockers"], dict) else {}
    approval_report = sources["approvals"] if isinstance(sources["approvals"], dict) else {}
    client_attention = sources["client_attention"] if isinstance(sources["client_attention"], dict) else {}
    loop_state = sources["loop_state"] if isinstance(sources["loop_state"], dict) else {}
    health_loop = ((loop_state.get("loops") or {}).get("system_health_loop") or {})
    last_loop = health_loop.get("last_run") or {}
    loop_summary = last_loop.get("summary") or {}
    workers = pilot.get("workers") or []
    workforce_workers = (sources["workforce"] or {}).get("workers") if isinstance(sources["workforce"], dict) else None
    worker_rows = workforce_workers or workers
    top_money = (scoreboard.get("scoreboard") or [{}])[0]
    revenue_next = revenue.get("exact_next_money_action", UNKNOWN)
    cost = _build_cost_summary(sources, pilot=pilot)
    paths = sources["paths"]
    evidence_refs = [_source_ref(paths[name]) for name in ("pilot", "revenue", "money_scoreboard", "blockers", "approvals", "loop_state", "loop_ledger", "builder_ledger", "learning", "workforce") if paths[name].exists()]
    generated_at = _now()
    latest_source = _latest_timestamp([
        pilot.get("ending_commit"), revenue.get("generated_at"), blockers.get("generated_at"),
        approval_report.get("generated_at"), health_loop.get("last_updated_at"),
    ])
    brief = {
        "brief_id": f"daily_brief_{_stable_id([generated_at[:10], opportunity.get('id'), revenue.get('confirmed_revenue_usd')])}",
        "generated_at": generated_at,
        "scope": "internal_nexus_operator_report_backed",
        "status": "REPORT_BACKED_PARTIAL",
        "top_priority": {
            "title": revenue_next,
            "reason": "The revenue dashboard identifies this as the exact next money action; no live charge is asserted.",
            "source": _source_ref(paths["revenue"]),
        },
        "highest_value_next_action": revenue_next,
        "money_opportunity": {
            "title": top_money.get("title", UNKNOWN),
            "opportunity_id": top_money.get("opportunity_id", UNKNOWN),
            "score": top_money.get("overall_score", UNKNOWN),
            "revenue_potential_score": top_money.get("revenue_potential", UNKNOWN),
            "approval_required": top_money.get("approval_needed", UNKNOWN),
            "next_action": top_money.get("ray_next_action", UNKNOWN),
            "source": _source_ref(paths["money_scoreboard"]),
        },
        "revenue_status": {
            "confirmed_revenue_usd": revenue.get("confirmed_revenue_usd", UNKNOWN),
            "pending_test_revenue_usd": revenue.get("pending_test_revenue_usd", UNKNOWN),
            "possible_offer_value_usd": revenue.get("possible_offer_value_usd", UNKNOWN),
            "blocked_revenue_usd": revenue.get("blocked_revenue_usd", UNKNOWN),
            "real_charge": revenue.get("real_charge", UNKNOWN),
            "source": _source_ref(paths["revenue"]),
        },
        "revenue_risks": blockers.get("blockers", [])[:5],
        "opportunity_updates": [{
            "id": opportunity.get("id", UNKNOWN),
            "title": opportunity.get("title", UNKNOWN),
            "status": opportunity.get("status", UNKNOWN),
            "base_score": opportunity.get("base_score", UNKNOWN),
            "change": UNKNOWN,
            "change_reason": "No prior comparable canonical baseline is present in the Phase 9 record.",
            "next_action": opportunity.get("recommended_next_action", UNKNOWN),
        }],
        "research_updates": {
            "status": pilot.get("research", {}).get("status", UNKNOWN),
            "evidence_count": pilot.get("research", {}).get("evidence_count", UNKNOWN),
            "duplicates_removed": pilot.get("research", {}).get("duplicates_removed", UNKNOWN),
            "ai_calls": pilot.get("research", {}).get("ai_calls", UNKNOWN),
        },
        "creative_updates": {
            "status": pilot.get("creative", {}).get("status", UNKNOWN),
            "selected_territory": pilot.get("creative", {}).get("selected_territory", UNKNOWN),
            "territory_count": pilot.get("creative", {}).get("territory_count", UNKNOWN),
        },
        "builder_updates": {
            "status": pilot.get("builder_status", UNKNOWN),
            "worker_used": pilot.get("worker_used", UNKNOWN),
            "verification": pilot.get("verification_status", UNKNOWN),
            "workers": [{"worker_id": row.get("worker_id", UNKNOWN), "classification": row.get("classification", UNKNOWN), "version": row.get("version", UNKNOWN), "reason": row.get("availability_reason", row.get("reason", UNKNOWN))} for row in worker_rows],
        },
        "loop_updates": {
            "system_health_loop": last_loop.get("status", UNKNOWN),
            "system_status": loop_summary.get("system_status", UNKNOWN),
            "active_runs": loop_summary.get("active_runs", UNKNOWN),
            "failed_runs": loop_summary.get("failed_runs", UNKNOWN),
            "pending_approvals": loop_summary.get("pending_approvals", UNKNOWN),
            "last_updated_at": health_loop.get("last_updated_at", UNKNOWN),
        },
        "marketing_updates": {
            "status": (sources["marketing"] or {}).get("status", UNKNOWN),
            "mode": ((sources["marketing"] or {}).get("details") or {}).get("mode", UNKNOWN),
            "value_proven": False,
            "note": "Receipt says no underlying job was executed.",
        },
        "learning_updates": {
            "status": (sources["learning"] or {}).get("status", UNKNOWN),
            "observation_count": (sources["learning"] or {}).get("observation_count", UNKNOWN),
            "proposal_count": (sources["learning"] or {}).get("proposal_count", UNKNOWN),
            "detectors": [
                {"detector": item.get("detector", UNKNOWN), "result": item.get("result", UNKNOWN)}
                for item in ((sources["learning"] or {}).get("detectors") or [])
            ],
            "approval_required": ((sources["learning"] or {}).get("approval_policy") or {}).get("approval_required", UNKNOWN),
        },
        "workforce_updates": {
            "status": (sources["workforce"] or {}).get("status", UNKNOWN),
            "worker_count": len(worker_rows),
            "kilo_decision": ((sources["workforce"] or {}).get("kilo_recommendation") or {}).get("decision", UNKNOWN),
            "kilo_classification": next((row.get("classification") for row in worker_rows if row.get("worker_id") == "kilo"), UNKNOWN),
            "source": _source_ref(paths["workforce"]) if paths["workforce"].exists() else UNKNOWN,
        },
        "client_attention": {
            "status": "REPORT_BACKED_NOT_LIVE" if client_attention else NOT_AVAILABLE,
            "stuck_clients": len(client_attention.get("stuck_clients", [])) if client_attention else UNKNOWN,
            "revenue_risk_clients": len(client_attention.get("revenue_risk_clients", [])) if client_attention else UNKNOWN,
            "highest_risk": (client_attention.get("revenue_risk_clients") or [{}])[0] if client_attention else UNKNOWN,
            "external_contacted": False if client_attention else UNKNOWN,
            "source": _source_ref(paths["client_attention"]) if paths["client_attention"].exists() else UNKNOWN,
        },
        "approvals_needed": {
            "pending_loop_count": loop_summary.get("pending_approvals", UNKNOWN),
            "ray_review_cards": approval_report.get("cards_total", UNKNOWN),
            "approve_today_count": approval_report.get("approve_today_count", UNKNOWN),
            "decision": revenue_next,
        },
        "system_health": {
            "status": loop_summary.get("system_status", UNKNOWN),
            "failed_runs": loop_summary.get("failed_runs", UNKNOWN),
            "blockers_total": blockers.get("blockers_total", UNKNOWN),
            "scheduler": (sources["scheduler"] or {}).get("status", UNKNOWN),
        },
        "provider_health": {"status": "REPORT_BACKED", "source": _source_ref(paths["pilot"])},
        "worker_health": [{"worker_id": row.get("worker_id", UNKNOWN), "installed": row.get("installed", UNKNOWN), "classification": row.get("classification", UNKNOWN), "version": row.get("version", UNKNOWN), "probe_result": row.get("execution_probe_status", row.get("probe_result", UNKNOWN))} for row in worker_rows],
        "cost_summary": cost,
        "token_summary": {key: cost[key] for key in ("input_tokens", "output_tokens", "ai_calls", "zero_token_executions")},
        "deterministic_execution_share": cost["deterministic_execution_share"],
        "ai_execution_share": cost["ai_execution_share"],
        "blockers": blockers.get("blockers", [])[:8] + ([{"blocker": "External builder execution adapter", "status": "blocked", "next_action": "Register a separately approved bounded adapter."}] if pilot.get("builder_status") == "PARTIAL" else []),
        "decisions_needed": [revenue_next, "Review Ray approval queue before any external action."],
        "recommended_actions": [revenue_next, "Keep the Crawl4AI opportunity at PILOT_PROPOSED until a separate authorization advances it.", "Keep deterministic loops and investigate only stale or failed sources."],
        "evidence_refs": evidence_refs,
        "confidence": "MEDIUM",
        "freshness": {"status": "MIXED_REPORT_AGES", "latest_source_timestamp": latest_source or UNKNOWN, "live_supabase_read": NOT_AVAILABLE},
    }
    return brief


def render_daily_brief(brief: Dict[str, Any]) -> str:
    revenue = brief["revenue_status"]
    cost = brief["cost_summary"]
    lines = [
        "# Hermes Daily Brief — Phase 11",
        "",
        f"- brief_id: `{brief['brief_id']}`",
        f"- generated_at: `{brief['generated_at']}`",
        f"- status: **{brief['status']}**",
        f"- confidence: `{brief['confidence']}`",
        f"- freshness: `{brief['freshness']['status']}`",
        "",
        "## Top priority",
        "",
        f"**{brief['top_priority']['title']}**",
        "",
        brief["top_priority"]["reason"],
        "",
        "## What changed / attention / value",
        "",
        f"- opportunity: {brief['opportunity_updates'][0]['title']} → `{brief['opportunity_updates'][0]['status']}`; change: `{brief['opportunity_updates'][0]['change']}`",
        f"- confirmed revenue: `${revenue['confirmed_revenue_usd']}`; pending test revenue: `${revenue['pending_test_revenue_usd']}`",
        f"- possible offer value: `${revenue['possible_offer_value_usd']}`; blocked revenue: `${revenue['blocked_revenue_usd']}`",
        f"- selected creative territory: `{brief['creative_updates']['selected_territory']}`",
        f"- builder: `{brief['builder_updates']['status']}`; verification: `{brief['builder_updates']['verification']}`",
        "",
        "## Cost/value intelligence",
        "",
        f"- deterministic execution share: `{brief['deterministic_execution_share']}`",
        f"- AI execution share: `{brief['ai_execution_share']}`",
        f"- input/output tokens: `{cost['input_tokens']}` / `{cost['output_tokens']}`",
        f"- AI calls: `{cost['ai_calls']}`; zero-token executions: `{cost['zero_token_executions']}`",
        f"- provider cost USD: `${cost['provider_cost_usd']}`; local compute executions: `{cost['local_compute_executions']}`",
        f"- value events: `{cost['value_events']}`; successful records: `{cost['successful_records']}`",
        "",
        "## Decisions, blockers, and next actions",
        "",
    ]
    lines.extend(f"- decision: {item}" for item in brief["decisions_needed"])
    lines.extend(f"- blocker: {item.get('blocker', UNKNOWN)} — {item.get('next_action', UNKNOWN)}" for item in brief["blockers"][:5])
    lines.extend(f"- recommended: {item}" for item in brief["recommended_actions"])
    lines.extend(["", "## Evidence", ""])
    lines.extend(f"- `{ref}`" for ref in brief["evidence_refs"])
    return "\n".join(lines) + "\n"


def write_daily_brief_reports() -> Dict[str, Any]:
    brief = build_daily_brief()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "daily_brief.json").write_text(json.dumps(brief, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / "daily_brief.md").write_text(render_daily_brief(brief), encoding="utf-8")
    return brief


if __name__ == "__main__":
    print(json.dumps(write_daily_brief_reports(), indent=2, sort_keys=True))
