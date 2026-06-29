#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,write_json,write_report  # noqa:E402
def build():
 files=["src/data/clientDataMode.js","src/services/clientDashboardLiveData.ts","src/pages/client/ClientPortalPages.jsx"];present={x:(ROOT/x).exists() for x in files};cards=[{"id":"approve-client-dashboard-live-test-read","title":"Approve /client/dashboard live Supabase read for fake customer","status":"pending_Ray_review","approval_required":True,"feature_flag":"VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT","default_enabled":False,"external_action_performed":False,"created_at":now()}];write_json(SUPABASE_READY/"frontend_live_data_approval_cards_latest.json",cards)
 report={"ok":all(present.values()),"generated_at":now(),"status":"live_read_path_implemented_flag_off","files":present,"route":"/client/dashboard","feature_flag":"VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT","feature_flag_default":False,"authenticated_supabase_client_only":True,"service_role_frontend":False,"static_fallback_preserved":True,"test_plan":["Insert approved synthetic test rows","Create tenant_memberships row for authenticated test user","Run SQL Editor RLS verification","Set feature flag in local/preview environment","Authenticate and verify only the fake customer is visible","Unset flag to roll back"],"external_action_performed":False};write_report("client_dashboard_live_data_flag","Client Dashboard Live-Data Flag",report,{"Test plan":report["test_plan"],"Approval":cards});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
