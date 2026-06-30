#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import RUNTIME,now,offers,read_json,write_report
def build():
 rows=offers();checkout=read_json(RUNTIME/"stripe_test_checkout_session_latest.json",{});possible=sum(x.get("price_usd",0) for x in rows if isinstance(x.get("price_usd"),(int,float)));report={"ok":True,"generated_at":now(),"status":"revenue_dashboard_active_internal","confirmed_revenue_usd":0,"pending_test_revenue_usd":97 if "open" in checkout.get("status","") else 0,"possible_offer_value_usd":possible,"blocked_revenue_usd":97,"offer_readiness":{"total":len(rows),"test_ready":1,"draft_or_gated":len(rows)-1},"funnel_readiness":"internal_pipeline_ready_external_conversion_gated","exact_next_money_action":"Approve and manually complete the $97 Stripe test Checkout, then verify synthetic onboarding.","real_charge":False,"external_action_performed":False};write_report("revenue_dashboard","Revenue Dashboard",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
