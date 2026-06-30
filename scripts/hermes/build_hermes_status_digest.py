#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation')); from activation_common import write_report
from hermes_context_common import load_context
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');x=a.parse_args();c=load_context();p={'ok':True,'status':'advisor_digest_ready','summary':f"Two cycles running; {c['ray_review_cards']} approvals; {c['actionable_candidates']} actionable money candidates; $0 confirmed revenue.",'top_priorities':['Prove fake customer/payment journey','Fix Resend','Select research-to-money candidates'],'external_action_performed':False};write_report('hermes_status_digest','Hermes Status Digest',p,{'Priorities':p['top_priorities']});print(json.dumps(p)) if x.json else None
if __name__=='__main__':main()
