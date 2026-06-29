#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,now,parse_env,read_json,write_json,write_report  # noqa:E402,F401

TARGETS=ROOT/"configs"/"youtube_research_channels.json"
CACHE=ROOT/"data"/"cache"/"youtube"

def approved_targets():
 return [x for x in read_json(TARGETS,{}).get("channels",[]) if x.get("enabled") and x.get("approved_by_ray") and x.get("url")]

def env_values():
 values={}
 for path in (ROOT/".env",ROOT/".env.local",ROOT/".env.nexus.recovered.local"):values.update(parse_env(path))
 return values

def api_key_status():
 values=env_values();names=["YOUTUBE_API_KEY","YOUTUBE_DATA_API_KEY","GOOGLE_API_KEY","GOOGLE_CLOUD_API_KEY"]
 present=[x for x in names if values.get(x)]
 return {"present":bool(present),"detected_key_names":present,"selected_key_name":present[0] if present else None,"value":values.get(present[0],"") if present else ""}

def stable_id(prefix,value):return f"{prefix}-{hashlib.sha256(str(value).encode()).hexdigest()[:16]}"

def record(id,category,title,**extra):
 return {"id":id,"tenant_id":"tenant_demo_goclear","client_id":"synthetic_research_only","category":category,"title":title,"summary":extra.pop("summary",title),"status":extra.pop("status","internal_active"),"priority":extra.pop("priority","medium"),"risk_level":extra.pop("risk_level","low"),"automation_level":extra.pop("automation_level","internal_active"),"client_visible":False,"approval_required":extra.pop("approval_required",False),"source":"approved_youtube_research","recommended_next_action":extra.pop("recommended_next_action","Review internally."),"created_at":now(),**extra}

def ensure_dirs():
 for p in (CACHE/"api_metadata",CACHE/"ytdlp_metadata",ROOT/"data/sources/youtube_transcripts",ROOT/"data/sources/notebooklm_exports",ROOT/"data/sources/notebooklm_notes",ROOT/"data/exports/notebooklm/youtube"):p.mkdir(parents=True,exist_ok=True)
