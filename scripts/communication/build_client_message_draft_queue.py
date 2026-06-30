#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from communication_common import LANES,SUPABASE_READY,draft,now,write_json,write_report
def build():
 rows=[draft(x) for x in LANES];write_json(SUPABASE_READY/"client_message_draft_queue_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"client_message_drafts_ready","draft_count":len(rows),"sent_count":0,"approval_required_count":len(rows),"external_action_performed":False};write_report("client_message_draft_queue","Client Message Draft Queue",report,{"Drafts":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
