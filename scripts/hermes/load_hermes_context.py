#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation')); from activation_common import write_report
from hermes_context_common import load_context
def main():
 a=argparse.ArgumentParser(); a.add_argument('--json',action='store_true'); x=a.parse_args(); ctx=load_context(); payload={'ok':True,'status':'hermes_context_loaded','sources_available':ctx['sources_available'],'context':{k:v for k,v in ctx.items() if k not in ('sources',)},'external_action_performed':False}; write_report('hermes_system_context','Hermes System Context',payload,{'Context sources':ctx['sources']}); print(json.dumps(payload)) if x.json else None
if __name__=='__main__':main()
