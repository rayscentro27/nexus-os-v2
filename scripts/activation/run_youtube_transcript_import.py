#!/usr/bin/env python3
"""Import only approved local transcript text; never fetches media."""
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,approved_targets,ensure_dirs,now,read_json,record,write_json,write_report
SOURCE=ROOT/"data/sources/youtube_transcripts"
def build():
 ensure_dirs();targets=approved_targets();tokens={str(v).lower() for x in targets for v in (x.get("id"),x.get("handle")) if v};files=sorted(SOURCE.glob("*.txt"));imports=[];rejected=[]
 for i,path in enumerate(files,1):
  approved=any(t in path.stem.lower() for t in tokens) or path.with_suffix(path.suffix+".approved").exists()
  if not approved:rejected.append({"file":path.name,"reason":"not_attached_to_approved_target"});continue
  text=path.read_text(errors="replace").strip()
  if not text:continue
  topics=[x for x in ("credit","funding","business profile","documents","banking","marketing","subscription") if x in text.lower()]
  imports.append(record(f"manual-transcript-{i}","youtube_review_item",path.stem.replace("_"," ").title(),status="real_transcript",source_file=str(path.relative_to(ROOT)),review_type="real_transcript",character_count=len(text),extracted_topics=topics,content_excerpt=text[:500],media_downloaded=False))
 opportunities=[record(f"yt-transcript-opportunity-{i+1}","youtube_opportunity",f"Source-derived opportunity: {x['title']}",source_item_id=x["id"],approval_required=True) for i,x in enumerate(imports)]
 ideas=[record(f"yt-transcript-content-{i+1}","youtube_content_idea",f"Original explainer from {x['title']}",source_item_id=x["id"],approval_required=True,draft_only=True) for i,x in enumerate(imports)]
 write_json(SUPABASE_READY/"youtube_transcript_imports_latest.json",imports);write_json(SUPABASE_READY/"youtube_review_items_latest.json",imports);write_json(SUPABASE_READY/"youtube_opportunities_latest.json",opportunities);write_json(SUPABASE_READY/"youtube_content_ideas_latest.json",ideas)
 report={"ok":True,"generated_at":now(),"status":"real_transcript_review_active" if imports else "configured_missing_transcripts","files_found":len(files),"transcripts_imported":len(imports),"rejected_unapproved":rejected,"opportunities_created":len(opportunities),"content_ideas_created":len(ideas),"video_downloaded":False,"audio_downloaded":False,"external_action_performed":False,"next_required_action":"Review imported transcript outputs." if imports else "Place one approved .txt transcript in data/sources/youtube_transcripts/ and rerun."};write_report("youtube_transcript_import","YouTube Transcript Import",report,{"Imports":imports,"Rejected":rejected});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
