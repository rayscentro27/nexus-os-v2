#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 account=read_json(RUNTIME/"oanda_demo_account_check_latest.json",{});pricing=read_json(RUNTIME/"oanda_demo_pricing_check_latest.json",{});instruments=read_json(RUNTIME/"oanda_demo_instruments_check_latest.json",{});bridge=read_json(RUNTIME/"vibe_oanda_demo_bridge_dry_run_latest.json",{});tournament=read_json(RUNTIME/"trading_demo_tournament_latest.json",{});gates={"practice_account":account.get("ok",False),"pricing":pricing.get("ok",False),"instruments":instruments.get("ok",False),"bridge_dry_run":bridge.get("ok",False),"tournament":tournament.get("ok",False)};report={"ok":all(gates.values()),"generated_at":now(),"status":"trading_demo_readiness_cycle_passed" if all(gates.values()) else "trading_demo_readiness_cycle_blocked","gates":gates,"recurring_demo_orders_allowed":False,"live_orders_allowed":False,"orders_placed":False,"external_action_performed":False};write_report("trading_demo_readiness_cycle","Trading Demo Readiness Cycle",report,{"Gates":gates});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
