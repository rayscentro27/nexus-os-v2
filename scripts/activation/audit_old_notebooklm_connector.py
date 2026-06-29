#!/usr/bin/env python3
"""Recover legacy NotebookLM integration metadata without auth or browser automation."""
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from youtube_engine_common import ROOT,SUPABASE_READY,now,record,write_json,write_report

LEGACY=Path.home()/"nexuslive"
CANDIDATES=[LEGACY/"scripts/check_notebooklm_cli.py",LEGACY/"lib/notebooklm_ingest_adapter.py",LEGACY/"scripts/test_notebooklm_ingest_adapter.py",LEGACY/"docs/notebooklm_operator_workflow.md"]

def build():
 found=[p for p in CANDIDATES if p.exists()];binary=LEGACY/".venv-notebooklm/bin/nlm";version=""
 if binary.exists():
  run=subprocess.run([str(binary),"--version"],capture_output=True,text=True,timeout=10)
  version=((run.stdout or run.stderr).strip().splitlines() or [""])[0] if run.returncode==0 else ""
 formats=[]
 for p in found:
  text=p.read_text(errors="replace").lower()
  for ext in ("txt","md","json","pdf","pasted notes"):
   if ext in text and ext not in formats:formats.append(ext)
 status="legacy_cli_and_adapter_found" if binary.exists() and len(found)>=2 else "legacy_adapter_found_cli_missing" if found else "not_found"
 recovery={"selector_command":"nlm notebook list --json","source_commands":["nlm source list <notebook-id> --json","nlm source get <source-id> --json"],"legacy_queue":str(LEGACY/"reports/knowledge_intake/notebooklm_intake_queue.json"),"target_import_folders":["data/sources/notebooklm_exports","data/sources/notebooklm_notes"],"apply_allowed":False,"review_required":True}
 out=[record("old-notebooklm-connector","notebooklm_connector_status","Legacy NotebookLM connector",status=status,legacy_cli_path=str(binary) if binary.exists() else None,legacy_files=[str(x) for x in found],formats=formats,recovery_plan=recovery,approval_required=True)]
 write_json(SUPABASE_READY/"old_notebooklm_connector_status_latest.json",out)
 report={"ok":True,"generated_at":now(),"status":status,"old_cli_found":binary.exists(),"cli_path":str(binary) if binary.exists() else None,"cli_version":version,"files_found":len(found),"files":[str(x) for x in found],"formats":formats,"wrote_directly_to_nexus":False,"legacy_dry_run_queue_supported":True,"consumer_browser_automation":False,"auth_attempted":False,"raw_secrets_included":False,"recovery_plan":recovery,"external_action_performed":False}
 write_report("old_notebooklm_connector_audit","Old NotebookLM Connector Audit",report,{"Files":report["files"],"Recovery plan":recovery});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
