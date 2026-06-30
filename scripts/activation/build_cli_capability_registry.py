#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402

INTERNAL={"git","node","npm","npx","python3","pip3","pnpm","yarn","jq","openssl","sqlite3","ffmpeg","imagemagick","magick","tesseract","codex","claude","opencode","gemini","ollama","notebooklm_legacy_adapter","vibe_recovered_adapter"}
READ_ONLY={"gh","curl","wget","supabase","netlify","vercel","docker","colima","orb","psql","yt-dlp","playwright","chromium","chrome","notebooklm","oanda"}
APPROVAL={"stripe","resend","facebook","instagram","vibe-trading","vibe_trading_python","oanda_demo_api_connector"}

def classify(item):
 name=item["tool_name"]
 if not item["installed"]: level="unavailable"
 elif name in INTERNAL: level="internal_safe"
 elif name in READ_ONLY: level="read_only"
 else: level="approval_gated"
 engines=[]
 if name in {"yt-dlp","ffmpeg","tesseract"}:engines=["research","youtube"]
 elif name in {"supabase","psql"}:engines=["database","client_portal"]
 elif name in {"stripe"}:engines=["payments","onboarding"]
 elif name in {"oanda","oanda_demo_api_connector","vibe-trading","vibe_trading_python","vibe_recovered_adapter"}:engines=["trading"]
 elif name in {"git","gh"}:engines=["repo_research","deployment"]
 elif name in {"netlify","vercel"}:engines=["deployment"]
 elif name in {"notebooklm","notebooklm_legacy_adapter"}:engines=["research"]
 elif name in {"codex","claude","opencode","gemini","ollama"}:engines=["internal_ai_tools"]
 safe=[item["detection_command"]] if item.get("detection_command") else []
 blocked=[]
 if name=="stripe":blocked=["stripe commands with --live","live charges","live payment links"]
 elif name=="supabase":blocked=["db reset --linked","db push --include-all","destructive SQL"]
 elif name=="yt-dlp":blocked=["video download","audio download","cookies","unapproved targets"]
 elif name in {"oanda","oanda_demo_api_connector","vibe-trading","vibe_trading_python","vibe_recovered_adapter"}:blocked=["live/funded orders","live account use"]
 elif name in {"resend","facebook","instagram"}:blocked=["send or publish without Ray approval"]
 return {**item,"safe_commands":safe,"blocked_commands":blocked,"requires_approval":level=="approval_gated" or name in {"supabase","netlify","vercel","gh","oanda"},"external_action_possible":name in {"gh","curl","wget","supabase","netlify","vercel","stripe","yt-dlp","playwright","chrome","chromium","oanda","resend","facebook","instagram"},"default_access_level":level,"connected_nexus_engines":engines,"recommended_next_action":"Use only listed safe commands." if item["installed"] else "Install only if a current Nexus engine requires it.","notes":"Detection and version only; credentials were not read or printed."}

def build():
 audit=read_json(RUNTIME/"cli_capability_audit_latest.json",{});records=[classify(x) for x in audit.get("tools",[])]
 config={"version":1,"generated_at":now(),"tools":records};write_json(ROOT/"configs/cli_capability_registry.json",config)
 access={"version":1,"generated_at":now(),"default_deny_external":True,"tools":[{"tool_name":x["tool_name"],"access_level":x["default_access_level"],"connected_nexus_engines":x["connected_nexus_engines"],"requires_approval":x["requires_approval"],"safe_commands":x["safe_commands"],"blocked_commands":x["blocked_commands"]} for x in records]};write_json(ROOT/"configs/nexus_tool_access_registry.json",access);write_json(SUPABASE_READY/"nexus_tool_access_registry_latest.json",access["tools"])
 report={"ok":bool(records),"generated_at":now(),"status":"cli_registry_built","tools":records,"tools_count":len(records),"installed_count":sum(x["installed"] for x in records),"internal_safe_count":sum(x["default_access_level"]=="internal_safe" for x in records),"read_only_count":sum(x["default_access_level"]=="read_only" for x in records),"approval_gated_count":sum(x["default_access_level"]=="approval_gated" for x in records),"unavailable_count":sum(x["default_access_level"]=="unavailable" for x in records),"external_action_performed":False};write_report("cli_capability_registry","CLI Capability Registry",report,{"Access summary":{k:report[k] for k in ("installed_count","internal_safe_count","read_only_count","approval_gated_count","unavailable_count")}});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
