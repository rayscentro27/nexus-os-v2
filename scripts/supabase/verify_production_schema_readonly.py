#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,write_report  # noqa:E402
MIGRATION=ROOT/"supabase/migrations/20260629095450_client_portal_core_tables.sql"
def build():
 expected=sorted(set(re.findall(r"create table if not exists public\.([a-z0-9_]+)",MIGRATION.read_text(errors="ignore"),re.I)))
 run=subprocess.run(["supabase","inspect","db","table-stats","--linked"],cwd=ROOT,capture_output=True,text=True,timeout=60)
 visible=sorted(set(re.findall(r"public\.([a-z0-9_]+)\s+\|",run.stdout)))
 migration=subprocess.run(["supabase","migration","list"],cwd=ROOT,capture_output=True,text=True,timeout=60)
 applied="20260629095450" in migration.stdout and "20260629090000" in migration.stdout;missing=[x for x in expected if x not in visible]
 report={"ok":run.returncode==0 and applied and not missing,"generated_at":now(),"status":"production_schema_visible_readonly" if run.returncode==0 and not missing else "production_schema_verification_incomplete","linked_project":"iqjwgpnujbeoyaeuwehj","read_only_inspection":True,"expected_tables":expected,"visible_expected_tables":[x for x in expected if x in visible],"missing_expected_tables":missing,"expected_table_count":len(expected),"visible_table_count":len(visible),"migrations_applied":applied,"database_write_performed":False,"external_action_performed":False}
 write_report("production_schema_readonly_verification","Production Schema Read-Only Verification",report,{"Expected tables":expected,"Missing":missing});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
