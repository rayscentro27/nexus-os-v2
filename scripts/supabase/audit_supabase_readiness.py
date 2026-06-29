#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from supabase_activation_common import *


def build()->dict:
 migrations=sorted((ROOT/"supabase"/"migrations").glob("*.sql")); exports=sorted(SUPABASE_READY.glob("*.json")); present=env_presence("SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY","VITE_SUPABASE_URL","VITE_SUPABASE_ANON_KEY")
 mapped=[{"file":p.name,"table":FILE_TABLE_MAP[p.name]} for p in exports if p.name in FILE_TABLE_MAP]
 report={"ok":True,"generated_at":now(),"status":"ready_for_migration_review","existing_migrations":[p.name for p in migrations],
  "existing_migration_count":len(migrations),"supabase_ready_export_count":len(exports),"mapped_export_count":len(mapped),"mapped_exports":mapped,
  "required_tables":TABLES,"required_rls":["tenant membership select policy","tenant-scoped client access","admin/operator write policy","client-visible guidance policy","service-side insert boundary"],
  "tenant_requirements":["tenant_id on every client/business record","client_id where client-owned","tenant_memberships role lookup"],
  "storage_buckets":[{"name":"client-documents-private","public":False,"status":"draft_required"}],
  "auth_roles":["admin","operator","client"],"insertion_order":["tenant_memberships","client_profiles","subscription_memberships","readiness_scores","client_tasks","client_documents","workflow/opportunity records","guidance/questions/escalations","proof/engine/connector records"],
  "env_presence":present,"raw_env_values_included":False,"live_database_inspected":False,"live_insertion_performed":False,
  "blockers":["Ray migration approval","linked Supabase project confirmation","tenant membership seed","RLS policy tests","private storage policy","insert execution approval"],
  "can_activate_today":"migration_and_dry_run_yes; live tables only after Ray approval",
  "next_approval_command":"supabase db push --dry-run (after reviewing DRAFT_client_portal_core_tables.sql and renaming it to a timestamped migration)",
  "external_action_performed":False,"summary":"Local schemas, exports, insertion order, and RLS requirements are ready for review; no database call was made."}
 write_report("supabase_production_readiness","Supabase Production Readiness",report,{"Mapped exports":mapped,"Blockers":report["blockers"]});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0
if __name__=="__main__":raise SystemExit(main())
