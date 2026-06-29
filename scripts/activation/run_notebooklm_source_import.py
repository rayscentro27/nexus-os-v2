#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from youtube_engine_common import ROOT,SUPABASE_READY,ensure_dirs,now,record,write_json,write_report
def build():
 ensure_dirs();paths=[]
 for folder in (ROOT/"data/sources/notebooklm_exports",ROOT/"data/sources/notebooklm_notes"):
  paths.extend([p for p in folder.iterdir() if p.is_file() and p.name.lower() != "readme.md" and p.suffix.lower() in {".txt",".md",".json"}])
 sources=[]
 for i,p in enumerate(sorted(paths),1):
  text=p.read_text(errors="replace");lower=text.lower();domains=[x for x in ("credit repair","business funding","client portal","content","social","affiliate","partner","trading") if x in lower]
  sources.append(record(f"notebooklm-{i}","notebooklm_source",p.stem,status="imported_local_approved_source",source_file=str(p.relative_to(ROOT)),format=p.suffix.lower().lstrip("."),character_count=len(text),domains=domains,content_excerpt=text[:500],approval_required=True))
 opps=[record(f"notebooklm-opportunity-{i+1}","notebooklm_opportunity",f"Review NotebookLM note: {x['title']}",source_item_id=x["id"],opportunity_types=["monetization","client_workflow","content_social","partner"],approval_required=True) for i,x in enumerate(sources)]
 cards=[record(f"notebooklm-approval-{i+1}","approval_card",f"Approve NotebookLM source: {x['title']}",source_item_id=x["id"],status="pending_Ray_review",risk_level="medium",automation_level="approval_required",approval_required=True) for i,x in enumerate(sources)]+[record("approve-notebooklm-selected-import","approval_card","Approve NotebookLM selected notebook import workflow in Nexus v2",status="pending_Ray_review",risk_level="medium",automation_level="approval_required",approval_required=True)]
 write_json(SUPABASE_READY/"notebooklm_sources_latest.json",sources);write_json(SUPABASE_READY/"notebooklm_opportunities_latest.json",opps);write_json(SUPABASE_READY/"notebooklm_approval_cards_latest.json",cards)
 report={"ok":True,"generated_at":now(),"status":"local_import_complete" if sources else "manual_import_folder_ready","sources_imported":len(sources),"opportunities_created":len(opps),"approval_cards_created":len(cards),"consumer_browser_automation":False,"live_database_inserted":False,"external_action_performed":False};write_report("notebooklm_source_import","NotebookLM Source Import",report,{"Sources":sources,"Approvals":cards});return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
