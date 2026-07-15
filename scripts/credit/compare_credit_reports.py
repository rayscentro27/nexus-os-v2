#!/usr/bin/env python3
"""Bounded, synthetic-safe report comparison helper; never asserts causation or deletion."""
import argparse, json, sys, os, ssl, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
try:
    import certifi
except ImportError:
    certifi = None

def compare(prior, later):
    previous={row['canonicalAccountId']:row for row in prior}; current={row['canonicalAccountId']:row for row in later}; results=[]
    for key, before in previous.items():
        after=current.get(key)
        if not after:
            low=before.get('matchConfidence')=='low'
            results.append({'type':'uncertain_comparison' if low else 'account_not_found_on_later_report','canonicalAccountId':key,'confidence':'low' if low else 'high','causal':False})
            continue
        changed=False
        if before.get('balance') is not None and after.get('balance') is not None and before['balance'] != after['balance']: results.append({'type':'balance_changed','canonicalAccountId':key,'confidence':'high','causal':False}); changed=True
        if before.get('accountStatus') and after.get('accountStatus') and before['accountStatus'] != after['accountStatus']: results.append({'type':'status_changed','canonicalAccountId':key,'confidence':'high','causal':False}); changed=True
        if before.get('ownership') and after.get('ownership') and before['ownership'] != after['ownership']: results.append({'type':'ownership_changed','canonicalAccountId':key,'confidence':'medium','causal':False}); changed=True
        if not changed: results.append({'type':'no_measurable_change','canonicalAccountId':key,'confidence':'medium','causal':False})
    for key in current:
        if key not in previous: results.append({'type':'account_newly_present','canonicalAccountId':key,'confidence':'medium','causal':False})
    return results

parser=argparse.ArgumentParser()
parser.add_argument('--prior-json', type=Path); parser.add_argument('--later-json', type=Path)
parser.add_argument('--prior-report-id'); parser.add_argument('--later-report-id')
parser.add_argument('--persist', action='store_true')
args=parser.parse_args()
def env_values():
    values={}
    for path in (Path('.env'),):
        if path.exists():
            for line in path.read_text().splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    key,value=line.split('=',1); values[key.strip()]=value.strip().strip('"').strip("'")
    values.update({k:v for k,v in os.environ.items() if v})
    return values
def rest(base,key,path,method='GET',body=None):
    headers={'apikey':key,'Authorization':f'Bearer {key}','Content-Type':'application/json','Prefer':'return=representation'}
    request=urllib.request.Request(base.rstrip('/')+path,headers=headers,method=method,data=json.dumps(body).encode() if body is not None else None)
    context=ssl.create_default_context(cafile=certifi.where()) if certifi else None
    with urllib.request.urlopen(request,context=context,timeout=30) as response:
        return json.loads(response.read() or b'[]')
if args.persist and args.prior_report_id and args.later_report_id:
    env=env_values(); base=env.get('SUPABASE_URL') or env.get('VITE_SUPABASE_URL'); key=env.get('SUPABASE_SERVICE_ROLE_KEY')
    if not base or not key:
        print('FAIL: server-side Supabase configuration is unavailable',file=sys.stderr);sys.exit(2)
    q=lambda table,where: rest(base,key,f'/rest/v1/{table}?{urllib.parse.urlencode(where)}')
    prior_rows=q('credit_canonical_accounts',{'document_id':f'eq.{args.prior_report_id}','select':'id,normalized_creditor_label,canonical_status'})
    later_rows=q('credit_canonical_accounts',{'document_id':f'eq.{args.later_report_id}','select':'id,normalized_creditor_label,canonical_status'})
    if not prior_rows or not later_rows:
        print('FAIL: both reports require persisted canonical accounts',file=sys.stderr);sys.exit(2)
    def account_snapshots(rows, report_id):
        snapshots=[]
        for account in rows:
            links=q('credit_canonical_account_tradelines',{'canonical_account_id':f"eq.{account['id']}",'select':'tradeline_id'})
            ids=[x['tradeline_id'] for x in links]
            if not ids:
                snapshots.append({'canonicalAccountId':str(account.get('normalized_creditor_label','')),'accountStatus':account.get('canonical_status')}); continue
            values=q('credit_bureau_tradelines',{'id':f"in.({','.join(ids)})",'select':'balance,account_status_original,ownership_original,account_suffix'})
            balances=[x.get('balance') for x in values if x.get('balance') is not None]
            statuses=[x.get('account_status_original') for x in values if x.get('account_status_original')]
            ownership=[x.get('ownership_original') for x in values if x.get('ownership_original')]
            suffix=next((x.get('account_suffix') for x in values if x.get('account_suffix')), 'none')
            snapshots.append({'canonicalAccountId':f"{account.get('normalized_creditor_label','')}|{suffix}",'balance':'|'.join(str(x) for x in sorted(balances)) if balances else None,'accountStatus':'|'.join(sorted(set(statuses))) if statuses else account.get('canonical_status'),'ownership':'|'.join(sorted(set(ownership))) if ownership else None})
        return snapshots
    prior=account_snapshots(prior_rows,args.prior_report_id); later=account_snapshots(later_rows,args.later_report_id)
    if not prior or not later: print('FAIL: canonical snapshots are incomplete',file=sys.stderr);sys.exit(2)
    observations=compare(prior,later)
    # Resolve tenant/client from the prior document and persist an immutable run plus results.
    docs=q('client_documents',{'id':f'eq.{args.prior_report_id}','select':'tenant_id,client_id'})
    if not docs: print('FAIL: prior report metadata is unavailable',file=sys.stderr);sys.exit(2)
    tenant,client=docs[0]['tenant_id'],docs[0]['client_id']; engine='outcome-analytics-v1.2'
    now=datetime.now(timezone.utc).isoformat()
    run_body={'tenant_id':tenant,'client_id':client,'prior_report_id':args.prior_report_id,'later_report_id':args.later_report_id,'status':'complete','comparison_engine_version':engine,'confidence':'medium','summary':{'observation_count':len(observations)},'completed_at':now}
    existing_runs=q('credit_report_comparison_runs',{'tenant_id':f'eq.{tenant}','client_id':f'eq.{client}','prior_report_id':f'eq.{args.prior_report_id}','later_report_id':f'eq.{args.later_report_id}','comparison_engine_version':f'eq.{engine}','select':'id','limit':'1'})
    run=existing_runs[0] if existing_runs else rest(base,key,'/rest/v1/credit_report_comparison_runs',method='POST',body=run_body)[0]
    rows=[]
    for item in observations:
        rows.append({'comparison_run_id':run['id'],'tenant_id':tenant,'client_id':client,'prior_report_id':args.prior_report_id,'later_report_id':args.later_report_id,'canonical_account_id':item.get('canonicalAccountId'),'observation_type':item['type'],'observation_value':{'causal':False},'observation_source':'structured_report_comparison','confidence':item['confidence'],'notes':'Observed report sequence; not a causal conclusion.'})
    if rows: rest(base,key,'/rest/v1/credit_report_comparison_results',method='POST',body=rows)
    outcome_rows=[{'tenant_id':tenant,'client_id':client,'report_id':args.later_report_id,'prior_report_id':args.prior_report_id,'canonical_account_id':item.get('canonicalAccountId'),'observation_type':item['type'],'observation_value':{'causal':False},'observation_source':'structured_report_comparison','confidence':item['confidence'],'comparison_engine_version':engine,'notes':'Observed report sequence; not a causal conclusion.'} for item in observations]
    if outcome_rows: rest(base,key,'/rest/v1/strategy_outcome_observations',method='POST',body=outcome_rows)
    rest(base,key,'/rest/v1/credit_readiness_history',method='POST',body={'tenant_id':tenant,'client_id':client,'report_id':args.later_report_id,'prior_report_id':args.prior_report_id,'credit_profile_status':'action_needed','tier_1_status':'action_needed','tier_2_status':'insufficient_information','requirements':[],'source':'system'})
    print(json.dumps({'comparison_run_id':run['id'],'observation_count':len(observations),'causal':False}));sys.exit(0)
if not (args.prior_json and args.later_json):
    print('This bounded helper requires --prior-json and --later-json, or --persist with two report IDs.', file=sys.stderr); sys.exit(2)
prior=json.loads(args.prior_json.read_text()); later=json.loads(args.later_json.read_text())
if not isinstance(prior, list) or not isinstance(later, list):
    print('Each JSON input must be a JSON array of sanitized canonical accounts.', file=sys.stderr); sys.exit(2)
print(json.dumps({'comparison_engine_version':'outcome-analytics-v1','observations':compare(prior,later),'causal':False}, indent=2))
