#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,write_report  # noqa:E402
QUERY="""select (select count(*) from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving') client_profiles,(select count(*) from public.subscription_memberships where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving') memberships,(select count(*) from public.payments_status where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving') payments;"""
def build():
 p=subprocess.run(["supabase","db","query","--linked","--output","json",QUERY],cwd=ROOT,capture_output=True,text=True,timeout=45);row={}
 if p.returncode==0:
  m=re.search(r'\{\s*"boundary".*\}\s*(?:A new version|$)',p.stdout,re.S)
  try:data=json.loads(m.group(0).split("\nA new version")[0] if m else p.stdout);row=(data.get("rows") or [{}])[0]
  except json.JSONDecodeError:row={}
 verified=all(int(row.get(k,0))>=1 for k in ("client_profiles","memberships","payments"));report={"ok":True,"generated_at":now(),"status":"fake_customer_records_verified" if verified else "fake_customer_not_inserted","verified":verified,"record_counts":{k:int(row.get(k,0)) for k in ("client_profiles","memberships","payments")},"query_read_only":True,"real_client_data_used":False,"database_write_performed":False,"external_action_performed":False};write_report("fake_customer_records_verification","Fake Customer Records Verification",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
