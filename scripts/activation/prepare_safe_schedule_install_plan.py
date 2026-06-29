#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess
from youtube_engine_common import ROOT,SUPABASE_READY,now,record,write_json,write_report
def build():
 plist=ROOT/"ops/launchd/com.nexus.continuous-loop.plist";validation=subprocess.run(["plutil","-lint",str(plist)],capture_output=True,text=True) if plist.exists() else None;valid=bool(validation and validation.returncode==0);commands=["mkdir -p ~/Library/LaunchAgents","cp ~/nexus-os-v2/ops/launchd/com.nexus.continuous-loop.plist ~/Library/LaunchAgents/","launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.nexus.continuous-loop.plist","launchctl kickstart gui/$UID/com.nexus.continuous-loop"]
 rollback=["launchctl bootout gui/$UID ~/Library/LaunchAgents/com.nexus.continuous-loop.plist","rm ~/Library/LaunchAgents/com.nexus.continuous-loop.plist"]
 cards=[record("approve-safe-schedule-install","approval_card","Approve safe internal automation schedule install",status="pending_Ray_review",approval_required=True,risk_level="medium")];write_json(SUPABASE_READY/"safe_schedule_approval_cards_latest.json",cards)
 report={"ok":valid,"generated_at":now(),"status":"launchd_plan_ready_not_installed" if valid else "launchd_draft_invalid_or_missing","plist_path":str(plist.relative_to(ROOT)) if plist.exists() else None,"plist_valid":valid,"installed":False,"commands":commands,"rollback_commands":rollback,"safe_internal_only":True,"external_actions_enabled":False,"permanent_daemon_started":False,"approval_required":True,"external_action_performed":False};write_report("safe_schedule_install_plan","Safe Schedule Install Plan",report,{"Install commands":commands,"Rollback commands":rollback});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
