#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import SUPABASE_READY,now,write_json,write_report
def build():
 audiences=["past readiness inquiry","abandoned $97 test journey","business-credit checklist lead","funding-readiness prospect","inactive membership prospect"];rows=[{"id":f"reactivation-draft-{i+1}","audience":x,"offer":"readiness_review_97","purpose":"Invite the prospect to request a current readiness review","cta":"Reply or book only after Ray approves this draft and recipient selection.","status":"draft_only_not_sent","risk_level":"medium","approval_required":True,"source_reason":"Revenue recovery funnel","created_at":now()} for i,x in enumerate(audiences)];write_json(SUPABASE_READY/"lead_reactivation_drafts_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"lead_reactivation_drafts_ready","draft_count":len(rows),"sent_count":0,"external_action_performed":False};write_report("lead_reactivation_drafts","Lead Reactivation Drafts",report,{"Drafts":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
