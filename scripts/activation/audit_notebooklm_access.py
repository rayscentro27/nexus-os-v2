#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import SUPABASE_READY,env_values,ensure_dirs,now,write_json,write_report
def build():
 ensure_dirs();values=env_values();names=[x for x in ("NOTEBOOKLM_API_KEY","NOTEBOOKLM_ENTERPRISE_API_KEY","GOOGLE_CLOUD_PROJECT") if values.get(x)];report={"ok":True,"generated_at":now(),"status":"enterprise_api_configured" if names else "manual_folder_bridge_ready","enterprise_or_api_env_present":bool(names),"detected_key_names":names,"raw_values_included":False,"consumer_browser_automation":False,"manual_export_import_supported":True,"external_action_performed":False};write_report("notebooklm_access_audit","NotebookLM Access Audit",report);return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
