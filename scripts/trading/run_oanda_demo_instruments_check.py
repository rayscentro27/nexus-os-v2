#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from oanda_demo_common import account_path,request
MAJORS=["AUD_USD","EUR_USD","GBP_USD","USD_CAD","NZD_USD","USD_CHF","USD_JPY"]
def build():
 ok,code,data,error=request("GET",account_path("/instruments"));names={x.get("name") for x in data.get("instruments",[])};available=[x for x in MAJORS if x in names];report={"ok":ok and bool(available),"generated_at":now(),"status":"demo_instruments_check_passed" if ok and available else "demo_instruments_check_failed","http_status":code,"instrument_count":len(names),"aud_usd_available":"AUD_USD" in names,"safe_major_instruments":available,"error_sanitized":error,"live_endpoint_used":False,"orders_placed":False,"external_action_performed":False};write_report("oanda_demo_instruments_check","Oanda Demo Instruments Check",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
