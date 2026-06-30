#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,read_json,write_json  # noqa:E402
JOBS={
 "cli_capability_audit_daily":"python3 scripts/activation/audit_local_cli_capabilities.py --json",
 "nexus_tool_access_validation_daily":"python3 scripts/activation/validate_cli_tool_access.py --json",
 "100_step_activation_status_daily":"python3 scripts/activation/verify_100_step_activation_status.py --json",
 "research_source_discovery_daily":"python3 scripts/research/run_research_source_discovery.py --json --safe-internal",
 "research_source_scoring_daily":"python3 scripts/research/score_research_sources.py --json",
 "research_opportunity_extraction_daily":"python3 scripts/research/extract_research_opportunities.py --json",
 "research_memory_export_daily":"python3 scripts/research/build_research_memory_exports.py --json",
 "research_ray_review_cards_daily":"python3 scripts/research/build_research_ray_review_cards.py --json",
 "research_hermes_brief_daily":"python3 scripts/research/build_research_hermes_brief.py --json",
 "notebooklm_watched_folder_sync_daily":"python3 scripts/activation/sync_selected_notebooklm_notebooks.py --json",
 "youtube_api_metadata_refresh_daily":"python3 scripts/activation/run_youtube_api_metadata_intake.py --json",
 "youtube_transcript_import_daily":"python3 scripts/activation/run_youtube_transcript_import.py --json",
 "oanda_demo_account_check_daily":"python3 scripts/trading/run_oanda_demo_account_check.py --json",
 "oanda_demo_pricing_check_daily":"python3 scripts/trading/run_oanda_demo_pricing_check.py --json",
 "oanda_demo_instruments_check_daily":"python3 scripts/trading/run_oanda_demo_instruments_check.py --json",
 "vibe_paper_backtest_dry_run_daily":"python3 scripts/trading/run_vibe_paper_backtest_dry_run.py --json",
 "vibe_oanda_demo_bridge_dry_run_daily":"python3 scripts/trading/run_vibe_oanda_demo_bridge_dry_run.py --json",
 "stripe_test_status_check_daily":"python3 scripts/payments/audit_stripe_cli_and_env.py --json",
 "payment_onboarding_dry_run_daily":"python3 scripts/payments/run_payment_to_customer_onboarding_dry_run.py --json",
 "resend_connection_audit_daily":"python3 scripts/activation/audit_resend_connection.py --json",
 "fake_customer_gate_refresh_daily":"python3 scripts/client_flow/prepare_persistent_fake_customer_insert_gate.py --json",
 "frontend_live_data_readiness_daily":"python3 scripts/client_flow/prepare_frontend_live_data_readiness.py --json",
 "blocker_matrix_update_daily":"python3 scripts/activation/build_global_blocker_resolution_matrix.py --json",
 "ray_review_refresh_daily":"python3 scripts/communication/build_ray_review_queue.py --json",
 "hermes_brief_refresh_daily":"python3 scripts/communication/build_hermes_advisor_inbox.py --json",
 "engine_health_check_daily":"python3 scripts/activation/run_daily_operating_cycle.py --json --scheduled",
 "evening_closeout_daily":"python3 scripts/activation/run_evening_closeout_cycle.py --json --scheduled"
}
def build():
 path=ROOT/"configs/automation_schedule_registry.json";data=read_json(path,{"version":1,"automations":[]});by={x["automation_id"]:x for x in data.get("automations",[])}
 for aid,command in JOBS.items():by[aid]={"automation_id":aid,"name":aid.replace("_"," ").title(),"category":"operating","enabled":True,"schedule_type":"launchd_daily" if aid in {"engine_health_check_daily","evening_closeout_daily"} else "daily_cycle_job","cadence":"daily","command":command,"mode":"internal_safe","approval_required":False,"external_action_allowed":False,"max_runtime_minutes":10,"cooldown_minutes":720,"quota_policy":None,"required_env_vars":[],"output_reports":[],"proof_events":True,"dashboard_visible":True,"failure_behavior":"log_and_continue","next_run_hint":"daily operating cycle","safety_notes":"Internal/read-only/draft/dry-run only; no send, charge, insert, publish, dispute, or order."}
 data["automations"]=list(by.values());data["version"]=max(3,data.get("version",1));data["operating_phase_updated_at"]=now();write_json(path,data)
 roadmap=read_json(ROOT/"configs/nexus_100_step_activation_checklist.json",{});roadmap["current_operating_focus"]={"phase":"automation_communication_monetization","automation":"daily and evening bounded launchd cycles","communication":"Hermes inbox, Ray Review, drafts, receipts","monetization":"$97 readiness-review synthetic journey and research-to-offer pipeline","external_actions_default":"approval_gated","updated_at":now()};write_json(ROOT/"configs/nexus_100_step_activation_checklist.json",roadmap)
 return {"ok":True,"generated_at":now(),"operating_jobs_upserted":len(JOBS),"registry_total":len(data["automations"])}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
