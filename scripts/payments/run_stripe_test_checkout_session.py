#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,urllib.parse
from stripe_test_execution_common import SUPABASE_READY,fingerprint,load_private,mask,metadata_args,now,run_cli,save_private,verify_test_mode,write_json,write_report
def build(reuse_open=False):
 gate=verify_test_mode()
 if not gate["ok"]:
  report={"ok":False,"generated_at":now(),"status":"blocked_test_mode_not_verified","attempted":False,"created":False,"external_action_performed":False};write_report("stripe_test_checkout_session","Stripe Test Checkout Session",report);return report
 existing=load_private().get("checkout",{}) if reuse_open else {};reused=bool(existing.get("id"))
 args=["checkout","sessions","retrieve",existing["id"],"--confirm"] if reused else ["checkout","sessions","create","--confirm","--idempotency","nexus-test-checkout-julius-97-v1","--mode","payment","--client-reference-id","client_test_julius_erving","--customer-email","ray@goclearonline.com","--success-url","https://nexusv20.netlify.app/client?stripe_test=success","-d","cancel_url=https://nexusv20.netlify.app/client?stripe_test=cancel","-d","line_items[0][quantity]=1","-d","line_items[0][price_data][currency]=usd","-d","line_items[0][price_data][unit_amount]=9700","-d","line_items[0][price_data][product_data][name]=GoClear/Apex Credit & Funding Readiness Review (TEST)",*metadata_args()]
 ok,data,code=run_cli(args);safe=ok and data.get("livemode") is False and str(data.get("id","")).startswith("cs_test_")
 if safe:save_private("checkout",{"id":data.get("id"),"url":data.get("url"),"status":data.get("status"),"payment_status":data.get("payment_status"),"livemode":False,"created_at":now()})
 url=str(data.get("url") or "");host=urllib.parse.urlparse(url).hostname or ""
 public={"id":"stripe-test-checkout-97","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"stripe_test_checkout_status","title":"$97 readiness review test Checkout","status":"open_test_session" if safe else "creation_failed","amount_cents":9700,"currency":"usd","test_mode":True,"livemode":False if safe else None,"checkout_session_fingerprint":fingerprint(data.get("id")),"checkout_url_generated":bool(url),"checkout_url_host":host,"checkout_completed":False,"do_not_contact":True,"do_not_charge":True,"approval_required":True,"external_action_performed":safe,"created_at":now()}
 write_json(SUPABASE_READY/"stripe_test_checkout_status_latest.json",[public])
 report={"ok":safe,"generated_at":now(),"status":"test_checkout_session_reused_open_not_completed" if safe and reused else "test_checkout_session_created_open_not_completed" if safe else "test_checkout_creation_failed","attempted":True,"created":safe,"reused_existing":reused,"livemode":data.get("livemode") if ok else None,"session_id_masked":mask(data.get("id")),"session_id_fingerprint":fingerprint(data.get("id")),"checkout_url_generated":bool(url),"checkout_url_test_mode_safe":safe and host.endswith("stripe.com"),"checkout_url_host":host,"checkout_completed":data.get("status")=="complete","payment_status":data.get("payment_status") if safe else None,"real_charge_created":False,"email_sent":False,"browser_opened":False,"raw_object_saved_gitignored":safe,"cli_exit_code":code,"external_action_performed":not reused and safe}
 write_report("stripe_test_checkout_session","Stripe Test Checkout Session",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--reuse-open",action="store_true");a=p.parse_args();r=build(a.reuse_open);print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 2)
