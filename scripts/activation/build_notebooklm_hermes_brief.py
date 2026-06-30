#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 listing=read_json(RUNTIME/"notebooklm_notebook_list_latest.json",{});sync=read_json(RUNTIME/"notebooklm_selected_notebook_sync_latest.json",{});recs=["The historical community nlm CLI is no longer installed; do not recreate its cookie/session automation without separate approval.","Use the recovered legacy adapter and approved watched folders for selected NotebookLM exports.","When an approved export arrives, assign its notebook name to a research lane and run the daily sync."]
 report={"ok":True,"generated_at":now(),"status":"notebooklm_hermes_brief_ready","admin_only":True,"access_mode":listing.get("access_mode"),"notebooks_found":listing.get("notebooks_found_count",0),"sync_status":sync.get("status"),"recommendations_count":len(recs),"recommendations":recs,"external_action_performed":False};write_report("notebooklm_hermes_brief","NotebookLM Hermes Brief",report,{"Recommendations":recs});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
