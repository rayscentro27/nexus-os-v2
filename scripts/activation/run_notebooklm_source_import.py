#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,ensure_dirs,now,record,write_json,write_report
def build():
 ensure_dirs();paths=[]
 for folder in (ROOT/"data/sources/notebooklm_exports",ROOT/"data/sources/notebooklm_notes"):
  paths.extend([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".txt",".md",".json"}])
 sources=[]
 for i,p in enumerate(sorted(paths),1):
  text=p.read_text(errors="replace");sources.append(record(f"notebooklm-{i}","notebooklm_source",p.stem,status="imported_local_source",source_file=str(p.relative_to(ROOT)),content_excerpt=text[:1000],approval_required=True))
 opps=[record(f"notebooklm-opportunity-{i+1}","notebooklm_opportunity",f"Review NotebookLM note: {x['title']}",source_item_id=x["id"],approval_required=True) for i,x in enumerate(sources)];write_json(SUPABASE_READY/"notebooklm_sources_latest.json",sources);write_json(SUPABASE_READY/"notebooklm_opportunities_latest.json",opps);report={"ok":True,"generated_at":now(),"status":"local_import_complete" if sources else "manual_import_folder_ready","sources_imported":len(sources),"opportunities_created":len(opps),"consumer_browser_automation":False,"external_action_performed":False};write_report("notebooklm_source_import","NotebookLM Source Import",report,{"Sources":sources});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
