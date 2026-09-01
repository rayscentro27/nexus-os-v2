"""Bounded, no-spend Growth Validation Loop for accepted opportunities.

This module prepares and measures internal/organic validation. It never sends
outreach, publishes, spends, charges, or treats projections as demand.
"""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any
from nexus_agent_platform.governed import persistence
from .contracts import assign_work_order, build_work_order, complete_work_order

EVENTS=("VISIT","LEAD","QUALIFIED","BOOKING_INTENT","SERVICE_INTENT","MEMBERSHIP_INTEREST","OBJECTION")
ALLOWED_STATUSES={"ACCEPT_FOR_VALIDATION","VALIDATING"}
def now(): return datetime.now(timezone.utc).isoformat()
def fp(value): return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()[:20]
def first_opportunity():
    return next((x for x in persistence.read_records("opportunities") if x.get("schema_version")=="nexus.business-opportunity.v1" and x.get("status") in ALLOWED_STATUSES), None)
def validation_plan(opportunity:dict[str,Any])->dict[str,Any]:
    oid=opportunity["opportunity_id"]
    return {"plan_id":"growth_plan_"+fp(oid),"opportunity_id":oid,"status":"READY_FOR_GOVERNED_VALIDATION","mode":"NO_SPEND_ORGANIC_MEASUREMENT","offer":{"entry":"mobile interior/exterior detail validation offer","core":"scheduled full detail","upsell":"multi-vehicle/fleet package","membership":"monthly maintenance hypothesis"},"funnel":["TRAFFIC","LEAD","QUALIFICATION","BOOKING","SERVICE","FOLLOW_UP","MEMBERSHIP_REPEAT"],"measurement_events":list(EVENTS),"provisional_thresholds":{"lead_rate":"define after baseline","booking_rate":"define after baseline","membership_interest":"observe; no minimum claimed","average_ticket":"record only when real service occurs","CAC":"UNKNOWN until authorized paid test"},"prohibited_actions":["ad_spend","social_publishing","email_outreach","sms_outreach","payment_collection","external_customer_contact_without_approval"],"created_at":now()}
def record_event(plan_id:str,event_type:str,source:str="operator_input",count:int=1,metadata:dict[str,Any]|None=None)->dict[str,Any]:
    if event_type not in EVENTS: raise ValueError("unknown_validation_event")
    if count<0: raise ValueError("event_count_must_be_nonnegative")
    event_id="event_"+fp({"plan_id":plan_id,"event_type":event_type,"source":source,"metadata":metadata or {}})
    row={"event_id":event_id,"plan_id":plan_id,"event_type":event_type,"source":source,"count":count,"metadata":metadata or {},"observed":True,"created_at":now()}
    if not any(x.get("event_id")==event_id for x in persistence.read_records("metrics")): persistence.append_record("metrics",row)
    return row
def aggregate(plan_id:str)->dict[str,Any]:
    rows=[x for x in persistence.read_records("metrics") if x.get("plan_id")==plan_id and x.get("event_type") in EVENTS]
    counts={e:sum(int(x.get("count",0)) for x in rows if x.get("event_type")==e) for e in EVENTS}
    visits=counts["VISIT"]; leads=counts["LEAD"]; qualified=counts["QUALIFIED"]; bookings=counts["BOOKING_INTENT"]
    return {"plan_id":plan_id,"sample_status":"NO_REAL_VALIDATION_DATA" if not rows else "OBSERVED_SAMPLE_INSUFFICIENT","counts":counts,"lead_rate":round(leads/visits,4) if visits else None,"qualification_rate":round(qualified/leads,4) if leads else None,"booking_intent_rate":round(bookings/qualified,4) if qualified else None,"cac":"UNKNOWN","revenue":None,"retention":None,"source":"observed_events_only","updated_at":now()}
def run_growth_validation()->dict[str,Any]:
    opportunity=first_opportunity()
    if not opportunity: raise RuntimeError("accepted_opportunity_missing")
    plan=validation_plan(opportunity); existing_plan=next((x for x in persistence.read_records("business_research") if x.get("type")=="GROWTH_VALIDATION_PLAN" and x.get("opportunity_id")==opportunity["opportunity_id"]),None)
    if existing_plan: plan=existing_plan.get("result",plan)
    else: persistence.append_record("business_research",{"research_id":plan["plan_id"],"type":"GROWTH_VALIDATION_PLAN","opportunity_id":opportunity["opportunity_id"],"result":plan,"created_at":now()})
    prior=next((x for x in persistence.read_records("work_orders") if x.get("work_type")=="growth_validation" and x.get("inputs",{}).get("opportunity_id")==opportunity["opportunity_id"] and x.get("status")=="COMPLETED"),None)
    if prior: work=prior
    else:
        work=build_work_order(goal_id="goal_revenue_opportunities",work_type="growth_validation",owner_specialist="GROWTH",inputs={"opportunity_id":opportunity["opportunity_id"],"plan_id":plan["plan_id"],"mode":"NO_SPEND_ORGANIC_MEASUREMENT"},authority_required="internal_read_only",cost_budget={"max_usd":0},retry_budget={"max_attempts":2}); work=assign_work_order(work,required_capabilities=("analytics",)); work=complete_work_order(work,{"status":"PASS","plan_id":plan["plan_id"],"verification":"bounded measurement contract persisted","external_action_performed":False},receipt_ref="pending"); receipt="growth_receipt_"+fp(work["work_order_id"]); work["receipt_refs"]=[receipt]; persistence.append_record("business_receipts",{"receipt_id":receipt,"work_order_id":work["work_order_id"],"opportunity_id":opportunity["opportunity_id"],"stage":"GROWTH_VALIDATION","verified":True,"external_action_performed":False,"created_at":now()}); persistence.append_record("work_orders",work)
    summary=aggregate(plan["plan_id"]); persistence.append_record("metrics",{"metric_id":"growth_metrics_"+fp(plan["plan_id"]),"opportunity_id":opportunity["opportunity_id"],"plan_id":plan["plan_id"],"type":"GROWTH_VALIDATION_METRICS","result":summary,"created_at":now()}); persistence.append_record("outcomes",{"outcome_id":"growth_outcome_"+fp(plan["plan_id"]),"opportunity_id":opportunity["opportunity_id"],"plan_id":plan["plan_id"],"status":summary["sample_status"],"real_world_validation":False,"created_at":now()})
    return {"status":"PASS","opportunity_id":opportunity["opportunity_id"],"plan":plan,"work_order":work,"metrics":summary,"evidence_state":"NO_REAL_VALIDATION_DATA","external_actions":{"ad_spend":False,"publishing":False,"email_outreach":False,"sms_outreach":False,"payments":False},"nova_return":{"what_changed":"bounded no-spend Growth validation is ready","evidence":summary,"recommendation":"collect approved real evidence before changing the opportunity decision"}}
