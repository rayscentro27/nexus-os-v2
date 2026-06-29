#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from stripe_test_execution_common import SUPABASE_READY,fingerprint,mask,metadata_args,now,run_cli,save_private,verify_test_mode,write_json,write_report
def build():
 gate=verify_test_mode()
 if not gate["ok"]:
  report={"ok":False,"generated_at":now(),"status":"blocked_test_mode_not_verified","attempted":False,"created":False,"external_action_performed":False};write_report("stripe_test_payment_intent","Stripe Test PaymentIntent",report);return report
 args=["payment_intents","create","--idempotency","nexus-test-paymentintent-julius-97-v1","--amount","9700","--currency","usd","--description","GoClear/Apex $97 Readiness Review TEST",*metadata_args()]
 ok,data,code=run_cli(args);safe=ok and data.get("livemode") is False and str(data.get("id","")).startswith("pi_")
 if safe:save_private("payment_intent",{"id":data.get("id"),"status":data.get("status"),"livemode":False,"amount":data.get("amount"),"created_at":now()})
 public={"id":"stripe-test-payment-intent-97","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"stripe_test_payment_intent_status","title":"$97 readiness review test PaymentIntent","status":data.get("status") if safe else "creation_failed","amount_cents":9700,"currency":"usd","test_mode":True,"livemode":False if safe else None,"payment_intent_fingerprint":fingerprint(data.get("id")),"confirmed":False,"charge_created":False,"do_not_contact":True,"do_not_charge":True,"approval_required":True,"external_action_performed":safe,"created_at":now()}
 write_json(SUPABASE_READY/"stripe_test_payment_intent_status_latest.json",[public])
 report={"ok":safe,"generated_at":now(),"status":"test_payment_intent_created_unconfirmed" if safe else "test_payment_intent_creation_failed","attempted":True,"created":safe,"livemode":data.get("livemode") if ok else None,"payment_intent_id_masked":mask(data.get("id")),"payment_intent_fingerprint":fingerprint(data.get("id")),"payment_intent_status":data.get("status") if safe else None,"confirmed":False,"payment_method_attached":False,"real_charge_created":False,"raw_object_saved_gitignored":safe,"cli_exit_code":code,"external_action_performed":safe}
 write_report("stripe_test_payment_intent","Stripe Test PaymentIntent",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 2)
