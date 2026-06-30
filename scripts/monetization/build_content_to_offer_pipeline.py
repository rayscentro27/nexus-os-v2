#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import SUPABASE_READY,now,read_json,write_json,write_report
def build():
 ideas=read_json(SUPABASE_READY/"youtube_content_drafts_latest.json",[]) or read_json(SUPABASE_READY/"youtube_content_ideas_latest.json",[]);rows=[{"content_id":x.get("id",f"content-{i+1}"),"title":x.get("title","Readiness education content"),"offer_tie_in":"readiness_review_97","cta":"Request a readiness review after Ray approves publication.","status":"draft_only","approval_required":True} for i,x in enumerate(ideas[:20])];write_json(SUPABASE_READY/"content_to_offer_pipeline_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"content_to_offer_pipeline_ready","drafts_mapped":len(rows),"published":0,"external_action_performed":False};write_report("content_to_offer_pipeline","Content to Offer Pipeline",report,{"Mappings":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
