#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent;sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402


def build()->dict:
 lifecycle=[{"id":f"dispute-stage-{i+1}","tenant_id":"tenant_demo_goclear","client_id":"synthetic_only","category":"dispute_approval","title":title,"status":status,"client_visible":client,"approval_required":approval,"external_action_performed":False,"created_at":now()} for i,(title,status,client,approval) in enumerate([
  ("Synthetic intake","internal_active",True,False),("Document dependency check","internal_active",True,False),("Draft letter preview","ready_for_Ray_review",True,True),("GoClear compliance review","approval_gated",False,True),("Client approval where required","approval_gated",True,True),("Sandbox connector proof","blocked",False,True),("Real send","blocked",False,True),("Proof/event tracking","internal_active",True,False)])]
 connectors=[{"id":"certified-mail-sandbox","mode":"sandbox_proposed","requirements":["vendor sandbox account","sandbox credential stored server-side","non-deliverable synthetic recipient","Ray approval","proof-only request","legal/compliance review"],"live_enabled":False,"approval_required":True},{"id":"internal-email-review","mode":"local_preview","requirements":["rendered preview","Ray/GoClear review","no SMTP recipient","no send call"],"live_enabled":False,"approval_required":True}]
 write_json(SUPABASE_READY/"dispute_approval_lifecycle_latest.json",lifecycle);write_json(SUPABASE_READY/"dispute_sandbox_connector_plan_latest.json",connectors)
 report={"ok":True,"generated_at":now(),"status":"sandbox_plan_ready","certified_mail_sandbox_requirements":connectors[0]["requirements"],"email_only_internal_review_requirements":connectors[1]["requirements"],"ray_approvals_before_real_send":["case evidence","letter content","recipient","channel/vendor","compliance confirmation","explicit external action"],"must_stay_blocked":["production bureau/creditor/collector contact","real certified mail","automatic dispute submission","unsupervised client claims","real PII in test records"],"real_disputes_sent":False,"external_action_performed":False,"summary":"The next layer is defined for synthetic sandbox proof; every real-send path remains disabled."}
 write_report("dispute_sandbox_upgrade_plan","Dispute Sandbox Upgrade Plan",report,{"Approval lifecycle":lifecycle,"Connector plans":connectors});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
