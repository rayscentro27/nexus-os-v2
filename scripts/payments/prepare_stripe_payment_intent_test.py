#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from payment_test_common import approval,env_data,now,stripe_cli,write_report
def build():
 ready=stripe_cli()["installed"] and env_data()["test_secret_detected"]
 plan={"amount_cents":9700,"currency":"usd","mode":"test","confirm":False,"capture_method":"automatic","metadata":{"client_id":"client_test_julius_erving","package":"readiness_review_97","test_only":"true"},"idempotency_required":True,"executed":False}
 card=approval("approve_stripe_test_payment_intent","Approve Stripe test PaymentIntent","Approve creation of one unconfirmed $97 test-mode PaymentIntent only.")
 report={"ok":True,"generated_at":now(),"status":"ready_for_Ray_approval" if ready else "test_key_or_cli_missing","test_mode_ready":ready,"payment_intent_created":False,"real_charge_created":False,"external_action_performed":False,"plan":plan}
 write_report("stripe_payment_intent_test_plan","Stripe PaymentIntent Test Plan",report,{"Plan":plan,"Approval":card});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
