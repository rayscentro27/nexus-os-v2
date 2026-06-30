#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import ROOT,SUPABASE_READY,now,read_json,write_json,write_report
def build():
 rows=read_json(ROOT/"configs/stripe_product_registry.json",{}).get("products",[]);write_json(SUPABASE_READY/"stripe_product_registry_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"stripe_test_product_registry_ready","mode":"test_only","products":len(rows),"test_products_open":sum(x["status"]=="test_session_open_unpaid" for x in rows),"live_products_created":0,"real_charge":False,"external_action_performed":False};write_report("stripe_product_registry","Stripe Product Registry",report,{"Products":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
