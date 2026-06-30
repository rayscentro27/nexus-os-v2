#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402
def build():
 rows=[{"id":"approve-recurring-oanda-demo-strategy","title":"Approve recurring Oanda demo strategy execution","status":"pending_Ray_review","approval_required":True,"live_trading_allowed":False,"external_action_performed":False,"created_at":now()},{"id":"approve-trading-education-offer-review","title":"Approve compliance review for trading education/demo research offer","status":"pending_Ray_review","approval_required":True,"live_trading_allowed":False,"external_action_performed":False,"created_at":now()}];write_json(SUPABASE_READY/"trading_operating_approval_cards_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"trading_review_cards_ready","cards_created":len(rows),"external_action_performed":False};write_report("trading_ray_review_cards","Trading Ray Review Cards",report,{"Cards":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
