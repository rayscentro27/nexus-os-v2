#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import RUNTIME,write_json,write_report
from hermes_context_common import advisor_response
def main():
 a=argparse.ArgumentParser();a.add_argument('--message',required=True);a.add_argument('--json',action='store_true');x=a.parse_args();r=advisor_response(x.message);p={'ok':True,'status':'hermes_advisor_response_ready','message':x.message,**r};
 path=RUNTIME/'hermes_advisor_response_examples_store.json'
 try: examples=json.loads(path.read_text())
 except: examples=[]
 examples=[e for e in examples if e.get('message')!=x.message]+[p];write_json(path,examples[-20:]);write_report('hermes_advisor_response_examples','Hermes Advisor Response Examples',{'ok':True,'status':'advisor_examples_ready','examples_count':len(examples[-20:]),'response_engine_mode':'local_contextual_advisor','external_action_performed':False},{'Examples':examples[-20:]});write_report('hermes_chat_messages','Hermes Chat Messages',p,{'Advisor response':[r['response']]});print(json.dumps(p)) if x.json else None
if __name__=='__main__':main()
