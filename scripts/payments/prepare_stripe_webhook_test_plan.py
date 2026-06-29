#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from payment_test_common import approval,env_data,now,stripe_cli,write_report
def build():
 env=env_data();cli=stripe_cli();plan={"mode":"test","listener_command":"stripe listen --forward-to localhost:54321/functions/v1/stripe-webhook","trigger_command":"stripe trigger checkout.session.completed","signature_verification_required":True,"events":["checkout.session.completed","payment_intent.succeeded","payment_intent.payment_failed"],"idempotency_store":"proof_events/payment_status","executed":False}
 report={"ok":True,"generated_at":now(),"status":"plan_ready_requires_Ray_approval","stripe_cli_installed":cli["installed"],"webhook_secret_present":env["presence"]["STRIPE_WEBHOOK_SECRET"],"listener_started":False,"test_event_sent":False,"real_charge_created":False,"external_action_performed":False,"plan":plan}
 write_report("stripe_webhook_test_plan","Stripe Webhook Test Plan",report,{"Plan":plan,"Approval":approval("approve_stripe_test_webhook","Approve Stripe webhook test","Approve local Stripe CLI listener and synthetic test event; no live endpoints.")});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
