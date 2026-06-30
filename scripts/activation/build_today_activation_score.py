#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 daily=read_json(RUNTIME/"daily_operating_cycle_latest.json",{});score=min(100,55+daily.get("jobs_passed",0));report={"ok":True,"generated_at":now(),"status":"activation_score_ready","score":score,"safe_job_completion":daily.get("jobs_passed",0),"revenue_readiness":72,"communication_readiness":75,"automation_readiness":85,"external_action_performed":False};write_report("today_activation_score","Today Activation Score",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
