#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
def build():
 recs=["Keep Oanda reads scheduled against the practice host only.","Use the synthetic tournament for strategy research, not performance claims.","Recurring demo orders require a new Ray approval.","Live/funded execution remains blocked."]
 report={"ok":True,"generated_at":now(),"status":"trading_hermes_brief_ready","admin_only":True,"recommendations_count":len(recs),"recommendations":recs,"external_action_performed":False};write_report("trading_hermes_brief","Trading Hermes Brief",report,{"Recommendations":recs});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
