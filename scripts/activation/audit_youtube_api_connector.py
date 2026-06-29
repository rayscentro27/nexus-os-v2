#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,api_key_status,approved_targets,now,read_json,write_json,write_report

def build():
 key=api_key_status();policy=read_json(ROOT/"configs/youtube_quota_policy.json",{});registry=read_json(ROOT/"configs/youtube_engine_registry.json",{})
 report={"ok":True,"generated_at":now(),"status":"api_configured_quota_cache_ready" if key["present"] else "targets_configured_connector_missing","api_key_present":key["present"],"detected_key_names":key["detected_key_names"],"raw_key_included":False,"approved_targets_count":len(approved_targets()),"quota_policy":policy,"cache_ready":True,"external_action_performed":False,"next_required_action":"Run quota-aware API metadata intake." if key["present"] else "Add a YouTube Data API key to a gitignored local/server environment."}
 safe={k:v for k,v in report.items()};write_report("youtube_api_connector_audit","YouTube API Connector Audit",report);write_json(SUPABASE_READY/"youtube_api_connector_status_latest.json",safe);write_json(SUPABASE_READY/"youtube_api_quota_policy_latest.json",policy)
 reg_report={"ok":True,"generated_at":now(),"status":"registry_active","roles":registry.get("roles",[]),"allowed_modes":registry.get("allowed_modes",[]),"external_action_performed":False};write_report("youtube_engine_registry","YouTube Engine Registry",reg_report,{"Roles":reg_report["roles"]});write_json(SUPABASE_READY/"youtube_engine_registry_latest.json",reg_report);return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
