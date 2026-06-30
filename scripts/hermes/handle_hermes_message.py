#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--message',required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); payload={'ok':True,'status':'local_safe_response_ready','message_received':True,'response':'Hermes created a safe delegation plan. Risky actions remain approval-gated.','external_action_performed':False}; write_report('hermes_chat_messages','Hermes Chat Messages',payload,{'Message':[a.message]}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
