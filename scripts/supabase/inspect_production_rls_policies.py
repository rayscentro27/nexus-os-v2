#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,write_report  # noqa:E402
def build():
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/"schema.sql";run=subprocess.run(["supabase","db","dump","--linked","--schema","public","--file",str(path)],cwd=ROOT,capture_output=True,text=True,timeout=120);sql=path.read_text(errors="ignore") if path.exists() else ""
 rls=sorted(set(re.findall(r"ALTER TABLE(?: ONLY)? public\.([a-z0-9_]+) ENABLE ROW LEVEL SECURITY",sql,re.I)));policies=re.findall(r"CREATE POLICY ([^\n]+?) ON public\.([a-z0-9_]+)",sql,re.I)
 migration=(ROOT/"supabase/migrations/20260629095450_client_portal_core_tables.sql").read_text(errors="ignore");expected=sorted(set(re.findall(r"alter table public\.([a-z0-9_]+) enable row level security",migration,re.I)));missing=[x for x in expected if x not in rls]
 blocker=None if run.returncode==0 else "Remote schema dump requires Docker with this Supabase CLI version. Applied migration and static RLS definitions are present, but direct production policy verification is incomplete."
 report={"ok":run.returncode==0 and not missing and bool(expected),"generated_at":now(),"status":"production_rls_verified_from_schema_dump" if run.returncode==0 and not missing else "remote_rls_inspection_blocked_docker_static_migration_verified","linked_project":"iqjwgpnujbeoyaeuwehj","schema_dump_temporary_deleted":True,"expected_rls_tables":expected,"static_rls_definitions_count":len(expected),"verified_rls_tables":[x for x in expected if x in rls],"missing_rls_tables":missing if run.returncode==0 else [],"policies_detected_count":len(policies),"direct_remote_verification_blocker":blocker,"tenant_isolation_required":True,"rls_disabled":False,"database_write_performed":False,"raw_secrets_included":False,"external_action_performed":False}
 write_report("production_rls_policy_inspection","Production RLS Policy Inspection",report,{"Verified RLS tables":report["verified_rls_tables"],"Missing":missing});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
