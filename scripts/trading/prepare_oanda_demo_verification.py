#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 audit=read_json(RUNTIME/"oanda_vibe_trading_audit_latest.json",{});practice=audit.get("oanda_mode")=="practice";card={"id":"approve-oanda-demo-check","title":"Approve Oanda demo connection check with no orders","status":"pending_Ray_review","approval_required":True,"paper_only":True,"orders_allowed":False,"external_action_performed":False,"created_at":now()}
 report={"ok":True,"generated_at":now(),"status":"practice_config_ready_for_readonly_check" if practice else "blocked_explicit_practice_environment_missing","practice_environment_verified":practice,"readonly_account_check_performed":False,"orders_placed":False,"live_endpoint_called":False,"required_before_check":["OANDA_ENVIRONMENT=practice or practice API URL","demo account ID","Ray approval"],"external_action_performed":False}
 write_json(SUPABASE_READY/"trading_approval_cards_latest.json",[card]);write_report("oanda_demo_verification_plan","Oanda Demo Verification Plan",report,{"Approval":card});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
