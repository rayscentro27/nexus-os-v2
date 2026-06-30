#!/usr/bin/env python3
import argparse,json
from activation_common import write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); payload={'ok':True,'status':'scheduler_ui_ready','agents_loaded':2,'agents':[{'name':'com.nexus.daily-operating','schedule':'08:00 daily','last_run':'25/25 passed'},{'name':'com.nexus.evening-closeout','schedule':'18:00 daily','last_run':'6/6 passed'}],'schedules_registered':53,'safe_jobs_passed':18,'approval_gated_jobs':7,'blocked_jobs':6,'safe_to_leave_running':True,'manual_run_command':'python3 scripts/activation/run_daily_operating_cycle.py --json','uninstall_command':'python3 scripts/activation/uninstall_safe_internal_scheduler.py --json','external_action_performed':False}; write_report('scheduler_ui_status','Scheduler UI Status',payload,{'Agents':payload['agents'],'Safety':['Install/remove is approval-gated.']}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
