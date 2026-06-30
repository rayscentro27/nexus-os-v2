#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
APPROVAL="approve-persistent-fake-customer"
INSERT_SQL="""begin;
insert into public.client_profiles (external_id,tenant_id,client_id,category,title,summary,status,client_visible,approval_required,source,payload)
values ('client_test_julius_erving','tenant_test_goclear','client_test_julius_erving','client_profile','Julius Erving','Synthetic test customer: Doctor J LLC, delivery driver, AZ','test_pending',false,true,'manual_test_customer','{"test_mode":true,"fake_customer":true,"do_not_contact":true,"do_not_charge":true,"email":"ray@goclearonline.com","primary_goal":"all"}'::jsonb)
on conflict (tenant_id,external_id) where external_id is not null do update set payload=excluded.payload,updated_at=now();
insert into public.subscription_memberships (id,tenant_id,client_id,category,title,status,client_visible,approval_required,payload)
values ('membership_test_julius_97','tenant_test_goclear','client_test_julius_erving','subscription_membership','$97 readiness review','test_not_paid',false,true,'{"test_mode":true,"fake_customer":true,"do_not_charge":true,"amount_cents":9700}'::jsonb)
on conflict (id) do update set status=excluded.status,updated_at=now();
insert into public.payments_status (id,tenant_id,client_id,category,title,status,client_visible,approval_required,payload)
values ('payment_test_julius_97','tenant_test_goclear','client_test_julius_erving','payment_status','Stripe test payment','test_open_unpaid',false,true,'{"test_mode":true,"fake_customer":true,"do_not_charge":true}'::jsonb)
on conflict (id) do update set status=excluded.status,updated_at=now();
commit;"""
CLEANUP_SQL="""begin;
delete from public.payments_status where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.subscription_memberships where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
commit;"""
def build(execute=False,cleanup=False,approval_id=None):
 rls=read_json(RUNTIME/"production_rls_cli_verification_latest.json",{});approved=approval_id==APPROVAL;ready=rls.get("ok",False) and approved
 action="cleanup" if cleanup else "insert";performed=False;error=None
 if execute and ready:
  sql=CLEANUP_SQL if cleanup else INSERT_SQL
  proc=subprocess.run(["supabase","db","query","--linked","--output","json",sql],cwd=ROOT,capture_output=True,text=True,timeout=45)
  performed=proc.returncode==0;error=None if performed else "Supabase linked query failed; raw output withheld."
 status="executed_approved_synthetic_cleanup" if performed and cleanup else "executed_approved_synthetic_insert" if performed else "execution_failed" if execute else "ready_for_explicit_Ray_approval"
 report={"ok":not execute or performed,"generated_at":now(),"status":status if rls.get("ok") else "blocked_rls_not_verified","action":action,"rls_verified":rls.get("ok",False),"approval_id_required":APPROVAL,"approval_present":approved,"execute_requested":execute,"database_write_performed":performed,"error":error,"test_mode":True,"fake_customer":True,"do_not_contact":True,"do_not_charge":True,"insert_command":f"python3 scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py --json --execute --approval-id {APPROVAL}","cleanup_command":f"python3 scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py --json --execute --cleanup --approval-id {APPROVAL}","external_action_performed":performed};write_report("fake_customer_persistent_insert_execution_packet","Fake Customer Persistent Insert Execution Packet",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--execute",action="store_true");p.add_argument("--cleanup",action="store_true");p.add_argument("--approval-id");a=p.parse_args();r=build(a.execute,a.cleanup,a.approval_id);print(json.dumps(r,indent=2) if a.json else r)
