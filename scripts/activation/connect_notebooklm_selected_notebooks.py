#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
from notebooklm_connector_common import classify,route
def build():
 config=read_json(ROOT/"configs/notebooklm_selected_notebooks.json",{});rows=[]
 for item in config.get("notebooks",[]):
  name=item.get("notebook_name","");rows.append({**item,"research_lane":item.get("research_lane") or route(name),"sync_enabled":item.get("sync_enabled",True),"review_schedule":item.get("review_schedule","daily"),"approval_required_for_import":item.get("approval_required_for_import",False)})
 access=classify();report={"ok":True,"generated_at":now(),"status":"selected_notebooks_connected" if rows else "awaiting_notebook_selection_watched_fallback_active","access_mode":access["access_mode"],"selected_notebooks_count":len(rows),"research_lanes_connected":sorted({x["research_lane"] for x in rows}),"watched_export_lanes":["credit_funding","business_credit","grants","payment_monetization","trading","marketing_content","nexus_upgrade","ai_automation","general_research"],"manual_export_required":access["manual_export_required"],"external_action_performed":False};write_json(SUPABASE_READY/"notebooklm_selected_notebooks_latest.json",rows);write_report("notebooklm_selected_notebook_registry","NotebookLM Selected Notebook Registry",report,{"Selected notebooks":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
