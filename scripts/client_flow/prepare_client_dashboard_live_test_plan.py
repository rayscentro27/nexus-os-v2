#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,write_report  # noqa:E402
def build():
 report={"ok":True,"generated_at":now(),"status":"live_dashboard_test_plan_ready_flag_off","route":"/client/dashboard","feature_flag":"VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT","enabled":False,"fallback_static_demo_data":True,"service_role_frontend":False,"requires_fake_customer_insert":True,"approval_required":True,"local_enable_command":"printf '\\nVITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true\\n' >> .env.local","production_enable_command":"netlify env:set VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT true","test_steps":["Insert approved synthetic customer","Verify authenticated tenant membership","Enable flag","Build and preview /client/dashboard","Confirm live records and fallback behavior"],"external_action_performed":False};write_report("client_dashboard_live_test_plan","Client Dashboard Live Test Plan",report);write_report("frontend_live_data_final_readiness","Frontend Live Data Final Readiness",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
