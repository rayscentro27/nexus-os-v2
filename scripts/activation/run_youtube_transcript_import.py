#!/usr/bin/env python3
"""Import locally supplied transcript text for internal analysis."""
from __future__ import annotations

import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402
SOURCE=ROOT/"data"/"sources"/"youtube_transcripts"


def build()->dict:
 SOURCE.mkdir(parents=True,exist_ok=True); files=sorted([p for p in SOURCE.glob("*.txt") if p.is_file()]); records=[]
 for i,path in enumerate(files,1):
  text=path.read_text(errors="replace").strip()
  if not text: continue
  terms=[x for x in ("credit","utilization","business profile","funding","documents","banking","marketing","subscription") if x in text.lower()]
  records.append({"id":f"manual-transcript-{i}","title":path.stem.replace("_"," ").title(),"source_file":str(path.relative_to(ROOT)),
    "source_type":"manual_local_transcript","approved_for_internal_review":True,"character_count":len(text),"extracted_topics":terms,
    "content_excerpt":text[:500],"media_downloaded":False,"created_at":now()})
 write_json(SUPABASE_READY/"youtube_transcript_imports_latest.json",records)
 status="real_transcript_review_active" if records else "configured_missing_transcripts"
 report={"ok":True,"generated_at":now(),"status":status,"transcript_directory":str(SOURCE.relative_to(ROOT)),"files_found":len(files),
  "transcripts_imported":len(records),"media_downloaded":False,"instructions":["Place approved UTF-8 .txt transcripts in data/sources/youtube_transcripts/.","Use a filename that identifies the source; do not add copyrighted video/audio.","Run this importer, then run_youtube_review_proof.py."],
  "next_required_action":"Run review proof." if records else "Add one approved transcript text file, then rerun this importer.",
  "external_action_performed":False,"summary":f"Imported {len(records)} local approved transcript files."}
 write_report("youtube_transcript_import","YouTube Transcript Import",report,{"Imported records":records,"Instructions":report["instructions"]});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0
if __name__=="__main__":raise SystemExit(main())
