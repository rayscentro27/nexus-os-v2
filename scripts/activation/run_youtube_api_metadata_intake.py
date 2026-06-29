#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,ssl,urllib.parse,urllib.request
from youtube_cache import get,put,status as cache_status
from youtube_engine_common import ROOT,SUPABASE_READY,api_key_status,approved_targets,now,read_json,record,write_json,write_report

def api(path,params,key):
 q=urllib.parse.urlencode({**params,"key":key})
 try:
  import certifi
  context=ssl.create_default_context(cafile=certifi.where())
 except ImportError:
  context=ssl.create_default_context()
 with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?{q}",timeout=20,context=context) as r:return json.loads(r.read())
def build():
 policy=read_json(ROOT/"configs/youtube_quota_policy.json",{});key=api_key_status();targets=approved_targets()[:policy.get("max_channels_per_run",4)];records=[];errors=[];units=0;cache_hits=0
 if key["present"]:
  for target in targets:
   cached=get("youtube_api",target["id"],policy.get("refresh_existing_after_hours",24)) if policy.get("prefer_cache") else None
   if cached:records.extend(cached.get("data",[]));cache_hits+=1;continue
   try:
    channel=api("channels",{"part":"id,snippet,contentDetails","forHandle":target["handle"],"maxResults":1},key["value"]);units+=1
    items=channel.get("items",[])
    if not items:errors.append({"target":target["id"],"error":"handle_not_resolved"});continue
    uploads=items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos=api("playlistItems",{"part":"snippet,contentDetails","playlistId":uploads,"maxResults":min(5,policy.get("max_new_videos_per_run",25))},key["value"]);units+=1
    batch=[]
    for item in videos.get("items",[]):
     sn=item.get("snippet",{});vid=item.get("contentDetails",{}).get("videoId")
     batch.append(record(f"youtube-{vid}","youtube_video_metadata",sn.get("title","YouTube video"),status="real_metadata",source_id=target["id"],channel_name=target["name"],video_id=vid,url=f"https://www.youtube.com/watch?v={vid}",description=sn.get("description","")[:1000],published_at=sn.get("publishedAt"),metadata_source="youtube_data_api_v3",approved_source=True,media_downloaded=False))
    records.extend(batch);put("youtube_api",target["id"],batch)
   except Exception as exc:errors.append({"target":target["id"],"error":exc.__class__.__name__})
 existing=read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[])
 merged={x.get("id"):x for x in existing if x.get("metadata_source")!="youtube_data_api_v3"}
 merged.update({x.get("id"):x for x in records})
 write_json(SUPABASE_READY/"youtube_video_metadata_latest.json",list(merged.values()));quota={"daily_budget":policy.get("daily_unit_budget"),"estimated_units_used":units,"estimated_remaining":policy.get("daily_unit_budget",1000)-units,"reserve_units":policy.get("reserve_units",250),"stopped_for_reserve":False,"cache_hits":cache_hits};write_json(SUPABASE_READY/"youtube_api_quota_status_latest.json",quota);cache_status()
 mode="real_metadata_review_active_api" if records else ("api_configured_quota_cache_ready" if key["present"] else "targets_configured_connector_missing")
 report={"ok":not bool(key["present"] and errors and not records),"generated_at":now(),"status":mode,"api_key_present":key["present"],"raw_key_included":False,"approved_targets_checked":len(targets) if key["present"] else 0,"metadata_records_created":len(records),"cache_hits":cache_hits,"quota":quota,"errors_sanitized":errors,"video_downloaded":False,"audio_downloaded":False,"external_action_performed":False};write_report("youtube_api_metadata_intake","YouTube API Metadata Intake",report,{"Sanitized errors":errors});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
