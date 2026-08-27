#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from datetime import datetime, timezone
import hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
def build():
 recs=["Keep Oanda reads scheduled against the practice host only.","Use the synthetic tournament for strategy research, not performance claims.","Recurring demo orders require a new Ray approval.","Live/funded execution remains blocked."]
 generated = now()
 provenance = {"source":"local Oanda practice/research configuration and synthetic tournament inputs","timestamp":generated,"instruments":["EUR_USD"],"timeframes":["research fixture / bounded daily context"],"data_freshness":"FRESH_AT_RUN","network_market_data_requested":False}
 analysis = {"market_state":"research-only bounded snapshot; live market state not asserted","strategy_research":"compare practice/synthetic outcomes before any demo-order proposal","historical_backtest":"not run in this bounded brief; no performance claim made","risk_commentary":"spread, slippage, approval, and live/funded authority remain explicit risk gates"}
 report={"ok":True,"generated_at":generated,"status":"trading_hermes_brief_ready","admin_only":True,"input_provenance":provenance,"research_analysis":analysis,"research_hash":hashlib.sha256(json.dumps({"provenance":provenance,"analysis":analysis},sort_keys=True).encode()).hexdigest(),"recommendations_count":len(recs),"recommendations":recs,"external_action_performed":False,"funded_live_trading":"PROHIBITED"};write_report("trading_hermes_brief","Trading Hermes Brief",report,{"Input provenance":provenance,"Research analysis":analysis,"Recommendations":recs});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
