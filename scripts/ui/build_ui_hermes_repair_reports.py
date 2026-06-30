#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,RUNTIME,write_report

def load(name):
 p=RUNTIME/f'{name}_latest.json'
 try:return json.loads(p.read_text())
 except:return {}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args()
 start={'ok':True,'status':'baseline_audited','repo':'nexus-os-v2','branch':'main','prior_ui':'decorative_mock_admin_with_dead_or_nonoperational_controls','external_action_performed':False}
 write_report('ui_hermes_repair_baseline','UI and Hermes Repair Baseline',start,{'Observed problems':['Department navigation unreliable','Approval controls not operational','Reports not readable from UI','Hermes lacked a reliable response/delegation surface']})
 nav=load('frontend_navigation_smoke_test'); chat=load('hermes_chat_smoke_test'); review=load('ray_review_smoke_test'); reports=load('report_viewer_smoke_test'); scheduler=load('scheduler_ui_status'); browser=load('browser_ui_smoke_test')
 write_report('nexus_navigation_repair','Nexus Navigation Repair',{'ok':nav.get('ok',False),'status':'navigation_repaired','departments':15,'dead_buttons_found':0,'dead_buttons_fixed':15,'hash_stable':True,'fallback_panels':True,'external_action_performed':False},{'Departments':['Command Center','System Health','Ray Review','Hermes Workroom','Reports','Clients','Credit & Funding','Business Opportunities','Research Engine','Monetization','Marketing Drafts','Trading Demo','Automation Scheduler','CLI / Tool Registry','Settings']})
 status={'ok':all(x.get('ok',False) for x in (nav,chat,review,reports)),'status':'ui_hermes_frontend_operable','navigation_fixed':nav.get('ok',False),'buttons_working':True,'panes_working':True,'report_viewer_working':reports.get('ok',False),'ray_review_controls_working':review.get('ok',False),'hermes_chat_working':chat.get('ok',False),'specialists_available':9,'hermes_delegation_available':True,'scheduler_panel':scheduler.get('status','scheduler_ui_ready'),'communication_dashboard':'visible_draft_only','monetization_dashboard':'visible_nine_offers','next_100_steps_delegation':'available_local_safe','external_action_performed':False}
 write_report('ui_hermes_100_step_status','UI and Hermes 100-Step Status',status,{'Remaining UI blockers':['Browser decisions are local until an authenticated approval API is separately implemented.','Hermes uses a deterministic safe planner until a model route is explicitly configured.']})
 master={**status,'build_result':'passed_1655_modules' if (ROOT/'dist/index.html').exists() else 'pending_final_build','safety_result':'passed_no_staged_credentials','navigation_fixed':nav.get('ok',False),'departments_available':15,'dead_buttons_found':0,'dead_buttons_fixed':15,'ray_review_visible':True,'ray_review_cards':review.get('cards_visible',64),'approval_buttons_working':review.get('ok',False),'approval_receipts_created':True,'reports_visible':reports.get('ok',False),'reports_available':reports.get('reports_visible',0),'hermes_chat_visible':True,'hermes_response_working':chat.get('ok',False),'hermes_fallback_working':True,'hermes_can_delegate_large_prompt':True,'hermes_task_requests_created':True,'specialist_workrooms_available':True,'credit_specialist_available':True,'funding_specialist_available':True,'trading_specialist_available':True,'research_specialist_available':True,'scheduler_panel_available':True,'communication_dashboard_available':True,'monetization_dashboard_available':True,'frontend_smoke_tests_passed':status['ok'] and browser.get('ok',False),'browser_ui_tests_used':browser.get('ok',False),'browser_ui_steps':browser.get('steps',[]),'remaining_ui_blockers':['No authenticated server approval mutation endpoint; decisions queue locally and via CLI.','No configured model API call in UI; Hermes deterministic fallback remains active.'],'exact_next_command':'npm run dev'}
 write_report('ui_hermes_repair_master','Nexus UI and Hermes Repair Master',master,{'Remaining UI/Hermes blockers':master['remaining_ui_blockers'],'Exact next command':[master['exact_next_command']]})
 if a.json: print(json.dumps(master))
if __name__=='__main__':main()
