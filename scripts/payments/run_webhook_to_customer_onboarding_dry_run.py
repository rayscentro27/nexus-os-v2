#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from stripe_test_execution_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report
def build():
 trigger=read_json(RUNTIME/"stripe_webhook_trigger_results_latest.json",{});events=trigger.get("accepted_event_types",[]);rows=[]
 for i,event in enumerate(events,1):rows.append({"id":f"webhook-dry-{i}","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"webhook_onboarding_dry_run","title":event,"status":"mapped_test_event_not_persisted","test_mode":True,"dry_run":True,"do_not_contact":True,"do_not_charge":True,"database_inserted":False,"email_sent":False,"created_at":now()})
 write_json(SUPABASE_READY/"webhook_to_customer_onboarding_records_latest.json",rows);report={"ok":bool(rows),"generated_at":now(),"status":"webhook_events_mapped_to_onboarding_dry_run" if rows else "no_verified_webhook_events","verified_event_types":events,"records_created":len(rows),"persistent_database_insert":False,"auth_user_created":False,"email_sent":False,"real_charge_made":False,"external_action_performed":False};write_report("webhook_to_customer_onboarding_dry_run","Webhook-to-Customer Onboarding Dry Run",report,{"Records":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
