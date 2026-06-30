#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from final_research_common import SUPABASE_READY,discover_sources,now,write_json,write_report
def build():
 items=discover_sources();lanes={x["lane"] for x in items};write_json(SUPABASE_READY/"research_sources_latest.json",items);report={"ok":True,"generated_at":now(),"status":"broad_safe_source_discovery_active","sources_discovered":len(items),"lanes_active":len(lanes),"lane_counts":{lane:sum(x["lane"]==lane for x in items) for lane in sorted(lanes)},"approved_sources":sum(x["approved_seed"] for x in items),"unapproved_sources_ingested":0,"network_fetch_performed":False,"external_action_performed":False};write_report("research_source_discovery","Research Source Discovery",report,{"Lane counts":report["lane_counts"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--safe-internal",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
