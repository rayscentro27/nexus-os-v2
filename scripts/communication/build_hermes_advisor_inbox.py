#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from communication_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report
def build():
 review=read_json(RUNTIME/"ray_review_queue_latest.json",{});research=read_json(RUNTIME/"research_hermes_brief_latest.json",{});revenue=read_json(RUNTIME/"revenue_dashboard_latest.json",{});items=[
  {"title":"Process today’s highest-value Ray Review decisions","priority":"P0","source":"ray_review","next_action":"Review the first 12 approval cards."},
  {"title":"Advance the $97 synthetic onboarding journey","priority":"P0","source":"monetization","next_action":"Approve fake-customer insertion or complete Stripe test Checkout."},
  {"title":"Fix Resend configuration","priority":"P1","source":"communications","next_action":"Verify goclearonline.com and replace/re-scope the key."},
  {"title":"Import one NotebookLM watched export","priority":"P1","source":"research","next_action":"Place an approved export in the watched folder."},
  {"title":"Review research-to-offer candidates","priority":"P1","source":"research","next_action":"Choose one high-value source for offer adaptation."},
 ];write_json(SUPABASE_READY/"hermes_advisor_inbox_latest.json",items);report={"ok":True,"generated_at":now(),"status":"hermes_advisor_inbox_ready","admin_only":True,"inbox_count":len(items),"ray_review_cards":review.get("cards_total",0),"research_recommendations":research.get("recommendations_count",0),"next_money_action":revenue.get("exact_next_money_action","Complete the $97 test onboarding proof."),"risky_execution_allowed":False,"external_action_performed":False};write_report("hermes_advisor_inbox","Hermes Advisor Inbox",report,{"Inbox":items});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
