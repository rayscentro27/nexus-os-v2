#!/usr/bin/env python3
"""Build factual monetization-intelligence links from stored V1 evidence.

No recommendation, ranking, publishing, or work-order authority exists here.
All durable records reuse research_sources and research_questions.
"""
from __future__ import annotations

import hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb
from nexus_agent_platform.content_intelligence import persist_signal
from nexus_agent_platform.proactive_discovery import run_lane


def now(): return datetime.now(timezone.utc).isoformat()


def get_sources(source_type: str) -> list[dict[str, Any]]:
    code, rows = sb.get("research_sources", f"select=id,title,url,author,metadata,source_type&source_type=eq.{sb.q(source_type)}&limit=500")
    return rows if code == 200 and isinstance(rows, list) else []


def source_payload(row):
    return (row.get("metadata") or {}).get("raw_signal") or (row.get("metadata") or {}).get("raw_discovery") or {}


def find_prior_findings(topic: str) -> list[dict[str, Any]]:
    code, rows = sb.get("research_findings", "select=id,finding,alpha_decision,recommendation,created_at&limit=100")
    if code != 200 or not isinstance(rows, list): return []
    return [x for x in rows if topic.lower() in json.dumps(x).lower()]


def write_record(record_type: str, identity: str, title: str, payload: dict[str, Any]) -> dict[str, Any]:
    return persist_signal(record_type, title, payload.get("url"), payload.get("provider") or payload.get("creator_name") or "Nexus", identity, payload)


def question(question: str, topic: str) -> dict[str, Any]:
    code, rows = sb.insert("research_questions", {"question": question, "requester": "monetization_intelligence_v1", "department": "RESEARCH", "status": "OPEN", "priority": 50, "next_action": "Route through deterministic proactive discovery; no direct AI search."})
    if code not in (200, 201) or not rows: return {"question": question, "write": False, "readback": False}
    qid = rows[0].get("id")
    rc, back = sb.get("research_questions", f"select=id,question,status&id=eq.{sb.q(qid)}")
    return {"question": question, "question_id": qid, "topic": topic, "write": True, "readback": rc == 200 and bool(back)}


def topic_package(topic: str, content: list[dict[str, Any]], trends: list[dict[str, Any]], affiliates: list[dict[str, Any]], offers: list[dict[str, Any]], prior: list[dict[str, Any]]) -> dict[str, Any]:
    package_id = "monetization_package_" + hashlib.sha256(topic.encode()).hexdigest()[:24]
    payload = {"package_id": package_id, "topic": topic, "content_source_ids": [x.get("id") for x in content],
               "creator_source_ids": [], "trend_source_ids": [x.get("id") for x in trends],
               "affiliate_source_ids": [x.get("id") for x in affiliates], "owned_offer_source_ids": [x.get("id") for x in offers],
               "prior_finding_ids": [x.get("id") for x in prior], "recommendation_status": "NOT_REQUESTED", "created_at": now()}
    result = write_record("MONETIZATION_INPUT_PACKAGE", package_id, f"Monetization input package: {topic}", payload)
    payload.update({"source_id": result.get("source_id"), "readback": result.get("readback")})
    return payload


def build_topic(topic: str, content_rows, trend_rows, affiliate_rows, offer_rows, prior_rows):
    content = [x for x in content_rows if topic.lower() in json.dumps(source_payload(x)).lower()]
    # The online-business V1 content query is present in raw_signal; funding rows
    # likewise.  Trend records carry an explicit topic.
    trends = [x for x in trend_rows if topic.lower() in json.dumps(source_payload(x)).lower()]
    if topic == "business funding":
        aff = [x for x in affiliate_rows if "fund" in json.dumps(source_payload(x)).lower()]
        need = "Businesses and entrepreneurs seeking funding options, readiness, and application guidance."
    else:
        aff = [x for x in affiliate_rows if not "fund" in json.dumps(source_payload(x)).lower()]
        need = "Aspiring entrepreneurs seeking practical online-business models, tools, and beginner guidance."
    offers = []
    for row in offer_rows:
        raw = source_payload(row)
        blob = json.dumps(raw).lower()
        if topic == "business funding" and any(k in blob for k in ("fund", "credit", "grant", "readiness")): offers.append(row)
        if topic != "business funding" and any(k in blob for k in ("affiliate", "business", "consult", "education")): offers.append(row)
    package = topic_package(topic, content, trends, aff, offers, prior_rows)
    relations=[]
    evidence=[x.get("id") for x in content+trends+aff+offers if x.get("id")]
    for row in offers:
        raw=source_payload(row); oid=raw.get("offer_id")
        payload={"relationship_id": "need-offer-"+hashlib.sha256((topic+str(oid)).encode()).hexdigest()[:20], "topic":topic,"need_statement":need,"need_id":"need-"+hashlib.sha256(need.encode()).hexdigest()[:16],"solution_id":oid,"solution_type":"OWNED_OFFER","match_explanation":"Configured offer language overlaps the stored topic/need evidence; this is a factual relationship, not a promotion decision.","evidence_source_ids":evidence,"verification_status":"CONFIGURED_CATALOG","created_at":now(),"recommendation_status":"NOT_REQUESTED"}
        result=write_record("MONETIZATION_RELATIONSHIP",payload["relationship_id"],f"Need to owned offer: {topic}",payload); payload["source_id"]=result.get("source_id");payload["readback"]=result.get("readback");relations.append(payload)
    for row in aff:
        raw=source_payload(row); oid=raw.get("program_name") or row.get("id")
        payload={"relationship_id":"need-affiliate-"+hashlib.sha256((topic+str(oid)).encode()).hexdigest()[:20],"topic":topic,"need_statement":need,"need_id":"need-"+hashlib.sha256(need.encode()).hexdigest()[:16],"solution_id":oid,"solution_type":"AFFILIATE_OFFER","match_explanation":"Official program page is related to the topic; commercial terms remain pending verification.","evidence_source_ids":evidence,"verification_status":raw.get("verification_status","VERIFICATION_PENDING"),"created_at":now(),"recommendation_status":"NOT_REQUESTED"}
        result=write_record("MONETIZATION_RELATIONSHIP",payload["relationship_id"],f"Need to affiliate program: {topic}",payload);payload["source_id"]=result.get("source_id");payload["readback"]=result.get("readback");relations.append(payload)
    for row in content:
        raw=source_payload(row); urls=re.findall(r"https?://[^\s)]+", raw.get("description") or "")
        if urls:
            for url in urls[:10]:
                payload={"creator_id":raw.get("channel_id"),"creator_name":raw.get("channel"),"content_id":raw.get("video_id"),"monetization_method":"LINK_IN_DESCRIPTION","evidence":{"url":url,"video_title":raw.get("title")},"source_id":row.get("id"),"observed_at":now(),"verification_status":"OBSERVED","recommendation_status":"NOT_REQUESTED"}
                result=write_record("CREATOR_MONETIZATION_OBSERVATION",f"creator-link:{raw.get('video_id')}:{url}",f"Creator monetization observation: {raw.get('video_id')}",payload);payload["readback"]=result.get("readback");relations.append(payload)
    return {"topic":topic,"package":package,"content":content,"trends":trends,"affiliates":aff,"offers":offers,"need":need,"relations":relations}


def main():
    report=json.load(open(ROOT/"reports/research/NEXUS_CONTENT_TREND_MONETIZATION_V1_2026-09-29.json"))
    content_rows=get_sources("YOUTUBE_CONTENT_SIGNAL"); trend_rows=get_sources("TREND_SIGNAL"); affiliate_rows=get_sources("AFFILIATE_PROGRAM"); offer_rows=get_sources("OWNED_OFFER_CATALOG")
    prior=[]
    for topic in ("business funding","online business"):
        prior.extend(find_prior_findings(topic))
    topics=[build_topic("business funding",content_rows,trend_rows,affiliate_rows,offer_rows,find_prior_findings("business funding")),build_topic("online business",content_rows,trend_rows,affiliate_rows,offer_rows,find_prior_findings("online business"))]
    followups=[question("Verify official affiliate or partner terms for Canary Financial business funding program.","business funding"),question("Identify observable monetization methods and official program pages associated with online business creators.","online business")]
    loop=[]
    for q in followups:
        if q["write"]:
            result=run_lane(q["question"],"WEB_SEARCH",window_days=30,bounds={"max_queries":1,"max_results_per_query":3,"max_new_sources":3,"max_runtime_per_lane":30})
            loop.append({"question_id":q.get("question_id"),"discovery_run_id":result.get("discovery_run_id"),"status":result.get("status"),"readback":result.get("supabase_readback"),"sources_appended":result.get("sources_appended_to_fifo",0)})
    rels=[r for t in topics for r in t["relations"]]
    solution_relationships=[r for r in rels if r.get("solution_type")]
    creator_observations=[r for r in rels if r.get("monetization_method")]
    readbacks=[t["package"]["readback"] for t in topics]+[r.get("readback") for r in rels]+[x["readback"] for x in followups]+[x["readback"] for x in loop]
    payload={"status":"PASS_REAL" if topics and solution_relationships and all(readbacks) else "PARTIAL_REAL","created_at":now(),"topics":topics,"followups":followups,"followup_loop":loop,"real_monetization_relationships_created":len(solution_relationships),"real_creator_monetization_observations_created":len(creator_observations),"real_followup_questions_created":len(followups),"supabase_readback_pass":all(readbacks),"recommendation_layer_added":False,"company_recommendations_created":0,"priority_rankings_created":0,"autonomous_work_orders_created":0,"merch_products_created":0,"affiliate_links_published":0,"content_published":0,"universal_fifo_changed":False,"oracle_hermes_changed":False,"clickbank_offers_ingested":0,"rights_status":"NOT_CHECKED"}
    out=ROOT/"reports/research/NEXUS_MONETIZATION_INTELLIGENCE_V1_2026-09-29.json";out.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    md=ROOT/"reports/research/NEXUS_MONETIZATION_INTELLIGENCE_V1_2026-09-29.md";md.write_text("# Nexus Monetization Intelligence V1\n\n"+"\n".join(f"{k.upper()}={v}" for k,v in payload.items() if k not in {"topics","followups","followup_loop"})+"\n")
    print(json.dumps({k:payload[k] for k in ("status","real_monetization_relationships_created","real_followup_questions_created","supabase_readback_pass")},indent=2));return 0 if payload["status"] in {"PASS_REAL","PARTIAL_REAL"} else 1

if __name__ == "__main__": raise SystemExit(main())
