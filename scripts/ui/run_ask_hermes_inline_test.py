#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');a.add_argument('--url',default='http://127.0.0.1:4174/?ui-smoke=1#command');x=a.parse_args();checks={};error=''
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True);page=b.new_page(viewport={'width':1920,'height':1080});page.goto(x.url,wait_until='domcontentloaded');before=page.url;page.get_by_role('button',name='Ask Hermes without leaving this page').click();checks['drawer_opens']=page.locator('.hermes-inline-drawer').is_visible();checks['department_preserved']=page.url==before;page.get_by_role('textbox',name='Ask Hermes inline').fill('did you have your coffee this morning');page.get_by_role('button',name='Send',exact=True).last.click();page.get_by_text('Not coffee, but I’m awake',exact=False).wait_for();checks['conversational_response']=True;checks['close_works']=page.get_by_role('button',name='Close Hermes chat').is_visible();checks['full_workroom_secondary']=page.get_by_role('button',name='Open full Hermes Workroom').is_visible();b.close()
 except Exception as e:error=str(e)
 ok=all(checks.values()) and not error;payload={'ok':ok,'status':'ask_hermes_inline_passed' if ok else 'ask_hermes_inline_failed','checks':checks,'navigates_away_by_default':False if checks.get('department_preserved') else True,'error':error,'external_action_performed':False};write_report('ask_hermes_inline_test','Ask Hermes Inline Test',payload,{'Checks':checks});print(json.dumps(payload)) if x.json else None;raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
