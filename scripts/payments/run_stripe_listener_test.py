#!/usr/bin/env python3
"""Bounded Stripe CLI test listener and trigger proof; never uses --live."""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time,urllib.request
from stripe_test_execution_common import PRIVATE_DIR,ROOT,cli_env,now,verify_test_mode,write_report
EVENTS=["checkout.session.completed","payment_intent.succeeded","payment_intent.payment_failed"]
def build(bounded=False):
 gate=verify_test_mode();results=[];received=[];listener_started=False;server_started=False;secret_ok=False
 if not gate["ok"]:
  report={"ok":False,"generated_at":now(),"status":"blocked_test_mode_not_verified","listener_started":False,"external_action_performed":False};write_report("stripe_listener_test","Stripe Listener Test",report);return report
 secret_run=subprocess.run(["stripe","listen","--print-secret"],cwd=ROOT,env=cli_env(),capture_output=True,text=True,timeout=30);secret=(secret_run.stdout or "").strip();secret_ok=secret.startswith("whsec_")
 if not secret_ok:
  report={"ok":False,"generated_at":now(),"status":"blocked_listener_secret_unavailable","listener_started":False,"secret_printed":False,"external_action_performed":False};write_report("stripe_listener_test","Stripe Listener Test",report);return report
 log=PRIVATE_DIR/"stripe_webhook_event_summaries.local.jsonl";PRIVATE_DIR.mkdir(parents=True,exist_ok=True);log.unlink(missing_ok=True)
 env=cli_env();env["STRIPE_WEBHOOK_SECRET"]=secret
 server=subprocess.Popen([sys.executable,str(ROOT/"scripts/payments/stripe_webhook_test_server.py")],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);server_started=True
 listener=None
 try:
  for _ in range(20):
   try:
    with urllib.request.urlopen("http://127.0.0.1:8787/health",timeout=1) as r:
     if r.status==200:break
   except Exception:time.sleep(.2)
  listener=subprocess.Popen(["stripe","listen","--events",",".join(EVENTS),"--forward-to","localhost:8787/api/stripe/webhook","--format","JSON"],cwd=ROOT,env=cli_env(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);listener_started=True;time.sleep(2)
  for event in EVENTS:
   p=subprocess.run(["stripe","trigger",event],cwd=ROOT,env=cli_env(),capture_output=True,text=True,timeout=90);results.append({"event_type":event,"trigger_succeeded":p.returncode==0,"exit_code":p.returncode})
  time.sleep(4)
  if log.exists():
   for line in log.read_text(errors="ignore").splitlines():
    try:
     item=json.loads(line)
     if item.get("accepted"):received.append(item.get("event_type"))
    except json.JSONDecodeError:pass
 finally:
  if listener and listener.poll() is None:listener.terminate();
  if listener:
   try:listener.wait(timeout=5)
   except subprocess.TimeoutExpired:listener.kill();listener.wait(timeout=3)
  if server.poll() is None:server.terminate()
  try:server.wait(timeout=5)
  except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
 report={"ok":all(x["trigger_succeeded"] for x in results) and all(x in received for x in EVENTS),"generated_at":now(),"status":"bounded_test_listener_and_triggers_passed" if all(x in received for x in EVENTS) else "bounded_listener_partial_or_failed","bounded":bounded,"test_mode_verified":True,"listener_started":listener_started,"server_started":server_started,"signing_secret_available":secret_ok,"signing_secret_printed":False,"trigger_results":results,"accepted_event_types":sorted(set(received)),"events_received_count":len(received),"listener_stopped":True,"server_stopped":True,"live_mode_used":False,"real_charge_made":False,"external_action_performed":True}
 write_report("stripe_listener_test","Stripe Listener Test",report,{"Trigger results":results,"Accepted event types":sorted(set(received))});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--bounded",action="store_true");a=p.parse_args();r=build(a.bounded);print(json.dumps(r,indent=2) if a.json else r);raise SystemExit(0 if r["ok"] else 2)
