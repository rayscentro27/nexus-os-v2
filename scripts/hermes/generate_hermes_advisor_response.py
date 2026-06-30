#!/usr/bin/env python3
import argparse,json
from hermes_context_common import advisor_response
def main():
 a=argparse.ArgumentParser();a.add_argument('--message',required=True);a.add_argument('--json',action='store_true');x=a.parse_args();print(json.dumps({'ok':True,**advisor_response(x.message)}))
if __name__=='__main__':main()
