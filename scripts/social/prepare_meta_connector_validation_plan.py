#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent;sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,env_presence,now,write_json,write_report  # noqa:E402


def build()->dict:
 names=["META_PAGE_ACCESS_TOKEN","META_PAGE_ID","META_APP_ID","META_APP_SECRET","VITE_META_PAGE_ACCESS_TOKEN","VITE_META_PAGE_ID","VITE_META_IG_ACCOUNT_ID"]
 present=env_presence(*names);configured=any(present.values()) and (present["META_PAGE_ID"] or present["VITE_META_PAGE_ID"])
 drafts=[]
 titles=["Know your funding blockers before applying","The $97 Readiness Review explained","Three documents that slow funding readiness","Business profile consistency check","Why readiness comes before applications"]
 for i,title in enumerate(titles,1):drafts.append({"id":f"social-readiness-{i}","tenant_id":"tenant_demo_goclear","client_id":"synthetic_marketing_only","category":"social_draft","title":title,"summary":f"Draft-only educational post: {title}. Request a GoClear $97 Funding Readiness Review to identify next steps; outcomes are not guaranteed.","status":"ready_for_Ray_review","priority":"high","risk_level":"medium","automation_level":"approval_required","client_visible":False,"approval_required":True,"public_content_published":False,"created_at":now()})
 plan={"id":"meta-validation-plan","connector":"Meta Graph API","configured_by_key_presence":configured,"key_presence":present,"raw_values_included":False,"network_validated":False,"safe_validation_request":"GET /me/accounts?fields=id,name (read-only, separately approved; never log token)","sandbox_test_requirements":["Ray selects owned test page/account","confirm token scope and expiry","read-only identity check","approve exact unpublished/test post design","retain publish gate"],"publish_enabled":False,"approval_required":True}
 write_json(SUPABASE_READY/"meta_connector_validation_plan_latest.json",plan);write_json(SUPABASE_READY/"social_readiness_review_drafts_latest.json",drafts)
 report={"ok":True,"generated_at":now(),"status":"connector_config_present_validation_pending" if configured else "connector_missing","key_presence":present,"raw_values_included":False,"network_validated":False,"publish_enabled":False,"drafts_created":len(drafts),"ray_review_required":True,"safe_validation_command":"Use a separately approved read-only Graph API /me/accounts request with token redaction.","external_action_performed":False,"summary":"Prepared Meta read-only validation and five $97 drafts; no network call or post occurred."}
 write_report("meta_connector_validation_plan","Meta Connector Validation Plan",report,{"Plan":plan,"Drafts":drafts});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
