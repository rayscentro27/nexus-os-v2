#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 bridge=read_json(RUNTIME/"vibe_oanda_demo_bridge_latest.json",{});backtest=read_json(RUNTIME/"vibe_paper_backtest_dry_run_latest.json",{});summary=backtest.get("summary",{});report={"ok":bridge.get("ok",False),"generated_at":now(),"status":"vibe_oanda_demo_bridge_dry_run_passed" if bridge.get("ok") else "vibe_oanda_demo_bridge_dry_run_blocked","signal":{"strategy_id":summary.get("strategy_id"),"instrument":"AUD_USD","side":"buy","units":1,"mode":"demo_practice","tag":"NEXUS_VIBE_DEMO_SMOKE_TEST"},"metrics":{"trades":summary.get("total_trades"),"win_rate":summary.get("win_rate"),"simulated_pl_usd":summary.get("net_pnl_usd"),"drawdown_pct":summary.get("max_drawdown_pct")},"order_request_validated":bridge.get("ok",False),"order_placed":False,"live_endpoint_used":False,"real_money_trade":False,"external_action_performed":False};write_report("vibe_oanda_demo_bridge_dry_run","Vibe / Oanda Demo Bridge Dry Run",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
