#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from marketing_common import SUPABASE_READY,TOPICS,item,now,write_json,write_report
def build():
 rows=[{**item(i,x,"short_video_script"),"beats":["Hook","One readiness insight","Safe next step","Approved CTA"]} for i,x in enumerate(TOPICS[:5])];write_json(SUPABASE_READY/"short_video_script_queue_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"short_video_scripts_ready","script_count":len(rows),"published":0,"external_action_performed":False};write_report("short_video_script_queue","Short Video Script Queue",report,{"Scripts":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
