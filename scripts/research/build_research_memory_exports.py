#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import ROOT,RUNTIME,SUPABASE_READY,load_scores,now,read_json,write_json,write_report
def build():
 sources=load_scores();opps=read_json(SUPABASE_READY/"research_opportunities_latest.json",[]);memory={"generated_at":now(),"source_count":len(sources),"opportunity_count":len(opps),"lane_summary":{},"top_opportunities":opps[:25],"safety":"Internal research memory only; no publish, contact, trade, charge, or client guidance."}
 for item in sources:memory["lane_summary"][item["lane"]]=memory["lane_summary"].get(item["lane"],0)+1
 write_json(RUNTIME/"research_memory_latest.json",memory);write_json(ROOT/"data/exports/notebooklm/research_bundles/final_daily_research_memory_latest.json",memory);report={"ok":True,"generated_at":now(),"status":"research_memory_exports_ready","sources_exported":len(sources),"opportunities_exported":len(opps),"notebooklm_bundle_created":True,"external_action_performed":False};write_report("research_memory_exports","Research Memory Exports",report,{"Lane summary":memory["lane_summary"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
