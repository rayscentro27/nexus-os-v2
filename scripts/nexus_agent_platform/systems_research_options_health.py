"""Closed-state Systems checks for notebook expansion and Options data readiness."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = Path.home() / ".nexus/venvs/notebooklm-py/bin/notebooklm"
RECOVERY = {
    "NOTEBOOKLM_ACCESS": "NOTEBOOK_BROWSER_AUTH_RECOVERY",
    "NOTEBOOK_SOURCE_EXPANSION": "NOTEBOOK_RESEARCH_RECOVERY",
    "NOTEBOOK_RESEARCH_RETURN": "NOTEBOOK_RESEARCH_RECOVERY",
    "OPTIONS_DATA_PROVIDER": "OPTIONS_DATA_CAPABILITY_RECOVERY",
    "OPTIONS_CHAIN_ACCESS": "OPTIONS_DATA_CAPABILITY_RECOVERY",
    "OPTIONS_HISTORICAL_DATA": "OPTIONS_HISTORICAL_DATA_RECOVERY",
    "OPTIONS_PAPER_CAPABILITY": "OPTIONS_PAPER_RECOVERY",
}


def run() -> dict:
    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts/nexus_agent_platform"))
        import feeder_runtime as feeder
        source_id = "fixture_business_funding_first_citizens_20261007"
        sources = feeder._request(f"nexus_feeder_sources?source_id=eq.{source_id}&select=source_id,notebook_reference,notebook_output,ingestion_status")
        source = sources[0] if sources else {}
        gaps = feeder._request(f"nexus_feeder_research_gaps?source_id=eq.{source_id}&select=question_id,status,answer_packet") if source else []
        settings = feeder._request("research_notebooklm_automation_settings?settings_id=eq.NOTEBOOKLM_RESEARCH&select=settings_id,enabled,automation_mode,preferred_path,public_sources_only,sensitive_client_data_allowed,destructive_notebook_actions_allowed,sharing_actions_allowed,max_imported_sources_per_pass,max_research_passes_per_gap,max_gaps_per_notebook_session")
        sessions = feeder._request("research_notebooklm_sessions?select=research_session_id,status,automation_path,started_at,completed_at,sources_imported&order=started_at.desc&limit=10")
        data_bank = feeder._request("options_data_source_bank?source_id=eq.ALPACA_OPTIONS_DATA&select=status,nexus_tested,evidence")
        execution_bank = feeder._request("options_execution_engine_bank?engine_id=eq.ALPACA_OPTIONS_DATA_READONLY&select=status,nexus_tested,live_trading_capability,evidence")
    except Exception as exc:
        return {"status": "CHECK_ERROR", "error": f"SUPABASE_RUNTIME_RECOVERY:{type(exc).__name__}", "checks": {}}

    # The existing CLI health command can take around 75 seconds in the
    # persistent profile. Match the bounded operator timeout so Systems does
    # not report a false authentication failure.
    doctor = subprocess.run([str(CLI), "doctor"], text=True, capture_output=True, timeout=90) if CLI.exists() else None
    notebook_access = "PASS" if doctor and doctor.returncode == 0 else ("NOT_CONFIGURED" if not CLI.exists() else "BLOCKED_BY_AUTH")
    setting = settings[0] if settings else {}
    latest = sessions[0] if sessions else {}
    expansion_sessions = [row for row in sessions if row.get("automation_path") in {"CLI", "BROWSER_OPERATOR"}]
    import_success = any(any(source.get("indexing_status") == "ready"
                             for source in (row.get("sources_imported") or [])) for row in expansion_sessions)
    expansion = "PASS" if import_success else ("IDLE_HEALTHY" if not any(g.get("status") in {"OPEN", "IN_PROGRESS"} for g in gaps) else "DEGRADED")
    returned = "PASS" if sessions and sessions[0].get("status") in {"COMPLETED", "RESEARCH_REQUIRED"} else ("IDLE_HEALTHY" if not gaps else "DEGRADED")
    alpaca = data_bank[0] if data_bank else {}
    evidence = alpaca.get("evidence") or {}
    caps = evidence.get("capabilities") or {}
    historical = evidence.get("historical") or {}
    provider_state = "PASS" if evidence.get("auth_status") == "PASS" and alpaca.get("nexus_tested") else ("BLOCKED_BY_AUTH" if not evidence else "NOT_CONFIGURED")
    quote_state = "PASS" if caps.get("bid") == "PASS" and caps.get("ask") == "PASS" else "DEGRADED"
    greeks_state = "PASS" if all(caps.get(name) == "PASS" for name in ("iv", "delta", "gamma", "theta", "vega")) else "DEGRADED"
    liquidity_state = "PASS" if caps.get("volume") == "PASS" and caps.get("open_interest") == "PASS" else "DEGRADED"
    historical_state = "PASS" if all(historical.get(name) == "PASS" for name in
        ("bars", "trades", "quotes", "chain_reconstruction", "iv", "greeks", "open_interest")) else "DEGRADED"
    paper_state = "PASS" if evidence.get("paper_mode") == "ENABLED" else "NOT_CONFIGURED"
    checks = {
        "NOTEBOOKLM_ACCESS": notebook_access,
        "NOTEBOOKLM_CLI_AUTH": notebook_access,
        "NOTEBOOKLM_BROWSER_AUTH": "NOT_APPLICABLE" if setting.get("preferred_path") == "CLI" else "NOT_CONFIGURED",
        "NOTEBOOKLM_NOTEBOOK_ACCESS": "PASS" if source.get("notebook_reference") and notebook_access == "PASS" else "DEGRADED",
        "NOTEBOOKLM_SOURCE_SEARCH": "PASS" if expansion_sessions else ("IDLE_HEALTHY" if not gaps else "DEGRADED"),
        "NOTEBOOKLM_SOURCE_IMPORT": "PASS" if import_success else ("IDLE_HEALTHY" if not gaps else "DEGRADED"),
        "NOTEBOOKLM_INDEXING": "PASS" if any(row.get("status") in {"COMPLETED", "RESEARCH_REQUIRED"} and row.get("sources_imported") for row in expansion_sessions) else ("IDLE_HEALTHY" if not gaps else "DEGRADED"),
        "NOTEBOOKLM_REANALYSIS": "PASS" if any((row.get("gaps_attempted") or []) for row in expansion_sessions) else ("IDLE_HEALTHY" if not gaps else "DEGRADED"),
        "NOTEBOOKLM_RETURN_TO_FEEDER": returned,
        "NOTEBOOK_SOURCE_EXPANSION": expansion,
        "NOTEBOOK_RESEARCH_RETURN": returned,
        "OPTIONS_DATA_PROVIDER": provider_state,
        "OPTIONS_CHAIN_ACCESS": "PASS" if evidence.get("capabilities") and evidence.get("data_mode") == "ENABLED" else provider_state,
        "OPTIONS_HISTORICAL_DATA": historical_state,
        "OPTIONS_PAPER_CAPABILITY": paper_state,
        "ALPACA_AUTH": provider_state,
        "ALPACA_ACCOUNT": "PASS" if evidence.get("account_status") == "ACTIVE" else "DEGRADED",
        "ALPACA_CHAIN": "PASS" if evidence.get("capabilities") and evidence.get("data_mode") == "ENABLED" else provider_state,
        "ALPACA_QUOTES": quote_state,
        "ALPACA_GREEKS": greeks_state,
        "ALPACA_LIQUIDITY": liquidity_state,
        "ALPACA_HISTORICAL": historical_state,
        "ALPACA_PAPER": paper_state,
    }
    recovery = {**RECOVERY, "NOTEBOOKLM_CLI_AUTH": "NOTEBOOK_CLI_RECOVERY", "NOTEBOOKLM_BROWSER_AUTH": "NOTEBOOK_BROWSER_AUTH_RECOVERY",
                "NOTEBOOKLM_NOTEBOOK_ACCESS": "NOTEBOOK_RESEARCH_RECOVERY", "NOTEBOOKLM_SOURCE_SEARCH": "NOTEBOOK_RESEARCH_RECOVERY",
                "NOTEBOOKLM_SOURCE_IMPORT": "NOTEBOOK_IMPORT_RECOVERY", "NOTEBOOKLM_INDEXING": "NOTEBOOK_INDEXING_RECOVERY",
                "NOTEBOOKLM_REANALYSIS": "NOTEBOOK_RESEARCH_RECOVERY", "NOTEBOOKLM_RETURN_TO_FEEDER": "RESEARCH_RETURN_RECOVERY",
                "ALPACA_AUTH": "OPTIONS_DATA_CAPABILITY_RECOVERY", "ALPACA_ACCOUNT": "OPTIONS_DATA_CAPABILITY_RECOVERY",
                "ALPACA_CHAIN": "OPTIONS_DATA_CAPABILITY_RECOVERY", "ALPACA_QUOTES": "OPTIONS_DATA_CAPABILITY_RECOVERY",
                "ALPACA_GREEKS": "OPTIONS_DATA_CAPABILITY_RECOVERY", "ALPACA_LIQUIDITY": "OPTIONS_DATA_CAPABILITY_RECOVERY",
                "ALPACA_HISTORICAL": "OPTIONS_HISTORICAL_DATA_RECOVERY", "ALPACA_PAPER": "OPTIONS_PAPER_RECOVERY"}
    next_workflows = {key: recovery[key] for key, value in checks.items() if value not in {"PASS", "IDLE_HEALTHY", "NOT_APPLICABLE"}}
    overall = "PASS" if all(value in {"PASS", "IDLE_HEALTHY", "NOT_APPLICABLE"} for value in checks.values()) else "DEGRADED"
    return {"status": overall, "generated_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "next_workflows": next_workflows, "alpaca_live_trading_enabled": False,
            "notebooklm_automation_mode": setting.get("automation_mode", "NOT_CONFIGURED"),
            "notebooklm_active_path": setting.get("preferred_path", "NOT_CONFIGURED"),
            "notebooklm_enabled": bool(setting.get("enabled")),
            "last_notebook_research_at": latest.get("started_at"),
            "last_source_imported_at": latest.get("completed_at") if latest.get("sources_imported") else None,
            "last_return_to_feeder_at": latest.get("completed_at") if latest.get("status") == "COMPLETED" else None,
            "open_notebook_gaps": sum(g.get("status") in {"OPEN", "IN_PROGRESS"} for g in gaps),
            "completed_notebook_gaps": sum(g.get("status") == "COMPLETED" for g in gaps),
            "blocked_notebook_gaps": sum(g.get("status") == "BLOCKED_EXTERNAL" for g in gaps),
            "failed_notebook_gaps": sum(g.get("status") == "FAILED_RETRYABLE" for g in gaps),
            "notebook_reference_present": bool(source.get("notebook_reference")),
            "first_citizens_open_gaps": sum(g.get("status") != "COMPLETED" for g in gaps),
            "alpaca_bank_readback": bool(data_bank and execution_bank),
            "alpaca_last_tested_at": evidence.get("last_tested_at"),
            "alpaca_checks": {k: checks[k] for k in checks if k.startswith("ALPACA_")},
            "auth_values_exposed": False}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
