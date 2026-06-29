#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,socket,urllib.error,urllib.request
from pathlib import Path
from stripe_test_execution_common import ROOT,SUPABASE_READY,now,write_json,write_report
ENDPOINT="http://127.0.0.1:3000/api/stripe/webhook"
def build():
 source_matches=[]
 for base in (ROOT/"src",ROOT/"scripts",ROOT/"supabase"):
  if not base.exists():continue
  for p in base.rglob("*"):
   if p.is_file() and p.suffix.lower() in {".py",".js",".jsx",".ts",".tsx"}:
    if p.resolve()==Path(__file__).resolve():continue
    try:
     if "/api/stripe/webhook" in p.read_text(errors="ignore") or "stripe-webhook" in p.name:source_matches.append(str(p.relative_to(ROOT)))
    except OSError:pass
 port_open=False
 try:
  with socket.create_connection(("127.0.0.1",3000),timeout=2):port_open=True
 except OSError:pass
 status=None;content_type=""
 if port_open:
  try:
   r=urllib.request.urlopen(ENDPOINT,timeout=5);status=r.status;content_type=r.headers.get("Content-Type","")
  except urllib.error.HTTPError as exc:status=exc.code;content_type=exc.headers.get("Content-Type","")
  except OSError:pass
 endpoint_exists=bool(source_matches) and status not in {None,404}
 listener="stripe listen --forward-to localhost:3000/api/stripe/webhook"
 triggers=["stripe trigger checkout.session.completed","stripe trigger payment_intent.succeeded"]
 public={"id":"stripe-webhook-test-status","tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"stripe_webhook_test_status","title":"Stripe local webhook test","status":"endpoint_missing_implementation_required" if not endpoint_exists else "endpoint_ready_for_test_listener","test_mode":True,"endpoint":ENDPOINT,"port_3000_open":port_open,"endpoint_http_status":status,"listener_started":False,"trigger_attempted":False,"event_received":False,"approval_required":True,"external_action_performed":False,"created_at":now()}
 write_json(SUPABASE_READY/"stripe_webhook_test_status_latest.json",[public])
 report={"ok":True,"generated_at":now(),"status":public["status"],"local_endpoint_exists":endpoint_exists,"source_matches":source_matches,"port_3000_open":port_open,"endpoint_http_status":status,"endpoint_content_type":content_type.split(";",1)[0],"listener_ready":endpoint_exists,"listener_started":False,"trigger_attempted":False,"event_received":False,"listener_command":listener,"test_trigger_commands":triggers,"webhook_secret_printed":False,"real_charge_created":False,"external_action_performed":False,"next_required_action":"Implement and approve a local signature-verifying webhook endpoint before starting the listener or triggers." if not endpoint_exists else "Approve starting the test listener and synthetic triggers."}
 write_report("stripe_webhook_test_execution_plan","Stripe Webhook Test Execution Plan",report,{"Commands prepared, not executed":[listener,*triggers]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
