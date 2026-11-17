#!/usr/bin/env python3
"""One bounded TradingView pass through the existing Research acquisition path."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.proactive_discovery import run_lane
from nexus_agent_platform.proactive_objectives import FAMILIES, SOURCE_POLICY, record_objective_run
from nexus_agent_platform.research_quality import assess_run, persist_raw_signals
from research.proactive_research_memory import query_family


def main() -> dict:
    family = next(row for row in FAMILIES if row["family"] == "TRADING_INTELLIGENCE")
    objective = {**family, "objective_family": family["family"],
        "objective_id": "proactive_trading_intelligence", "target_customer_or_department": family["target"],
        "research_question": family["question"], "query": family["queries"][0],
        "query_family": query_family(family["queries"][0]), "source_class": family["source_class"],
        "business_reason": family["business_reason"], "score_components": {"TRADINGVIEW_MONITORED_SOURCE_CANARY": 1},
        "why_selected": "The designated TradingView permanent source was due for first-class monitoring certification.",
        "evidence_needed": family["useful"], "best_source_classes": SOURCE_POLICY[family["family"]]["classes"],
        "why_these_sources": SOURCE_POLICY[family["family"]]["strategy"]}
    history = ROOT / "data/governed/tradingview_research_cycles.jsonl"
    prior_receipt = {}
    cycle_history = []
    try:
        cycle_history = [json.loads(line) for line in history.read_text().splitlines() if line.strip()]
        prior_receipt = next((row for row in reversed(cycle_history) if int(row.get("items_checked", 0) or 0) > 0), {})
    except (OSError, IndexError, ValueError):
        pass
    prior_scripts = {str(row.get("url")): row
                     for row in prior_receipt.get("top_candidates", [])}
    result = run_lane(objective["query"], "TRADINGVIEW_PUBLIC_SCRIPTS",
        bounds={"max_queries": 1, "max_results_per_query": 8, "max_new_sources": 8, "max_runtime_per_lane": 90},
        use_lane_followup=False)
    quality = assess_run(objective, result)
    signal_ids = persist_raw_signals(objective, result, quality)
    rows = result.get("records", [])
    new_or_updated = 0
    for row in rows:
        key = str(row.get("url"))
        prior = prior_scripts.get(key)
        row["monitor_change"] = ("BASELINE" if not prior_scripts else "NEW") if not prior else "UPDATED" if row.get("updated_at") != prior.get("updated_at") else "UNCHANGED"
        if row["monitor_change"] in {"NEW", "UPDATED"}: new_or_updated += 1
    queue_work_ids = sorted({str(row["queue_work_id"]) for row in rows if row.get("queue_work_id")})
    source_registry_path = ROOT / "data/runtime/alpha_source_registry.json"
    registry = json.loads(source_registry_path.read_text())
    now = datetime.now(timezone.utc).isoformat()
    matched = [row for row in registry if row.get("source_id") == "tradingview_editors_picks"]
    for row in matched:
        row["last_checked"] = now
        row["scan_frequency"] = row.get("scan_frequency") or "P1D"
        row["next_check"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        row["health"] = "PASS" if result.get("status") == "COMPLETED" else "DEGRADED"
        row["last_execution"] = {"lane": "TRADINGVIEW_PUBLIC_SCRIPTS", "status": result.get("status"),
            "items_checked": len(rows), "discovery_run_id": result.get("discovery_run_id")}
    source_registry_path.write_text(json.dumps(registry, indent=2) + "\n")
    strategies = sum(row.get("script_type") == "STRATEGY" for row in rows)
    indicators = sum(row.get("script_type") == "INDICATOR" for row in rows)
    qualified = [row for row in rows if row.get("qualification_status") == "QUALIFIED_FOR_INDEPENDENT_TEST"
                 or row.get("qualification_status") == "DUPLICATE" and row.get("access_type") == "OPEN_SOURCE"
                 and float(row.get("qualification_score") or 0) >= float(row.get("qualification_threshold") or 0.7)]
    all_work_ids = sorted(set(queue_work_ids) | {str(work_id) for receipt in cycle_history
        for work_id in receipt.get("queue_work_ids", [])})
    worker_log = ROOT / "data/runtime/notebooklm_research_results.jsonl"
    worker_rows = []
    try:
        for line in worker_log.read_text().splitlines()[-3000:]:
            try: worker_rows.append(json.loads(line))
            except ValueError: continue
    except OSError:
        pass
    work_results = [row for row in worker_rows if row.get("work_id") in set(all_work_ids)
                    and row.get("outcome") == "EXTRACTED"]
    finding_ids = sorted({str((row.get("persistence") or {}).get("finding", {}).get("finding_id")) for row in work_results
                          if (row.get("persistence") or {}).get("finding", {}).get("status") == "PERSISTED"})
    trading_handoffs = [{"handoff_id": h.get("handoff_id"), "target_department": h.get("target_department"), "status": h.get("status")}
                        for row in work_results for h in ((row.get("persistence") or {}).get("handoffs") or [])
                        if h.get("target_department") in {"TRADING", "MERCURY_TRADING"} and h.get("created")]
    if finding_ids:
        result["evidence_supported_finding_count"] = len(finding_ids)
    result["department_handoffs_created"] = len(trading_handoffs)
    quality = assess_run(objective, result)
    result["quality_assessment"] = quality
    result["raw_signal_ids"] = signal_ids
    objective_run = record_objective_run(objective, result)
    receipt = {
        "schema_version": "nexus.tradingview-research-canary.v1", "recorded_at": now,
        "execution_status": result.get("status"), "registry_enabled": bool(matched and matched[0].get("enabled")),
        "source_url": "https://www.tradingview.com/scripts/editors-picks/",
        "access_method": "bounded public HTML; no login/authenticated pages",
        "research_question": objective["research_question"], "evidence_needed": objective["evidence_needed"],
        "source_classes_used": result.get("source_classes_used", []),
        "discovery_run_id": result.get("discovery_run_id"), "queries": result.get("queries", []),
        "items_checked": len(rows), "new_or_updated": new_or_updated,
        "strategies_found": strategies, "indicators_found": indicators,
        "qualified_for_testing": len(qualified), "findings_created": len(finding_ids), "finding_ids": finding_ids,
        "handoffs_to_trading": len(trading_handoffs), "trading_handoffs": trading_handoffs, "queue_work_ids": all_work_ids,
        "worker_results": [{"work_id": row.get("work_id"), "queue_status": row.get("queue_status"),
            "finding_id": (row.get("persistence") or {}).get("finding", {}).get("finding_id"),
            "handoff_ids": [h.get("handoff_id") for h in ((row.get("persistence") or {}).get("handoffs") or [])]}
            for row in work_results],
        "raw_signal_ids": signal_ids, "research_quality": quality, "objective_run": objective_run,
        "top_candidates": [{k: row.get(k) for k in ("script_id","title","url","script_type","access_type","market","timeframe","author","published_at","updated_at","description","claimed_metrics","risk_rules","source_logic_inspection","qualification_criteria","qualification_score","qualification_status","qualification_reason","persistence_disposition","queue_work_id")} for row in rows[:8]],
        "provider_errors": result.get("failed_queries", []), "duplicates": result.get("duplicates", 0),
        "new_sources_persisted": result.get("new_sources", 0),
    }
    path = ROOT / "reports/runtime/tradingview_research_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    main()
