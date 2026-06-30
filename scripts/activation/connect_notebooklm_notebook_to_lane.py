#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from notebooklm_connector_common import route
def build(name,notebook_id):return {"ok":bool(name),"notebook_name":name,"notebook_id":notebook_id,"research_lane":route(name),"sync_enabled":True,"review_schedule":"daily","approval_required_for_import":False,"external_action_performed":False}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--name",required=True);p.add_argument("--notebook-id",default="");a=p.parse_args();r=build(a.name,a.notebook_id);print(json.dumps(r,indent=2) if a.json else r)
