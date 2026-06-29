#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from supabase_activation_common import *


def sql()->str:
 existing={"client_profiles","business_opportunities","partner_offers"}
 shared=[("tenant_id","text"),("client_id","text"),("category","text"),("title","text"),("summary","text"),("status","text"),("score","numeric"),("priority","text"),("risk_level","text"),("automation_level","text"),("client_visible","boolean not null default false"),("approval_required","boolean not null default false"),("goclear_review_status","text"),("source","text"),("source_concept","text"),("recommended_next_action","text"),("payload","jsonb not null default '{}'::jsonb"),("updated_at","timestamptz not null default now()")]
 lines=["-- DRAFT ONLY: review, timestamp, and approve before applying.","-- Additive core client portal schema; no DROP/TRUNCATE/destructive statements.","-- Three legacy UUID tables are extended in place; export ids map to external_id.","begin;", "",
 "create table if not exists public.tenant_memberships (tenant_id text not null, user_id uuid not null references auth.users(id) on delete cascade, role text not null check (role in ('super_admin','admin','operator','client')), client_id text, created_at timestamptz not null default now(), primary key (tenant_id,user_id));"]
 for table in TABLES:
  lines.append("")
  if table in existing:
   lines += [f"-- Existing UUID table: preserve rows/schema and add portal fields safely.",f"alter table public.{table} add column if not exists external_id text;"]
   lines += [f"alter table public.{table} add column if not exists {name} {kind};" for name,kind in shared]
   lines += [f"create unique index if not exists {table}_tenant_external_idx on public.{table}(tenant_id,external_id) where external_id is not null;"]
  else:
   lines += [f"create table if not exists public.{table} (", "  id text primary key,", "  tenant_id text not null,", "  client_id text,", "  category text,", "  title text,", "  summary text,", "  status text not null default 'open',", "  score numeric,", "  priority text,", "  risk_level text,", "  automation_level text,", "  client_visible boolean not null default false,", "  approval_required boolean not null default false,", "  goclear_review_status text,", "  source text,", "  source_concept text,", "  recommended_next_action text,", "  payload jsonb not null default '{}'::jsonb,", "  created_at timestamptz not null default now(),", "  updated_at timestamptz not null default now()", ");"]
  lines += [f"create index if not exists {table}_tenant_client_idx on public.{table}(tenant_id,client_id);",f"alter table public.{table} enable row level security;",
  f"create policy \"{table}_tenant_select\" on public.{table} for select to authenticated using (public.nexus_is_active_admin() or exists (select 1 from public.tenant_memberships tm where tm.tenant_id={table}.tenant_id and tm.user_id=auth.uid() and (tm.role in ('super_admin','admin','operator') or (tm.role='client' and tm.client_id={table}.client_id and {table}.client_visible))));",
  f"create policy \"{table}_operator_write\" on public.{table} for all to authenticated using (public.nexus_is_active_admin() or exists (select 1 from public.tenant_memberships tm where tm.tenant_id={table}.tenant_id and tm.user_id=auth.uid() and tm.role in ('super_admin','admin','operator'))) with check (public.nexus_is_active_admin() or exists (select 1 from public.tenant_memberships tm where tm.tenant_id={table}.tenant_id and tm.user_id=auth.uid() and tm.role in ('super_admin','admin','operator')));",
  f"grant select, insert, update on public.{table} to authenticated;"]
 lines += ["","alter table public.tenant_memberships enable row level security;","create policy \"memberships_self_or_admin_select\" on public.tenant_memberships for select to authenticated using (user_id=auth.uid() or public.nexus_is_active_admin());","create policy \"memberships_admin_manage\" on public.tenant_memberships for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());","grant select, insert, update on public.tenant_memberships to authenticated;","","-- Private storage bucket and storage.objects policies require separate review and are intentionally not auto-created.","-- Legacy UUID tables require id -> external_id transformation in the future execution runner.","commit;",""]
 return "\n".join(lines)


def build()->dict:
 path=ROOT/"supabase"/"migrations"/"DRAFT_client_portal_core_tables.sql";path.write_text(sql())
 report={"ok":True,"generated_at":now(),"status":"draft_generated","migration_path":str(path.relative_to(ROOT)),"tables_drafted":TABLES,"table_count":len(TABLES),
  "rls_enabled_in_draft":True,"destructive_statements":False,"live_database_changed":False,"next_required_action":"Ray reviews SQL/RLS, runs local Supabase tests, then renames to a timestamped migration.","external_action_performed":False}
 write_report("supabase_migration_draft","Supabase Migration Draft",report,{"Tables":TABLES});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
