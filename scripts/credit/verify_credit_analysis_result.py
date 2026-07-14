#!/usr/bin/env python3
"""Fail-loud, non-PII verification for a completed synthetic credit analysis."""
from __future__ import annotations
import argparse,json,os,ssl,sys,urllib.parse,urllib.request
from pathlib import Path
import certifi
def env():
    out=dict(os.environ)
    for name in (".env.local",".env"):
        p=Path(name)
        if p.exists():
            for line in p.read_text(errors="ignore").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):k,v=line.split("=",1);out.setdefault(k.strip(),v.strip().strip('"').strip("'"))
    return out
def get(url,key,path):
    req=urllib.request.Request(f"{url.rstrip('/')}/rest/v1/{path}",headers={"apikey":key,"Authorization":f"Bearer {key}"})
    with urllib.request.urlopen(req,context=ssl.create_default_context(cafile=certifi.where()),timeout=30) as r:return json.loads(r.read() or b"[]")
def main():
    p=argparse.ArgumentParser();p.add_argument("--document-name",required=True);p.add_argument("--expected-accounts",type=int,required=True);p.add_argument("--expected-inquiries",type=int,required=True);p.add_argument("--expected-candidates",type=int,default=26);p.add_argument("--expected-personal-variations",type=int,default=2);p.add_argument("--expected-drafts",type=int,default=21);p.add_argument("--expected-recommendations",type=int,default=42);a=p.parse_args();e=env();url=e.get("SUPABASE_URL");key=e.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:print("ERROR: server-side environment required; no secret values printed.",file=sys.stderr);return 1
    docs=get(url,key,f"client_documents?title=eq.{urllib.parse.quote(a.document_name)}&select=id,client_id&order=created_at.desc&limit=1")
    if not docs:print("FAIL: expected synthetic document metadata not found",file=sys.stderr);return 2
    document_id=docs[0]["id"];rows=get(url,key,f"credit_report_parser_results?document_id=eq.{urllib.parse.quote(document_id)}&extraction_success=eq.true&select=id,document_id,status,accounts,inquiries,negative_candidates,personal_info_variations,structured_item_drafts,dispute_strategy_suggestions,bureaus_detected,utilization_summary,warnings,created_at&order=created_at.desc&limit=5")
    if not rows:print("FAIL: no successful parser result",file=sys.stderr);return 2
    latest=rows[0];fields=("accounts","inquiries","negative_candidates","personal_info_variations","structured_item_drafts","dispute_strategy_suggestions","bureaus_detected","warnings")
    if any(not isinstance(latest.get(f),list) for f in fields) or not isinstance(latest.get("utilization_summary"),dict):print("FAIL: stored JSONB shape is not native arrays/objects",file=sys.stderr);return 3
    expected={"accounts":a.expected_accounts,"inquiries":a.expected_inquiries,"negative_candidates":a.expected_candidates,"personal_info_variations":a.expected_personal_variations,"structured_item_drafts":a.expected_drafts,"dispute_strategy_suggestions":a.expected_recommendations};actual={k:len(latest[k]) for k in expected}
    if actual!=expected:print(f"FAIL: safe count mismatch expected={expected} actual={actual}",file=sys.stderr);return 4
    bureaus={str(x).lower() for x in latest["bureaus_detected"]}
    if not {"experian","equifax","transunion"}<=bureaus:print("FAIL: all three bureaus were not detected",file=sys.stderr);return 5
    if any(len(r.get("accounts") or [])==0 for r in rows[:1]):print("FAIL: latest successful result is a stale zero-count row",file=sys.stderr);return 6
    jobs=get(url,key,f"credit_analysis_jobs?document_id=eq.{urllib.parse.quote(document_id)}&status=in.(queued,processing)&select=id,parser_version")
    grouped={}
    for j in jobs:grouped[j["parser_version"]]=grouped.get(j["parser_version"],0)+1
    if any(v>1 for v in grouped.values()):print("FAIL: duplicate active jobs for parser version",file=sys.stderr);return 7
    complete=get(url,key,f"credit_analysis_jobs?document_id=eq.{urllib.parse.quote(document_id)}&status=eq.complete&select=id,parser_result_id&order=completed_at.desc&limit=1")
    if not complete:print("FAIL: no completed analysis job",file=sys.stderr);return 8
    print(json.dumps({"ok":True,"parser_status":"complete","accounts":actual["accounts"],"inquiries":actual["inquiries"],"funding_impact_candidates":actual["negative_candidates"],"personal_information_variations":actual["personal_info_variations"],"structured_item_drafts":actual["structured_item_drafts"],"recommendations":actual["dispute_strategy_suggestions"],"bureaus":3,"native_jsonb":True,"document_link_verified":latest["document_id"]==document_id,"duplicate_active_jobs":False},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
