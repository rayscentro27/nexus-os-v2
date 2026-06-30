#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import ROOT,write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');x=a.parse_args();profiles=json.loads((ROOT/'configs/specialist_personality_profiles.json').read_text())['profiles'];p={'ok':True,'status':'specialist_personalities_active','profiles':len(profiles),'credit_specialist':True,'external_action_performed':False};write_report('specialist_personality_profiles','Specialist Personality Profiles',p,{'Profiles':profiles});print(json.dumps(p)) if x.json else None
if __name__=='__main__':main()
