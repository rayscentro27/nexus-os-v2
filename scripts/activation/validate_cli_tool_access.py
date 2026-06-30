#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 reg=read_json(ROOT/"configs/nexus_tool_access_registry.json",{});policy=read_json(ROOT/"configs/cli_safety_policy.json",{});tools=reg.get("tools",[]);violations=[]
 for item in tools:
  if item.get("access_level") in {"approval_gated","blocked"} and not item.get("requires_approval"):violations.append(item["tool_name"])
 report={"ok":bool(tools) and not violations,"generated_at":now(),"status":"tool_access_validated","tools_validated":len(tools),"safety_violations":violations,"default_deny_external":reg.get("default_deny_external"),"blocked_command_rules":len(policy.get("global_blocked_commands",[])),"external_action_performed":False};write_json(SUPABASE_READY/"nexus_tool_access_validation_latest.json",[report]);write_report("nexus_tool_access_registry","Nexus Tool Access Registry",report,{"Safety policy":policy});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 1)
