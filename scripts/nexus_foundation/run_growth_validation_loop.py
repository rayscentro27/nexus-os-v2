#!/usr/bin/env python3
import argparse,json
from .growth_validation_loop import run_growth_validation
def main():
 p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');a=p.parse_args();r=run_growth_validation();print(json.dumps(r,indent=2) if a.json else f"Growth validation {r['status']}: {r['opportunity_id']}")
if __name__=='__main__': main()
