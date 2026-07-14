#!/usr/bin/env python3
"""Bounded credit-strategy source intake. Unapproved source content never reaches Clyde."""
from __future__ import annotations
import argparse, hashlib, json, os, ssl, sys, urllib.request
from pathlib import Path
import certifi
ROOT=Path(__file__).resolve().parents[2]
PROMOTIONAL=("four days","87%","dispute everything","always required","automatic deletion","$1,000","must delete","guaranteed")
def env():
    out=dict(os.environ)
    for p in (ROOT/".env.local",ROOT/".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k,v=line.split("=",1);out.setdefault(k.strip(),v.strip().strip("\"'"))
    return out
def request(method,url,key,path,body=None):
    req=urllib.request.Request(f"{url.rstrip('/')}/rest/v1/{path}",method=method,headers={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=representation"},data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req,context=ssl.create_default_context(cafile=certifi.where()),timeout=30) as r:return json.loads(r.read() or b"[]")
def classify(data):
    leads=[{"summarized_claim":x,"strategy_category":x.replace(" ","_"),"evidence_type":"practitioner_discovery","official_support_status":"needs_verification","risk_score":45,"promotional_language":False,"disposition":"practitioner","review_notes":"Useful discovery lead; official verification required before approval."} for x in data.get("strategy_leads",[])]
    rejected=[{"summarized_claim":x,"strategy_category":"promotional_claim","evidence_type":"promotional","official_support_status":"unsupported","risk_score":95,"promotional_language":True,"disposition":"rejected","review_notes":"Rejected: unsupported outcome, timing, legal, or blanket-dispute claim."} for x in data.get("promotional_claims",[]) if any(p.lower() in x.lower() for p in PROMOTIONAL)]
    return leads+rejected
def main():
    p=argparse.ArgumentParser();p.add_argument("--source-type",required=True);p.add_argument("--input-file",type=Path,required=True);p.add_argument("--title",required=True);p.add_argument("--creator",default="");p.add_argument("--category",default="credit_strategy");p.add_argument("--dry-run",action="store_true");a=p.parse_args(); raw=a.input_file.read_bytes(); data=json.loads(raw); digest=hashlib.sha256(raw).hexdigest(); claims=classify(data); summary={"content_hash":digest,"strategy_leads":sum(not c["promotional_language"] for c in claims),"rejected_promotional_claims":sum(c["promotional_language"] for c in claims),"status":"needs_verification"}
    if a.dry_run:print(json.dumps(summary,indent=2));return 0
    e=env();url=e.get("SUPABASE_URL");key=e.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:print("ERROR: server-side Supabase environment is required; no secret values printed.",file=sys.stderr);return 1
    existing=request("GET",url,key,f"credit_strategy_sources?content_hash=eq.{digest}&select=id")
    if existing:source_id=existing[0]["id"]
    else:source_id=request("POST",url,key,"credit_strategy_sources",{"source_type":a.source_type,"title":a.title,"creator":a.creator,"source_reference":str(a.input_file.resolve().relative_to(ROOT)),"content_hash":digest,"category":a.category,"source_confidence":"low","review_status":"needs_verification","metadata":{"classification":"practitioner_promotional","raw_content_stored":False}})[0]["id"]
    if not request("GET",url,key,f"credit_strategy_claims?source_id=eq.{source_id}&select=id&limit=1"):
        request("POST",url,key,"credit_strategy_claims",[{"source_id":source_id,**c} for c in claims])
    print(json.dumps({**summary,"source_id":source_id},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
