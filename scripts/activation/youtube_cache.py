#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from youtube_engine_common import CACHE,ensure_dirs,now,read_json,write_json,write_report

def path_for(connector,key):return CACHE/("api_metadata" if connector=="youtube_api" else "ytdlp_metadata")/f"{key}.json"
def get(connector,key,max_age_hours=24):
 p=path_for(connector,key);d=read_json(p,{})
 if not d:return None
 try:age=(datetime.now(timezone.utc)-datetime.fromisoformat(d["last_checked_at"])).total_seconds()/3600
 except Exception:return None
 return d if age<max_age_hours else None
def put(connector,key,data):
 payload={"cache_key":key,"connector_used":connector,"last_checked_at":now(),"contains_secrets":False,"data":data};write_json(path_for(connector,key),payload);return payload
def status():
 ensure_dirs();files=list(CACHE.rglob("*.json"));r={"ok":True,"generated_at":now(),"status":"cache_ready","cache_enabled":True,"cache_file_count":len(files),"api_cache_count":len(list((CACHE/"api_metadata").glob("*.json"))),"ytdlp_cache_count":len(list((CACHE/"ytdlp_metadata").glob("*.json"))),"secrets_cached":False,"external_action_performed":False};write_report("youtube_cache_status","YouTube Cache Status",r);return r
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=status();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
