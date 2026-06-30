#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build(execute=False):
 records=read_json(SUPABASE_READY/"payment_to_customer_onboarding_records_latest.json",[]);direct=read_json(RUNTIME/"production_rls_cli_verification_latest.json",{});cleanup=(ROOT/"reports/manual_publish/fake_customer_cleanup_sql_packet_latest.sql").exists()
 test_only=bool(records) and all(x.get("test_mode") is True and x.get("dry_run") is True for x in records);gates={"rls_directly_verified":direct.get("ok",False),"tables_found_25":direct.get("tables_found")==25,"rls_enabled_25":direct.get("rls_enabled")==25,"authenticated_policies_55":direct.get("authenticated_policies")==55,"unsafe_public_policies_zero":direct.get("unsafe_public_or_unconditional_policies")==0,"records_test_only":test_only,"cleanup_packet_ready":cleanup,"explicit_execute":execute};ready=all(v for k,v in gates.items() if k!="explicit_execute")
 allowed=ready and execute
 plan={"id":"persistent-fake-customer-plan","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"persistent_insert_plan","title":"Julius Erving / Doctor J LLC synthetic test insertion","status":"ready_for_Ray_approval_explicit_execute" if ready else "blocked_gate_not_passed","source_records":len(records),"insertion_order":["client_profiles","subscription_memberships","payments_status","client_tasks","client_documents","admin_review_queue","proof_events"],"cleanup_where":{"tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving"},"test_mode":True,"fake_customer":True,"do_not_contact":True,"do_not_charge":True,"approval_required":True,"execute_requested":execute,"database_insert_performed":False,"created_at":now()}
 write_json(SUPABASE_READY/"persistent_fake_customer_insert_plan_latest.json",[plan]);report={"ok":True,"generated_at":now(),"status":plan["status"],"gates":gates,"ready_for_approval":ready,"execute_flag_supported":True,"execute_used":execute,"persistent_database_insert":False,"cleanup_plan_ready":cleanup,"ray_review_card":"Approve persistent fake customer Supabase insertion for Julius Erving / Doctor J LLC.","external_action_performed":False}
 write_report("persistent_fake_customer_insert_gate","Persistent Fake Customer Insert Gate",report,{"Gate checks":gates,"Cleanup":plan["cleanup_where"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--execute",action="store_true");a=p.parse_args();r=build(a.execute);print(json.dumps(r,indent=2) if a.json else r)
