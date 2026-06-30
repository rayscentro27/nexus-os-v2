#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 checkout=read_json(RUNTIME/"stripe_test_checkout_session_latest.json",{});intent=read_json(RUNTIME/"stripe_test_payment_intent_latest.json",{});dry=read_json(RUNTIME/"payment_to_customer_onboarding_dry_run_latest.json",{});verify=read_json(RUNTIME/"fake_customer_records_verification_latest.json",{});live=read_json(RUNTIME/"client_dashboard_live_read_test_latest.json",{});report={"ok":True,"generated_at":now(),"status":"test_payment_onboarding_path_ready_external_steps_gated","checkout_status":checkout.get("status"),"payment_intent_status":intent.get("payment_intent_status") or intent.get("status"),"onboarding_dry_run_status":dry.get("status"),"fake_customer_inserted":verify.get("verified",False),"dashboard_live_read":live.get("status"),"real_charge":False,"persistent_insert":False,"email_sent":False,"next_action":"Approve the persistent synthetic customer insert or manually complete the Stripe test Checkout.","external_action_performed":False};write_report("payment_to_onboarding_status","Payment to Onboarding Status",report);write_report("fake_customer_live_dashboard_payment_path","Fake Customer Live Dashboard Payment Path",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
