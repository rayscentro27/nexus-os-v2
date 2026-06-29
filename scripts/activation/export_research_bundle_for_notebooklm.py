#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,ensure_dirs,now,read_json,write_json,write_report
def build():
 ensure_dirs();outdir=ROOT/"data/exports/notebooklm/research_bundles";outdir.mkdir(parents=True,exist_ok=True)
 sources={"youtube_metadata":read_json(SUPABASE_READY/"youtube_video_metadata_latest.json",[])[:30],"youtube_scores":read_json(SUPABASE_READY/"youtube_research_scores_latest.json",[])[:30],"payment_concepts":read_json(SUPABASE_READY/"payment_repo_concepts_latest.json",[])[:20]}
 bundle={"generated_at":now(),"title":"Nexus approved research bundle","manual_notebooklm_upload_only":True,"contains_real_client_data":False,"sources":sources,"instructions":["Upload manually to an appropriate NotebookLM notebook.","Do not add client PII.","Export approved notes back to data/sources/notebooklm_exports/."],"external_action_performed":False}
 path=outdir/"nexus_research_bundle_latest.json";write_json(path,bundle)
 report={"ok":True,"generated_at":now(),"status":"manual_notebooklm_bundle_ready","bundle_path":str(path.relative_to(ROOT)),"source_groups":len(sources),"source_records":sum(len(x) for x in sources.values()),"consumer_browser_automation":False,"external_action_performed":False}
 write_report("notebooklm_research_bundle","NotebookLM Research Bundle",report,{"Instructions":bundle["instructions"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
