#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import write_report
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hermes'));from hermes_context_common import advisor_response
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');x=a.parse_args();samples={m:advisor_response(m) for m in ['good morning','did you sleep','what should I do next?','give me the next 100 steps for automation communication and monetization']};checks={'greeting_natural':'Good morning, Ray' in samples['good morning']['response'],'casual_natural':"I don’t sleep" in samples['did you sleep']['response'],'next_steps_contextual':'top three priorities' in samples['what should I do next?']['response'],'delegation_program':'operating program' in samples['give me the next 100 steps for automation communication and monetization']['response']};p={'ok':all(checks.values()),'status':'hermes_delegation_smoke_passed','checks':checks,'mode':'local_contextual_advisor','external_action_performed':False};write_report('hermes_delegation_smoke_test','Hermes Delegation Smoke Test',p,{'Checks':checks});print(json.dumps(p)) if x.json else None
if __name__=='__main__':main()
