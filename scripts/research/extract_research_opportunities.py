#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_scores,now,stable_id,write_json,write_report
def build():
 items=[]
 for x in load_scores()[:60]:
  items.append({"id":stable_id("opportunity",x["id"]),"tenant_id":"tenant_demo_goclear","client_id":"synthetic_research_only","category":"research_opportunity","title":f"Adapt: {x['title']}","summary":f"Evaluate approved {x['lane']} source for Nexus revenue, client workflow, or operational improvements.","status":"ready_for_Ray_review","score":x["score"],"priority":"high" if x["score"]>=70 else "medium","risk_level":x["risk_level"],"automation_level":"admin_review_required","client_visible":False,"approval_required":True,"source":x["id"],"source_concept":x["lane"],"recommended_next_action":x["recommended_next_action"],"created_at":now()})
 write_json(SUPABASE_READY/"research_opportunities_latest.json",items);report={"ok":True,"generated_at":now(),"status":"research_opportunities_extracted","opportunities_created":len(items),"high_priority":sum(x["priority"]=="high" for x in items),"external_action_performed":False};write_report("research_opportunities","Research Opportunities",report,{"Top opportunities":items[:15]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
