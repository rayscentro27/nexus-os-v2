#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from communication_common import RUNTIME,now,read_json,write_report
def build():
 scheduler=read_json(RUNTIME/"safe_internal_scheduler_verification_latest.json",{});review=read_json(RUNTIME/"ray_review_queue_latest.json",{});messages=read_json(RUNTIME/"client_message_draft_queue_latest.json",{});report={"ok":True,"generated_at":now(),"status":"plain_english_status_ready","summary":f"Nexus has {scheduler.get('loaded_count',0)} safe schedules loaded, {review.get('cards_total',0)} decisions queued, and {messages.get('draft_count',0)} unsent message drafts. No risky external action is automatic.","safe_now":"Research, scoring, drafts, practice market reads, paper backtests, and status refreshes.","needs_approval":"Payments, customer inserts, sends, publishing, disputes, and any order execution.","external_action_performed":False};write_report("plain_english_status","Plain English System Status",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
