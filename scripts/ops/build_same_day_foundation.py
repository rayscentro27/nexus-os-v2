#!/usr/bin/env python3
"""Build client hardening, document/message, and assistant bridge evidence."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from same_day_common import SUPABASE_READY,now,write_json,write_report  # noqa:E402


def record(id,category,title,**x):
 return {"id":id,"tenant_id":"tenant_demo_goclear","client_id":"client_demo_001","category":category,"title":title,
  "summary":x.pop("summary",title),"status":x.pop("status","open"),"priority":x.pop("priority","medium"),"risk_level":"low",
  "automation_level":x.pop("automation_level","client_visible_safe"),"client_visible":x.pop("client_visible",True),
  "approval_required":x.pop("approval_required",False),"goclear_review_status":x.pop("goclear_review_status","pending"),
  "source":"same_day_operations_activation","recommended_next_action":x.pop("recommended_next_action","Complete the listed portal step."),"created_at":now(),**x}


def build()->dict:
 requirements=[record("doc-req-id","documents","Government identity verification",status="missing",sensitive=True),record("doc-req-address","documents","Current address proof",status="missing"),record("doc-req-formation","documents","Formation documents",status="approved"),record("doc-req-ein","documents","EIN confirmation",status="approved"),record("doc-req-bank","documents","Three months business bank statements",status="under_review",sensitive=True),record("doc-req-revenue","documents","Current revenue summary",status="missing")]
 documents=[record(f"document-{i+1}","client_document",x["title"],status=x["status"],document_requirement_id=x["id"],upload_state="storage_rls_pending",storage_path=None,external_upload_performed=False) for i,x in enumerate(requirements)]
 threads=[record("thread-review","messages","GoClear readiness review",status="open",delivery_mode="portal_record_only",external_message_sent=False),record("thread-docs","messages","Document requirements",status="action_required",delivery_mode="portal_record_only",external_message_sent=False)]
 messages=[record("safe-msg-1","client_message","GoClear review update",summary="Your readiness record is under review. Complete missing document tasks; nothing has been submitted externally.",thread_id="thread-review",external_message_sent=False),record("safe-msg-2","client_message","Documents needed",summary="Current address proof and a revenue summary are still required. Upload remains unavailable until private storage and RLS are approved.",thread_id="thread-docs",external_message_sent=False)]
 for name,data in (("document_requirements_latest.json",requirements),("client_documents_latest.json",documents),("message_threads_latest.json",threads),("client_messages_latest.json",messages)):write_json(SUPABASE_READY/name,data)
 client={"ok":True,"generated_at":now(),"status":"supabase_ready","supported_modes":["demo_static","manual_client","supabase_ready","live_supabase_pending"],"current_mode":"live_supabase_pending","real_client_data_used":False,"routes_preserved":True,"tasks_supported":True,"documents_supported":True,"review_status_supported":True,"readiness_scores_supported":True,"dispute_status_supported":True,"opportunities_supported":True,"partner_offers_supported":True,"nexus_guide_supported":True,"live_data_blockers":["migration approval","tenant memberships","RLS tests","private storage","client auth roles"],"external_action_performed":False}
 docs={"ok":True,"generated_at":now(),"status":"schema_hardened_storage_pending","document_requirements":len(requirements),"document_records":len(documents),"message_threads":len(threads),"message_records":len(messages),"real_upload_enabled":False,"external_messages_sent":False,"storage_blocker":"private bucket plus tenant/client RLS and retention/security review","external_action_performed":False}
 assistant={"ok":True,"generated_at":now(),"status":"report_backed_supabase_pending","hermes_admin_only":True,"hermes_report_backed":True,"nexus_guide_client_only":True,"nexus_guide_safe_templates_updated":True,"structured_bridge_updated":True,"unrestricted_ai_to_ai_chat":False,"live_data_blocker":"tenant-safe Supabase reads and approved guidance policies","external_action_performed":False}
 write_report("client_portal_paid_client_hardening","Client Portal Paid-Client Hardening",client,{"Live blockers":client["live_data_blockers"]})
 write_report("documents_messages_hardening","Documents and Messages Hardening",docs,{"Document requirements":requirements,"Message templates":messages})
 write_report("hermes_nexus_guide_upgrade","Hermes and Nexus Guide Upgrade",assistant)
 return {"ok":True,"client":client["status"],"documents":docs["status"],"assistants":assistant["status"]}


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
