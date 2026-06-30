#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
from oanda_demo_common import account_path,load_local,mask,request,save_local
def build(demo_only):
 local=load_local("oanda_demo_smoke");trade=str(local.get("trade_id") or "");order=str(local.get("order_id") or "");closed=bool(local.get("closed"));attempted=False;code=None;error=None
 if demo_only and not closed and trade:
  attempted=True;closed,code,_,error=request("PUT",account_path(f"/trades/{urllib.parse.quote(trade,safe='')}/close"),{"units":"ALL"})
 elif demo_only and not closed and order:
  attempted=True;closed,code,_,error=request("PUT",account_path(f"/orders/{urllib.parse.quote(order,safe='')}/cancel"),{})
 if local and closed:local["closed"]=True;save_local("oanda_demo_smoke",local)
 report={"ok":closed,"generated_at":now(),"status":"demo_smoke_closeout_confirmed" if closed else "demo_smoke_closeout_not_confirmed","demo_only":demo_only,"closeout_api_attempted":attempted,"http_status":code,"trade_id_masked":mask(trade),"order_id_masked":mask(order),"error_sanitized":error,"live_endpoint_used":False,"real_money_trade":False,"external_action_performed":attempted};write_report("oanda_demo_trade_closeout","Oanda Demo Trade Closeout",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--demo-only",action="store_true");a=p.parse_args();r=build(a.demo_only);print(json.dumps(r,indent=2) if a.json else r)
