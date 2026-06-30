#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,plistlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,read_json,write_report  # noqa:E402
LABELS=["com.nexus.daily-operating","com.nexus.evening-closeout"]
def valid_plist(path):
 try:
  with path.open("rb") as f:payload=plistlib.load(f)
  args=payload.get("ProgramArguments",[]);return bool(args and "--scheduled" in args and not any(x in " ".join(args) for x in ("--live","trade_smoke","email_send","social_publish")))
 except Exception:return False
def build(internal_safe_only=False):
 policy=read_json(ROOT/"configs/safe_scheduler_policy.json",{});sources={label:ROOT/f"ops/launchd/{label}.plist" for label in LABELS};valid=internal_safe_only and policy.get("internal_safe_only") and all(valid_plist(x) for x in sources.values());installed=[];errors=[];uid=os.getuid();dest=Path.home()/"Library/LaunchAgents";dest.mkdir(parents=True,exist_ok=True)
 if valid:
  for label,source in sources.items():
   target=dest/source.name;subprocess.run(["launchctl","bootout",f"gui/{uid}",str(target)],capture_output=True);shutil.copy2(source,target);p=subprocess.run(["launchctl","bootstrap",f"gui/{uid}",str(target)],capture_output=True,text=True)
   if p.returncode==0:installed.append(label)
   else:errors.append({"label":label,"error":"launchctl_bootstrap_failed"})
 report={"ok":valid and len(installed)==len(LABELS),"generated_at":now(),"status":"safe_internal_scheduler_installed" if len(installed)==len(LABELS) else "install_ready_manual_required" if valid else "scheduler_policy_validation_failed","scheduler_type":"launchd","installed_labels":installed,"frequency":{"daily":"08:00 local","evening":"18:00 local"},"internal_safe_only":True,"external_actions_allowed":False,"manual_install_command":"python3 scripts/activation/install_safe_internal_scheduler.py --json --internal-safe-only","errors":errors,"external_action_performed":bool(installed)};write_report("safe_internal_scheduler_activation","Safe Internal Scheduler Activation",report,{"Installed labels":installed});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--internal-safe-only",action="store_true");a=p.parse_args();r=build(a.internal_safe_only);print(json.dumps(r,indent=2) if a.json else r)
