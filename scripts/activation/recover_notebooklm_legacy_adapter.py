#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from youtube_engine_common import ROOT,SUPABASE_READY,now,read_json,record,write_json,write_report
LEGACY=Path.home()/"nexuslive/lib/notebooklm_ingest_adapter.py";WRAPPER=ROOT/"scripts/activation/notebooklm_legacy_adapter_v2.py"
def build():
 found=LEGACY.exists();text=LEGACY.read_text(errors="ignore") if found else "";safe_parts=[x for x in ("NOTEBOOK_DOMAIN_MAP","build_proposed_record","summarize_intake_queue","dedup_key") if x in text];unsafe=[x for x in ("SUPABASE_SERVICE_ROLE_KEY","_supabase_post","auth status") if x in text]
 cards=read_json(SUPABASE_READY/"notebooklm_approval_cards_latest.json",[]);title="Approve NotebookLM selected notebook import workflow in Nexus v2";cards=[x for x in cards if x.get("title")!=title]+[record("approve-notebooklm-selected-import","approval_card",title,status="pending_Ray_review",approval_required=True,risk_level="medium")];write_json(SUPABASE_READY/"notebooklm_approval_cards_latest.json",cards)
 report={"ok":found and WRAPPER.exists(),"generated_at":now(),"status":"legacy_adapter_recovered_safe_wrapper_ready" if found and WRAPPER.exists() else "legacy_adapter_missing","legacy_path":str(LEGACY),"v2_wrapper":str(WRAPPER.relative_to(ROOT)),"safe_parts_adapted":safe_parts,"excluded_risky_parts":unsafe,"manual_selected_notebook_import_supported":True,"consumer_browser_automation":False,"legacy_auth_used":False,"database_inserted":False,"approval_cards_created":1,"external_action_performed":False}
 write_report("notebooklm_legacy_adapter_recovery","NotebookLM Legacy Adapter Recovery",report,{"Safe parts":safe_parts,"Excluded":unsafe});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
