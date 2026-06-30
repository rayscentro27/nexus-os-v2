#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import SUPABASE_READY, write_json, write_report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args()
    tasks=[{'id':f'hermes-task-{i+1}','specialist':name,'status':'queued_local_safe','approval_required':risk,'external_action_performed':False} for i,(name,risk) in enumerate([('Automation Engineer',False),('Research Specialist',False),('Monetization Specialist',False),('Credit Specialist',True),('Marketing Specialist',True)])]
    write_json(SUPABASE_READY/'hermes_task_requests_latest.json',tasks)
    payload={'ok':True,'status':'hermes_task_requests_created','task_requests':len(tasks),'external_action_performed':False}
    write_report('hermes_task_requests','Hermes Task Requests',payload,{'Requests':tasks})
    if a.json: print(json.dumps(payload))
if __name__=='__main__': main()
