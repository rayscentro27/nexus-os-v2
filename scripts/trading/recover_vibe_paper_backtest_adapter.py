#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 legacy=[p for p in [Path.home()/"nexuslive/nexus-strategy-lab/backtest/engine.py",Path.home()/"nexuslive/nexus-strategy-lab/trading/paper_trade_executor.py",ROOT/"scripts/trading/vibe_trading_adapter.py"] if p.exists()];cards=read_json(SUPABASE_READY/"trading_approval_cards_latest.json",[]);cards.append({"id":"approve-vibe-paper-adapter","title":"Approve Vibe/paper backtest adapter test","status":"pending_Ray_review","approval_required":True,"paper_only":True,"live_trading_allowed":False,"external_action_performed":False,"created_at":now()});write_json(SUPABASE_READY/"trading_approval_cards_latest.json",cards)
 report={"ok":bool(legacy),"generated_at":now(),"status":"paper_backtest_adapter_recovery_ready","legacy_components":[str(x) for x in legacy],"vibe_cli_required":False,"vibe_cli_executed":False,"backtest_executed":False,"paper_order_placed":False,"live_order_placed":False,"adapter_boundary":["JSON signal input","bounded historical backtest","report-only output","no broker credentials"],"external_action_performed":False};write_report("vibe_paper_backtest_recovery","Vibe / Paper Backtest Recovery",report,{"Components":report["legacy_components"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
