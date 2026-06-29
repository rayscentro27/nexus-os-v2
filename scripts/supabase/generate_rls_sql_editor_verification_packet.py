#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,write_report  # noqa:E402
SQL="""-- READ-ONLY Nexus client RLS verification packet
select c.relname as table_name, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as force_rls
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname in (
  'client_profiles','client_tasks','client_documents','readiness_scores','credit_workflow_items',
  'dispute_cases','dispute_letter_drafts','business_profile_requirements','funding_readiness_scores',
  'business_opportunities','partner_offers','approval_cards','admin_review_queue','approved_client_guidance',
  'client_questions','client_escalations','proof_events','connector_health','engine_runs','youtube_sources',
  'youtube_review_items','social_drafts','subscription_memberships','payments_status','tenant_memberships')
order by c.relname;

select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname='public' and tablename in (
  'client_profiles','client_tasks','client_documents','readiness_scores','credit_workflow_items',
  'dispute_cases','dispute_letter_drafts','business_profile_requirements','funding_readiness_scores',
  'business_opportunities','partner_offers','approval_cards','admin_review_queue','approved_client_guidance',
  'client_questions','client_escalations','proof_events','connector_health','engine_runs','youtube_sources',
  'youtube_review_items','social_drafts','subscription_memberships','payments_status','tenant_memberships')
order by tablename, policyname;

-- Must return zero rows: public/anon or unconditional permissive access.
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname='public' and (
  roles && array['public','anon']::name[] or coalesce(qual,'') ~* '^\\s*true\\s*$' or coalesce(with_check,'') ~* '^\\s*true\\s*$');
"""
def build():
 path=ROOT/"reports/manual_publish/rls_sql_editor_verification_packet_latest.sql";path.write_text(SQL)
 report={"ok":True,"generated_at":now(),"status":"read_only_sql_packet_generated","packet_path":str(path.relative_to(ROOT)),"statements":3,"checks":["table exists and RLS enabled","policy names/commands/roles/permissive mode","tenant/client/admin predicates","public permissive true policies"],"contains_mutation_sql":False,"database_write_performed":False,"approval_required":True,"external_action_performed":False};write_report("rls_sql_editor_verification_packet","RLS SQL Editor Verification Packet",report,{"SQL":f"```sql\n{SQL}\n```"});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
