#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from notebooklm_connector_common import classify
def build():
 access=classify();report={"ok":True,"generated_at":now(),"status":"notebooklm_automation_options_audited","access_mode":access["access_mode"],"official_api_configured":access["official_api_configured"],"local_cli_found":access["cli"]["found"],"legacy_adapter_found":access["legacy_adapter_found"],"watched_folder_ready":bool(access["watched_folders"]),"manual_export_required":access["manual_export_required"],"consumer_browser_automation":False,"credentials_printed":False,"external_action_performed":False};write_report("notebooklm_access_mode_classification","NotebookLM Access Mode Classification",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
