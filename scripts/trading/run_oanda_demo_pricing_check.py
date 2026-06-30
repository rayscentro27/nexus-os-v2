#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
from oanda_demo_common import account_path,request
def build():
 instruments=read_json(RUNTIME/"oanda_demo_instruments_check_latest.json",{}).get("safe_major_instruments",[]);instrument="AUD_USD" if "AUD_USD" in instruments else instruments[0] if instruments else "AUD_USD";ok,code,data,error=request("GET",account_path("/pricing"),query={"instruments":instrument});price=(data.get("prices") or [{}])[0] if ok else {};bid=((price.get("bids") or [{}])[0]).get("price");ask=((price.get("asks") or [{}])[0]).get("price");report={"ok":ok and bool(bid and ask),"generated_at":now(),"status":"demo_pricing_check_passed" if ok and bid and ask else "demo_pricing_check_failed","http_status":code,"instrument":instrument,"bid":bid,"ask":ask,"tradeable":price.get("tradeable"),"error_sanitized":error,"live_endpoint_used":False,"orders_placed":False,"external_action_performed":False};write_report("oanda_demo_pricing_check","Oanda Demo Pricing Check",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
