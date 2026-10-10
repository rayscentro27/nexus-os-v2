#!/usr/bin/env python3
"""Bounded YouTube Data API metadata intake; never downloads media."""
from __future__ import annotations

import argparse, json, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
sys.path.insert(0,str(ROOT/"scripts"))
from activation.governed_http import get_json as governed_get_json  # noqa:E402
from same_day_common import SUPABASE_READY, env_presence, now, read_json, write_json, write_report  # noqa:E402
from youtube_local_tool import audit as audit_local_tool
from nexus_runtime_env import load_runtime_env  # noqa:E402


def key_value()->str:
    values=load_runtime_env(allowed_keys={"YOUTUBE_API_KEY", "YOUTUBE_DATA_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_API_KEY"})
    return values.get("YOUTUBE_API_KEY","")


def api(path:str, params:dict, key:str)->dict:
    query=urllib.parse.urlencode({**params,"key":key})
    return governed_get_json(f"https://www.googleapis.com/youtube/v3/{path}?{query}",
        provider="GOOGLE", service="youtube_data_api", timeout=15, estimated_units=1)


def build()->dict:
    config=read_json(ROOT/"configs"/"youtube_research_channels.json",{}); target=read_json(ROOT/"configs"/"youtube_source_targets.json",{})
    channels=[x for x in config.get("channels",[]) if x.get("enabled") and x.get("approved_by_ray")]
    local_tool=audit_local_tool(); key=key_value(); records=[]; errors=[]; network=False
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
    if records:
        status="real_metadata_review_active_api"
    elif channels and local_tool["local_ytdlp_available"]:
        status="targets_configured_ytdlp_available_needs_approved_probe"
    elif local_tool["local_ytdlp_available"]:
        status="local_ytdlp_available_no_approved_targets"
    else:
        status="targets_configured_connector_missing" if channels and not key else ("queue_only_no_real_review" if channels else "not_configured")
    report={"ok":not bool(key and errors and not records),"generated_at":now(),"status":status,"targets_configured":len(channels),
      "api_key_present":bool(key),"network_request_performed":network,"metadata_records_created":len(records),"errors_sanitized":errors,
      "local_ytdlp_available":local_tool["local_ytdlp_available"],"ytdlp_path":local_tool["ytdlp_path"],"ytdlp_version":local_tool["ytdlp_version"],
      "ytdlp_probe_performed":False,"ytdlp_probe_approval_required":bool(channels and local_tool["local_ytdlp_available"]),
      "media_downloaded":False,"external_publish_performed":False,
      "exact_setup_needed":[] if records else (["Ray approval for local yt-dlp metadata/subtitle probe"] if channels and local_tool["local_ytdlp_available"] else ["YOUTUBE_API_KEY or approved local transcript text"]),
      "next_required_action":"Review imported metadata in Ray Review." if records else ("Approve local yt-dlp metadata/subtitle probe for queued YouTube targets." if channels and local_tool["local_ytdlp_available"] else "Add YOUTUBE_API_KEY to a gitignored local/server environment or place an approved transcript in data/sources/youtube_transcripts/."),
      "summary":f"Created {len(records)} bounded metadata records; no media was downloaded."}
    write_report("youtube_metadata_intake","YouTube Metadata Intake",report,{"Metadata records":records,"Sanitized errors":errors});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0
if __name__=="__main__":raise SystemExit(main())
