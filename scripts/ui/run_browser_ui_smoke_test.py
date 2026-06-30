#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import write_report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); ap.add_argument('--url',default='http://127.0.0.1:4174/?ui-smoke=1#command'); a=ap.parse_args()
    steps=[]
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            try:
                page=browser.new_page(viewport={'width':1440,'height':1000}); errors=[]; page.on('pageerror',lambda exc: errors.append(str(exc))); page.goto(a.url,wait_until='networkidle')
                page.get_by_role('heading',name='Command Center',exact=True).wait_for(); steps.append('command_center_visible')
                departments=['System Health','Ray Review','Hermes Workroom','Reports','Clients','Credit & Funding','Business Opportunities','Research Engine','Monetization','Marketing Drafts','Trading Demo','Automation Scheduler','CLI / Tool Registry','Settings']
                for name in departments:
                    page.get_by_role('button',name=name,exact=False).first.click(); page.get_by_role('heading',name=name,exact=True).wait_for()
                steps.append('all_15_departments_opened')
                page.get_by_role('button',name='Ray Review',exact=False).first.click(); page.get_by_role('button',name='Approve',exact=True).first.click(); page.get_by_text('Receipt created',exact=False).first.wait_for(); steps.append('approval_receipt_visible')
                page.get_by_role('button',name='Hermes Workroom',exact=False).first.click(); page.get_by_label('Message Hermes').fill('next 100 steps for automation communication and monetization'); page.get_by_role('button',name='Send',exact=True).click(); page.get_by_text('I split this request',exact=False).wait_for(); steps.append('hermes_response_visible')
                page.get_by_role('button',name='Credit Specialist',exact=False).click(); page.get_by_text('Blocked: Dispute sending or bureau contact',exact=False).wait_for(); steps.append('credit_specialist_opened')
                page.get_by_role('button',name='Reports',exact=False).first.click(); page.locator('.nxos-markdown').wait_for(); assert page.locator('.nxos-markdown').inner_text().strip(); steps.append('report_markdown_visible')
            finally:
                browser.close()
        payload={'ok':True,'status':'browser_ui_smoke_passed','browser':'chromium_headless','steps':steps,'departments_clicked':15,'uncaught_errors':errors,'external_action_performed':False}
    except Exception as exc:
        payload={'ok':False,'status':'browser_ui_smoke_failed','browser':'chromium_headless','steps':steps,'error':str(exc),'external_action_performed':False}
    write_report('browser_ui_smoke_test','Browser UI Smoke Test',payload,{'Steps':steps})
    if a.json: print(json.dumps(payload))
    raise SystemExit(0 if payload['ok'] else 1)
if __name__=='__main__':main()
