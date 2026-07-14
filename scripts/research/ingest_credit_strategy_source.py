#!/usr/bin/env python3
"""Bounded credit-strategy source intake. Unapproved source content never reaches Clyde."""
from __future__ import annotations
import argparse, hashlib, json, os, ssl, sys, urllib.parse, urllib.request
from pathlib import Path
import certifi
ROOT=Path(__file__).resolve().parents[2]
PROMOTIONAL=("four days","87%","dispute everything","dispute every","always required","automatic deletion","automatic $1,000","must delete","guaranteed")
SOURCE_TYPES={"official_government","statute","regulation","bureau_guidance","court_or_enforcement","github","youtube","practitioner","article","educator","internal_outcome"}
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
def claim_row(text,promotional=False):
    lower=text.lower(); guarantee=any(x in lower for x in ("guaranteed","automatic deletion","must delete","automatic $1,000")); universal=any(x in lower for x in ("everything","every negative","always required","87%")); legal=any(x in lower for x in ("must delete","$1,000","statutory damages")); rejected=promotional or guarantee or universal or legal
    return {"summarized_claim":text,"strategy_category":"promotional_claim" if rejected else text.replace(" ","_"),"claim_category":"credit_strategy_discovery","claim_type":"promotional_claim" if promotional else "practitioner_method","evidence_type":"promotional" if rejected else "practitioner_discovery","evidence_level":"unsupported" if rejected else "anecdotal","evidence_score":0 if rejected else 20,"official_support_status":"unsupported" if rejected else "needs_verification","risk_score":95 if rejected else 45,"promotional_language":promotional,"guarantee_language":guarantee,"universal_claim":universal,"legal_conclusion":legal,"client_safe":False,"actionable":False,"review_required":True,"approval_state":"rejected" if rejected else "needs_review","disposition":"rejected" if rejected else "practitioner","rejection_reason":"Unsupported promotional, universal, outcome, or legal claim." if rejected else None,"review_notes":"Rejected and preserved for research history." if rejected else "Useful discovery lead; official verification and Ray approval required."}
def classify(data):
    leads=[claim_row(x) for x in data.get("strategy_leads",[])]
    rejected=[claim_row(x,True) for x in data.get("promotional_claims",[]) if any(p.lower() in x.lower() for p in PROMOTIONAL)]
    return leads+rejected
def main():
    p=argparse.ArgumentParser();p.add_argument("--source-type",required=True,choices=sorted(SOURCE_TYPES));p.add_argument("--input-file",type=Path,required=True);p.add_argument("--title",required=True);p.add_argument("--creator",default="");p.add_argument("--category",default="credit_strategy");p.add_argument("--source-url",default="");p.add_argument("--dry-run",action="store_true");a=p.parse_args(); raw=a.input_file.read_bytes(); data=json.loads(raw); digest=hashlib.sha256(raw).hexdigest(); claims=classify(data); summary={"content_hash":digest,"strategy_leads":sum(not c["promotional_language"] for c in claims),"rejected_promotional_claims":sum(c["promotional_language"] for c in claims),"status":"needs_verification","auto_approved":False}
    if a.dry_run:print(json.dumps(summary,indent=2));return 0
    e=env();url=e.get("SUPABASE_URL");key=e.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:print("ERROR: server-side Supabase environment is required; no secret values printed.",file=sys.stderr);return 1
    existing=request("GET",url,key,f"credit_strategy_sources?content_hash=eq.{digest}&select=id")
    source_patch={"author_publisher":a.creator,"source_url":a.source_url or None,"reliability_score":20,"promotional_risk_score":90,"authority_level":"practitioner","processing_state":"classified","sanitized_summary":"Practitioner/promotional discovery artifact; claims require authority review before strategy use.","provenance_metadata":{"adapter":"existing_credit_strategy_ingest_v2","client_data_used":False}}
    if existing:
        source_id=existing[0]["id"];request("PATCH",url,key,f"credit_strategy_sources?id=eq.{source_id}",source_patch)
    else:source_id=request("POST",url,key,"credit_strategy_sources",{"source_type":a.source_type,"title":a.title,"creator":a.creator,"author_publisher":a.creator,"source_url":a.source_url or None,"source_reference":str(a.input_file.resolve().relative_to(ROOT)),"content_hash":digest,"category":a.category,"source_confidence":"low","reliability_score":20,"promotional_risk_score":90,"authority_level":"practitioner","processing_state":"classified","review_status":"needs_verification","sanitized_summary":"Practitioner/promotional discovery artifact; claims require authority review before strategy use.","provenance_metadata":{"adapter":"existing_credit_strategy_ingest_v2","client_data_used":False},"metadata":{"classification":"practitioner_promotional","raw_content_stored":False}})[0]["id"]
    for claim in claims:
        encoded=urllib.parse.quote(claim["summarized_claim"],safe="")
        found=request("GET",url,key,f"credit_strategy_claims?source_id=eq.{source_id}&summarized_claim=eq.{encoded}&select=id&limit=1")
        if found:request("PATCH",url,key,f"credit_strategy_claims?id=eq.{found[0]['id']}",claim)
        else:request("POST",url,key,"credit_strategy_claims",{"source_id":source_id,**claim})
    print(json.dumps({**summary,"source_id":source_id},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
