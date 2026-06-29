#!/usr/bin/env python3
"""Prove the local webhook signature path with an ephemeral synthetic fixture."""
from __future__ import annotations
import argparse,hashlib,hmac,json,os,secrets,subprocess,sys,time,urllib.request
from stripe_test_execution_common import PRIVATE_DIR,PRIVATE_STATE,ROOT,now,read_json,write_report
def build():
 secret="fixture_"+secrets.token_hex(24);env=dict(os.environ);env["STRIPE_WEBHOOK_SECRET"]=secret
 server=subprocess.Popen([sys.executable,str(ROOT/"scripts/payments/stripe_webhook_test_server.py"),"--once"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 event={"id":"evt_test_nexus_fixture","type":"checkout.session.completed","data":{"object":{"id":"cs_test_nexus_fixture","livemode":False,"payment_status":"paid","metadata":{"test_mode":"true","dry_run_onboarding":"true"}}}}
 payload=json.dumps(event,separators=(",",":")).encode();stamp=str(int(time.time()));sig=hmac.new(secret.encode(),stamp.encode()+b"."+payload,hashlib.sha256).hexdigest();received=False;status=None
 try:
  time.sleep(.5);req=urllib.request.Request("http://127.0.0.1:8787/api/stripe/webhook",data=payload,headers={"Content-Type":"application/json","Stripe-Signature":f"t={stamp},v1={sig}"},method="POST")
  with urllib.request.urlopen(req,timeout=5) as response:status=response.status;received=response.status==200
 except Exception:received=False
 finally:
  try:server.wait(timeout=3)
  except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=3)
 summary=read_json(PRIVATE_DIR/"stripe_webhook_event_summary_latest.local.json",{})
 report={"ok":received and summary.get("signature_valid") is True,"generated_at":now(),"status":"local_signed_fixture_received" if received else "local_fixture_failed","fixture_attempted":True,"stripe_cli_trigger_attempted":False,"signature_verified":summary.get("signature_valid",False),"test_mode_verified":summary.get("test_mode",False),"event_received":received,"http_status":status,"listener_shutdown":server.poll() is not None,"webhook_secret_printed":False,"raw_payload_committed":False,"real_charge_created":False,"external_network_action":False}
 write_report("stripe_webhook_endpoint","Stripe Webhook Endpoint",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 2)
