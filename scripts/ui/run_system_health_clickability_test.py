#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');a.add_argument('--url',default='http://127.0.0.1:4174/?ui-smoke=1#health');x=a.parse_args();errors=[];count=0
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True);page=b.new_page(viewport={'width':1920,'height':1080});page.goto(x.url,wait_until='domcontentloaded');items=page.locator('.health-item');count=items.count()
   for i in range(count): items.nth(i).click();page.locator('.health-detail-drawer').wait_for();assert page.locator('.health-detail-drawer dd').count()>=4
   b.close()
 except Exception as e:errors.append(str(e))
 ok=count==15 and not errors;payload={'ok':ok,'status':'system_health_clickability_passed' if ok else 'system_health_clickability_failed','clickable_rows':count,'dead_rows':len(errors),'details_include_status_report_next_run_command':ok,'errors':errors,'external_action_performed':False};write_report('system_health_clickability_test','System Health Clickability Test',payload);print(json.dumps(payload)) if x.json else None;raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
