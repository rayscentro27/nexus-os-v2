#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,ensure_dirs,now,read_json,write_json,write_report
def build():
 ensure_dirs();items=read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[]);scores=read_json(SUPABASE_READY/"youtube_research_scores_latest.json",[]);bundle={"generated_at":now(),"purpose":"manual NotebookLM upload","media_included":False,"metadata_items":items,"scores":scores,"instructions":["Upload manually to an approved NotebookLM workspace.","Do not include raw client data or secrets.","Return notes via data/sources/notebooklm_notes/."]};path=ROOT/"data/exports/notebooklm/youtube/youtube_research_bundle_latest.json";write_json(path,bundle);report={"ok":True,"generated_at":now(),"status":"manual_export_ready","bundle_path":str(path.relative_to(ROOT)),"metadata_items":len(items),"score_items":len(scores),"video_or_audio_included":False,"external_action_performed":False};write_report("youtube_notebooklm_export_bundle","YouTube NotebookLM Export Bundle",report);return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
