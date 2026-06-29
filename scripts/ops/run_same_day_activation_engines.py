#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from same_day_common import ROOT,now,write_report  # noqa:E402

COMMANDS=[
 ("env_audit",["python3","scripts/ops/audit_env_connectors.py","--json"]),("env_recovery",["python3","scripts/ops/prepare_safe_env_recovery.py","--json"]),
 ("connector_harness",["python3","scripts/connectors/run_connector_test_harness.py","--json"]),("youtube_metadata",["python3","scripts/activation/run_youtube_metadata_intake.py","--json"]),
 ("youtube_transcripts",["python3","scripts/activation/run_youtube_transcript_import.py","--json"]),("youtube_review",["python3","scripts/activation/run_youtube_review_proof.py","--json"]),
 ("supabase_readiness",["python3","scripts/supabase/audit_supabase_readiness.py","--json"]),("supabase_migration",["python3","scripts/supabase/generate_client_portal_migrations.py","--json"]),
 ("supabase_insert_plan",["python3","scripts/supabase/prepare_supabase_insert_runner.py","--json"]),("supabase_dry_run",["python3","scripts/supabase/run_supabase_insert_dry_run.py","--json"]),
 ("client_hardening",["python3","scripts/ops/build_same_day_foundation.py","--json"]),("dispute_sandbox",["python3","scripts/disputes/prepare_dispute_sandbox_upgrade_plan.py","--json"]),
 ("meta_plan",["python3","scripts/social/prepare_meta_connector_validation_plan.py","--json"]),("payment_crm",["python3","scripts/monetization/prepare_payment_crm_path.py","--json"]),
 ("ray_review",["python3","scripts/approvals/prioritize_ray_review_cards.py","--json"]),("full_activation",["python3","scripts/activation/run_nexus_full_activation.py","--run-all","--json"]),
 ("continuous_once",["python3","scripts/activation/run_nexus_continuous_loop.py","--once","--json","--safe-internal","--local-only","--feedback-enabled"])]


def run()->dict:
 results=[]
 for name,cmd in COMMANDS:
  p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=180)
  results.append({"engine":name,"found":(ROOT/cmd[1]).exists(),"ran":True,"passed":p.returncode==0,"exit_code":p.returncode,"command":" ".join(cmd),"stdout_tail":p.stdout[-800:],"stderr_tail":p.stderr[-400:],"external_action_attempted":False})
 report={"ok":all(x["passed"] for x in results),"generated_at":now(),"status":"internal_active","engines_found":sum(x["found"] for x in results),"engines_run":len(results),"engines_passed":sum(x["passed"] for x in results),"engines_failed":sum(not x["passed"] for x in results),"results":results,"external_action_performed":False,"summary":f"Ran {len(results)} same-day engines; {sum(x['passed'] for x in results)} passed."}
 write_report("same_day_activation_engine_run","Same-Day Activation Engine Run",report,{"Engine results":results});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=run();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0 if r["ok"] else 1
if __name__=="__main__":raise SystemExit(main())
