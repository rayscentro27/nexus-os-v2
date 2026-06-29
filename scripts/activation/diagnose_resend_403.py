#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 audit=read_json(RUNTIME/"resend_connection_audit_latest.json",{});status=audit.get("http_status");sender=audit.get("sender_domain");causes=[]
 if status==403:causes.append("API key is accepted by the endpoint but lacks domain-list permission, is restricted, revoked, or belongs to a different Resend account/project.")
 if sender and sender!="goclearonline.com":causes.append(f"Configured sender domain is {sender}, which does not match the intended goclearonline.com domain.")
 if not audit.get("sender_domain_verified"):causes.append("Sender-domain verification cannot be proven with the current key/configuration.")
 report={"ok":True,"generated_at":now(),"status":"resend_403_diagnosed_configuration_and_permission_blocker" if status==403 else "resend_non_403_state","api_key_present":audit.get("api_key_present",False),"http_status":status,"provider_error_category":audit.get("error_sanitized"),"likely_causes":causes,"classified_as":["api_key_permission_or_account_scope","from_domain_mismatch" if sender!="goclearonline.com" else "domain_verification_unproven"],"local_code_bug_likely":False,"email_sent":False,"raw_key_included":False,"external_action_performed":False}
 write_report("resend_403_diagnosis","Resend 403 Diagnosis",report,{"Likely causes":causes});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
