#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shlex,subprocess
from youtube_engine_common import ROOT,SUPABASE_READY,now,read_json,record,write_json,write_report
SAFE_LOOP={"youtube_api_metadata_refresh","youtube_transcript_import","youtube_research_scoring","youtube_research_outputs","notebooklm_source_import","oanda_vibe_trading_audit","stripe_test_payment_status_check","payment_to_client_onboarding_dry_run"}
def build(run_loop_safe=False):
 entries=read_json(ROOT/"configs/automation_schedule_registry.json",{}).get("automations",[]);results=[];executed=[];violations=[]
 for x in entries:
  command=x.get("command");parts=shlex.split(command) if command else [];script=ROOT/parts[1] if len(parts)>1 and parts[0].startswith("python") else None;exists=not command or bool(script and script.exists())
  unsafe=bool(x.get("enabled") and x.get("external_action_allowed") and not x.get("approval_required"))
  if unsafe:violations.append(x["automation_id"])
  results.append({**x,"command_exists":exists,"safety_valid":not unsafe})
  if run_loop_safe and x["automation_id"] in SAFE_LOOP and x.get("enabled") and exists:
   p=subprocess.run(parts,cwd=ROOT,capture_output=True,text=True,timeout=x.get("max_runtime_minutes",10)*60);executed.append({"automation_id":x["automation_id"],"passed":p.returncode==0,"exit_code":p.returncode})
 report={"ok":not violations and all(x["command_exists"] for x in results),"generated_at":now(),"status":"registry_valid","scheduled_automation_count":len(entries),"enabled_internal_automations":sum(x["enabled"] and not x["external_action_allowed"] for x in entries),"approval_gated_automations":sum(x["approval_required"] for x in entries),"blocked_external_automations":sum(not x["enabled"] and x["mode"].startswith("approval_gated") for x in entries),"safety_violations":violations,"loop_safe_automation_ids":sorted(SAFE_LOOP),"loop_safe_executed":executed,"next_recommended_run":"Run cache-aware YouTube, local source imports, connector audits, and payment onboarding dry-run; keep payments and trading execution gated.","external_action_performed":False,"entries":results};write_json(SUPABASE_READY/"automation_schedule_registry_latest.json",results);write_report("automation_schedule_registry","Automation Schedule Registry",report,{"Schedules":results,"Loop-safe executions":executed});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--run-loop-safe",action="store_true");a=p.parse_args();r=build(a.run_loop_safe);print(json.dumps(r,indent=2) if a.json else r);return 0 if r["ok"] else 1
if __name__=="__main__":raise SystemExit(main())
