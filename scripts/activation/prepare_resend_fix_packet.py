#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402
def build():
 steps=["In Resend dashboard confirm the API key belongs to the intended account and has Full access or domain-read permission.","Verify goclearonline.com in Resend Domains.","Correct the local sender to GoClear <onboarding@goclearonline.com>; current configuration points at a different TLD.","Rerun python3 scripts/activation/audit_resend_connection.py --json.","Only after HTTP 200/domain verified, approve one test email to Ray."]
 cards=[{"id":"approve-resend-fix-test","title":"Approve Resend fix and test email after 403 diagnosis","status":"blocked_until_403_resolved","approval_required":True,"email_sent":False,"external_action_performed":False,"created_at":now()}];write_json(SUPABASE_READY/"resend_email_approval_cards_latest.json",cards)
 report={"ok":True,"generated_at":now(),"status":"resend_fix_packet_ready","exact_fix_steps":steps,"test_email_approved":False,"email_sent":False,"approval_cards_created":1,"raw_key_included":False,"external_action_performed":False};write_report("resend_fix_packet","Resend Fix Packet",report,{"Fix steps":steps,"Approval":cards});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
