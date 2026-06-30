#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from communication_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report
def build():
 cards=[];seen=set()
 for path in sorted(SUPABASE_READY.glob("*approval*cards*_latest.json")):
  payload=read_json(path,[]);payload=payload if isinstance(payload,list) else payload.get("cards",[]) if isinstance(payload,dict) else []
  for item in payload:
   if not isinstance(item,dict):continue
   title=str(item.get("title") or item.get("decision") or "Review approval item");key=title.lower().strip()
   if key in seen:continue
   seen.add(key);cards.append({**item,"title":title,"source_file":path.name,"status":item.get("status","pending_Ray_review"),"approval_required":True})
 cards.sort(key=lambda x:(0 if any(k in x["title"].lower() for k in ("$97","payment","customer","resend")) else 1,x["title"]));write_json(SUPABASE_READY/"ray_review_operating_queue_latest.json",cards);report={"ok":True,"generated_at":now(),"status":"ray_review_queue_refreshed","cards_total":len(cards),"approve_today_count":min(12,len(cards)),"external_actions_executed":0,"external_action_performed":False};write_report("ray_review_queue","Ray Review Queue",report,{"Top cards":cards[:25]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
