#!/usr/bin/env python3
from __future__ import annotations
import os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

DAILY_COMMANDS=[
 ("cli_audit",["python3","scripts/activation/audit_local_cli_capabilities.py","--json"]),
 ("tool_access",["python3","scripts/activation/validate_cli_tool_access.py","--json"]),
 ("checklist",["python3","scripts/activation/verify_100_step_activation_status.py","--json"]),
 ("research_discovery",["python3","scripts/research/run_research_source_discovery.py","--json","--safe-internal"]),
 ("research_scoring",["python3","scripts/research/score_research_sources.py","--json"]),
 ("research_opportunities",["python3","scripts/research/extract_research_opportunities.py","--json"]),
 ("research_money",["python3","scripts/research/build_research_to_money_pipeline.py","--json"]),
 ("research_memory",["python3","scripts/research/build_research_memory_exports.py","--json"]),
 ("notebooklm_sync",["python3","scripts/activation/sync_selected_notebooklm_notebooks.py","--json"]),
 ("youtube_metadata",["python3","scripts/activation/run_youtube_api_metadata_intake.py","--json"]),
 ("youtube_transcripts",["python3","scripts/activation/run_youtube_transcript_import.py","--json"]),
 ("oanda_account",["python3","scripts/trading/run_oanda_demo_account_check.py","--json"]),
 ("oanda_pricing",["python3","scripts/trading/run_oanda_demo_pricing_check.py","--json"]),
 ("oanda_instruments",["python3","scripts/trading/run_oanda_demo_instruments_check.py","--json"]),
 ("vibe_backtest",["python3","scripts/trading/run_vibe_paper_backtest_dry_run.py","--json"]),
 ("vibe_bridge_dry",["python3","scripts/trading/run_vibe_oanda_demo_bridge_dry_run.py","--json"]),
 ("stripe_status",["python3","scripts/payments/audit_stripe_cli_and_env.py","--json"]),
 ("payment_dry_run",["python3","scripts/payments/run_payment_to_customer_onboarding_dry_run.py","--json"]),
 ("resend_audit",["python3","scripts/activation/audit_resend_connection.py","--json"]),
 ("fake_customer_gate",["python3","scripts/client_flow/prepare_persistent_fake_customer_insert_gate.py","--json"]),
 ("frontend_readiness",["python3","scripts/client_flow/prepare_frontend_live_data_readiness.py","--json"]),
 ("blocker_matrix",["python3","scripts/activation/build_global_blocker_resolution_matrix.py","--json"]),
 ("ray_review",["python3","scripts/communication/build_ray_review_queue.py","--json"]),
 ("hermes_inbox",["python3","scripts/communication/build_hermes_advisor_inbox.py","--json"]),
 ("revenue_dashboard",["python3","scripts/monetization/build_revenue_dashboard.py","--json"]),
]
EVENING_COMMANDS=[
 ("blocker_matrix",["python3","scripts/activation/build_global_blocker_resolution_matrix.py","--json"]),
 ("checklist",["python3","scripts/activation/verify_100_step_activation_status.py","--json"]),
 ("revenue_dashboard",["python3","scripts/monetization/build_revenue_dashboard.py","--json"]),
 ("ray_review",["python3","scripts/communication/build_ray_review_queue.py","--json"]),
 ("hermes_inbox",["python3","scripts/communication/build_hermes_advisor_inbox.py","--json"]),
 ("plain_status",["python3","scripts/communication/build_plain_english_status.py","--json"]),
]
def run_commands(commands,scheduled=False,max_seconds=2700):
 env=dict(os.environ)
 if scheduled:env["NEXUS_RUNTIME_ONLY"]="1"
 started=time.monotonic();results=[]
 for name,cmd in commands:
  script=ROOT/cmd[1]
  if not script.exists():results.append({"job":name,"ran":False,"passed":False,"status":"script_missing"});continue
  remaining=max_seconds-(time.monotonic()-started)
  if remaining<=1:results.append({"job":name,"ran":False,"passed":False,"status":"cycle_timeout"});break
  try:
   p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=min(remaining,600));results.append({"job":name,"ran":True,"passed":p.returncode==0,"exit_code":p.returncode,"status":"passed" if p.returncode==0 else "nonfatal_blocker"})
  except subprocess.TimeoutExpired:results.append({"job":name,"ran":True,"passed":False,"status":"timeout"})
 return results
