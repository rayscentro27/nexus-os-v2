#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,ssl,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,parse_env,write_report  # noqa:E402
from nexus_runtime_env import load_runtime_env  # noqa:E402
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from activation.governed_http import get_json as governed_get_json  # noqa:E402
def build():
 values=dict(os.environ)
 for p in (ROOT/".env",ROOT/".env.local",ROOT/".env.nexus.recovered.local",Path.home()/"nexuslive/.env"):values.update(parse_env(p))
 values.update(load_runtime_env())
 token=values.get("OANDA_API_TOKEN") or values.get("OANDA_API_KEY") or values.get("OANDA_ACCESS_TOKEN") or "";account=values.get("OANDA_ACCOUNT_ID","");mode=(values.get("OANDA_ENVIRONMENT") or values.get("OANDA_API_URL") or "").lower();practice=mode in {"practice","demo"} or "api-fxpractice.oanda.com" in mode;checked=False;status_code=None;error=None;account_currency=None
 if practice and token and account:
  try:
   data=governed_get_json(f"https://api-fxpractice.oanda.com/v3/accounts/{account}/summary",provider="OANDA",service="practice_account_summary",headers={"Authorization":f"Bearer {token}"},timeout=20,estimated_units=1)
   checked=True;account_currency=(data.get("account") or {}).get("currency")
  except Exception as exc:error=exc.__class__.__name__
 report={"ok":checked,"generated_at":now(),"status":"oanda_practice_readonly_verified" if checked else "blocked_explicit_practice_environment_missing" if not practice else "oanda_practice_readonly_check_failed","practice_environment_explicit":practice,"token_present":bool(token),"account_id_present":bool(account),"readonly_check_performed":checked,"http_status":status_code,"account_currency":account_currency,"error_sanitized":error,"orders_placed":False,"live_endpoint_called":False,"credentials_printed":False,"external_action_performed":False,"exact_blocker":None if checked else "Set OANDA_ENVIRONMENT=practice (or OANDA_API_URL=https://api-fxpractice.oanda.com) for the existing demo credentials, then approve rerun."}
 write_report("oanda_demo_readonly_check","Oanda Demo Read-Only Check",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
