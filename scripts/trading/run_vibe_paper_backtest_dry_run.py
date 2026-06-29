#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,os,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
ENGINE=Path.home()/"nexuslive/nexus-strategy-lab/backtest/engine.py"
def build():
 summary={};error=None
 if ENGINE.exists():
  try:
   os.environ["NEXUS_DRY_RUN"]="true";random.seed(20260629);spec=importlib.util.spec_from_file_location("nexus_legacy_backtest",ENGINE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);summary=module.quick_test("nexus_vibe_recovery_fixture")
  except Exception as exc:error=exc.__class__.__name__
 report={"ok":bool(summary),"generated_at":now(),"status":"synthetic_paper_backtest_passed" if summary else "paper_backtest_failed","engine_path":str(ENGINE),"dry_run":True,"synthetic_only":True,"summary":summary,"error_sanitized":error,"broker_credentials_used":False,"oanda_api_called":False,"paper_order_placed":False,"live_order_placed":False,"external_action_performed":False};write_report("vibe_paper_backtest_dry_run","Vibe / Paper Backtest Dry Run",report,{"Backtest summary":summary});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
