#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_scores,now,write_json,write_report
def build():
 rows=[{"source_id":x["id"],"title":x["title"],"client_value":x["client_value"],"credit_funding_value":x["credit_funding_value"],"recommended_client_use":"GoClear-reviewed readiness task or educational explanation","client_visible":False,"approval_required":True,"status":"admin_review_required"} for x in load_scores() if x["client_value"]>=60][:40];write_json(SUPABASE_READY/"research_to_client_opportunity_pipeline_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"research_to_client_pipeline_ready","opportunities":len(rows),"external_action_performed":False};write_report("research_to_client_opportunity_pipeline","Research to Client Opportunity Pipeline",report,{"Opportunities":rows[:20]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
