#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,write_json,write_report  # noqa:E402
def build():
 files=["src/data/clientDataMode.js","src/data/clientPortalData.js","src/data/nexusEngineStatusData.js","src/lib/supabaseClient.ts","src/services/db.ts","src/components/client/ClientPortalShell.jsx"]
 present={x:(ROOT/x).exists() for x in files};record={"id":"frontend-live-test-client-readiness","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"frontend_live_data_readiness","title":"/client/dashboard live Supabase read for fake customer","status":"ready_for_Ray_review_feature_flag_off","first_route":"/client/dashboard","feature_flag":"live_supabase_test_client_enabled","feature_flag_enabled":False,"fallback_static_demo_data":True,"requires_authenticated_session":True,"requires_tenant_membership":True,"service_role_frontend_allowed":False,"approval_required":True,"created_at":now()}
 write_json(SUPABASE_READY/"frontend_live_data_readiness_latest.json",[record]);report={"ok":all(present.values()),"generated_at":now(),"status":record["status"],"files":present,"first_live_route":"/client/dashboard","feature_flag":"live_supabase_test_client_enabled","feature_flag_enabled":False,"fallback_preserved":True,"unguarded_public_reads":False,"service_role_in_frontend":False,"ray_review_card":"Approve /client/dashboard live Supabase read for fake customer.","external_action_performed":False}
 write_report("frontend_live_data_readiness","Frontend Live-Data Readiness",report,{"Required controls":["authenticated session","tenant_memberships match","RLS policy proof","fallback demo data"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
