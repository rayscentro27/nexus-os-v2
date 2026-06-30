#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');a.add_argument('--url',default='http://127.0.0.1:4174/?ui-smoke=1#command');x=a.parse_args();checks={};dead=[]
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True);page=b.new_page(viewport={'width':1920,'height':1080});page.set_default_timeout(8000);page.goto(x.url,wait_until='domcontentloaded',timeout=20000);page.get_by_role('heading',name='Command Center',exact=True).wait_for()
   metrics=page.locator('.nexus-home-metric');checks['four_clickable_metrics']=metrics.count()==4
   for i in range(metrics.count()): metrics.nth(i).click();page.go_back();page.goto(x.url,wait_until='domcontentloaded')
   checks['money_rows_clickable']=page.locator('.nexus-money-actions button').count()==3
   checks['running_rows_clickable']=page.locator('.command-click-row').count()>=8
   checks['approval_items_clickable']=page.locator('.nexus-next-approvals button').count()==3
   checks['copy_command_clickable']=page.locator('.next-command-card button').count()==1
   box=page.locator('.nexus-command-center').bounding_box();checks['fits_1920x1080']=bool(box and box['y']>=0 and box['y']+box['height']<=1080)
   checks['no_horizontal_overflow']=page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
   action_count=page.locator('.nexus-command-center button').count();checks['visible_action_count']=action_count>=20
   b.close()
 except Exception as e: dead.append(str(e))
 ok=all(checks.values()) and not dead;p={'ok':ok,'status':'command_center_clickability_passed' if ok else 'command_center_clickability_failed','checks':checks,'clickable_actions':action_count if 'action_count' in locals() else 0,'dead_actions':len(dead),'errors':dead,'external_action_performed':False};write_report('command_center_clickability_test','Command Center Clickability Test',p,{'Checks':checks});print(json.dumps(p)) if x.json else None;raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
