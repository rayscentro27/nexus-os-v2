#!/usr/bin/env python3
import argparse,json
from hermes_context_common import classify
def main():
 a=argparse.ArgumentParser();a.add_argument('--message',required=True);a.add_argument('--json',action='store_true');x=a.parse_args();p={'ok':True,'intent':classify(x.message)};print(json.dumps(p))
if __name__=='__main__':main()
