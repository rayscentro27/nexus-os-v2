#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,ssl,sys,urllib.error,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,now,parse_env,write_report  # noqa:E402
def build():
 values=dict(os.environ)
 for p in (ROOT/".env",ROOT/".env.local",ROOT/".env.nexus.recovered.local"):values.update(parse_env(p))
 key=values.get("RESEND_API_KEY","");sender=values.get("RESEND_FROM_EMAIL") or values.get("RESEND_FROM") or values.get("EMAIL_FROM") or "";domains=[];error=None;http_status=None;checked=False
 if key:
  try:
   import certifi
   ctx=ssl.create_default_context(cafile=certifi.where());req=urllib.request.Request("https://api.resend.com/domains",headers={"Authorization":f"Bearer {key}"})
   with urllib.request.urlopen(req,timeout=20,context=ctx) as response:http_status=response.status;data=json.loads(response.read());checked=True;domains=[{"name":x.get("name"),"status":x.get("status")} for x in data.get("data",[]) if isinstance(x,dict)]
  except urllib.error.HTTPError as exc:error="HTTPError";http_status=exc.code
  except Exception as exc:error=exc.__class__.__name__
 sender_email=sender.split("<",1)[-1].split(">",1)[0].strip() if "<" in sender else sender.strip();sender_domain=sender_email.rsplit("@",1)[-1] if "@" in sender_email else "";verified={x["name"] for x in domains if x.get("status")=="verified"};report={"ok":bool(key) and checked,"generated_at":now(),"status":"resend_readonly_verified" if checked else "resend_key_missing" if not key else "resend_verification_failed","api_key_present":bool(key),"raw_key_included":False,"readonly_api_check_performed":checked,"http_status":http_status,"domain_records":domains,"verified_domain_count":len(verified),"sender_configured":bool(sender),"sender_domain":sender_domain or None,"sender_domain_verified":sender_domain in verified if sender_domain else False,"email_sent":False,"error_sanitized":error,"external_action_performed":False}
 write_report("resend_connection_audit","Resend Connection Audit",report,{"Domains":domains});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
