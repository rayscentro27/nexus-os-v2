#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,load_sources,now,score_item,write_json,write_report
def build():
 scores=[score_item(x) for x in load_sources()];scores.sort(key=lambda x:x["score"],reverse=True);write_json(SUPABASE_READY/"research_source_scores_latest.json",scores);report={"ok":True,"generated_at":now(),"status":"research_sources_scored","sources_scored":len(scores),"high_value_sources":sum(x["score"]>=70 for x in scores),"approval_required":sum(x["approval_required"] for x in scores),"external_action_performed":False};write_report("research_source_scores","Research Source Scores",report,{"Top sources":[{"title":x["title"],"lane":x["lane"],"score":x["score"]} for x in scores[:20]]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
