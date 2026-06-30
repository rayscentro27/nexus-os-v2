#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'activation'))
from activation_common import ROOT, write_report

REPORTS=[
('final_daily_activation_master_latest.md','Final Daily Activation Master','Operations'),('operating_activation_master_latest.md','Operating Activation Master','Operations'),('oanda_vibe_notebooklm_master_latest.md','Oanda / Vibe / NotebookLM Master','Connectors'),('revenue_dashboard_latest.md','Revenue Dashboard','Monetization'),('ray_review_queue_latest.md','Ray Review Queue','Approvals'),('hermes_advisor_inbox_latest.md','Hermes Advisor Inbox','Communication'),('research_to_money_pipeline_latest.md','Research to Money Pipeline','Research'),('safe_internal_scheduler_verification_latest.md','Safe Scheduler Verification','Automation'),('cli_capability_registry_latest.md','CLI Capability Registry','Tools'),('nexus_100_step_activation_status_latest.md','100-Step Activation Status','Operations'),('global_blocker_resolution_matrix_latest.md','Global Blocker Matrix','Operations'),('operating_frontend_status_latest.md','Frontend Operating Status','System'),('all_blockers_resolution_master_latest.md','All Blockers Resolution','Operations')]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); rows=[]
    for filename,title,category in REPORTS:
        path=ROOT/'reports/manual_publish'/filename
        rows.append({'id':filename.removesuffix('_latest.md'),'title':title,'category':category,'path':str(path.relative_to(ROOT)),'modified':path.stat().st_mtime_ns and __import__('datetime').datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat() if path.exists() else None,'available':path.exists(),'command':'python3 scripts/activation/run_daily_operating_cycle.py --json','content':path.read_text(errors='replace')[:100000] if path.exists() else ''})
    (ROOT/'src/data/reportRegistry.js').write_text('export const reportRegistry = '+json.dumps(rows,indent=2)+';\n')
    payload={'ok':True,'status':'report_registry_ready','reports_total':len(rows),'reports_available':sum(x['available'] for x in rows),'missing':sum(not x['available'] for x in rows),'external_action_performed':False}
    write_report('report_registry','Nexus Report Registry',payload,{'Reports':rows})
    if a.json: print(json.dumps(payload))
if __name__=='__main__': main()
