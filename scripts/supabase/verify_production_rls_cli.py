#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,write_report  # noqa:E402
QUERY="""with targets(table_name) as (values ('client_profiles'),('client_tasks'),('client_documents'),('readiness_scores'),('credit_workflow_items'),('dispute_cases'),('dispute_letter_drafts'),('business_profile_requirements'),('funding_readiness_scores'),('business_opportunities'),('partner_offers'),('approval_cards'),('admin_review_queue'),('approved_client_guidance'),('client_questions'),('client_escalations'),('proof_events'),('connector_health'),('engine_runs'),('youtube_sources'),('youtube_review_items'),('social_drafts'),('subscription_memberships'),('payments_status'),('tenant_memberships')) select (select count(*) from targets) expected_tables,(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace join targets t on t.table_name=c.relname where n.nspname='public' and c.relkind in ('r','p')) tables_found,(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace join targets t on t.table_name=c.relname where n.nspname='public' and c.relrowsecurity) rls_enabled,(select count(*) from pg_policies p join targets t on t.table_name=p.tablename where p.schemaname='public') policies_found,(select count(*) from pg_policies p join targets t on t.table_name=p.tablename where p.schemaname='public' and 'authenticated'=any(p.roles)) authenticated_policies,(select count(*) from pg_policies where schemaname='public' and (roles && array['public','anon']::name[] or coalesce(qual,'') ~* '^\\s*true\\s*$' or coalesce(with_check,'') ~* '^\\s*true\\s*$')) unsafe_public_or_unconditional_policies;"""
def build():
 p=subprocess.run(["supabase","db","query","--linked","--output","json",QUERY],cwd=ROOT,capture_output=True,text=True,timeout=45);payload={}
 if p.returncode==0:
  match=re.search(r'\{\s*"boundary".*\}\s*(?:A new version|$)',p.stdout,re.S)
  try: data=json.loads(match.group(0).split("\nA new version")[0] if match else p.stdout);payload=(data.get("rows") or [{}])[0]
  except json.JSONDecodeError:payload={}
 ok=payload.get("tables_found")==25 and payload.get("rls_enabled")==25 and payload.get("authenticated_policies")==55 and payload.get("unsafe_public_or_unconditional_policies")==0
 report={"ok":ok,"generated_at":now(),"status":"direct_production_rls_verified" if ok else "direct_rls_verification_failed","project_ref":"iqjwgpnujbeoyaeuwehj","expected_tables":25,"tables_found":payload.get("tables_found"),"rls_enabled":payload.get("rls_enabled"),"policies_found":payload.get("policies_found"),"authenticated_policies":payload.get("authenticated_policies"),"unsafe_public_or_unconditional_policies":payload.get("unsafe_public_or_unconditional_policies"),"database_write_performed":False,"external_action_performed":False,"error_sanitized":None if p.returncode==0 else "Supabase linked query failed"};write_report("production_rls_cli_verification","Production RLS CLI Verification",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 1)
