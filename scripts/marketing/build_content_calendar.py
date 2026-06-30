#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from marketing_common import SUPABASE_READY,TOPICS,item,now,write_json,write_report
def build():
 rows=[{**item(i,x,"calendar"),"day":i+1} for i,x in enumerate(TOPICS)];write_json(SUPABASE_READY/"content_calendar_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"seven_day_content_calendar_ready","entries":len(rows),"published":0,"external_action_performed":False};write_report("content_calendar","Content Calendar",report,{"Calendar":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
