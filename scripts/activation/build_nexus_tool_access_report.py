#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402
def build():
 audit=read_json(RUNTIME/"cli_capability_audit_latest.json",{});reg=read_json(ROOT/"configs/cli_capability_registry.json",{});tools=reg.get("tools",[]);installed=[x for x in tools if x.get("installed")];connected=[x for x in installed if x.get("connected_nexus_engines")];not_connected=[x for x in installed if not x.get("connected_nexus_engines")];missing=[x["tool_name"] for x in tools if not x.get("installed")]
 recommendations=[]
 if "psql" in missing:recommendations.append("Optional: brew install libpq && brew link --force libpq (Supabase CLI query already covers current need).")
 if "vibe-trading" in missing:recommendations.append("Do not install until trusted package/repository is identified; recovered synthetic adapter already works.")
 report={"ok":True,"generated_at":now(),"status":"tool_access_report_ready","installed_tools":[x["tool_name"] for x in installed],"missing_tools":missing,"connected_tools":[x["tool_name"] for x in connected],"installed_not_connected":[x["tool_name"] for x in not_connected],"internal_safe_tools":[x["tool_name"] for x in tools if x.get("default_access_level")=="internal_safe" and x.get("installed")],"read_only_tools":[x["tool_name"] for x in tools if x.get("default_access_level")=="read_only" and x.get("installed")],"approval_gated_tools":[x["tool_name"] for x in tools if x.get("default_access_level")=="approval_gated" and x.get("installed")],"blocked_actions":sorted({y for x in tools for y in x.get("blocked_commands",[])}),"legacy_capabilities":audit.get("legacy_files",[])[:25],"install_recommendations":recommendations,"do_not_integrate":["live Stripe execution","live Oanda orders","unapproved yt-dlp downloads","consumer NotebookLM browser automation"],"external_action_performed":False};write_report("nexus_tool_access_report","Nexus Tool Access Report",report,{"Install recommendations":recommendations});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
