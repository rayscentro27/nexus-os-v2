#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
def build():
 steps=["Open Supabase project iqjwgpnujbeoyaeuwehj → SQL Editor.","Paste the generated read-only RLS verification packet.","Confirm every expected table has relrowsecurity=true.","Review policy roles, commands, permissive mode, qual and with_check expressions.","Reject any anon/public policy or unconditional true policy.","Save/export results without secrets and rerun the insert gate."]
 report={"ok":True,"generated_at":now(),"status":"no_docker_sql_editor_path_ready","docker_required":False,"target_project":"iqjwgpnujbeoyaeuwehj","read_only":True,"steps":steps,"ray_review_card":"Approve no-Docker RLS SQL verification in Supabase SQL Editor.","database_write_performed":False,"external_action_performed":False};write_report("no_docker_rls_verification_plan","No-Docker RLS Verification Plan",report,{"Steps":steps});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
