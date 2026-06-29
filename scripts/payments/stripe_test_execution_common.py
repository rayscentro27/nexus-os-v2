#!/usr/bin/env python3
"""Strict Stripe CLI test-mode execution helpers."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402,F401

PRIVATE_DIR=ROOT/".stripe_test_runtime"
PRIVATE_STATE=PRIVATE_DIR/"stripe_test_objects_latest.local.json"

def cli_env():
 env=dict(os.environ)
 for name in ("STRIPE_API_KEY","STRIPE_SECRET_KEY","STRIPE_TEST_SECRET_KEY"):
  env.pop(name,None)
 return env

def run_cli(args:list[str],timeout=45):
 if "--live" in args: raise RuntimeError("live_mode_forbidden")
 p=subprocess.run(["stripe",*args],cwd=ROOT,env=cli_env(),capture_output=True,text=True,timeout=timeout)
 if p.returncode != 0:return False,{},p.returncode
 try:return True,json.loads(p.stdout),0
 except json.JSONDecodeError:return False,{},p.returncode

def verify_test_mode():
 ok,data,code=run_cli(["balance","retrieve","--confirm"])
 return {"ok":ok and data.get("livemode") is False,"livemode":data.get("livemode") if ok else None,"exit_code":code,"read_only_request_performed":True,"live_mode_requested":False}

def mask(value:str):
 value=str(value or "")
 return f"{value[:4]}***{value[-4:]}" if len(value)>10 else "***"

def fingerprint(value:str):return hashlib.sha256(str(value).encode()).hexdigest()[:12] if value else ""

def load_private():return read_json(PRIVATE_STATE,{})
def save_private(key:str,value:dict):
 PRIVATE_DIR.mkdir(parents=True,exist_ok=True);state=load_private();state[key]=value
 PRIVATE_STATE.write_text(json.dumps(state,indent=2)+"\n");PRIVATE_STATE.chmod(0o600)

def metadata_args():
 values={"test_mode":"true","package":"readiness_review_97","client_name":"Julius Erving","client_email":"ray@goclearonline.com","business_name":"Doctor J LLC","state":"AZ","do_not_contact":"true","dry_run_onboarding":"true"}
 return [item for k,v in values.items() for item in ("-d",f"metadata[{k}]={v}")]
