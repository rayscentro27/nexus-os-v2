#!/usr/bin/env python3
"""Bounded YouTube Data API metadata intake; never downloads media."""
from __future__ import annotations

import argparse, json, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY, env_presence, now, parse_env, read_json, write_json, write_report  # noqa:E402


def key_value()->str:
    values={}
    for p in (ROOT/".env",ROOT/".env.local",ROOT/".env.nexus.recovered.local"): values.update(parse_env(p))
    return values.get("YOUTUBE_API_KEY","")


def api(path:str, params:dict, key:str)->dict:
    query=urllib.parse.urlencode({**params,"key":key})
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?{query}",timeout=15) as response:
        return json.loads(response.read())


def build()->dict:
    config=read_json(ROOT/"configs"/"youtube_research_channels.json",{}); target=read_json(ROOT/"configs"/"youtube_source_targets.json",{})
    channels=[x for x in config.get("channels",[]) if x.get("enabled") and x.get("approved_by_ray")]
    key=key_value(); records=[]; errors=[]; network=False
    if key:
        for channel in channels:
            try:
                network=True
                info=api("channels",{"part":"id,snippet,contentDetails","forHandle":channel["handle"],"maxResults":1},key).get("items",[])
                if not info: errors.append({"channel":channel["name"],"error":"handle_not_resolved"}); continue
                uploads=info[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
                items=api("playlistItems",{"part":"snippet,contentDetails","playlistId":uploads,"maxResults":target.get("max_results_per_channel",3)},key).get("items",[])
                for item in items:
                    sn=item.get("snippet",{}); vid=item.get("contentDetails",{}).get("videoId")
                    records.append({"id":f"youtube-{vid}","source_id":channel["id"],"channel_name":channel["name"],"video_id":vid,
                        "title":sn.get("title"),"description":sn.get("description","")[:1000],"published_at":sn.get("publishedAt"),
                        "url":f"https://www.youtube.com/watch?v={vid}","categories":channel.get("categories",[]),"metadata_source":"youtube_data_api_v3",
                        "approved_source":True,"transcript_available":False,"media_downloaded":False,"created_at":now()})
            except Exception as exc:
                errors.append({"channel":channel["name"],"error":exc.__class__.__name__})
    write_json(SUPABASE_READY/"youtube_video_metadata_latest.json",records)
    status="real_metadata_review_active" if records else ("targets_configured_connector_missing" if not key else "configured_no_new_items")
    report={"ok":not bool(key and errors and not records),"generated_at":now(),"status":status,"targets_configured":len(channels),
      "api_key_present":bool(key),"network_request_performed":network,"metadata_records_created":len(records),"errors_sanitized":errors,
      "media_downloaded":False,"external_publish_performed":False,"exact_setup_needed":[] if key else ["YOUTUBE_API_KEY"],
      "next_required_action":"Review imported metadata in Ray Review." if records else "Add YOUTUBE_API_KEY to a gitignored local/server environment or place an approved transcript in data/sources/youtube_transcripts/.",
      "summary":f"Created {len(records)} bounded metadata records; no media was downloaded."}
    write_report("youtube_metadata_intake","YouTube Metadata Intake",report,{"Metadata records":records,"Sanitized errors":errors});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0
if __name__=="__main__":raise SystemExit(main())
