#!/usr/bin/env python3
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import RUNTIME,write_report
from generate_specialist_response import respond
def main():
 a=argparse.ArgumentParser();a.add_argument('--specialist');a.add_argument('--message',required=True);a.add_argument('--json',action='store_true');x=a.parse_args();rules=[('credit',r'credit|dispute|readiness'),('funding',r'funding|grant|lender'),('trading',r'trad|oanda|vibe'),('research',r'research|source'),('monetization',r'money|offer|revenue'),('automation',r'automation|safe jobs')];s=x.specialist or next((n for n,p in rules if re.search(p,x.message,re.I)),'hermes');p={'ok':True,'specialist':s,'status':'specialist_response_ready','message':x.message,'response':respond(s,x.message),'external_action_performed':False};write_report('specialist_response_examples','Specialist Response Examples',p,{'Response':[p['response']]});print(json.dumps(p))
if __name__=='__main__':main()
