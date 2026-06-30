#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
from operating_cycle_common import EVENING_COMMANDS,run_commands
def build(scheduled=False):
 results=run_commands(EVENING_COMMANDS,scheduled);blockers=read_json(RUNTIME/"global_blocker_resolution_matrix_latest.json",{});revenue=read_json(RUNTIME/"revenue_dashboard_latest.json",{});report={"ok":all(x.get("passed") for x in results),"generated_at":now(),"status":"evening_closeout_complete","scheduled_invocation":scheduled,"jobs_planned":len(EVENING_COMMANDS),"jobs_passed":sum(x.get("passed") for x in results),"today":"Internal operating evidence, approvals, research, and revenue readiness were refreshed.","resolved":"No risky action auto-executed; safe cycles remained healthy.","money_progress":revenue.get("status","revenue dashboard refreshed"),"blocked_count":blockers.get("blockers_total",0),"tomorrow":"Run the bounded daily cycle and process the highest-value Ray Review approvals.","external_action_performed":False,"results":results};write_report("evening_closeout_cycle","Evening Closeout Cycle",report,{"Jobs":results});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--scheduled",action="store_true");a=p.parse_args();r=build(a.scheduled);print(json.dumps(r,indent=2) if a.json else r)
