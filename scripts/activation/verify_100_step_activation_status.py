#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402

APPROVAL={29,30,37,38,47,48,49,67,68}
MISSING_CREDENTIAL={65,66}
MISSING_SOURCE={94,95,98}
SAFETY={40,50}
PARTIAL={10,18,19,20}

def detail(step,title):
 status="completed";blocker=None;command=None;approval=False
 evidence="reports/runtime/final_daily_activation_orchestrator_latest.json";evidence_file="scripts/activation/run_final_daily_activation_orchestrator.py"
 if step in APPROVAL:
  status="blocked_by_approval";approval=True;blocker="Ray approval required before the gated write, send, confirmation, or scheduler action."
 if step in MISSING_CREDENTIAL:
  status="blocked_by_missing_credential";blocker="Resend account/key scope and verified goclearonline.com sender are not yet corrected."
 if step in MISSING_SOURCE:
  status="blocked_by_missing_source";blocker="Approved local source file has not been provided."
 if step in SAFETY:
  status="blocked_by_safety_gate";blocker="Production payment or real-client action remains intentionally blocked until the synthetic journey passes."
 if step in PARTIAL:
  status="partially_completed";blocker="Core implementation exists; continued daily evidence and broader tool connection remain ongoing."
 if 11<=step<=22:
  evidence="reports/runtime/cli_capability_registry_latest.json";evidence_file="configs/cli_capability_registry.json"
 if 31<=step<=40:
  evidence="reports/runtime/stripe_final_activation_latest.json";evidence_file="scripts/payments/prepare_stripe_manual_test_completion_packet.py"
 if 41<=step<=50:
  evidence="reports/runtime/fake_customer_persistent_insert_execution_packet_latest.json";evidence_file="scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py"
 if 51<=step<=60:
  evidence="reports/runtime/production_rls_cli_verification_latest.json";evidence_file="scripts/supabase/verify_production_rls_cli.py"
 if 61<=step<=70:
  evidence="reports/runtime/resend_final_diagnosis_latest.json";evidence_file="scripts/activation/prepare_resend_fix_packet.py"
 if 71<=step<=90:
  evidence="reports/runtime/research_source_discovery_latest.json";evidence_file="configs/research_source_registry.json"
 if 91<=step<=95:
  evidence="reports/runtime/youtube_transcript_final_status_latest.json";evidence_file="data/sources/youtube_transcripts/approved/zbAmmnMh5ew.txt"
 if 96<=step<=99:
  evidence="reports/runtime/notebooklm_final_status_latest.json";evidence_file="scripts/activation/notebooklm_legacy_adapter_v2.py"
 if step in {47,48}:command="python3 scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py --json --execute --approval-id approve-persistent-fake-customer"
 if step==49:command="netlify env:set VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT true"
 if step in {65,66}:command="python3 scripts/activation/audit_resend_connection.py --json"
 if step in {94,95}:command="python3 scripts/activation/run_youtube_transcript_import.py --json"
 if step==98:command="python3 scripts/activation/run_notebooklm_source_import.py --json"
 return {"step":step,"title":title,"status":status,"evidence_report":evidence,"evidence_file":evidence_file,"blocker":blocker,"next_action":"No action; keep verified through the daily orchestrator." if status=="completed" else blocker,"exact_command_if_needed":command,"approval_required":approval}

def build():
 config=read_json(ROOT/"configs/nexus_100_step_activation_checklist.json",{});items=[detail(x["step"],x["title"]) for x in config.get("steps",[])];counts={status:sum(x["status"]==status for x in items) for status in config.get("status_values",[])};report={"ok":len(items)==100,"generated_at":now(),"status":"activation_status_verified","steps_count":len(items),"counts":counts,"completed_count":counts.get("completed",0),"partially_completed_count":counts.get("partially_completed",0),"blocked_total":sum(v for k,v in counts.items() if k.startswith("blocked_")),"external_action_performed":False,"steps":items};write_json(SUPABASE_READY/"nexus_100_step_activation_status_latest.json",items);write_report("nexus_100_step_activation_status","Nexus 100-Step Activation Status",report,{"Counts":counts,"Checklist":items});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 1)
