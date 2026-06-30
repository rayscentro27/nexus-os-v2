#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 verify=read_json(RUNTIME/"oanda_demo_account_verification_latest.json",{});account=read_json(RUNTIME/"oanda_demo_account_check_latest.json",{});pricing=read_json(RUNTIME/"oanda_demo_pricing_check_latest.json",{});instruments=read_json(RUNTIME/"oanda_demo_instruments_check_latest.json",{});gates={"demo_verified":verify.get("ok",False),"account_check":account.get("ok",False),"pricing_check":pricing.get("ok",False),"instruments_check":instruments.get("ok",False),"live_endpoint_unused":not any(x.get("live_endpoint_used",False) for x in (verify,account,pricing,instruments))};report={"ok":all(gates.values()),"generated_at":now(),"status":"oanda_demo_connector_verified" if all(gates.values()) else "oanda_demo_connector_gate_failed","gates":gates,"practice_host":"https://api-fxpractice.oanda.com","live_endpoint_used":False,"orders_placed":False,"real_money_actions":False,"external_action_performed":False};write_report("oanda_demo_connector_report","Oanda Demo Connector Report",report,{"Gates":gates});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
