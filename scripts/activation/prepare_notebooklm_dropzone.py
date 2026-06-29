#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,now,write_report
def build():
 base=ROOT/"data/sources/notebooklm_exports";pending=base/"pending";approved=base/"approved";notes=ROOT/"data/sources/notebooklm_notes";notes_approved=notes/"approved"
 for p in (pending,approved,notes_approved):p.mkdir(parents=True,exist_ok=True)
 template=pending/"selected_notebook_export.template.json"
 if not template.exists():template.write_text(json.dumps({"notebook_name":"Nexus Funding","domain":"funding","summary":"Paste approved NotebookLM summary here.","insights":[],"source_urls":[],"approved_by":"Ray","internal_review_only":True},indent=2)+"\n")
 files=[p for p in list(approved.iterdir())+list(notes_approved.iterdir()) if p.is_file() and p.suffix.lower() in {".txt",".md",".json"}]
 instructions=["Export/copy the selected NotebookLM summary as .txt, .md, or .json.","Place it in data/sources/notebooklm_exports/approved/.","Do not include client PII or credentials.","Run python3 scripts/activation/run_notebooklm_source_import.py --json."]
 report={"ok":True,"generated_at":now(),"status":"approved_sources_ready" if files else "dropzone_ready_waiting_for_export","approved_export_path":str(approved.relative_to(ROOT)),"approved_notes_path":str(notes_approved.relative_to(ROOT)),"template_path":str(template.relative_to(ROOT)),"allowed_types":[".txt",".md",".json"],"approved_source_count":len(files),"instructions":instructions,"consumer_browser_automation":False,"external_action_performed":False};write_report("notebooklm_dropzone","NotebookLM Dropzone",report,{"Instructions":instructions});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
