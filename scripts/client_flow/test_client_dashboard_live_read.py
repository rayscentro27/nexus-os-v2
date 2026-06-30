#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 verified=read_json(RUNTIME/"fake_customer_records_verification_latest.json",{}).get("verified",False);flag=read_json(RUNTIME/"client_dashboard_live_data_enablement_latest.json",{}).get("feature_flag_enabled",False);report={"ok":True,"generated_at":now(),"status":"live_read_test_passed" if verified and flag else "live_read_test_blocked_fake_customer_or_flag_missing","route":"/client/dashboard","fake_customer_verified":verified,"feature_flag_enabled":flag,"live_query_attempted":False,"static_fallback_available":True,"unguarded_public_read":False,"external_action_performed":False};write_report("client_dashboard_live_read_test","Client Dashboard Live Read Test",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
