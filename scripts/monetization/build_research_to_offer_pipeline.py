#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import SUPABASE_READY,now,read_json,write_json,write_report
def build():
 scores=read_json(SUPABASE_READY/"research_source_scores_latest.json",[]);rows=[{"source_id":x.get("id"),"source_title":x.get("title"),"score":x.get("score"),"recommended_offer":"readiness_review_97" if x.get("credit_funding_value",0)>=60 else "business_credit_checklist" if x.get("content_value",0)>=60 else "monthly_readiness_membership","status":"offer_adaptation_review_required","approval_required":True} for x in scores[:20]];write_json(SUPABASE_READY/"research_to_offer_pipeline_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"research_to_offer_pipeline_ready","candidates":len(rows),"external_action_performed":False};write_report("research_to_offer_pipeline","Research to Offer Pipeline",report,{"Candidates":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
