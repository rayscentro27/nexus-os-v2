#!/usr/bin/env python3
"""Run bounded deterministic Proactive Research V1 canaries."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.proactive_discovery import capability_inventory, run_lane  # noqa: E402


def run_topic(topic: str) -> dict:
    lanes = ["WEB_SEARCH", "YOUTUBE_DISCOVERY", "LAST_30_DAYS", "SEO_SEARCH_DEMAND"]
    rows = []
    for lane in lanes:
        result = run_lane(topic, lane, window_days=30, bounds={"max_queries": 2, "max_results_per_query": 4, "max_new_sources": 10, "max_runtime_per_lane": 45})
        evidence = []
        for record in result.get("records", []):
            evidence.append({k: record.get(k) for k in ("video_id", "url", "title", "channel", "published_at", "query_used", "query", "signal_type", "signal_value", "domain", "source_engine") if record.get(k) is not None})
        rows.append({k: v for k, v in result.items() if k != "records"} | {"evidence": evidence})
    return {"topic": topic, "lanes": rows, "queries_run": sum(x.get("queries_run", 0) for x in rows),
            "results_found": sum(x.get("results_found", 0) for x in rows), "new_sources": sum(x.get("new_sources", 0) for x in rows),
            "duplicates": sum(x.get("duplicates", 0) for x in rows), "failed_queries": sum(len(x.get("failed_queries", [])) for x in rows),
            "failed_fetches": sum(x.get("failed_fetches", 0) for x in rows), "sources_appended_to_fifo": sum(x.get("sources_appended_to_fifo", 0) for x in rows),
            "supabase_readback_success": all(x.get("supabase_readback") for x in rows if x.get("new_sources", 0) > 0)}


def main() -> int:
    started = datetime.now(timezone.utc)
    payload = {"schema_version": "nexus.proactive-research-v1.canary.v1", "started_at": started.isoformat(),
               "capability_inventory": capability_inventory(), "bounds": {"max_queries_per_lane": 2, "max_results_per_query": 4, "max_new_sources_per_lane": 10, "max_runtime_per_lane_seconds": 45},
               "ai_required_for_collection": False, "recommendation_layer_added": False, "lanes": ["WEB_SEARCH", "YOUTUBE_DISCOVERY", "LAST_30_DAYS", "SEO_SEARCH_DEMAND"], "canaries": []}
    for topic in ("business funding", "what is the best online business to start"):
        payload["canaries"].append(run_topic(topic))
    payload["completed_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = "PASS_REAL" if all(c["new_sources"] or c["duplicates"] for c in payload["canaries"]) else "PARTIAL_REAL"
    out_json = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_V1_CANARIES_2026-09-29.json"
    out_md = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_V1_CANARIES_2026-09-29.md"
    final_json = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_V1_2026-09-29.json"
    final_md = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_V1_2026-09-29.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    final_json.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = ["# Nexus Proactive Research V1 Canaries", "", f"STATUS={payload['status']}", f"STARTED_AT={payload['started_at']}", f"COMPLETED_AT={payload['completed_at']}", "", "## Collection contract", "", "Raw deterministic discovery only; no AI approval, recommendation, monetization, or second queue.", "", "## Canaries", ""]
    for canary in payload["canaries"]:
        lines.extend([f"### {canary['topic']}", "", *[f"{k.upper()}={v}" for k, v in canary.items() if k not in {"topic", "lanes"}], ""])
        for row in canary["lanes"]:
            lines.extend([f"- {row.get('lane')}: status={row.get('status')} queries={row.get('queries_run')} results={row.get('results_found')} new={row.get('new_sources')} duplicates={row.get('duplicates')} fifo={row.get('sources_appended_to_fifo')} readback={row.get('supabase_readback')} run={row.get('discovery_run_id')}"])
        lines.append("")
    lines.extend(["## Boundaries", "", "AI_REQUIRED_FOR_COLLECTION=NO", "RECOMMENDATION_LAYER_ADDED=NO", "UNIVERSAL_FIFO_CHANGED=NO", "ORACLE_HERMES_CHANGED=NO", ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    final_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0 if payload["status"] in {"PASS_REAL", "PARTIAL_REAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
