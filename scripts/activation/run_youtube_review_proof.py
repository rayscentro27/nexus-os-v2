#!/usr/bin/env python3
"""Review real imported YouTube metadata/transcripts and report the honest mode."""
from __future__ import annotations

import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
from youtube_local_tool import audit as audit_local_tool


def rec(id,category,title,**extra):
 return {"id":id,"tenant_id":"tenant_demo_goclear","client_id":"synthetic_research_only","category":category,"title":title,
  "summary":extra.pop("summary",title),"status":extra.pop("status","generated_report_only"),"priority":extra.pop("priority","medium"),
  "risk_level":extra.pop("risk_level","low"),"automation_level":extra.pop("automation_level","internal_active"),"client_visible":False,
  "approval_required":extra.pop("approval_required",True),"source":"approved_youtube_intake","recommended_next_action":extra.pop("recommended_next_action","Ray reviews this item."),"created_at":now(),**extra}


def build()->dict:
 config=read_json(ROOT/"configs"/"youtube_research_channels.json",{}); channels=[x for x in config.get("channels",[]) if x.get("enabled")]
 metadata=read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[]); transcripts=read_json(SUPABASE_READY/"youtube_transcript_imports_latest.json",[])
 intake=read_json(ROOT/"reports"/"runtime"/"youtube_metadata_intake_latest.json",{})
 probe_report=read_json(ROOT/"reports"/"runtime"/"youtube_ytdlp_probe_latest.json",{})
 local_tool=audit_local_tool()
 items=[];opps=[];ideas=[]
 for m in metadata:
  items.append(rec(f"review-{m['id']}","youtube_review_item",m.get("title","YouTube metadata"),review_type="real_metadata",video_id=m.get("video_id"),source_url=m.get("url"),real_source=True))
 for t in transcripts:
  items.append(rec(f"review-{t['id']}","youtube_review_item",t["title"],review_type="real_transcript",source_file=t["source_file"],topics=t.get("extracted_topics",[]),real_source=True))
 sources=items or []
 for i,item in enumerate(sources[:10],1):
  opps.append(rec(f"yt-opportunity-{i}","youtube_opportunity",f"Readiness content angle from {item['title']}",score=75,
    summary="Validate the source concept against GoClear policy, then adapt it into original educational content."))
  ideas.append(rec(f"yt-content-{i}","youtube_content_idea",f"Original readiness explainer: {item['title']}",draft_only=True))
 approvals=[rec("yt-approval-real-intake","youtube_approval_card","Approve continued bounded YouTube intake",priority="high",risk_level="medium",
   summary="Approve metadata/transcript intake cadence and the first source-derived content adaptations.")]
 if local_tool["local_ytdlp_available"] and channels:
  approvals.append(rec("yt-approval-local-ytdlp-probe","youtube_approval_card","Approve local yt-dlp metadata/subtitle probe for queued YouTube targets",priority="high",risk_level="medium",
   summary="Approve metadata and subtitle-availability checks for configured targets only. No video/audio download, restriction bypass, content reuse, or publication."))
 existing_approvals=read_json(SUPABASE_READY/"youtube_approval_cards_latest.json",[])
 approvals=list({item.get("title",item.get("id")):item for item in existing_approvals+approvals}.values())
 if transcripts: mode="real_transcript_review_active"
 elif metadata and any(item.get("metadata_source")=="yt_dlp_local_probe" for item in metadata): mode="real_metadata_review_active_ytdlp_local"
 elif metadata: mode="real_metadata_review_active_api"
 elif channels and local_tool["local_ytdlp_available"]: mode="targets_configured_ytdlp_available_needs_approved_probe"
 elif local_tool["local_ytdlp_available"]: mode="local_ytdlp_available_no_approved_targets"
 elif channels and not intake.get("api_key_present"): mode="targets_configured_connector_missing"
 elif channels: mode="queue_only_no_real_review"
 else: mode="not_configured"
 queued=[{"id":x["id"],"name":x["name"],"url":x["url"],"status":"queued"} for x in channels]
 for name,data in (("youtube_review_items_latest.json",items),("youtube_opportunities_latest.json",opps),("youtube_approval_cards_latest.json",approvals),("youtube_content_ideas_latest.json",ideas),("youtube_research_queue_latest.json",queued)):write_json(SUPABASE_READY/name,data)
 report={"ok":True,"generated_at":now(),"status":mode,"youtube_engine_found":True,"channels_configured":len(channels),"videos_configured":len(metadata),
  "metadata_available":bool(metadata),"transcripts_available":bool(transcripts),"api_or_connector_configured":bool(intake.get("api_key_present") or metadata),
  "local_ytdlp_available":local_tool["local_ytdlp_available"],"ytdlp_path":local_tool["ytdlp_path"],"ytdlp_version":local_tool["ytdlp_version"],
  "ytdlp_probe_performed":bool(probe_report.get("targets_checked")),"local_metadata_subtitle_probe_available":local_tool["local_ytdlp_available"],
  "real_video_review_performed":bool(items),"review_mode":mode,"reviewed_items_count":len(items),"queued_items_count":len(queued),
  "opportunities_created_count":len(opps),"content_ideas_created_count":len(ideas),"approval_cards_created_count":len(approvals),
  "exactly_reviewed":[{"title":x["title"],"review_type":x["review_type"]} for x in items],
  "blocked_reason":None if items else ("Local yt-dlp is available, but no metadata/subtitle probe has Ray approval and no approved transcript text is imported." if local_tool["local_ytdlp_available"] and channels else ("YOUTUBE_API_KEY is absent and no approved transcript .txt files exist." if not intake.get("api_key_present") else "Connector is configured but returned no metadata; inspect sanitized intake errors.")),
  "next_required_action":"Ray reviews extracted opportunities." if items else ("Approve local yt-dlp metadata/subtitle probe for queued YouTube targets." if local_tool["local_ytdlp_available"] and channels else "Add YOUTUBE_API_KEY locally/server-side or place one approved transcript .txt file in data/sources/youtube_transcripts/."),
  "external_action_performed":False,"public_content_published":False,
  "summary":f"YouTube mode is {mode}; reviewed {len(items)} real imported records and queued {len(queued)} targets."}
 write_report("youtube_review_proof","YouTube Review Proof",report,{"Reviewed":items,"Queued":queued,"Opportunities":opps});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0
if __name__=="__main__":raise SystemExit(main())
