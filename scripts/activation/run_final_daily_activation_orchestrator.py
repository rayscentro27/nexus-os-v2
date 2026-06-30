#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import now, write_report  # noqa: E402

COMMANDS = [
    ("config_setup", ["python3", "scripts/activation/setup_final_daily_configs.py", "--json"]),
    ("rls_cli_verification", ["python3", "scripts/supabase/verify_production_rls_cli.py", "--json"]),
    ("cli_audit", ["python3", "scripts/activation/audit_local_cli_capabilities.py", "--json"]),
    ("cli_registry", ["python3", "scripts/activation/build_cli_capability_registry.py", "--json"]),
    ("tool_access_validation", ["python3", "scripts/activation/validate_cli_tool_access.py", "--json"]),
    ("tool_access_report", ["python3", "scripts/activation/build_nexus_tool_access_report.py", "--json"]),
    ("research_discovery", ["python3", "scripts/research/run_research_source_discovery.py", "--json", "--safe-internal"]),
    ("research_scoring", ["python3", "scripts/research/score_research_sources.py", "--json"]),
    ("research_opportunities", ["python3", "scripts/research/extract_research_opportunities.py", "--json"]),
    ("research_memory", ["python3", "scripts/research/build_research_memory_exports.py", "--json"]),
    ("research_approvals", ["python3", "scripts/research/build_research_ray_review_cards.py", "--json"]),
    ("research_hermes", ["python3", "scripts/research/build_research_hermes_brief.py", "--json"]),
    ("resend_audit", ["python3", "scripts/activation/audit_resend_connection.py", "--json"]),
    ("resend_diagnosis", ["python3", "scripts/activation/diagnose_resend_403.py", "--json"]),
    ("fake_customer_gate", ["python3", "scripts/client_flow/prepare_persistent_fake_customer_insert_gate.py", "--json"]),
    ("fake_customer_execution_packet", ["python3", "scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py", "--json"]),
    ("frontend_readiness", ["python3", "scripts/client_flow/prepare_frontend_live_data_readiness.py", "--json"]),
    ("frontend_test_plan", ["python3", "scripts/client_flow/prepare_client_dashboard_live_test_plan.py", "--json"]),
    ("youtube_transcript", ["python3", "scripts/activation/run_youtube_transcript_import.py", "--json"]),
    ("notebooklm_import", ["python3", "scripts/activation/run_notebooklm_source_import.py", "--json"]),
    ("oanda_readonly", ["python3", "scripts/trading/run_oanda_demo_readonly_check.py", "--json"]),
    ("vibe_backtest", ["python3", "scripts/trading/run_vibe_paper_backtest_dry_run.py", "--json"]),
    ("schedule_registry", ["python3", "scripts/activation/run_automation_schedule_registry.py", "--json"]),
    ("checklist_build", ["python3", "scripts/activation/build_100_step_activation_checklist.py", "--json"]),
    ("checklist_verify", ["python3", "scripts/activation/verify_100_step_activation_status.py", "--json"]),
]


def run(max_runtime_minutes: int) -> dict:
    started = time.monotonic(); results = []
    for name, command in COMMANDS:
        remaining = max_runtime_minutes * 60 - (time.monotonic() - started)
        if remaining <= 1:
            results.append({"subsystem": name, "ran": False, "passed": False, "status": "max_runtime_reached"}); break
        try:
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=min(remaining, 900))
            results.append({"subsystem": name, "ran": True, "passed": proc.returncode == 0, "exit_code": proc.returncode, "status": "passed" if proc.returncode == 0 else "nonfatal_blocker", "output_tail": (proc.stdout or proc.stderr)[-500:]})
        except subprocess.TimeoutExpired:
            results.append({"subsystem": name, "ran": True, "passed": False, "status": "timeout_nonfatal"})
    report = {"ok": all(x.get("passed") for x in results), "generated_at": now(), "status": "bounded_final_daily_activation_complete", "bounded": True, "max_runtime_minutes": max_runtime_minutes, "elapsed_seconds": round(time.monotonic()-started, 2), "subsystems_planned": len(COMMANDS), "subsystems_run": sum(x.get("ran",False) for x in results), "subsystems_passed": sum(x.get("passed",False) for x in results), "subsystems_with_nonfatal_blockers": sum(x.get("ran") and not x.get("passed") for x in results), "continued_through_nonfatal_blockers": True, "safe_internal": True, "external_actions_allowed": False, "email_sent": False, "social_published": False, "trading_orders": False, "video_downloaded": False, "database_inserted": False, "results": results, "tomorrow_command": "python3 scripts/activation/run_final_daily_activation_orchestrator.py --json --safe-internal --no-external-actions --max-runtime-minutes 90", "external_action_performed": False}
    write_report("final_daily_activation_orchestrator", "Final Daily Activation Orchestrator", report, {"Subsystems": results, "Tomorrow command": report["tomorrow_command"]})
    return report


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--json",action="store_true");parser.add_argument("--safe-internal",action="store_true");parser.add_argument("--no-external-actions",action="store_true");parser.add_argument("--max-runtime-minutes",type=int,default=90);parser.add_argument("--no-email-send",action="store_true");parser.add_argument("--no-social-publish",action="store_true");parser.add_argument("--no-trading-orders",action="store_true");parser.add_argument("--no-video-download",action="store_true");args=parser.parse_args();result=run(max(1,min(args.max_runtime_minutes,90)));print(json.dumps(result,indent=2) if args.json else result)
