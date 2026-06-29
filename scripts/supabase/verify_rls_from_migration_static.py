#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,write_report  # noqa:E402
def build():
 text=(ROOT/"supabase/migrations/20260629095450_client_portal_core_tables.sql").read_text(errors="ignore");tables=sorted(set(re.findall(r"alter table public\.([a-z0-9_]+) enable row level security",text,re.I)));policies=re.findall(r'create policy "([^"]+)" on public\.([a-z0-9_]+) for ([a-z]+) to ([a-z_]+) (.+?);',text,re.I);public_true=[{"policy":p[0],"table":p[1]} for p in policies if p[3].lower() in {"anon","public"} or re.search(r"using\s*\(\s*true\s*\)",p[4],re.I)];tenant_filters=sum("tenant_id" in p[4] for p in policies);admin_filters=sum("nexus_is_active_admin" in p[4] for p in policies)
 report={"ok":bool(tables) and len(policies)>=len(tables) and not public_true,"generated_at":now(),"status":"static_rls_migration_verified","migration":"20260629095450_client_portal_core_tables.sql","rls_enabled_tables":tables,"rls_enabled_count":len(tables),"policies_count":len(policies),"authenticated_only_policies":sum(p[3].lower()=="authenticated" for p in policies),"tenant_filter_policy_count":tenant_filters,"admin_filter_policy_count":admin_filters,"public_permissive_true_policies":public_true,"destructive_sql_executed":False,"database_write_performed":False,"external_action_performed":False};write_report("rls_static_verification","RLS Static Verification",report,{"RLS tables":tables,"Public permissive findings":public_true});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
