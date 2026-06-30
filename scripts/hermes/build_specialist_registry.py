#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); d=json.loads((ROOT/'configs/specialist_registry.json').read_text()); specialists=d['specialists']; payload={'ok':True,'status':'specialist_registry_ready','specialists_total':len(specialists),'credit_specialist_available':any(x['id']=='credit' for x in specialists),'external_action_performed':False}; write_report('specialist_registry','Nexus Specialist Registry',payload,{'Specialists':specialists}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
