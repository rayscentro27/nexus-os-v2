#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_scores,now,write_json,write_report
def build():
 rows=[{"source_id":x["id"],"title":x["title"],"content_value":x["content_value"],"formats":["educational post","newsletter section","short video script"],"offer_tie_in":"readiness_review_97","status":"draft_planning_only","approval_required":True} for x in load_scores() if x["content_value"]>=60][:40];write_json(SUPABASE_READY/"research_to_content_pipeline_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"research_to_content_pipeline_ready","content_candidates":len(rows),"published":0,"external_action_performed":False};write_report("research_to_content_pipeline","Research to Content Pipeline",report,{"Candidates":rows[:20]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
