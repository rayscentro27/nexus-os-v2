#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_scores,now,write_json,write_report
def build():
 rows=[{"source_id":x["id"],"title":x["title"],"Nexus_upgrade_value":x["Nexus_upgrade_value"],"automation_candidate":"internal extraction/scoring/task generation","external_action_allowed":False,"approval_required":x["risk_level"]!="low","status":"design_review"} for x in load_scores() if x["Nexus_upgrade_value"]>=60][:40];write_json(SUPABASE_READY/"research_to_automation_pipeline_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"research_to_automation_pipeline_ready","automation_candidates":len(rows),"external_automation_enabled":0,"external_action_performed":False};write_report("research_to_automation_pipeline","Research to Automation Pipeline",report,{"Candidates":rows[:20]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
