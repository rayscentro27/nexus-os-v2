#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import SUPABASE_READY,now,read_json,record,write_json,write_report
def build():
 metadata=read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[]);transcripts=read_json(SUPABASE_READY/"youtube_transcript_imports_latest.json",[]);scores=read_json(SUPABASE_READY/"youtube_research_scores_latest.json",[]);items=metadata+transcripts
 opportunities=[record(f"yt-business-{i+1}","youtube_business_opportunity",f"Validate source opportunity: {x['title']}",source_item_id=x.get("id"),approval_required=True) for i,x in enumerate(items)]
 content=[record(f"yt-content-draft-{i+1}","youtube_content_draft",f"Original educational draft: {x['title']}",source_item_id=x.get("id"),status="draft_only",approval_required=True,public_content_published=False) for i,x in enumerate(items)]
 social=[record(f"yt-social-draft-{i+1}","youtube_social_draft",f"Social hook: {x['title']}",source_item_id=x.get("id"),status="draft_only",approval_required=True,public_content_published=False) for i,x in enumerate(items)]
 hermes=[record("yt-hermes-next","youtube_hermes_recommendation","Prioritize the highest-scoring approved YouTube source",summary=f"Review {len(items)} source items and approve only original adaptations; no reused publication.",approval_required=True)] if items else [record("yt-hermes-probe","youtube_hermes_recommendation","Approve a bounded metadata/subtitle availability probe",approval_required=True)]
 cards=read_json(SUPABASE_READY/"youtube_approval_cards_latest.json",[]);titles={x.get("title") for x in cards};extra=[]
 for title in ["Approve local yt-dlp metadata/subtitle probe for queued YouTube targets","Approve YouTube-derived original content adaptation","Approve NotebookLM manual research bundle workflow"]:
  if title not in titles:extra.append(record(f"yt-card-{len(cards)+len(extra)+1}","youtube_approval_card",title,status="ready_for_Ray_review",priority="high",approval_required=True))
 cards+=extra;partners=[record(f"yt-partner-{i+1}","youtube_partner_idea",f"Partner-fit review from {x['title']}",source_item_id=x.get("id"),approval_required=True) for i,x in enumerate(items[:5])]
 outputs={"youtube_approval_cards_latest.json":cards,"youtube_hermes_recommendations_latest.json":hermes,"youtube_content_drafts_latest.json":content,"youtube_social_drafts_latest.json":social,"youtube_business_opportunities_latest.json":opportunities,"youtube_partner_ideas_latest.json":partners}
 for n,d in outputs.items():write_json(SUPABASE_READY/n,d)
 report={"ok":True,"generated_at":now(),"status":"outputs_ready_for_review","source_items":len(items),"score_items":len(scores),"approval_cards":len(cards),"hermes_recommendations":len(hermes),"content_drafts":len(content),"social_drafts":len(social),"business_opportunities":len(opportunities),"partner_ideas":len(partners),"public_content_published":False,"external_action_performed":False};write_report("youtube_research_outputs","YouTube Research Outputs",report);return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
