#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from stripe_test_execution_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report
def build():
 checkout=read_json(RUNTIME/"stripe_test_checkout_session_latest.json",{});intent=read_json(RUNTIME/"stripe_test_payment_intent_latest.json",{})
 base={"tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","test_mode":True,"dry_run":True,"do_not_contact":True,"do_not_charge":True,"external_action_performed":False,"created_at":now()}
 specs=[
  ("dry-client","client_profile","Julius Erving","pending_test_checkout_completion"),
  ("dry-business","business_profile","Doctor J LLC","test_profile_pending"),
  ("dry-package","subscription_membership","$97 readiness review","test_not_activated"),
  ("dry-payment-checkout","payment_status","Stripe test Checkout Session","test_open_unpaid" if checkout.get("created") else "test_missing"),
  ("dry-payment-intent","payment_status","Stripe test PaymentIntent","test_unconfirmed" if intent.get("created") else "test_missing"),
  ("dry-task-intake","client_task","Complete readiness intake","draft_only"),
  ("dry-task-documents","client_task","Review document checklist","draft_only"),
  ("dry-document-identity","client_document","Identity verification requirement","not_uploaded"),
  ("dry-document-business","client_document","Business formation requirement","not_uploaded"),
  ("dry-review","admin_review_queue","GoClear readiness review","pending_test_review"),
  ("dry-guidance","approved_client_guidance","Complete intake before funding review","test_template"),
  ("dry-proof","proof_event","Payment-to-customer onboarding dry-run generated","success"),
 ]
 rows=[{"id":i,"category":c,"title":t,"status":s,"client_visible":False,"approval_required":c in {"admin_review_queue","payment_status"},**base} for i,c,t,s in specs]
 write_json(SUPABASE_READY/"payment_to_customer_onboarding_records_latest.json",rows)
 report={"ok":True,"generated_at":now(),"status":"onboarding_dry_run_created","checkout_test_object_available":checkout.get("created",False),"payment_intent_test_object_available":intent.get("created",False),"records_created":len(rows),"persistent_database_insert":False,"auth_user_created":False,"email_sent":False,"sms_sent":False,"real_charge_created":False,"external_action_performed":False}
 write_report("payment_to_customer_onboarding_dry_run","Payment-to-Customer Onboarding Dry Run",report,{"Record categories":[x["category"] for x in rows]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
