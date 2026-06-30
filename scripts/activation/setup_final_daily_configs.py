#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import now, write_json  # noqa: E402


STEPS = [
    "Create one Final Daily Activation Orchestrator.",
    "Make the orchestrator run all safe internal subsystems from one command.",
    "Make the orchestrator bounded, not infinite.",
    "Add --safe-internal, --no-external-actions, and --max-runtime-minutes flags.",
    "Make the orchestrator continue through nonfatal blockers.",
    "Create one Global Blocker Matrix.",
    "Track every blocker by status, cause, fix attempted, result, and next action.",
    "Create one Master End-of-Day Report.",
    "Create one Tomorrow Command output.",
    "Make every subsystem produce reports, Supabase-ready exports, Ray Review cards, and Hermes summaries.",
    "Audit every CLI/tool installed on the Mac Mini.",
    "Detect paths and versions for each CLI.",
    "Detect missing high-value CLIs.",
    "Create configs/cli_capability_registry.json.",
    "Create configs/cli_safety_policy.json.",
    "Create configs/nexus_tool_access_registry.json.",
    "Classify each CLI as internal-safe, read-only, approval-gated, blocked, or unavailable.",
    "Connect safe CLIs to the correct Nexus engines.",
    "Add CLI status to System Health.",
    "Add CLI daily audit to the automation schedule.",
    "Define safe commands for each CLI.",
    "Define blocked commands for each CLI.",
    "Block Stripe live mode.",
    "Block Oanda live/funded trades.",
    "Block YouTube video/audio downloads.",
    "Block destructive Supabase commands.",
    "Block secret-committing.",
    "Block service-role usage in frontend.",
    "Require approval for external actions.",
    "Require approval for permanent scheduler installation.",
    "Keep Stripe test mode active.",
    "Keep live mode blocked.",
    "Track Checkout status.",
    "Track PaymentIntent status.",
    "Track webhook endpoint status.",
    "Track listener and trigger status.",
    "Keep Checkout manual completion approval-gated.",
    "Keep PaymentIntent confirmation approval-gated.",
    "Map webhook test events to onboarding dry-run.",
    "Prepare production Stripe plan, but keep it blocked.",
    "Use Julius Erving / Doctor J LLC as the only fake test customer.",
    "Keep fake customer marked test_mode: true.",
    "Keep do_not_contact: true.",
    "Keep do_not_charge: true.",
    "Generate persistent insert packet.",
    "Generate cleanup packet.",
    "Require approval before persistent fake customer insert.",
    "After insert, verify records exist.",
    "After verification, enable frontend live-data flag.",
    "Keep real customers blocked until fake journey passes.",
    "Store the successful RLS verification result.",
    "Record 25 tables found.",
    "Record 25 tables with RLS enabled.",
    "Record 55 authenticated policies.",
    "Record zero unsafe public policies.",
    "Use RLS result to unblock fake customer gate.",
    "Keep cleanup script ready.",
    "Keep frontend fallback static/demo data.",
    "Enable /client/dashboard as first live-data test route.",
    "Do not switch all client routes at once.",
    "Keep emails draft-only.",
    "Diagnose Resend 403.",
    "Confirm the cause: key/account permission plus .cc / .com sender mismatch.",
    "Add fix instructions for goclearonline.com.",
    "Require updated/re-scoped API key.",
    "Require verified sender/domain.",
    "Create test email approval card.",
    "Do not send onboarding email until approved.",
    "Prepare onboarding email draft.",
    "Add Resend status to System Health.",
    "Create configs/research_source_registry.json.",
    "Create configs/research_discovery_topics.json.",
    "Create configs/research_safety_policy.json.",
    "Create configs/research_scoring_policy.json.",
    "Add YouTube as one source lane, not the whole research engine.",
    "Add GitHub repo/topic discovery.",
    "Add NotebookLM export/import.",
    "Add old Nexus research recovery.",
    "Add local transcript/source-file discovery.",
    "Add payment/monetization source discovery.",
    "Add credit/funding/grant research lanes.",
    "Add trading research lanes.",
    "Add marketing/content/SEO lanes.",
    "Score sources for revenue potential.",
    "Score sources for client value.",
    "Score sources for Nexus upgrade value.",
    "Score sources for credit/funding value.",
    "Score sources for content value.",
    "Score sources for affiliate/partner value.",
    "Create research memory exports and Supabase-ready records.",
    "Keep YouTube API metadata active.",
    "Keep yt-dlp as metadata/subtitle probe only.",
    "Create transcript dropzone.",
    "Use data/sources/youtube_transcripts/approved/zbAmmnMh5ew.txt.",
    "Import transcript only after approved .txt exists.",
    "Recover NotebookLM legacy adapter into v2.",
    "Create NotebookLM approved export dropzone.",
    "Import selected NotebookLM exports if present.",
    "Export Nexus research bundles for NotebookLM.",
    "Create Ray Review cards for every new source/import action.",
]


def schedule(automation_id: str, command: str, category: str = "operations", cadence: str = "daily") -> dict:
    return {
        "automation_id": automation_id,
        "name": automation_id.replace("_", " ").title(),
        "category": category,
        "enabled": True,
        "schedule_type": "interval",
        "cadence": cadence,
        "command": command,
        "mode": "internal_safe",
        "approval_required": False,
        "external_action_allowed": False,
        "max_runtime_minutes": 10,
        "cooldown_minutes": 1440 if cadence == "daily" else 240,
        "quota_policy": None,
        "required_env_vars": [],
        "output_reports": [],
        "proof_events": True,
        "dashboard_visible": True,
        "failure_behavior": "log_and_continue",
        "next_run_hint": cadence,
        "safety_notes": "Internal reports and dry-run records only; no external action.",
    }


def build() -> dict:
    checklist = {
        "version": 1,
        "generated_at": now(),
        "status_values": ["completed", "partially_completed", "blocked_by_approval", "blocked_by_missing_credential", "blocked_by_missing_source", "blocked_by_missing_cli", "blocked_by_safety_gate", "not_applicable"],
        "steps": [{"step": index, "title": title} for index, title in enumerate(STEPS, 1)],
    }
    assert len(checklist["steps"]) == 100
    write_json(ROOT / "configs" / "nexus_100_step_activation_checklist.json", checklist)

    source_registry = {
        "version": 1,
        "lanes": [
            {"lane_id": "youtube", "approved": True, "source_paths": ["configs/youtube_source_targets.json", "configs/youtube_research_channels.json", "data/sources/youtube_transcripts/approved"], "network_mode": "approved_metadata_only"},
            {"lane_id": "github", "approved": True, "source_paths": ["configs/repo_research_targets.json", "configs/payment_repo_targets.json"], "network_mode": "seed_records_only"},
            {"lane_id": "notebooklm", "approved": True, "source_paths": ["data/sources/notebooklm_exports/approved", "data/sources/notebooklm_notes"], "network_mode": "local_only"},
            {"lane_id": "notebooklm_official_api", "approved": False, "source_paths": ["configs/notebooklm_automation_registry.json"], "network_mode": "blocked_missing_official_connector"},
            {"lane_id": "notebooklm_local_cli", "approved": False, "source_paths": ["configs/notebooklm_automation_registry.json"], "network_mode": "unavailable"},
            {"lane_id": "notebooklm_selected_notebooks", "approved": True, "source_paths": ["configs/notebooklm_selected_notebooks.json"], "network_mode": "registry_only"},
            {"lane_id": "notebooklm_legacy_adapter", "approved": True, "source_paths": [str(Path.home() / "nexuslive/lib/notebooklm_ingest_adapter.py")], "network_mode": "local_only"},
            {"lane_id": "notebooklm_watched_exports", "approved": True, "source_paths": ["data/sources/notebooklm_exports/approved"], "network_mode": "local_only"},
            {"lane_id": "old_nexus", "approved": True, "source_paths": [str(Path.home() / "nexuslive")], "network_mode": "local_only"},
            {"lane_id": "local_sources", "approved": True, "source_paths": ["data/sources"], "network_mode": "local_only"},
            {"lane_id": "payments", "approved": True, "source_paths": ["configs/payment_repo_targets.json"], "network_mode": "seed_records_only"},
            {"lane_id": "credit_funding_grants", "approved": True, "source_paths": ["reports/runtime/supabase_ready"], "network_mode": "local_only"},
            {"lane_id": "trading", "approved": True, "source_paths": ["scripts/trading", str(Path.home() / "nexuslive" / "nexus-strategy-lab")], "network_mode": "local_only"},
            {"lane_id": "oanda_demo_market_data", "approved": True, "source_paths": ["reports/runtime/oanda_demo_pricing_check_latest.json"], "network_mode": "practice_read_only"},
            {"lane_id": "oanda_demo_strategy_results", "approved": True, "source_paths": ["reports/runtime/oanda_demo_trade_smoke_test_latest.json"], "network_mode": "practice_test_results"},
            {"lane_id": "vibe_oanda_demo_bridge", "approved": True, "source_paths": ["reports/runtime/vibe_oanda_demo_bridge_latest.json"], "network_mode": "local_and_practice_test"},
            {"lane_id": "trading_demo_outcomes", "approved": True, "source_paths": ["reports/runtime/vibe_oanda_demo_strategy_smoke_test_latest.json"], "network_mode": "practice_test_results"},
            {"lane_id": "marketing_content_seo", "approved": True, "source_paths": ["scripts/research", "reports/runtime/supabase_ready"], "network_mode": "local_only"},
        ],
    }
    write_json(ROOT / "configs" / "research_source_registry.json", source_registry)
    write_json(ROOT / "configs" / "research_discovery_topics.json", {"version": 1, "topics": ["$97 readiness review", "monthly credit membership", "credit repair workflow", "business credit readiness", "business funding", "grants", "lender preparation", "entity bankability", "Stripe checkout", "payment onboarding", "AI automation", "NotebookLM research", "YouTube metadata", "Oanda practice", "paper backtesting", "SEO lead magnets", "affiliate partner offers"]})
    write_json(ROOT / "configs" / "research_safety_policy.json", {"version": 1, "approved_only": True, "allow_metadata": True, "allow_local_text": True, "blocked": ["publish", "contact", "email_send", "social_post", "trade", "funding_application", "video_download", "audio_download", "cookies", "automatic_repo_install"], "approval_required_for": ["new_network_lane", "high_risk_ingest", "client_visible_guidance", "external_action"]})
    write_json(ROOT / "configs" / "research_scoring_policy.json", {"version": 1, "dimensions": ["revenue_potential", "immediate_actionability", "client_value", "Nexus_upgrade_value", "credit_funding_value", "content_value", "affiliate_partner_value"], "effort_dimension": "implementation_effort", "risk_dimension": "risk_level", "score_range": [0, 100]})

    safety = {
        "version": 1,
        "global_blocked_commands": ["stripe --live", "supabase db reset --linked", "supabase db push --include-all", "oanda live order", "yt-dlp video download", "yt-dlp audio download", "git add .env", "service role in frontend"],
        "approval_required_actions": ["external writes", "payments confirmation", "email sending", "social publishing", "database insertion", "trading orders", "permanent scheduler installation"],
        "default_external_action_allowed": False,
    }
    write_json(ROOT / "configs" / "cli_safety_policy.json", safety)

    schedule_path = ROOT / "configs" / "automation_schedule_registry.json"
    current = json.loads(schedule_path.read_text()) if schedule_path.exists() else {"version": 1, "automations": []}
    additions = [
        schedule("cli_capability_audit_daily", "python3 scripts/activation/audit_local_cli_capabilities.py --json"),
        schedule("nexus_tool_access_validation_daily", "python3 scripts/activation/validate_cli_tool_access.py --json"),
        schedule("100_step_activation_status_daily", "python3 scripts/activation/verify_100_step_activation_status.py --json"),
        schedule("research_source_discovery", "python3 scripts/research/run_research_source_discovery.py --json --safe-internal", "research"),
        schedule("research_source_scoring", "python3 scripts/research/score_research_sources.py --json", "research"),
        schedule("research_opportunity_extraction", "python3 scripts/research/extract_research_opportunities.py --json", "research"),
        schedule("research_memory_export", "python3 scripts/research/build_research_memory_exports.py --json", "research"),
        schedule("research_ray_review_cards", "python3 scripts/research/build_research_ray_review_cards.py --json", "research", "every 4 hours"),
        schedule("research_hermes_brief", "python3 scripts/research/build_research_hermes_brief.py --json", "research", "every 4 hours"),
        schedule("stripe_status_check", "python3 scripts/payments/audit_stripe_cli_and_env.py --json", "payments"),
        schedule("payment_onboarding_dry_run", "python3 scripts/payments/run_payment_to_customer_onboarding_dry_run.py --json", "payments"),
        schedule("resend_connection_audit", "python3 scripts/activation/audit_resend_connection.py --json", "communications"),
        schedule("rls_verification_packet_refresh", "python3 scripts/supabase/verify_production_rls_cli.py --json", "database"),
        schedule("fake_customer_gate_refresh", "python3 scripts/client_flow/prepare_persistent_fake_customer_insert_gate.py --json", "client_flow"),
        schedule("frontend_live_data_readiness", "python3 scripts/client_flow/prepare_frontend_live_data_readiness.py --json", "client_flow"),
        schedule("oanda_demo_readonly_check", "python3 scripts/trading/run_oanda_demo_readonly_check.py --json", "trading"),
        schedule("vibe_paper_backtest_dry_run", "python3 scripts/trading/run_vibe_paper_backtest_dry_run.py --json", "trading"),
        schedule("notebooklm_cli_discovery_daily", "python3 scripts/activation/find_notebooklm_cli_connectors.py --json", "research"),
        schedule("notebooklm_selected_notebook_sync_daily", "python3 scripts/activation/sync_selected_notebooklm_notebooks.py --json", "research"),
        schedule("notebooklm_research_memory_build_daily", "python3 scripts/activation/build_notebooklm_research_memory.py --json", "research"),
        schedule("notebooklm_ray_review_cards_daily", "python3 scripts/activation/build_notebooklm_ray_review_cards.py --json", "research"),
        schedule("notebooklm_hermes_brief_daily", "python3 scripts/activation/build_notebooklm_hermes_brief.py --json", "research"),
        schedule("oanda_demo_account_check_daily", "python3 scripts/trading/run_oanda_demo_account_check.py --json", "trading"),
        schedule("oanda_demo_pricing_check_daily", "python3 scripts/trading/run_oanda_demo_pricing_check.py --json", "trading"),
        schedule("oanda_demo_instruments_check_daily", "python3 scripts/trading/run_oanda_demo_instruments_check.py --json", "trading"),
        schedule("vibe_paper_backtest_dry_run_daily", "python3 scripts/trading/run_vibe_paper_backtest_dry_run.py --json", "trading"),
        schedule("vibe_oanda_demo_bridge_dry_run_daily", "python3 scripts/trading/run_vibe_oanda_demo_bridge_dry_run.py --json", "trading"),
        schedule("trading_demo_outcomes_report_daily", "python3 scripts/activation/build_oanda_vibe_notebooklm_activation_reports.py --json", "trading"),
    ]
    additions.extend([
        {**schedule("oanda_recurring_demo_order_execution", "", "trading"), "enabled": False, "schedule_type": "manual", "mode": "approval_gated_demo_execution", "approval_required": True, "external_action_allowed": True, "safety_notes": "Recurring demo orders require a separate Ray approval."},
        {**schedule("vibe_oanda_demo_strategy_execution", "", "trading"), "enabled": False, "schedule_type": "manual", "mode": "approval_gated_demo_execution", "approval_required": True, "external_action_allowed": True, "safety_notes": "Strategy execution beyond the approved smoke test is blocked."},
        {**schedule("notebooklm_unofficial_browser_automation", "", "research"), "enabled": False, "schedule_type": "manual", "mode": "approval_gated_external", "approval_required": True, "external_action_allowed": False, "safety_notes": "Consumer browser/cookie automation remains blocked."}
    ])
    by_id = {item["automation_id"]: item for item in current.get("automations", [])}
    for item in additions:
        by_id[item["automation_id"]] = item
    current["automations"] = list(by_id.values())
    current["version"] = max(2, current.get("version", 1))
    write_json(schedule_path, current)
    return {"ok": True, "generated_at": now(), "checklist_steps": 100, "research_lanes": len(source_registry["lanes"]), "schedules": len(current["automations"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build()
    print(json.dumps(result, indent=2) if args.json else result)
