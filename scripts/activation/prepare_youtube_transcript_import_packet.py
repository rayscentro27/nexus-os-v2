#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,now,read_json,record,write_json,write_report
def build():
 imported=read_json(ROOT/"reports/runtime/youtube_transcript_import_latest.json",{});title="Approve YouTube transcript import for zbAmmnMh5ew";cards=read_json(SUPABASE_READY/"youtube_approval_cards_latest.json",[]);cards=[x for x in cards if x.get("title")!=title]+[record("approve-youtube-transcript-zbAmmnMh5ew","approval_card",title,status="pending_Ray_review",approval_required=True,risk_level="medium")];write_json(SUPABASE_READY/"youtube_approval_cards_latest.json",cards)
 instructions=["Place the user-provided transcript at data/sources/youtube_transcripts/approved/zbAmmnMh5ew.txt.","Confirm the matching metadata template fields and retain internal_review_only=true.","Run python3 scripts/activation/run_youtube_transcript_import.py --json.","Review extracted outputs before content reuse or publication."]
 report={"ok":True,"generated_at":now(),"status":"transcript_imported" if imported.get("transcripts_imported",0)>0 else "exact_import_packet_ready_waiting_for_txt","transcripts_imported":imported.get("transcripts_imported",0),"instructions":instructions,"approval_cards_created":1,"video_downloaded":False,"audio_downloaded":False,"external_action_performed":False};write_report("youtube_transcript_import_packet","YouTube Transcript Import Packet",report,{"Instructions":instructions});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
