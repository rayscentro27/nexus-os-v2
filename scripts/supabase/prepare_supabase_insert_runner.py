#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from supabase_activation_common import *


def build()->dict:
 exports=sorted(SUPABASE_READY.glob("*.json")); mapped=[{"file":p.name,"table":FILE_TABLE_MAP[p.name],"order":list(FILE_TABLE_MAP).index(p.name)+1} for p in exports if p.name in FILE_TABLE_MAP]
 unmapped=[p.name for p in exports if p.name not in FILE_TABLE_MAP]
 report={"ok":True,"generated_at":now(),"status":"dry_run_ready","mapped_files":mapped,"mapped_file_count":len(mapped),"unmapped_files":unmapped,
  "execute_gate":["explicit --execute","NEXUS_SUPABASE_INSERT_APPROVED=true","safe server-side Supabase env","applied reviewed migration","tenant seed and RLS tests"],
  "live_insertion_performed":False,"next_required_action":"Run the dry-run validator; do not execute until migration/RLS approval.","external_action_performed":False}
 write_report("supabase_insert_plan","Supabase Insert Plan",report,{"Mapped files":mapped,"Unmapped files":unmapped});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
