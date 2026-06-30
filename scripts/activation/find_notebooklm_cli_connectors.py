#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from notebooklm_connector_common import classify
def build():
 a=classify();report={"ok":True,"generated_at":now(),"status":"cli_found" if a["cli"]["found"] else "cli_missing_legacy_adapter_found" if a["legacy_adapter_found"] else "cli_and_adapter_missing","cli_found":a["cli"]["found"],"cli_path":a["cli"].get("selected",{}).get("path") if a["cli"].get("selected") else None,"cli_version":a["cli"].get("version"),"legacy_adapter_found":a["legacy_adapter_found"],"legacy_adapter_path":a["legacy_adapter_path"],"old_cli_expected_path":str(Path.home()/"nexuslive/.venv-notebooklm/bin/nlm"),"old_cli_binary_present":False,"credentials_printed":False,"external_action_performed":False};write_report("notebooklm_cli_discovery","NotebookLM CLI Discovery",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
