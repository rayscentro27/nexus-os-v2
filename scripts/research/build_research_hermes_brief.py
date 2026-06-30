#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_scores,now,read_json,write_report
def build():
 scores=load_scores();opps=read_json(SUPABASE_READY/"research_opportunities_latest.json",[]);recommendations=[f"Review {x['title']} ({x['lane']}, score {x['score']}) before adaptation." for x in scores[:10]];report={"ok":True,"generated_at":now(),"status":"research_hermes_brief_ready","admin_only":True,"sources_considered":len(scores),"opportunities_considered":len(opps),"recommendations_count":len(recommendations),"recommendations":recommendations,"next_money_action":"Review the top research opportunity that directly improves the $97 readiness-review intake and fulfillment path.","external_action_performed":False};write_report("research_hermes_brief","Research Hermes Brief",report,{"Recommendations":recommendations});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
