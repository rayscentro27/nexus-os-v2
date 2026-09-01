#!/usr/bin/env python3
import argparse,json
from .business_opportunity_loop import run_real_mobile_detailing_loop
def main():
 p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');a=p.parse_args();r=run_real_mobile_detailing_loop();print(json.dumps(r,indent=2) if a.json else f"Business opportunity loop {r['status']}: {r['opportunity']['opportunity_id']}")
if __name__=='__main__': main()
