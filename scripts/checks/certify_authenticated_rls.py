#!/usr/bin/env python3
"""Direct anon-session RLS certification for synthetic personas; never uses service role."""
import json, os, ssl, sys, urllib.request, urllib.error
from pathlib import Path
try:
    import certifi
except ImportError:
    certifi = None

def values():
    out={}
    for path in (Path('.env'), Path('.env.e2e.local')):
        if path.exists():
            for line in path.read_text().splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    key,value=line.split('=',1); out[key.strip()]=value.strip().strip('"').strip("'")
    out.update({k:v for k,v in os.environ.items() if v}); return out

def request(url, key, path, token=None, method='GET', body=None):
    headers={'apikey':key,'Authorization':f'Bearer {token or key}','Content-Type':'application/json'}
    req=urllib.request.Request(url.rstrip('/')+path,headers=headers,method=method,data=json.dumps(body).encode() if body is not None else None)
    context=ssl.create_default_context(cafile=certifi.where()) if certifi else None
    try:
        with urllib.request.urlopen(req,context=context,timeout=20) as response: return response.status, response.read()
    except urllib.error.HTTPError as error: return error.code, error.read()

def main():
    e=values(); base=e.get('SUPABASE_URL') or e.get('VITE_SUPABASE_URL'); anon=e.get('VITE_SUPABASE_ANON_KEY') or e.get('SUPABASE_ANON_KEY')
    if not base or not anon: print('FAIL configuration_missing'); return 2
    personas=['A','B','C']; tokens={}; failures=0
    for p in personas:
        email=e.get(f'E2E_PERSONA_{p}_EMAIL'); password=e.get(f'E2E_PERSONA_{p}_PASSWORD')
        status,raw=request(base,anon,'/auth/v1/token?grant_type=password',body={'email':email,'password':password},method='POST')
        if status != 200: print(f'FAIL {p}_authentication status={status}'); failures+=1; continue
        tokens[p]=json.loads(raw).get('access_token')
    tables=['client_documents','credit_report_parser_results','credit_bureau_tradelines','credit_canonical_accounts','credit_report_discrepancies','credit_strategy_matches','credit_strategy_client_selections','credit_strategy_evidence_links','credit_strategy_drafts','credit_report_comparison_runs','credit_report_comparison_results','strategy_outcome_observations','credit_readiness_history','credit_strategy_exceptions']
    for p,token in tokens.items():
        for table in tables:
            status,_=request(base,anon,f'/rest/v1/{table}?select=*&limit=100',token=token)
            if status != 200: print(f'FAIL {p}_read_{table} status={status}'); failures+=1
            else: print(f'PASS {p}_read_{table}')
        status,_=request(base,anon,'/rest/v1/credit_strategy_versions',token=token,method='POST',body={'strategy_id':'synthetic-forbidden','version':1,'title':'forbidden'})
        if status < 400: print(f'FAIL {p}_strategy_mutation_allowed'); failures+=1
        else: print(f'PASS {p}_strategy_mutation_denied')
    print(f'RLS_CERTIFICATION failures={failures} checks={len(tokens)*(len(tables)+1)}')
    return 1 if failures else 0
if __name__=='__main__': sys.exit(main())
