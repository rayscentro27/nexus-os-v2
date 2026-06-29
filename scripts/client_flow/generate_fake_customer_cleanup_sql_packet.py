#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,write_report  # noqa:E402
SQL="""-- SYNTHETIC TEST CLEANUP ONLY. Default behavior rolls back.
begin;
delete from public.payments_status where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.subscription_memberships where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_tasks where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_documents where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
select count(*) as remaining_rows from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
rollback;
"""
def build():
 path=ROOT/"reports/manual_publish/fake_customer_cleanup_sql_packet_latest.sql";path.write_text(SQL);report={"ok":True,"generated_at":now(),"status":"synthetic_cleanup_packet_ready_default_rollback","packet_path":str(path.relative_to(ROOT)),"scope":{"tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving"},"default_transaction_end":"rollback","cleanup_executed":False,"approval_required":True,"external_action_performed":False};write_report("fake_customer_cleanup_sql_packet","Fake Customer Cleanup SQL Packet",report,{"SQL":f"```sql\n{SQL}\n```"});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
