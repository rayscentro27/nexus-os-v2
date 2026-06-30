#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402,F401
TOPICS=["Five signs you are not funding-ready yet","Business profile items lenders may review","How utilization affects readiness","Documents to organize before a readiness review","Why applying too early can hurt","What the $97 readiness review includes","Monthly readiness progress checklist"]
def item(i,topic,format_name):return {"id":f"marketing-{format_name}-{i+1}","title":topic,"format":format_name,"source":"Nexus approved research and readiness workflows","audience":"business owners improving credit/funding readiness","offer_tie_in":"readiness_review_97","CTA":"Request a $97 readiness review after Ray approves this draft.","compliance_notes":"Educational only; no credit, removal, score, or funding guarantees.","approval_required":True,"status":"draft_only_not_published","created_at":now()}
