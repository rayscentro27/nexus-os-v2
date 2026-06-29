#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from payment_test_common import SUPABASE_READY,approval,env_data,now,payment_record,stripe_cli,write_json,write_report
def build():
 env=env_data();cli=stripe_cli();ready=cli["installed"] and env["test_secret_detected"]
 card=approval("approve_stripe_test_checkout","Approve Stripe CLI test Checkout","Approve one test-mode Checkout Session for the synthetic $97 package; no live mode.")
 plan={"product_name":"GoClear / Apex $97 Readiness Review (TEST)","amount_cents":9700,"currency":"usd","mode":"test","customer":"client_test_julius_erving","success_event":"checkout.session.completed","idempotency_key_template":"test-readiness-{client_id}-{attempt}","command_template":"stripe checkout sessions create --mode=payment --line-items[0][price_data][currency]=usd --line-items[0][price_data][unit_amount]=9700 ...","requires_Ray_approval":True,"executed":False}
 report={"ok":True,"generated_at":now(),"status":"ready_for_Ray_approval" if ready else "test_key_or_cli_missing","test_mode_ready":ready,"checkout_session_created":False,"live_payment_link_created":False,"real_charge_created":False,"external_action_performed":False,"plan":plan}
 write_json(SUPABASE_READY/"stripe_test_payment_status_latest.json",[payment_record()]);write_report("stripe_test_checkout_plan","Stripe Test Checkout Plan",report,{"Plan":plan,"Approval":card});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
