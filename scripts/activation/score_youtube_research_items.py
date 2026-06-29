#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import SUPABASE_READY,now,read_json,record,write_json,write_report

def build():
 items=read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[])+read_json(SUPABASE_READY/"youtube_transcript_imports_latest.json",[]);scores=[]
 for i,x in enumerate(items):
  text=(str(x.get("title",""))+" "+str(x.get("description",x.get("content_excerpt","")))).lower()
  has_credit=any(k in text for k in ("credit","funding","bank","llc","business"));base=78 if has_credit else 62
  scores.append(record(f"youtube-score-{i+1}","youtube_research_score",x.get("title","YouTube item"),source_item_id=x.get("id"),revenue_potential=base,immediate_actionability=base-5,nexus_upgrade_value=base-2,client_workflow_value=base,credit_repair_value=base if "credit" in text else 45,business_funding_value=base if has_credit else 40,content_marketing_value=72,affiliate_partner_value=55,risk_level="medium",approval_required=True,recommended_next_action="Ray reviews source fit before adaptation."))
 write_json(SUPABASE_READY/"youtube_research_scores_latest.json",scores);report={"ok":True,"generated_at":now(),"status":"scoring_complete","items_scored":len(scores),"external_action_performed":False};write_report("youtube_research_scoring","YouTube Research Scoring",report,{"Scores":scores});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
