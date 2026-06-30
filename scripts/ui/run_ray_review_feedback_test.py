#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');a.add_argument('--url',default='http://127.0.0.1:4174/?ui-smoke=1#rayreview');x=a.parse_args();checks={};error=''
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True);page=b.new_page(viewport={'width':1920,'height':1080});page.goto(x.url,wait_until='domcontentloaded');page.get_by_role('button',name='Approve',exact=True).first.click();toast=page.locator('.approval-receipt-toast');toast.wait_for();checks['status_visible']='Approval recorded' in toast.inner_text();checks['receipt_id_visible']='NXR-' in toast.inner_text();checks['queued_vs_executed_clear']='Underlying action executed: no' in toast.inner_text();checks['next_step_visible']='Queued for' in toast.inner_text();page.get_by_role('button',name='View receipt').click();checks['viewer_opens']=page.locator('.approval-receipt-viewer').is_visible();page.locator('.approval-receipt-viewer').get_by_role('button').click();checks['undo_available']=page.get_by_role('button',name='Undo local status').is_visible();page.get_by_role('button',name='Undo local status').click();checks['undo_works']=page.locator('.approval-receipt-toast').count()==0;b.close()
 except Exception as e:error=str(e)
 ok=all(checks.values()) and not error;payload={'ok':ok,'status':'ray_review_feedback_passed' if ok else 'ray_review_feedback_failed','checks':checks,'error':error,'underlying_action_executed':False};write_report('ray_review_feedback_test','Ray Review Feedback Test',payload,{'Checks':checks});print(json.dumps(payload)) if x.json else None;raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
