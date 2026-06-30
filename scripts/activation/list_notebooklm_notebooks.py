#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402
from notebooklm_connector_common import classify,list_via_cli
def build():
 access=classify();listed,rows,error=list_via_cli();report={"ok":True,"generated_at":now(),"status":"notebooks_listed" if listed else "notebook_listing_unavailable_fallback_active","access_mode":access["access_mode"],"notebooks_listed":listed,"notebooks_found_count":len(rows),"notebooks":rows,"error_sanitized":error,"manual_export_required":not listed,"watched_folder_fallback":not listed,"cookies_used":False,"external_action_performed":False};write_json(SUPABASE_READY/"notebooklm_notebook_list_latest.json",rows);write_report("notebooklm_notebook_list","NotebookLM Notebook List",report,{"Notebooks":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
