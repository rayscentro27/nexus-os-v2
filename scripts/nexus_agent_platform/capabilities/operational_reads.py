"""Canonical structured current-state reads for Hermes and Nova.

This module is read-only.  It applies one freshness/authority convention and
returns structured envelopes; conversational agents render the result but do
not define its meaning.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .currentness import classify_record, count_by_class, is_synthetic_record

ROOT = Path(__file__).resolve().parents[3]

AUTHORITY_RANKS = {
    "live_governed_state": 1,
    "current_runtime_ledger": 2,
    "current_structured_report": 3,
    "recent_historical_report": 4,
    "study_snapshot": 5,
    "static_knowledge": 6,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _timestamp(data: Any, path: Path) -> Optional[str]:
    if isinstance(data, dict):
        for key in ("generated_at", "completed_at", "updated_at", "retrieved_at"):
            if isinstance(data.get(key), str):
                return data[key]
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return None


def _age(timestamp: Optional[str]) -> Optional[float]:
    if not timestamp:
        return None
    try:
        value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return max(0.0, (_now() - value).total_seconds())
    except ValueError:
        return None


def _envelope(capability: str, data: Any, *, status: str, source_type: str,
              path: Optional[Path], warnings=None, errors=None,
              source_timestamp: Optional[str] = None) -> Dict[str, Any]:
    source_path = str(path.relative_to(ROOT)) if path and path.is_absolute() and path.is_relative_to(ROOT) else str(path or "UNKNOWN")
    freshness_age = _age(source_timestamp)
    freshness = "UNKNOWN" if freshness_age is None else ("FRESH" if freshness_age < 172800 else "STALE")
    return {
        "status": status,
        "as_of": source_timestamp or "UNKNOWN",
        "source_type": source_type,
        "source_path": source_path,
        "freshness": freshness,
        "data": data,
        "warnings": list(warnings or []),
        "errors": list(errors or []),
        "provenance": {
            "capability": capability,
            "source_type": source_type,
            "source_path": source_path,
            "source_timestamp": source_timestamp or "UNKNOWN",
            "freshness_age_seconds": freshness_age,
            "authority_rank": AUTHORITY_RANKS.get(source_type, 99),
        },
    }


def _report(capability: str, filename: str, source_type: str = "current_structured_report"):
    path = ROOT / filename
    data = _load(path)
    if data is None:
        return _envelope(capability, {}, status="UNAVAILABLE", source_type=source_type,
                         path=path, errors=[f"Source unavailable: {filename}"])
    return _envelope(capability, data, status="OK", source_type=source_type,
                     path=path, source_timestamp=_timestamp(data, path))


def _client_count() -> Dict[str, Any]:
    from nexus_agent_platform.agents.hermes import _get_client_count
    raw = _get_client_count()
    status = "OK" if raw.get("error") is None and raw.get("provenance", {}).get("status") == "success" else "UNAVAILABLE"
    prov = raw.get("provenance", {})
    return _envelope("CLIENT_COUNT", raw, status=status,
                     source_type=prov.get("source_type", "live_governed_state"),
                     path=None, source_timestamp=prov.get("retrieved_at"))


def _business_loops() -> Dict[str, Any]:
    result = _report("BUSINESS_LOOP_STATUS", "reports/hermes_modernization/live_loop_results.json", "current_runtime_ledger")
    if result["status"] == "OK":
        loops = result["data"].get("loops", {}) if isinstance(result["data"], dict) else {}
        result["data"] = {"active_count": len(loops), "loops": loops}
    return result


def _business_opportunities() -> Dict[str, Any]:
    result = _report("BUSINESS_OPPORTUNITIES", "reports/hermes_modernization/live_research_decisions.json")
    if result["status"] != "OK":
        return result
    rows = result["data"].get("decisions", [])
    source_timestamp = result.get("as_of")
    classified = []
    for row in rows:
        meta = classify_record(row, source_timestamp=source_timestamp,
                               synthetic=is_synthetic_record(row))
        classified.append({**row, **meta})
    eligible = [row for row in classified if row["live_response_eligible"]]
    filtered = count_by_class(classified)
    result["data"] = {
        "total": len(eligible),
        "by_decision": {key: sum(1 for row in eligible if row.get("decision") == key) for key in ("ACCEPT", "WATCH", "REJECT", "NEEDS_MORE_EVIDENCE")},
        "items": eligible[:50],
        "taxonomy": "CURRENT opportunities only; research history excluded",
        "filtered_counts": filtered,
    }
    result["status"] = "OK" if eligible else "EMPTY"
    result["warnings"] = list(result.get("warnings", []))
    result["warnings"].append("Historical, synthetic, and non-current research decisions were excluded from the live opportunity view.")
    return result


def _research_history() -> Dict[str, Any]:
    result = _report("RESEARCH_HISTORY", "reports/hermes_modernization/live_research_session.json")
    if result["status"] == "OK":
        data = result["data"]
        result["data"] = {
            "state": data.get("state", "UNKNOWN"),
            "started_at": data.get("started_at", "UNKNOWN"),
            "completed_at": data.get("completed_at", "UNKNOWN"),
            "sources_searched": data.get("sources_searched", "UNKNOWN"),
            "sources_ok": data.get("sources_ok", "UNKNOWN"),
            "sources_failed": data.get("sources_failed", "UNKNOWN"),
            "queries": data.get("query_records", [])[-10:],
        }
    return result


def _alpha_latest() -> Dict[str, Any]:
    result = _report("ALPHA_LATEST", "reports/hermes_modernization/live_research_decisions.json")
    if result["status"] == "OK":
        d = result["data"]
        result["data"] = {"counts": d.get("counts", {}), "latest_decisions": d.get("decisions", [])[:10], "not_study_snapshot": True}
    return result


def _ai_cost() -> Dict[str, Any]:
    result = _report("AI_COST_SUMMARY", "reports/hermes_modernization/daily_brief.json")
    if result["status"] == "OK":
        d = result["data"]
        result["data"] = {"cost_summary": d.get("cost_summary", {}), "token_summary": d.get("token_summary", {}), "source_is_daily_brief": True}
    return result


def _payment_gate() -> Dict[str, Any]:
    result = _report("PAYMENT_GATE", "reports/hermes_modernization/stripe_test_mode_proof.json")
    if result["status"] == "OK":
        d = result["data"]
        evidence = d.get("evidence", {})
        result["data"] = {
            "gate": "BLOCKED_UNTIL_TEST_KEYS_RECONCILED" if d.get("live_key_present") else "TEST_MODE_READY",
            "stripe_mode": "NOT_CONFIRMED_TEST" if d.get("live_key_present") else "TEST",
            "live_key_present": d.get("live_key_present", "UNKNOWN"),
            "charges_enabled": evidence.get("pilot_controls", {}).get("contract_meta", {}).get("charges_enabled", "UNKNOWN"),
            "live_payment_links": evidence.get("pilot_controls", {}).get("contract_meta", {}).get("live_payment_links", "UNKNOWN"),
            "next_action": d.get("next_action", "UNKNOWN"),
            "no_live_revenue_recorded": d.get("no_live_revenue_recorded", "UNKNOWN"),
        }
        result["warnings"].append("Stripe artifact reports live keys; TEST MODE is not currently confirmed.") if d.get("live_key_present") else None
    return result


def _client_journey() -> Dict[str, Any]:
    result = _report("CLIENT_JOURNEY_GATE", "reports/hermes_modernization/client_journey_proof.json")
    if result["status"] == "OK":
        d = result["data"]
        result["data"] = {"gate": "NO_GO" if d.get("crj_bridge", {}).get("requires_ray_approval") else "GO", "journey": d.get("journey", {}), "crj_bridge": d.get("crj_bridge", {})}
    return result


def _approvals() -> Dict[str, Any]:
    result = _report("APPROVAL_QUEUE", "reports/runtime/ray_review_queue_latest.json")
    if result["status"] == "OK":
        d = result["data"]
        result["data"] = {"cards_total": d.get("cards_total", "UNKNOWN"), "approve_today_count": d.get("approve_today_count", "UNKNOWN"), "external_actions_executed": d.get("external_actions_executed", "UNKNOWN")}
    return result


def _blockers() -> Dict[str, Any]:
    """Derive blockers from current governed state, never from a daily brief."""
    from nexus_agent_platform.governed import persistence, work_orders
    from nexus_agent_platform.governed.approvals import get_pending_approvals

    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    approvals = get_pending_approvals(requested_for="ray", include_self=False)
    for approval in approvals:
        items.append({
            "id": approval.get("id"),
            "title": approval.get("action_summary") or approval.get("action_id"),
            "status": "WAITING_RAY",
            "blocking": True,
            "source": "data/governed/approvals.jsonl",
            **classify_record(approval, source_timestamp=approval.get("created_at"), now=now),
        })

    latest: dict[str, dict[str, Any]] = {}
    for record in persistence.read_records("work_orders"):
        latest[record["work_order_id"]] = record
    for order in latest.values():
        if order.get("status") != "blocked":
            continue
        items.append({
            "id": order.get("work_order_id"),
            "title": order.get("expected_outcome") or order.get("action_id"),
            "status": "BLOCKED",
            "blocking": True,
            "source": "data/governed/work_orders.jsonl",
            **classify_record(order, source_timestamp=order.get("created_at"), now=now),
        })

    historical_report = ROOT / "reports/hermes_modernization/daily_brief.json"
    historical_count = 0
    historical_data = _load(historical_report)
    if isinstance(historical_data, dict) and isinstance(historical_data.get("blockers"), list):
        historical_count = len(historical_data["blockers"])

    return {
        "status": "OK" if items else "EMPTY",
        "capability": "BLOCKERS",
        "source": "governed_current_state",
        "source_type": "live_governed_read",
        "freshness": "live",
        "data": {
            "blockers": items,
            "items": items,
            "current_count": len(items),
            "filtered_historical_count": historical_count,
            "filtered_synthetic_count": 0,
            "historical_report_excluded": "reports/hermes_modernization/daily_brief.json",
        },
        "warnings": [] if items else ["No active governed blocker was found."],
        "errors": [],
        "provenance": {
            "capability": "BLOCKERS",
            "source_type": "live_governed_read",
            "source_timestamp": now.isoformat(),
            "freshness": "live",
            "authority": "Nexus governed approvals and work-order state",
        },
    }


def _workforce() -> Dict[str, Any]:
    result = _report("WORKFORCE_STATUS", "reports/hermes_modernization/live_runtime_status.json", "current_runtime_ledger")
    if result["status"] == "OK":
        result["data"] = {"worker_pool": result["data"].get("worker_pool", []), "provider_health": result["data"].get("contract", {}).get("worker_pool", {})}
    return result


def _evidence(arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    query = str((arguments or {}).get("query", "")).lower()
    refs = [
        "reports/hermes_modernization/daily_brief.json",
        "reports/hermes_modernization/live_loop_results.json",
        "reports/hermes_modernization/live_research_decisions.json",
        "reports/hermes_modernization/live_research_session.json",
        "reports/hermes_modernization/client_journey_proof.json",
        "reports/hermes_modernization/stripe_test_mode_proof.json",
        "reports/hermes_modernization/live_runtime_status.json",
        "reports/runtime/ray_review_queue_latest.json",
    ]
    matched = [ref for ref in refs if not query or query in ref.lower()]
    return _envelope("EVIDENCE_LOOKUP", {"query": query or "UNKNOWN", "refs": matched, "count": len(matched)}, status="OK", source_type="current_structured_report", path=ROOT / matched[0] if matched else None, source_timestamp=None)


def read_operational_capability(capability: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    readers = {
        "SYSTEM_HEALTH": lambda: _report("SYSTEM_HEALTH", "reports/hermes_modernization/live_runtime_status.json", "current_runtime_ledger"),
        "PROCESS_STATUS": lambda: _report("PROCESS_STATUS", "reports/runtime/nexus_process_inventory_latest.json"),
        "BUSINESS_LOOP_STATUS": _business_loops,
        "BUSINESS_OPPORTUNITIES": _business_opportunities,
        "RESEARCH_HISTORY": _research_history,
        "ALPHA_LATEST": _alpha_latest,
        "AI_COST_SUMMARY": _ai_cost,
        "PAYMENT_GATE": _payment_gate,
        "CLIENT_JOURNEY_GATE": _client_journey,
        "APPROVAL_QUEUE": _approvals,
        "BLOCKERS": _blockers,
        "CLIENT_COUNT": _client_count,
        "WORKFORCE_STATUS": _workforce,
        "EVIDENCE_LOOKUP": lambda: _evidence(arguments),
        "DAILY_BRIEF": lambda: _report("DAILY_BRIEF", "reports/hermes_modernization/daily_brief.json"),
    }
    reader = readers.get(capability)
    if reader is None:
        return _envelope(capability, {}, status="UNAVAILABLE", source_type="static_knowledge", path=None, errors=["Unknown governed operational capability"])
    try:
        return reader()
    except Exception as exc:
        return _envelope(capability, {}, status="ERROR", source_type="current_runtime_ledger", path=None, errors=[str(exc)])
