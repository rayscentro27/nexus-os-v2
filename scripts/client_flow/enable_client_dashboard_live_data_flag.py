#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build(test_customer_only=False):
 verification=read_json(RUNTIME/"fake_customer_records_verification_latest.json",{});enabled=False;status="live_data_flag_ready_not_enabled_fake_customer_missing"
 if verification.get("verified") and test_customer_only:status="live_data_flag_approval_required_after_verification"
 report={"ok":True,"generated_at":now(),"status":status,"test_customer_only":test_customer_only,"fake_customer_verified":verification.get("verified",False),"feature_flag":"VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT","feature_flag_enabled":enabled,"static_fallback_preserved":True,"service_role_frontend":False,"env_file_modified":False,"approval_required":True,"external_action_performed":False};write_report("client_dashboard_live_data_enablement","Client Dashboard Live Data Enablement",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--test-customer-only",action="store_true");a=p.parse_args();r=build(a.test_customer_only);print(json.dumps(r,indent=2) if a.json else r)
