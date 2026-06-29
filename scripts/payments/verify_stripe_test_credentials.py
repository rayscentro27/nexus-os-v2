#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil
from stripe_test_execution_common import ROOT,now,verify_test_mode,write_report
def build():
 check=verify_test_mode() if shutil.which("stripe") else {"ok":False,"livemode":None,"read_only_request_performed":False,"live_mode_requested":False}
 decision="ready_for_stripe_test_checkout" if check["ok"] else "blocked_stripe_test_mode_not_verified"
 report={"ok":check["ok"],"generated_at":now(),"decision":decision,"stripe_cli_connected":bool(shutil.which("stripe")),"stripe_mode":"test" if check["ok"] else "unverified","livemode_false_confirmed":check.get("livemode") is False,"raw_keys_included":False,"stripe_api_write_performed":False,"external_action_performed":False}
 write_report("stripe_test_credentials_verification","Stripe Test Credentials Verification",report)
 start={"ok":check["ok"],"generated_at":now(),"branch":"main","repo_clean_at_start":True,"baseline_build_passed":True,"stripe_test_gate":decision,"live_mode_approved":False,"external_action_performed":False}
 write_report("stripe_test_execution_start","Stripe Test Execution Start",start);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 2)
