#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,read_json,write_report  # noqa:E402
from setup_final_daily_configs import build as setup_configs
def build():
 setup_configs();config=read_json(ROOT/"configs/nexus_100_step_activation_checklist.json",{});steps=config.get("steps",[]);report={"ok":len(steps)==100,"generated_at":now(),"status":"exact_100_step_checklist_built","steps_count":len(steps),"allowed_statuses":config.get("status_values",[]),"external_action_performed":False};write_report("nexus_100_step_activation_checklist","Nexus 100-Step Activation Checklist",report,{"Steps":[f"{x['step']}. {x['title']}" for x in steps]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 1)
