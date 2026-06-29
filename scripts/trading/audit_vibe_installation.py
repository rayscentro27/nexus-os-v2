#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,write_report  # noqa:E402
def build():
 cli=shutil.which("vibe-trading");module=subprocess.run([sys.executable,"-m","vibe_trading","--version"],capture_output=True,text=True,timeout=10);legacy=[p for p in [Path.home()/"nexuslive/nexus-strategy-lab/backtest/engine.py",Path.home()/"nexuslive/nexus-strategy-lab/trading/paper_trade_executor.py",ROOT/"scripts/trading/vibe_trading_adapter.py"] if p.exists()]
 plan=["Do not install Vibe until the exact trusted package/repository and license are approved.","Use the recovered legacy Nexus synthetic backtest now; it has no broker dependency.","If Vibe is later approved, install into an isolated virtual environment and run version/help before adapter tests."]
 report={"ok":True,"generated_at":now(),"status":"vibe_cli_missing_legacy_backtest_available" if not cli else "vibe_cli_detected","cli_installed":bool(cli),"cli_path":cli,"python_module_installed":module.returncode==0,"legacy_components":[str(x) for x in legacy],"install_plan":plan,"package_installed_this_run":False,"external_action_performed":False};write_report("vibe_installation_audit","Vibe Installation Audit",report,{"Install/recovery plan":plan,"Legacy components":report["legacy_components"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
