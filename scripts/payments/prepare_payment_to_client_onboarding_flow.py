#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from payment_test_common import SUPABASE_READY,approval,now,payment_record,write_json,write_report
def build():
 steps=["Verify Stripe test event signature","Reject non-test or duplicate event","Upsert test payment status by event ID","Create tenant-scoped synthetic client idempotently","Assign $97 readiness workflow","Create approved client tasks and document requirements","Queue GoClear review","Record proof event"]
 records=[{"id":f"payment_onboarding_{i+1}","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"payment_customer_onboarding","title":title,"sequence":i+1,"status":"dry_run_template","test_only":True,"approval_required":i in {1,3},"external_action_performed":False,"created_at":now()} for i,title in enumerate(steps)]
 cards=[approval("approve_fake_customer_persist","Approve fake customer persistent Supabase insertion","Approve test-tenant records only after webhook proof passes.")]
 write_json(SUPABASE_READY/"payment_customer_onboarding_latest.json",records);write_json(SUPABASE_READY/"payment_approval_cards_latest.json",cards)
 report={"ok":True,"generated_at":now(),"status":"dry_run_onboarding_ready","steps":len(steps),"idempotent":True,"live_database_inserted":False,"client_contacted":False,"real_charge_created":False,"external_action_performed":False}
 write_report("payment_to_client_onboarding_flow","Payment-to-Client Onboarding Flow",report,{"Steps":steps,"Approvals":cards});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
