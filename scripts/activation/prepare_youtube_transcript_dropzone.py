#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,now,write_report
def build():
 base=ROOT/"data/sources/youtube_transcripts";pending=base/"pending";approved=base/"approved";pending.mkdir(parents=True,exist_ok=True);approved.mkdir(parents=True,exist_ok=True);template=pending/"zbAmmnMh5ew.metadata.template.json"
 if not template.exists():template.write_text(json.dumps({"video_id":"zbAmmnMh5ew","source_url":"https://www.youtube.com/watch?v=zbAmmnMh5ew","approved_by":"Ray","approved":True,"lawfully_obtained":True,"internal_review_only":True},indent=2)+"\n")
 files=list(approved.glob("*.txt"));report={"ok":True,"generated_at":now(),"status":"approved_transcript_ready" if files else "dropzone_ready_waiting_for_approved_txt","pending_path":str(pending.relative_to(ROOT)),"approved_path":str(approved.relative_to(ROOT)),"expected_filename":"zbAmmnMh5ew.txt","metadata_template":str(template.relative_to(ROOT)),"approved_txt_count":len(files),"video_downloaded":False,"audio_downloaded":False,"cookies_used":False,"external_action_performed":False};write_report("youtube_transcript_dropzone","YouTube Transcript Dropzone",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
