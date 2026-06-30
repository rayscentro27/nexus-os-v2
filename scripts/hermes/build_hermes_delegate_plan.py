#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import write_report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); ap.add_argument('--sample',default='next 100 steps'); a=ap.parse_args()
    jobs=[{'lane':'Automation Engineer','class':'safe_internal','job':'Map and verify internal jobs'},{'lane':'Monetization Specialist','class':'safe_internal','job':'Rank current revenue opportunities'},{'lane':'Credit Specialist','class':'approval_gated','job':'Review client readiness path'},{'lane':'Marketing Specialist','class':'approval_gated','job':'Prepare drafts only'},{'lane':'Hermes CEO Advisor','class':'blocked','job':'Hold charges, sends, publishing, inserts, disputes, and live trading'}]
    payload={'ok':True,'status':'delegation_plan_ready','prompt':a.sample,'jobs_total':len(jobs),'safe_internal_jobs':2,'approval_gated_jobs':2,'blocked_jobs':1,'external_action_performed':False}
    write_report('hermes_delegation_plan','Hermes Delegation Plan',payload,{'Specialist assignments':jobs,'Exact next commands':['python3 scripts/hermes/create_hermes_task_requests.py --json']})
    write_report('hermes_delegate_plan','Hermes Delegate Plan',payload,{'Specialist assignments':jobs,'Exact next commands':['python3 scripts/hermes/create_hermes_task_requests.py --json']})
    if a.json: print(json.dumps(payload))
if __name__=='__main__': main()
