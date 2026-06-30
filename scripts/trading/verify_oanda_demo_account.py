#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from oanda_demo_common import account_path,environment,request
def build():
 env=environment();ok=False;code=None;error=None;currency=None
 if env["live_endpoint_configured"]:status="live_endpoint_detected_blocked"
 elif not env["token_present"]:status="credentials_missing"
 elif not env["account_id_present"]:status="account_id_missing"
 else:
  ok,code,data,error=request("GET",account_path("/summary"));currency=(data.get("account") or {}).get("currency");status="demo_verified" if ok else "token_scope_failed" if code in {401,403} else "practice_endpoint_failed"
 report={"ok":ok,"generated_at":now(),"status":status,"practice_host":"https://api-fxpractice.oanda.com","credentials_detected":env["token_present"] and env["account_id_present"],"demo_endpoint_verified":ok,"account_currency":currency,"http_status":code,"error_sanitized":error,"live_endpoint_configured":env["live_endpoint_configured"],"live_endpoint_used":False,"orders_placed":False,"credentials_printed":False,"external_action_performed":False};write_report("oanda_demo_account_verification","Oanda Demo Account Verification",report);write_report("oanda_demo_policy","Oanda Demo Policy",{"ok":True,"generated_at":now(),"status":"demo_policy_active","practice_only":True,"preferred_allowed_endpoint":"https://api-fxpractice.oanda.com","live_endpoint_blocked":True,"max_smoke_units":1,"external_action_performed":False});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
