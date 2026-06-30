#!/usr/bin/env python3
"""Detect Oanda demo and Vibe Trading safely; never contacts a broker or places orders."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,parse_env,write_json,write_report  # noqa:E402

def envs():
 values={}
 for p in (ROOT/".env",ROOT/".env.local",ROOT/".env.nexus.recovered.local",Path.home()/"nexuslive/.env"):
  values.update(parse_env(p))
 names=["OANDA_API_KEY","OANDA_ACCESS_TOKEN","OANDA_ACCOUNT_ID","OANDA_ENVIRONMENT","OANDA_API_URL","OANDA_LIVE_ACCOUNT_ID","LIVE_TRADING","TRADING_LIVE"]
 present={x:bool(values.get(x)) for x in names};present["LIVE_TRADING"]=values.get("LIVE_TRADING","").strip().lower() in {"1","true","yes","enabled","live"};present["TRADING_LIVE"]=values.get("TRADING_LIVE","").strip().lower() in {"1","true","yes","enabled","live"};mode=(values.get("OANDA_ENVIRONMENT") or values.get("OANDA_API_URL") or "").lower()
 return present, ("practice" if any(x in mode for x in ("practice","demo")) else "live_detected_blocked" if "fxtrade" in mode or mode == "live" else "practice_candidate" if (present["OANDA_API_KEY"] or present["OANDA_ACCESS_TOKEN"]) and present["OANDA_ACCOUNT_ID"] else "unverified")

def build():
 present,mode=envs();cli=shutil.which("vibe-trading");version=""
 if cli:
  p=subprocess.run([cli,"--version"],capture_output=True,text=True,timeout=10);version=((p.stdout or p.stderr).strip().splitlines() or [""])[0]
 paths=[p for p in [Path.home()/"vibe-trading-ai",Path.home()/"vibe-trading",Path.home()/"nexuslive/trading-engine",Path.home()/"nexuslive/nexus-strategy-lab"] if p.exists()]
 backtests=[str(p) for p in [Path.home()/"nexuslive/nexus-strategy-lab/backtest/engine.py",ROOT/"scripts/trading/import_backtest_report.py"] if p.exists()]
 demo_ready=mode in {"practice","practice_candidate"} and (present["OANDA_API_KEY"] or present["OANDA_ACCESS_TOKEN"]) and present["OANDA_ACCOUNT_ID"]
 status="oanda_demo_credentials_ready_for_practice_probe" if demo_ready else "oanda_live_endpoint_detected_blocked" if mode=="live_detected_blocked" else "oanda_config_unverified_or_incomplete"
 record={"id":"oanda-vibe-status","tenant_id":"tenant_demo_goclear","client_id":"not_applicable","category":"trading_connector_status","title":"Oanda demo and Vibe Trading","status":status,"oanda_key_presence":present,"oanda_mode":mode,"vibe_cli_installed":bool(cli),"vibe_cli_path":cli,"vibe_version":version,"legacy_paths":[str(x) for x in paths],"backtest_runners":backtests,"integration_status":"legacy_paper_backtest_components_detected_vibe_cli_missing" if not cli and paths else "detected_not_executed","approval_required":True,"paper_only":True,"live_trading_blocked":True,"trade_placed":False,"broker_api_called":False,"external_action_performed":False,"created_at":now()}
 write_json(SUPABASE_READY/"oanda_vibe_trading_status_latest.json",[record]);report={"ok":True,"generated_at":now(),**{k:v for k,v in record.items() if k not in {"id","tenant_id","client_id","category","title","created_at"}},"ray_review_card":"Approve Oanda demo + Vibe Trading paper/backtest integration test."}
 write_report("oanda_vibe_trading_audit","Oanda Demo and Vibe Trading Audit",report,{"Detected paths":record["legacy_paths"],"Backtests":backtests});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
