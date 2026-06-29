#!/usr/bin/env python3
"""Bounded local Stripe-signature webhook verifier for synthetic/test events only."""
from __future__ import annotations
import argparse,hashlib,hmac,json,os,threading,time,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from stripe_test_execution_common import PRIVATE_DIR,mask,now,write_report
ALLOWED={"checkout.session.completed","payment_intent.succeeded","payment_intent.payment_failed","customer.created"}
SUMMARY=PRIVATE_DIR/"stripe_webhook_event_summary_latest.local.json"
SUMMARY_LOG=PRIVATE_DIR/"stripe_webhook_event_summaries.local.jsonl"
def verify(payload:bytes,header:str,secret:str,tolerance=300):
 parts=dict(x.split("=",1) for x in header.split(",") if "=" in x);stamp=parts.get("t","");sig=parts.get("v1","")
 if not stamp.isdigit() or abs(int(time.time())-int(stamp))>tolerance:return False
 expected=hmac.new(secret.encode(),stamp.encode()+b"."+payload,hashlib.sha256).hexdigest();return hmac.compare_digest(expected,sig)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  if self.path!="/health":self.send_response(404);self.end_headers();return
  self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(b'{"ok":true,"mode":"stripe_test_only"}')
 def do_POST(self):
  if self.path!="/api/stripe/webhook":self.send_response(404);self.end_headers();return
  payload=self.rfile.read(int(self.headers.get("Content-Length","0")));secret=os.environ.get("STRIPE_WEBHOOK_SECRET","");valid=bool(secret) and verify(payload,self.headers.get("Stripe-Signature",""),secret)
  try:event=json.loads(payload)
  except json.JSONDecodeError:event={}
  event_type=event.get("type");obj=(event.get("data") or {}).get("object") or {};test_only=obj.get("livemode") is False
  accepted=valid and test_only and event_type in ALLOWED
  PRIVATE_DIR.mkdir(parents=True,exist_ok=True);summary={"received_at":now(),"signature_valid":valid,"test_mode":test_only,"accepted":accepted,"event_type":event_type,"event_id_masked":mask(event.get("id")),"object_id_masked":mask(obj.get("id"))}
  SUMMARY.write_text(json.dumps(summary,indent=2)+"\n");SUMMARY.chmod(0o600)
  with SUMMARY_LOG.open("a") as f:f.write(json.dumps(summary)+"\n")
  SUMMARY_LOG.chmod(0o600)
  self.send_response(200 if accepted else 400);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(json.dumps({"received":accepted}).encode())
  if getattr(self.server,"once",False):threading.Thread(target=self.server.shutdown,daemon=True).start()
def main():
 p=argparse.ArgumentParser();p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=8787);p.add_argument("--once",action="store_true");p.add_argument("--once-health-check",action="store_true");a=p.parse_args()
 if a.once_health_check:
  server=ThreadingHTTPServer((a.host,a.port),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();ok=False;status=None
  try:
   with urllib.request.urlopen(f"http://{a.host}:{a.port}/health",timeout=3) as response:status=response.status;ok=response.status==200
  finally:server.shutdown();server.server_close();thread.join(timeout=3)
  report={"ok":ok,"generated_at":now(),"status":"health_check_passed" if ok else "health_check_failed","host":a.host,"port":a.port,"http_status":status,"server_stopped":True,"secret_required_for_webhooks":True,"secret_printed":False,"external_action_performed":False};write_report("stripe_webhook_server_health","Stripe Webhook Server Health",report);print(json.dumps(report,indent=2));return
 if not os.environ.get("STRIPE_WEBHOOK_SECRET"):raise SystemExit("STRIPE_WEBHOOK_SECRET is required; value is never printed")
 server=ThreadingHTTPServer((a.host,a.port),Handler);server.once=a.once;server.serve_forever()
if __name__=="__main__":main()
