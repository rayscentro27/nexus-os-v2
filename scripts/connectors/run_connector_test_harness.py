#!/usr/bin/env python3
"""Verify connector modes/configuration and emit local proof without external calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
from full_engine_common import SUPABASE, env_presence, read_json, record, write_json, write_report  # noqa: E402


def build() -> dict:
    connectors = read_json(ROOT / "configs" / "connector_registry.json", {}).get("connectors", [])
    registry_report = {"ok": True, "mode": "local_policy_registry", "status": "internal_active",
        "external_action_performed": False, "connectors": connectors,
        "summary": f"Registered {len(connectors)} connectors with explicit allowed/blocked actions."}
    write_report("connector_registry", "Connector Registry", registry_report, {"Connectors": connectors})
    env = env_presence("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "META_APP_ID", "META_APP_SECRET", "YOUTUBE_API_KEY", "OANDA_API_KEY", "OANDA_ACCOUNT_ID")
    results, events = [], []
    for item in connectors:
        configured = item["configured"]
        config_evidence = "registry"
        if item["connector_id"] == "social_connector_health":
            configured = all(env[name] for name in ("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "META_APP_ID", "META_APP_SECRET"))
            config_evidence = "required env names present; values not exposed; network validity not tested"
        elif item["connector_id"] == "youtube_research_connector":
            configured = env["YOUTUBE_API_KEY"]
            config_evidence = "YOUTUBE_API_KEY presence only; no network call"
        elif item["connector_id"] == "trading_demo_connector":
            configured = False
            config_evidence = "credentials present but demo/practice environment not confirmed"
        safe = item["external_action_performed"] is False and (
            item["mode"] == "internal" or not item["approval_required"] or item["live_enabled"] is False
        )
        status = item["status"]
        if item["connector_id"] == "social_connector_health" and configured:
            status = "connector_configured_publish_disabled"
        result = record(f"health-{item['connector_id']}", "connector_health", item["name"], status=status,
            connector_id=item["connector_id"], connector_mode=item["mode"], configured=configured,
            live_enabled=item["live_enabled"], approval_required=item["approval_required"], safe_policy_verified=safe,
            configuration_evidence=config_evidence, network_check_performed=False, required_env_vars=item["required_env_vars"],
            next_setup_step=item["next_setup_step"], recommended_next_action=item["next_setup_step"])
        results.append(result)
        events.append(record(f"proof-{item['connector_id']}", "connector_proof_event", f"Connector proof: {item['name']}",
            status="internal_active", connector_id=item["connector_id"], summary=f"Verified mode={item['mode']}, configured={configured}, live_enabled={item['live_enabled']}; no external call."))
    write_json(SUPABASE / "connector_health_latest.json", results)
    write_json(SUPABASE / "connector_proof_events_latest.json", events)
    report = {"ok": all(item["external_action_performed"] is False for item in results), "mode": "local_policy_and_config_presence",
        "status": "internal_active", "external_action_performed": False, "connectors_tested": len(results),
        "configured_count": sum(bool(item["configured"]) for item in results), "health_results": results,
        "proof_events_created": len(events), "summary": f"Tested {len(results)} connector policies/config states without external calls."}
    write_report("connector_test_harness", "Connector Test Harness", report, {"Connector health": results})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = build(); print(json.dumps(report, indent=2) if args.json else report["summary"]); return 0


if __name__ == "__main__":
    raise SystemExit(main())
