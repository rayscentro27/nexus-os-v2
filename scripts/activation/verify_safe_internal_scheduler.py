#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,write_report  # noqa:E402
LABELS=["com.nexus.daily-operating","com.nexus.evening-closeout"]
def build():
 uid=os.getuid();rows=[]
 for label in LABELS:
  p=subprocess.run(["launchctl","print",f"gui/{uid}/{label}"],capture_output=True,text=True);rows.append({"label":label,"loaded":p.returncode==0,"last_exit_status_reported":"last exit code" in p.stdout.lower()})
 ok=all(x["loaded"] for x in rows);report={"ok":ok,"generated_at":now(),"status":"safe_internal_scheduler_verified" if ok else "safe_internal_scheduler_not_fully_loaded","scheduler_type":"launchd","loaded_count":sum(x["loaded"] for x in rows),"expected_count":len(rows),"agents":rows,"external_actions_allowed":False,"external_action_performed":False};write_report("safe_internal_scheduler_verification","Safe Internal Scheduler Verification",report,{"Agents":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
