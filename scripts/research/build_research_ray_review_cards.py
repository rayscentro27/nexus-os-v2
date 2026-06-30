#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,now,read_json,stable_id,write_json,write_report
def build():
 opps=read_json(SUPABASE_READY/"research_opportunities_latest.json",[]);cards=[]
 for item in opps[:20]:cards.append({"id":stable_id("research_review",item["id"]),"tenant_id":"tenant_demo_goclear","client_id":"synthetic_research_only","category":"research_source_approval","title":f"Approve research adaptation: {item['title']}","reason":"New approved-lane source requires Ray review before adaptation or client-facing use.","risk":item["risk_level"],"exact_decision_needed":"approve/reject/defer internal adaptation","status":"pending_Ray_review","client_visible_after_approval":False,"external_action_performed":False,"approval_required":True,"created_at":now()})
 write_json(SUPABASE_READY/"research_approval_cards_latest.json",cards);report={"ok":True,"generated_at":now(),"status":"research_review_queue_ready","cards_created":len(cards),"external_action_performed":False};write_report("research_ray_review_cards","Research Ray Review Cards",report,{"Cards":cards});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
