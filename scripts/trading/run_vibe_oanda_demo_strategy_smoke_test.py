#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
from oanda_demo_common import execute_smoke
def build(demo_only,tiny_test):
 bridge=read_json(RUNTIME/"vibe_oanda_demo_bridge_latest.json",{});result=execute_smoke("NEXUS_VIBE_DEMO_SMOKE_TEST","AUD_USD",1,"vibe_oanda_demo_smoke") if demo_only and tiny_test and bridge.get("ok") else {"ok":False,"status":"vibe_strategy_smoke_gate_failed","demo_order_placed":False,"closed":False};report={"generated_at":now(),**result,"demo_only":demo_only,"tiny_test":tiny_test,"recovered_vibe_adapter":True,"live_endpoint_used":False,"real_money_trade":False,"external_action_performed":bool(result.get("demo_order_placed"))};write_report("vibe_oanda_demo_strategy_smoke_test","Vibe / Oanda Demo Strategy Smoke Test",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--demo-only",action="store_true");p.add_argument("--tiny-test",action="store_true");a=p.parse_args();r=build(a.demo_only,a.tiny_test);print(json.dumps(r,indent=2) if a.json else r)
