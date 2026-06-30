#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 backtest=read_json(RUNTIME/"vibe_paper_backtest_dry_run_latest.json",{});oanda=read_json(RUNTIME/"oanda_demo_connector_report_latest.json",{});smoke=read_json(RUNTIME/"oanda_demo_trade_smoke_test_latest.json",{});gates={"recovered_adapter_usable":backtest.get("ok",False),"oanda_demo_verified":oanda.get("ok",False),"oanda_smoke_closed":smoke.get("ok",False) and smoke.get("closed",False)};report={"ok":all(gates.values()),"generated_at":now(),"status":"vibe_oanda_demo_bridge_ready" if all(gates.values()) else "vibe_oanda_demo_bridge_blocked","gates":gates,"bridge_contract":{"input":"bounded synthetic strategy signal","output":"one-unit practice order request","required_tag":"NEXUS_VIBE_DEMO_SMOKE_TEST","immediate_close":True},"vibe_cli_required":False,"recovered_adapter_used":True,"live_endpoint_allowed":False,"live_trading_allowed":False,"order_placed":False,"external_action_performed":False};write_report("vibe_oanda_demo_bridge","Vibe / Oanda Demo Bridge",report,{"Gates":gates});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
