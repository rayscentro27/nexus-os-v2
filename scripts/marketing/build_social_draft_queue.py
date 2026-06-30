#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from marketing_common import SUPABASE_READY,TOPICS,item,now,write_json,write_report
def build():
 rows=[item(i,x,"social_post") for i,x in enumerate(TOPICS[:5])];write_json(SUPABASE_READY/"social_draft_queue_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"social_drafts_ready","draft_count":len(rows),"published":0,"external_action_performed":False};write_report("social_draft_queue","Social Draft Queue",report,{"Drafts":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
