#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from oanda_demo_common import execute_smoke
def build(instrument,units,demo_only):
 result=execute_smoke("NEXUS_DEMO_SMOKE_TEST",instrument,units,"oanda_demo_smoke") if demo_only else {"ok":False,"status":"demo_only_flag_required","demo_order_placed":False,"closed":False};report={"generated_at":now(),**result,"demo_only":demo_only,"live_endpoint_used":False,"real_money_trade":False,"external_action_performed":bool(result.get("demo_order_placed"))};write_report("oanda_demo_trade_smoke_test","Oanda Demo Trade Smoke Test",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--demo-only",action="store_true");p.add_argument("--units",type=int,default=1);p.add_argument("--instrument",default="AUD_USD");a=p.parse_args();r=build(a.instrument,a.units,a.demo_only);print(json.dumps(r,indent=2) if a.json else r)
