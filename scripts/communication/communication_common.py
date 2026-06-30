#!/usr/bin/env python3
from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402,F401
LANES=["onboarding","credit_repair","business_funding_readiness","grants","business_credit","trading_education","payment_confirmation","lead_reactivation","document_reminder","abandoned_checkout","appointment_follow_up"]
def ident(prefix,value):return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:14]}"
def draft(lane):
 labels={"onboarding":"Welcome and next-step overview","credit_repair":"Credit workflow progress explanation","business_funding_readiness":"Funding-readiness next steps","grants":"Grant preparation update","business_credit":"Business-credit profile checklist","trading_education":"Demo trading education follow-up","payment_confirmation":"Test payment confirmation draft","lead_reactivation":"Readiness review reactivation","document_reminder":"Missing document reminder","abandoned_checkout":"$97 Checkout follow-up","appointment_follow_up":"Readiness review appointment follow-up"}
 return {"id":ident("message",lane),"tenant_id":"tenant_demo_goclear","client_id":"synthetic_or_unassigned","category":"message_draft","lane":lane,"title":labels[lane],"audience":"client_or_prospect_after_Ray_selection","purpose":labels[lane],"risk_level":"medium" if lane in {"credit_repair","business_funding_readiness","payment_confirmation"} else "low","required_approval":True,"suggested_cta":"Review your secure Nexus next-step checklist.","source_reason":"Operating communication template registry","status":"draft_only_not_sent","email_sent":False,"sms_sent":False,"created_at":now()}
