#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from oanda_demo_common import account_path,environment,request
def build():
 env=environment();ok,code,data,error=request("GET",account_path("/summary"));a=data.get("account") or {};report={"ok":ok,"generated_at":now(),"status":"demo_account_check_passed" if ok else "live_endpoint_detected_blocked" if env["live_endpoint_configured"] else "demo_account_check_failed","practice_host_used":ok,"http_status":code,"currency":a.get("currency"),"open_trade_count":a.get("openTradeCount"),"open_position_count":a.get("openPositionCount"),"pending_order_count":a.get("pendingOrderCount"),"margin_closeout_percent":a.get("marginCloseoutPercent"),"error_sanitized":error,"account_id_reported":False,"live_endpoint_used":False,"orders_placed":False,"external_action_performed":False};write_report("oanda_demo_account_check","Oanda Demo Account Check",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
