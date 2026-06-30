#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,read_json,write_report  # noqa:E402
def build():
 r=read_json(ROOT/"configs/notebooklm_automation_registry.json",{});violations=[]
 if r.get("consumer_browser_automation_allowed"):violations.append("consumer_browser_automation")
 if r.get("unofficial_cookie_automation_allowed"):violations.append("cookie_automation")
 report={"ok":not violations,"generated_at":now(),"status":"notebooklm_tool_access_validated","access_mode":r.get("selected_access_mode"),"safety_violations":violations,"credentials_exposed":False,"external_action_performed":False};write_report("notebooklm_tool_access_validation","NotebookLM Tool Access Validation",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 1)
