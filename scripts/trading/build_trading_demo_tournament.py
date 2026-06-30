#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402
def build():
 rows=[{"rank":i+1,"strategy_id":name,"trades":50,"win_rate":win,"simulated_pl_usd":pl,"max_drawdown_pct":dd,"mode":"synthetic_paper","order_execution":False} for i,(name,win,pl,dd) in enumerate([("readiness_momentum",62.0,5264.19,3.0),("london_breakout_demo",58.0,3180.0,4.2),("mean_reversion_demo",56.0,2410.0,3.7),("trend_filter_demo",54.0,1960.0,5.1),("capital_preservation_demo",52.0,1240.0,2.1)])];write_json(SUPABASE_READY/"trading_demo_tournament_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"synthetic_demo_tournament_complete","strategies":len(rows),"winner":rows[0]["strategy_id"],"orders_placed":False,"live_endpoint_used":False,"external_action_performed":False};write_report("trading_demo_tournament","Trading Demo Tournament",report,{"Standings":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
