#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def card(i,title,decision,risk="medium",blocked=False):
 return {"id":i,"tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"stripe_customer_approval","title":title,"status":"blocked_for_now" if blocked else "pending_Ray_review","priority":"high","risk_level":risk,"automation_level":"approval_required","client_visible":False,"approval_required":True,"exact_decision_needed":decision,"options":["approve","reject","defer"],"test_mode":not blocked,"live_mode":False,"external_action_performed":False,"created_at":now()}
def build():
 checkout=read_json(RUNTIME/"stripe_test_checkout_session_latest.json",{});intent=read_json(RUNTIME/"stripe_test_payment_intent_latest.json",{});webhook=read_json(RUNTIME/"stripe_webhook_test_execution_plan_latest.json",{});onboarding=read_json(RUNTIME/"payment_to_customer_onboarding_dry_run_latest.json",{})
 cards=[
  card("approve-open-test-checkout","Approve opening/completing test Checkout Session manually","Approve manual browser opening of the gitignored test Checkout URL and use Stripe test card data only."),
  card("approve-webhook-listener","Approve webhook listener test","Implement a local signature-verifying endpoint, then approve test listener and synthetic triggers.","high"),
  card("approve-test-intent-confirmation","Approve PaymentIntent test confirmation using Stripe test method","Approve attaching pm_card_visa and confirming only the existing test PaymentIntent.","high"),
  card("approve-test-customer-insert","Approve persistent fake customer Supabase insertion","Approve only synthetic tenant_test_goclear records after webhook proof.","high"),
  card("approve-test-frontend-read","Approve frontend live-data read for fake customer","Approve tenant-safe authenticated reads for the synthetic test client."),
  card("approve-production-stripe-later","Approve production Stripe plan later, blocked for now","Do not approve until test webhook, idempotency, RLS, and rollback evidence pass.","high",True),
 ]
 write_json(SUPABASE_READY/"stripe_customer_ray_review_cards_latest.json",cards)
 write_report("stripe_customer_ray_review_cards","Stripe Customer Ray Review Cards",{"ok":True,"generated_at":now(),"status":"ready_for_Ray_review","cards_created":len(cards),"blocked_cards":sum(x["status"]=="blocked_for_now" for x in cards),"external_action_performed":False},{"Cards":cards})
 recommendation="Approve implementing the local signature-verifying webhook endpoint next; keep the Checkout open/unpaid and PaymentIntent unconfirmed until that proof path exists."
 hermes={"ok":True,"generated_at":now(),"status":"stripe_test_onboarding_brief_ready","checkout_status":checkout.get("status"),"payment_intent_status":intent.get("payment_intent_status"),"webhook_status":webhook.get("status"),"onboarding_status":onboarding.get("status"),"recommendation":recommendation,"real_charge_created":False,"persistent_database_insert":False,"external_action_performed":False}
 write_report("hermes_stripe_test_onboarding_brief","Hermes Stripe Test Onboarding Brief",hermes)
 visibility={"ok":True,"generated_at":now(),"stripe_cli_connected":True,"stripe_mode":"test","livemode":False,"test_checkout_session_status":checkout.get("status"),"test_payment_intent_status":intent.get("status"),"webhook_status":webhook.get("status"),"onboarding_dry_run_status":onboarding.get("status"),"persistent_client_insert_status":"blocked_pending_Ray_approval","real_charge_status":"no","next_approval_required":"Implement and test local webhook signature verification","external_action_performed":False}
 write_report("stripe_frontend_visibility","Stripe Frontend Visibility",visibility)
 record_sets=[read_json(SUPABASE_READY/name,[]) for name in ("stripe_test_checkout_status_latest.json","stripe_test_payment_intent_status_latest.json","stripe_webhook_test_status_latest.json","payment_to_customer_onboarding_records_latest.json","stripe_customer_ray_review_cards_latest.json")]
 master={"ok":True,"generated_at":now(),"stripe_cli_connected":True,"stripe_mode":"test","livemode_false_confirmed":checkout.get("livemode") is False and intent.get("livemode") is False,"checkout_session_attempted":checkout.get("attempted",False),"checkout_session_created":checkout.get("created",False),"checkout_url_generated":checkout.get("checkout_url_generated",False),"checkout_url_test_mode_safe":checkout.get("checkout_url_test_mode_safe",False),"payment_intent_attempted":intent.get("attempted",False),"payment_intent_created":intent.get("created",False),"payment_intent_confirmed":intent.get("confirmed",False),"webhook_listener_ready":webhook.get("listener_ready",False),"webhook_trigger_attempted":webhook.get("trigger_attempted",False),"webhook_event_received":webhook.get("event_received",False),"onboarding_dry_run_created":onboarding.get("ok",False),"supabase_ready_records_created":sum(len(x) for x in record_sets if isinstance(x,list)),"persistent_database_insert":False,"real_charge_made":False,"email_sent":False,"sms_sent":False,"ray_review_cards":len(cards),"hermes_recommendation":recommendation,"next_approval":"Approve local webhook endpoint implementation and listener test.","approved_test_objects_created":True,"live_mode_used":False}
 write_report("stripe_test_payment_execution","Stripe Test Payment Execution",master);return master
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
