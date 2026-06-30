#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from communication_common import SUPABASE_READY,now,read_json,write_json,write_report
def build():
 cards=read_json(SUPABASE_READY/"ray_review_operating_queue_latest.json",[]);rows=[{"receipt_id":f"receipt-{i+1:04d}","approval_title":x.get("title"),"decision":"pending","decision_recorded":False,"external_action_released":False,"created_at":now()} for i,x in enumerate(cards)];write_json(SUPABASE_READY/"approval_receipts_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"approval_receipt_ledger_ready","receipts_created":len(rows),"decisions_recorded":0,"external_actions_released":0,"external_action_performed":False};write_report("approval_receipts","Approval Receipts",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
