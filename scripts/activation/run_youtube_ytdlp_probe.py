#!/usr/bin/env python3
"""Approval-scoped yt-dlp metadata/subtitle availability probe; never downloads media."""
from __future__ import annotations
import argparse,json,subprocess
from youtube_cache import get,put
from youtube_engine_common import SUPABASE_READY,approved_targets,now,read_json,record,write_json,write_report
from youtube_local_tool import audit

SAFE_BASE=["--dump-single-json","--skip-download","--no-warnings","--no-progress"]
def run_json(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90,check=False)
 if p.returncode:return None,p.stderr[-300:]
 try:return json.loads(p.stdout),None
 except json.JSONDecodeError:return None,"invalid_json"
def build(args):
 tool=audit();targets=approved_targets() if args.approved_only else []
 if not args.approved_only or not args.no_download:return {"ok":False,"status":"failed_with_error","blocked_reason":"--approved-only and --no-download are mandatory","external_action_performed":False}
 metadata=[];subtitles=[];errors=[];checked=0;cache_hits=0
 if tool["local_ytdlp_available"]:
  for target in targets:
   cached=get("ytdlp",target["id"],24)
   if cached:
    payload=cached.get("data",{});metadata.append(payload.get("metadata",{}));subtitles.append(payload.get("subtitle_availability",{}));checked+=1;cache_hits+=1;continue
   channel,err=run_json([tool["ytdlp_path"],*SAFE_BASE,"--flat-playlist","--playlist-end","1",target["url"]])
   if err:errors.append({"target":target["id"],"error":"probe_failed"});continue
   checked+=1;entries=channel.get("entries",[]) if isinstance(channel,dict) else []
   candidate=entries[0] if entries else channel
   video_id=(candidate or {}).get("id");url=(candidate or {}).get("url")
   if video_id and (not url or not str(url).startswith("http")):url=f"https://www.youtube.com/watch?v={video_id}"
   detail={}
   if url:
    detail,detail_err=run_json([tool["ytdlp_path"],*SAFE_BASE,"--no-playlist",url])
    if detail_err:errors.append({"target":target["id"],"error":"video_detail_probe_failed"});detail={}
   title=(detail or candidate or {}).get("title") or target["name"]
   rec=record(f"youtube-{video_id or target['id']}","youtube_video_metadata",title,status="real_metadata",source_id=target["id"],channel_name=target["name"],video_id=video_id,url=url or target["url"],description=(detail or {}).get("description","")[:1000],published_at=(detail or {}).get("timestamp"),metadata_source="yt_dlp_local_probe",approved_source=True,media_downloaded=False,audio_downloaded=False)
   metadata.append(rec)
   subs=(detail or {}).get("subtitles",{});auto=(detail or {}).get("automatic_captions",{})
   subtitles.append(record(f"subtitle-{video_id or target['id']}","youtube_subtitle_availability",title,status="availability_checked",video_id=video_id,source_url=url or target["url"],manual_subtitle_languages=sorted(subs),automatic_caption_languages=sorted(auto),subtitle_text_imported=False,approval_required=True))
   put("ytdlp",target["id"],{"metadata":rec,"subtitle_availability":subtitles[-1]})
 existing=read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[]);merged={x.get("id"):x for x in existing}
 for item in metadata:
  current=merged.get(item.get("id"),{})
  if current.get("metadata_source")!="youtube_data_api_v3":merged[item.get("id")]=item
 write_json(SUPABASE_READY/"youtube_video_metadata_latest.json",list(merged.values()));write_json(SUPABASE_READY/"youtube_ytdlp_probe_status_latest.json",metadata);write_json(SUPABASE_READY/"youtube_subtitle_availability_latest.json",subtitles)
 cards=read_json(SUPABASE_READY/"youtube_approval_cards_latest.json",[]);title="Approve importing approved subtitle/source text discovered by local yt-dlp probe";cards=[x for x in cards if x.get("title")!=title]+[record("yt-approve-subtitle-import","youtube_approval_card",title,status="ready_for_Ray_review",priority="high",risk_level="medium",approval_required=True)];write_json(SUPABASE_READY/"youtube_approval_cards_latest.json",cards)
 report={"ok":True,"generated_at":now(),"status":"real_metadata_review_active_ytdlp_local" if metadata else tool["status"],"local_ytdlp_available":tool["local_ytdlp_available"],"approved_targets_count":len(targets),"targets_checked":checked,"cache_hits":cache_hits,"metadata_records_created":len(metadata),"subtitle_records_created":len(subtitles),"subtitles_available_count":sum(bool(x.get("manual_subtitle_languages") or x.get("automatic_caption_languages")) for x in subtitles),"errors_sanitized":errors,"cookies_used":False,"video_downloaded":False,"audio_downloaded":False,"media_files_written":False,"restriction_bypass_performed":False,"external_action_performed":False};write_report("youtube_ytdlp_probe","YouTube yt-dlp Approved Probe",report,{"Subtitle availability":subtitles,"Sanitized errors":errors});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--approved-only",action="store_true");p.add_argument("--no-download",action="store_true");a=p.parse_args();r=build(a);print(json.dumps(r,indent=2) if a.json else r);return 0 if r.get("ok") else 2
if __name__=="__main__":raise SystemExit(main())
