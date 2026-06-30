#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,read_json,write_json,write_report  # noqa:E402
from notebooklm_connector_common import classify
def build():
 a=classify();registry=read_json(ROOT/"configs/notebooklm_automation_registry.json",{});registry["selected_access_mode"]=a["access_mode"];registry["generated_at"]=now();write_json(ROOT/"configs/notebooklm_automation_registry.json",registry);report={"ok":True,"generated_at":now(),"status":"notebooklm_automation_registry_ready","selected_access_mode":a["access_mode"],"cli_callable":a["cli"]["found"],"legacy_adapter_callable":a["legacy_adapter_found"],"watched_folders":a["watched_folders"],"browser_automation_allowed":False,"external_action_performed":False};write_report("notebooklm_automation_registry","NotebookLM Automation Registry",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
