#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 selected=read_json(SUPABASE_READY/"notebooklm_selected_notebooks_latest.json",[]);sources=read_json(SUPABASE_READY/"notebooklm_sources_latest.json",[]);memory={"generated_at":now(),"selected_notebooks":len(selected),"imported_sources":len(sources),"research_lanes":sorted({x.get("research_lane") for x in selected if x.get("research_lane")}),"status":"memory_ready" if selected or sources else "memory_waiting_for_selected_notebook_or_export"};write_json(RUNTIME/"notebooklm_research_memory_latest.json",memory);report={"ok":True,**memory,"external_action_performed":False};write_report("notebooklm_research_memory","NotebookLM Research Memory",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
