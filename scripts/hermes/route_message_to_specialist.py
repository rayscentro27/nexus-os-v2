#!/usr/bin/env python3
import argparse,json,re
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--message',required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); rules=[('Credit Specialist',r'credit|dispute'),('Funding Specialist',r'funding|grant|lender'),('Trading Specialist',r'trad|oanda|vibe'),('Research Specialist',r'research|source'),('Monetization Specialist',r'money|offer|revenue')]; target=next((n for n,p in rules if re.search(p,a.message,re.I)),'Hermes CEO Advisor'); out={'ok':True,'specialist':target,'status':'routed_local_safe','external_action_performed':False}; print(json.dumps(out))
if __name__=='__main__': main()
