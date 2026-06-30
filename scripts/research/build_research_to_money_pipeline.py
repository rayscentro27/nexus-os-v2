#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_scores,now,write_json,write_report
def build():
 rows=[]
 for x in load_scores()[:50]:rows.append({"source_id":x["id"],"title":x["title"],"score":x["score"],"make_money_now":x["revenue_potential"]>=70 and x["immediate_actionability"]>=60,"make_money_later":x["revenue_potential"]>=50,"help_client":x["client_value"]>=60,"improve_nexus":x["Nexus_upgrade_value"]>=60,"create_content":x["content_value"]>=60,"become_offer":x["revenue_potential"]>=60,"become_automation":x["Nexus_upgrade_value"]>=65,"status":"Ray_review_required","recommended_next_action":"Map to the $97 offer, subscription, or a small approved experiment."})
 write_json(SUPABASE_READY/"research_to_money_pipeline_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"research_to_money_pipeline_active","candidates":len(rows),"money_now_count":sum(x["make_money_now"] for x in rows),"money_later_count":sum(x["make_money_later"] for x in rows),"external_action_performed":False};write_report("research_to_money_pipeline","Research to Money Pipeline",report,{"Top candidates":rows[:20]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
