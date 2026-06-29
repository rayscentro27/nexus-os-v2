#!/usr/bin/env python3
"""Safe v2 wrapper for manually exported NotebookLM research; no auth/browser/DB writes."""
from __future__ import annotations
import hashlib
from youtube_engine_common import now,record
DOMAIN_MAP={"Nexus Grants":"grants","Nexus Trading":"trading","Nexus Funding":"funding","Nexus Credit":"credit","Nexus Business Opportunities":"business_opportunities","Nexus Marketing":"marketing","Nexus Operations":"operations"}
def proposed_record(notebook_name:str,summary:str,source_files:list[str]):
 key=hashlib.sha256(f"{notebook_name}|{summary[:240]}|{'|'.join(source_files)}".encode()).hexdigest()[:24]
 return record(f"notebooklm-{key}","notebooklm_source",notebook_name,status="proposed_manual_review",domain=DOMAIN_MAP.get(notebook_name,"operations"),summary=summary[:4000],source_files=source_files[:50],dedup_key=key,approval_required=True,consumer_browser_automation=False,database_inserted=False)
