#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
from operating_cycle_common import DAILY_COMMANDS,run_commands
def build(scheduled=False):
 results=run_commands(DAILY_COMMANDS,scheduled);blockers=read_json(RUNTIME/"global_blocker_resolution_matrix_latest.json",{});revenue=read_json(RUNTIME/"revenue_dashboard_latest.json",{});research=read_json(RUNTIME/"research_opportunities_latest.json",{});report={"ok":all(x.get("passed") for x in results),"generated_at":now(),"status":"daily_operating_cycle_complete","scheduled_invocation":scheduled,"jobs_planned":len(DAILY_COMMANDS),"jobs_passed":sum(x.get("passed") for x in results),"what_changed_overnight":"Safe source, connector, readiness, communication, and revenue reports refreshed.","blocked_count":blockers.get("blockers_total",0),"approval_ready":"Ray Review queue refreshed; all send/write/order actions remain gated.","money_today":revenue.get("exact_next_money_action","Complete the $97 test Checkout and approve synthetic onboarding proof."),"safe_today":["research discovery/scoring","draft generation","Oanda practice reads","Vibe paper backtest","NotebookLM watched-folder sync"],"hermes_recommends":"Prioritize the $97 readiness-review synthetic journey and revenue recovery drafts.","ray_needs_to_approve":["synthetic customer insert","test Checkout completion","Resend fix/test","safe scheduler changes"],"research_opportunities":research.get("opportunities_created",0),"exact_next_command":"python3 scripts/activation/run_daily_operating_cycle.py --json","external_action_performed":False,"results":results};write_report("daily_operating_cycle","Daily Operating Cycle",report,{"Jobs":results});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--scheduled",action="store_true");a=p.parse_args();r=build(a.scheduled);print(json.dumps(r,indent=2) if a.json else r)
