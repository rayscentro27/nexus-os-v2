#!/usr/bin/env python3
"""Bounded, synthetic-safe report comparison helper; never asserts causation or deletion."""
import argparse, json, sys
from pathlib import Path

def compare(prior, later):
    previous={row['canonicalAccountId']:row for row in prior}; current={row['canonicalAccountId']:row for row in later}; results=[]
    for key, before in previous.items():
        after=current.get(key)
        if not after:
            low=before.get('matchConfidence')=='low'
            results.append({'type':'uncertain_comparison' if low else 'account_not_found_on_later_report','canonicalAccountId':key,'confidence':'low' if low else 'high','causal':False})
            continue
        if before.get('balance') is not None and after.get('balance') is not None and before['balance'] != after['balance']: results.append({'type':'balance_changed','canonicalAccountId':key,'confidence':'high','causal':False})
        if before.get('accountStatus') and after.get('accountStatus') and before['accountStatus'] != after['accountStatus']: results.append({'type':'status_changed','canonicalAccountId':key,'confidence':'high','causal':False})
        if before.get('ownership') and after.get('ownership') and before['ownership'] != after['ownership']: results.append({'type':'ownership_changed','canonicalAccountId':key,'confidence':'medium','causal':False})
    for key in current:
        if key not in previous: results.append({'type':'account_newly_present','canonicalAccountId':key,'confidence':'medium','causal':False})
    return results

parser=argparse.ArgumentParser()
parser.add_argument('--prior-json', type=Path); parser.add_argument('--later-json', type=Path)
parser.add_argument('--prior-report-id'); parser.add_argument('--later-report-id')
args=parser.parse_args()
if not (args.prior_json and args.later_json):
    print('This bounded helper requires --prior-json and --later-json. Live report-id loading is intentionally not enabled without a server-side comparison policy.', file=sys.stderr); sys.exit(2)
prior=json.loads(args.prior_json.read_text()); later=json.loads(args.later_json.read_text())
if not isinstance(prior, list) or not isinstance(later, list):
    print('Each JSON input must be a JSON array of sanitized canonical accounts.', file=sys.stderr); sys.exit(2)
print(json.dumps({'comparison_engine_version':'outcome-analytics-v1','observations':compare(prior,later),'causal':False}, indent=2))
