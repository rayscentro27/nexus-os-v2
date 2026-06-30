#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 selected=read_json(SUPABASE_READY/"notebooklm_selected_notebooks_latest.json",[]);files=[]
 for base in (ROOT/"data/sources/notebooklm_exports/approved",ROOT/"data/sources/notebooklm_notes/approved"):
  if base.exists():files.extend(str(x.relative_to(ROOT)) for x in base.rglob("*") if x.is_file())
 records=[{"id":f"notebooklm-sync-{i+1}","notebook_name":x.get("notebook_name"),"notebook_id":x.get("notebook_id"),"research_lane":x.get("research_lane"),"status":"queued_for_local_approved_sync","created_at":now()} for i,x in enumerate(selected)];write_json(SUPABASE_READY/"notebooklm_selected_notebook_sync_latest.json",records);report={"ok":True,"generated_at":now(),"status":"selected_notebook_sync_complete" if records else "watched_folder_sync_complete_no_selected_notebooks","selected_notebooks_checked":len(selected),"approved_files_found":len(files),"records_created":len(records),"manual_export_required":not bool(records),"external_action_performed":False};write_report("notebooklm_selected_notebook_sync","NotebookLM Selected Notebook Sync",report,{"Approved files":files});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
