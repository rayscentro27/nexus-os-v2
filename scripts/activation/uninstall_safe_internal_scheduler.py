#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess
from pathlib import Path
LABELS=["com.nexus.daily-operating","com.nexus.evening-closeout"]
def build(execute=False):
 removed=[]
 if execute:
  for label in LABELS:
   target=Path.home()/f"Library/LaunchAgents/{label}.plist";subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}",str(target)],capture_output=True)
   if target.exists():target.unlink()
   removed.append(label)
 return {"ok":True,"execute_requested":execute,"removed":removed,"uninstall_command":"python3 scripts/activation/uninstall_safe_internal_scheduler.py --json --execute","external_action_performed":bool(removed)}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--execute",action="store_true");a=p.parse_args();r=build(a.execute);print(json.dumps(r,indent=2) if a.json else r)
