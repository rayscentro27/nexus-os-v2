#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import ROOT,write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');x=a.parse_args();ui=(ROOT/'src/components/SpecialistWorkroom.jsx').read_text();profiles=json.loads((ROOT/'configs/specialist_personality_profiles.json').read_text())['profiles'];checks={'nine_profiles':len(profiles)==9,'credit_available':"name: 'Credit Specialist'" in ui,'personality_voice':'Voice: strategic, direct, conversational' in ui,'safe_and_blocked':'Blocked:' in ui};p={'ok':all(checks.values()),'status':'specialist_workroom_smoke_passed','checks':checks,'external_action_performed':False};write_report('specialist_workroom_smoke_test','Specialist Workroom Smoke Test',p,{'Checks':checks});print(json.dumps(p)) if x.json else None
if __name__=='__main__':main()
