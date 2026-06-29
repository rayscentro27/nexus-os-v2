#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402
def build():
 draft={"id":"email-draft-julius-test-onboarding","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"onboarding_email_draft","to":"ray@goclearonline.com","subject":"TEST: Your GoClear $97 Readiness Review onboarding","body":"Hi Julius,\n\nThis is a test onboarding draft for the GoClear/Apex $97 Credit & Funding Readiness Review. Your next step would be to complete the readiness intake and review the document checklist in the client portal. No funding application, credit dispute, or external contact has occurred.\n\nGoClear Review Team","status":"draft_only_not_sent","test_mode":True,"do_not_contact":True,"approval_required":True,"email_sent":False,"created_at":now()}
 cards=[{"id":"approve-resend-test-email","title":"Approve Resend test email to Ray","status":"pending_Ray_review","approval_required":True,"test_mode":True,"external_action_performed":False,"created_at":now()},{"id":"approve-test-onboarding-email","title":"Approve onboarding email draft for Julius Erving test customer","status":"pending_Ray_review","approval_required":True,"test_mode":True,"external_action_performed":False,"created_at":now()}]
 write_json(SUPABASE_READY/"resend_email_approval_cards_latest.json",cards);report={"ok":True,"generated_at":now(),"status":"onboarding_email_draft_ready_not_sent","draft":draft,"approval_cards_created":len(cards),"email_sent":False,"sms_sent":False,"external_action_performed":False};write_report("onboarding_email_draft","Onboarding Email Draft",report,{"Draft body":draft["body"],"Approvals":cards});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
