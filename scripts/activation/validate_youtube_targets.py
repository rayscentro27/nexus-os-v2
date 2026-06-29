#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import SUPABASE_READY,approved_targets,now,record,write_json,write_report

def build():
 targets=[]
 for x in approved_targets():
  kind="playlist" if "playlist?list=" in x["url"] else "video" if "watch?v=" in x["url"] or "youtu.be/" in x["url"] else "channel"
  targets.append(record(f"approved-{x['id']}","youtube_approved_target",x["name"],status="approved",target_id=x["id"],target_type=kind,source_url=x["url"],approved=True,categories=x.get("categories",[])))
 report={"ok":True,"generated_at":now(),"status":"approved_targets_valid","approved_target_count":len(targets),"refused_unapproved_count":0,"missing_setup":[] if targets else ["Add target with enabled=true, approved_by_ray=true, and URL"],"external_action_performed":False};write_json(SUPABASE_READY/"youtube_approved_targets_latest.json",targets);write_report("youtube_approved_targets","YouTube Approved Targets",report,{"Targets":targets});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
