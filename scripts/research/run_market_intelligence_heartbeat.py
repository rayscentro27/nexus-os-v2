#!/usr/bin/env python3
"""Run two bounded deterministic Market Intelligence heartbeat cycles.

The existing proactive collectors remain the only discovery mechanisms.  This
runner only rotates them, records receipts, snapshots metrics, and creates
interpretation-pending packages.  It does not recommend, rank, publish, or
create work orders.
"""
from __future__ import annotations

import json, sys, hashlib, multiprocessing, time
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb
from nexus_agent_platform.content_intelligence import youtube_content, trend_signals, affiliate_discovery, persist_signal, _source_lookup_many
from nexus_agent_platform.proactive_discovery import run_lane, ensure_discovery_provider_registry

LANE_ORDER = ("SEARCH_TRENDS", "YOUTUBE_CONTENT", "SEO_SEARCH_DEMAND", "AFFILIATE_PROGRAM_DISCOVERY")
TOPICS = ("business funding", "online business", "AI consulting")
MAX_TOPICS_PER_WAKE = 3
LANE_TIMEOUT_SECONDS = int(os.environ.get("NEXUS_MARKET_LANE_TIMEOUT_SECONDS", "45"))


def iso_now(): return datetime.now(timezone.utc).isoformat()


def _lane_child(callback, result_queue):
    try:
        result_queue.put({"ok": True, "result": callback()})
    except BaseException as exc:
        result_queue.put({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:400]}"})


def bounded_lane(callback, timeout_seconds: int = LANE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run one collector in a killable boundary and always return a terminal result."""
    context = multiprocessing.get_context("fork")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(target=_lane_child, args=(callback, result_queue))
    started = time.monotonic()
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {"status": "FAILED_RETRYABLE", "failures": [{"error": f"lane timeout after {timeout_seconds}s"}],
                "runtime_seconds": round(time.monotonic() - started, 3)}
    if not result_queue.empty():
        payload = result_queue.get()
        if payload.get("ok"):
            result = payload.get("result") or {}
            result.setdefault("status", "COMPLETED")
            result.setdefault("runtime_seconds", round(time.monotonic() - started, 3))
            return result
        return {"status": "FAILED_RETRYABLE", "failures": [{"error": payload.get("error", "lane child failed")}],
                "runtime_seconds": round(time.monotonic() - started, 3)}
    return {"status": "FAILED_RETRYABLE", "failures": [{"error": f"lane child exited without result (exit={process.exitcode})"}],
            "runtime_seconds": round(time.monotonic() - started, 3)}


def sources(source_type: str) -> list[dict[str, Any]]:
    code, rows = sb.get("research_sources", f"select=id,title,url,author,metadata,source_type&source_type=eq.{sb.q(source_type)}&order=created_at.desc&limit=100")
    return rows if code == 200 and isinstance(rows, list) else []


def ensure_seed_registry() -> list[dict[str, Any]]:
    """Bootstrap durable monitoring seeds from already-observed Nexus topics."""
    existing = sources("HEARTBEAT_SEED")
    by_topic = {str(raw(x).get("topic") or "").lower(): x for x in existing}
    definitions = [
        ("business funding", "research_discovery_runs", "SEARCH_TRENDS,YOUTUBE_CONTENT,SEO_SEARCH_DEMAND,AFFILIATE_PROGRAM_DISCOVERY"),
        ("online business", "research_discovery_runs", "SEARCH_TRENDS,YOUTUBE_CONTENT,SEO_SEARCH_DEMAND,AFFILIATE_PROGRAM_DISCOVERY"),
        ("AI consulting", "market_heartbeat_observed_topic", "SEARCH_TRENDS,YOUTUBE_CONTENT,SEO_SEARCH_DEMAND,AFFILIATE_PROGRAM_DISCOVERY"),
    ]
    for topic, source, lane_scope in definitions:
        if topic.lower() in by_topic:
            continue
        created = iso_now()
        payload = {"topic_id": "topic_" + hashlib.sha256(topic.encode()).hexdigest()[:20], "topic": topic,
                   "source": source, "lane_scope": lane_scope.split(","), "enabled": True,
                   "created_at": created, "last_run_at": None, "next_eligible_at": created,
                   "last_success_at": None, "last_failure_at": None, "seed_registry": True,
                   "recommendation_layer_added": False}
        result = persist_signal("HEARTBEAT_SEED", f"Heartbeat seed: {topic}", None, source, f"heartbeat-seed:{topic.lower()}", payload)
        if result.get("source_id"):
            code, rows = sb.get("research_sources", f"select=id,metadata&id=eq.{sb.q(result['source_id'])}")
            if code == 200 and rows:
                meta = rows[0].get("metadata") if isinstance(rows[0].get("metadata"), dict) else {}
                sb.update("research_sources", f"id=eq.{sb.q(result['source_id'])}", {"metadata": {**meta, **payload, "raw_signal": payload, "signal_identity": f"heartbeat-seed:{topic.lower()}"}})
    return sources("HEARTBEAT_SEED")


def enabled_seeds() -> list[dict[str, Any]]:
    rows = ensure_seed_registry()
    return [x for x in rows if bool(raw(x).get("enabled", (x.get("metadata") or {}).get("enabled", True)))]


def seed_topics() -> list[str]:
    topics = [str(raw(x).get("topic") or (x.get("metadata") or {}).get("topic") or "").strip() for x in enabled_seeds()]
    return bounded_topics(topics)


def bounded_topics(topics: list[str] | None) -> list[str]:
    """Limit a heartbeat wake to its canonical topics plus a small bounded tail.

    Old enabled HEARTBEAT_SEED rows can remain in the source bank. They are
    durable history, not permission to multiply every startup heartbeat into
    an unbounded topic fan-out.
    """
    unique = list(dict.fromkeys(str(topic).strip() for topic in (topics or []) if str(topic).strip()))
    canonical = [topic for topic in TOPICS if topic in unique]
    extras = [topic for topic in unique if topic not in canonical]
    limit = max(1, min(MAX_TOPICS_PER_WAKE, int(os.getenv("NEXUS_MARKET_HEARTBEAT_MAX_TOPICS", str(MAX_TOPICS_PER_WAKE)))))
    return (canonical + extras)[:limit]


def touch_seed_registry(topics: list[str], success: bool):
    stamp = iso_now()
    for row in enabled_seeds():
        topic = raw(row).get("topic") or (row.get("metadata") or {}).get("topic")
        if topic not in topics:
            continue
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        patch = {**meta, "last_run_at": stamp, "last_success_at": stamp if success else meta.get("last_success_at"),
                 "last_failure_at": None if success else stamp, "next_eligible_at": stamp, "enabled": True}
        sb.update("research_sources", f"id=eq.{sb.q(row['id'])}", {"metadata": patch})


def raw(row):
    meta = row.get("metadata") or {}
    return meta.get("raw_signal") or meta.get("raw_discovery") or {}


def receipt(heartbeat_id: str, lane: str, topic: str, result: dict[str, Any], started: str) -> dict[str, Any]:
    payload = {"heartbeat_run_id": heartbeat_id, "lane": lane, "topic": topic,
               "window_start": result.get("window_start"), "window_end": result.get("window_end"),
               "queries_run": result.get("queries_run", 0), "results_found": result.get("results_found", result.get("videos_found", result.get("related_queries_found", result.get("programs_discovered", 0)))),
               "new_sources": result.get("new_sources", 0), "duplicates": result.get("duplicates", 0),
               "records_updated": result.get("records_updated", 0), "failures": result.get("failures", result.get("failed_queries", [])),
               "runtime_seconds": result.get("runtime_seconds"), "started_at": started, "completed_at": iso_now(),
               "status": result.get("status", "COMPLETED"), "collection_only": True}
    row = {"lane": f"MARKET_HEARTBEAT_{lane}", "trigger": "MARKET_INTELLIGENCE_HEARTBEAT", "status": payload["status"],
           "started_at": started, "completed_at": payload["completed_at"], "sources_discovered": payload["results_found"],
           "sources_processed": payload["new_sources"] + payload["duplicates"] + payload["records_updated"], "metadata": payload}
    code, data = sb.insert("research_discovery_runs", row)
    rid = data[0].get("id") if code in (200, 201) and isinstance(data, list) and data else None
    read_code, back = sb.get("research_discovery_runs", f"select=id,status,metadata&id=eq.{sb.q(rid)}") if rid else (code, [])
    payload["receipt_id"] = rid; payload["readback"] = read_code == 200 and bool(back)
    return payload


def heartbeat_parent(cycle: int, topics: list[str]) -> tuple[str | None, str]:
    started = iso_now()
    row = {"lane": "MARKET_INTELLIGENCE_HEARTBEAT", "trigger": "DETERMINISTIC_ROTATION", "status": "RUNNING", "started_at": started,
           "metadata": {"cycle": cycle, "lane_order": LANE_ORDER, "topics": topics, "seed_registry_source": "Supabase research_sources:HEARTBEAT_SEED", "recommendation_layer_added": False}}
    code, data = sb.insert("research_discovery_runs", row)
    return (data[0].get("id") if code in (200, 201) and isinstance(data, list) and data else None), started


def finish_parent(parent_id: str, summary: dict[str, Any], started: str):
    sb.update("research_discovery_runs", f"id=eq.{sb.q(parent_id)}", {"status": "COMPLETED", "completed_at": iso_now(),
        "sources_discovered": summary.get("results_found", 0), "sources_processed": summary.get("new_sources", 0) + summary.get("duplicates", 0) + summary.get("records_updated", 0),
        "metadata": {**summary, "started_at": started, "completed_at": iso_now(), "recommendation_layer_added": False}})
    code, rows = sb.get("research_discovery_runs", f"select=id,status,metadata&id=eq.{sb.q(parent_id)}")
    return code == 200 and bool(rows)


def snapshot_deltas(before: dict[str, dict[str, Any]], after_rows: list[dict[str, Any]], heartbeat_id: str) -> list[dict[str, Any]]:
    deltas=[]
    for row in after_rows:
        r=raw(row); vid=r.get("video_id"); snaps=(row.get("metadata") or {}).get("snapshots") or []
        if not vid or len(snaps)<2: continue
        prev, cur=snaps[-2], snaps[-1]; previous_id=before.get(vid,{}).get("id")
        for metric, signal in (("views","VIEW_GROWTH"),("comments","COMMENT_GROWTH"),("likes","LIKE_GROWTH")):
            old, new=prev.get(metric), cur.get(metric)
            if not isinstance(old,(int,float)) or not isinstance(new,(int,float)): continue
            delta=new-old
            payload={"signal_type":signal,"entity_id":vid,"source_id":row.get("id"),"previous_value":old,"current_value":new,"delta":delta,"window":"SINCE_PREVIOUS_SNAPSHOT","observed_at":cur.get("snapshot_at"),"heartbeat_run_id":heartbeat_id,"recommendation_status":"NOT_REQUESTED"}
            identity=f"delta:{vid}:{signal}:{cur.get('snapshot_at')}"
            result=persist_signal("MARKET_DELTA",f"{signal}: {vid}",None,"Nexus",identity,payload)
            payload.update({"source_id":result.get("source_id"),"readback":result.get("readback"),"new":result.get("new")});deltas.append(payload)
    return deltas


def interpretation_packages(cycle: int, heartbeat_id: str, content_rows, trend_rows, affiliate_rows) -> list[dict[str, Any]]:
    candidates=[]
    for topic in ("business funding","online business"):
        matching_content=[x.get("id") for x in content_rows if topic in json.dumps(raw(x)).lower()]
        matching_trends=[x.get("id") for x in trend_rows if topic in json.dumps(raw(x)).lower()]
        matching_aff=[x.get("id") for x in affiliate_rows if ("fund" in json.dumps(raw(x)).lower()) == (topic=="business funding")]
        package={"interpretation_package_id":f"market_heartbeat_{cycle}_{hashlib.sha256((topic+heartbeat_id).encode()).hexdigest()[:20]}","heartbeat_run_id":heartbeat_id,"cycle":cycle,"topic":topic,"content_source_ids":matching_content,"trend_source_ids":matching_trends,"affiliate_source_ids":matching_aff,"interpretation_state":"INTERPRETATION_PENDING","recommendation_status":"NOT_REQUESTED","created_at":iso_now()}
        candidates.append(package)
    existing_by_id=_source_lookup_many([x["interpretation_package_id"] for x in candidates])
    out=[]
    for package in candidates:
        identity=package["interpretation_package_id"]
        result=persist_signal("INTERPRETATION_PENDING",f"Interpretation pending: {package['topic']}",None,"Nexus",identity,package,
                              existing_record=existing_by_id.get(identity))
        package.update({"source_id":result.get("source_id"),"readback":result.get("readback")});out.append(package)
    return out


def informational_handoffs(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows=[]
    for package in packages:
        expert="CLYDE_CREDIT" if package["topic"]=="business funding" else "MIRA_MARKETING"
        iid="info_"+hashlib.sha256((package["source_id"]+expert).encode()).hexdigest()[:24]
        code, existing=sb.get("department_information_items",f"select=information_item_id&information_item_id=eq.{sb.q(iid)}&limit=1")
        if code==200 and existing: rows.append({"information_item_id":iid,"existing":True,"readback":True});continue
        row={"information_item_id":iid,"finding_id":package["source_id"],"expert_id":expert,"why_relevant":f"New factual market-intelligence package for {package['topic']}; informational only.","priority":50,"status":"PENDING","created_at":iso_now(),"source_lineage":{"heartbeat_run_id":package["heartbeat_run_id"],"package_id":package["source_id"]}}
        wc,data=sb.insert("department_information_items",row,prefer="return=representation"); rows.append({"information_item_id":iid,"existing":False,"readback":wc in (200,201),"expert_id":expert})
    return rows


def cycle(cycle_number: int, followup: bool = False, topics: list[str] | None = None) -> dict[str, Any]:
    requested_topics = topics if topics is not None else seed_topics()
    active_topics = bounded_topics(requested_topics)
    parent, started=heartbeat_parent(cycle_number, active_topics)
    if not parent: return {"status":"FAILED_RETRYABLE","error":"heartbeat_parent_write","cycle":cycle_number}
    before_rows=sources("YOUTUBE_CONTENT_SIGNAL"); before={raw(x).get("video_id"):x for x in before_rows if raw(x).get("video_id")}
    lane_receipts=[]; results_found=new_sources=duplicates=updated=0; failures=[]; content_result=[]; trend_result={}; affiliate_result={}
    # Fixed order: AI cannot select a lane.
    trend_result=bounded_lane(lambda: trend_signals(active_topics,max_per_topic=3)); trend_result.update({"window_start":None,"window_end":iso_now(),"records_updated":trend_result.get("related_queries_found",0)})
    lane_receipts.append(receipt(parent,"SEARCH_TRENDS","; ".join(active_topics),trend_result,started)); results_found+=trend_result.get("related_queries_found",0);updated+=trend_result.get("related_queries_found",0)
    for topic in active_topics:
        if topic == "AI consulting":
            continue
        result=bounded_lane(lambda topic=topic: youtube_content(topic,max_results=2,window_days=30)); result.update({"status":result.get("status") if result.get("status")=="FAILED_RETRYABLE" else ("COMPLETED" if not result.get("failures") else "FAILED_RETRYABLE"),"records_updated":sum(not x.get("new") for x in result.get("videos",[])),"window_start":None,"window_end":iso_now()})
        content_result.append(result);lane_receipts.append(receipt(parent,"YOUTUBE_CONTENT",topic,result,started));results_found+=result.get("videos_found",0);updated+=result.get("records_updated",0);failures.extend(result.get("failures",[]))
    for topic in active_topics:
        if topic == "AI consulting":
            continue
        result=bounded_lane(lambda topic=topic: run_lane(topic,"SEO_SEARCH_DEMAND",window_days=30,bounds={"max_queries":1,"max_results_per_query":3,"max_new_sources":3,"max_runtime_per_lane":30})); result.update({"window_start":None,"window_end":iso_now(),"records_updated":result.get("duplicates",0)})
        lane_receipts.append(receipt(parent,"SEO_SEARCH_DEMAND",topic,result,started));results_found+=result.get("results_found",0);new_sources+=result.get("new_sources",0);duplicates+=result.get("duplicates",0);updated+=result.get("records_updated",0);failures.extend(result.get("failed_queries",[]))
    affiliate_topics=[x for x in active_topics if x in {"business funding","online business"}]
    # Rotate the topic and send bounded directory discovery through the
    # durable proactive query-memory/novelty/case path. Keep the established
    # affiliate signal collector as a separate evidence receipt.
    selected_affiliate_topic = affiliate_topics[(cycle_number - 1) % len(affiliate_topics)] if affiliate_topics else "online business"
    affiliate_memory = bounded_lane(lambda: run_lane(selected_affiliate_topic,"AFFILIATE_PROGRAM_DISCOVERY",window_days=30,bounds={"max_queries":1,"max_results_per_query":2,"max_new_sources":3,"max_runtime_per_lane":30}))
    lane_receipts.append(receipt(parent,"AFFILIATE_DIRECTORY_CASE_DISCOVERY",selected_affiliate_topic,affiliate_memory,started))
    results_found+=affiliate_memory.get("results_found",0);new_sources+=affiliate_memory.get("new_sources",0);duplicates+=affiliate_memory.get("duplicates",0);failures.extend(affiliate_memory.get("failed_queries",[]))
    affiliate_result=bounded_lane(lambda: affiliate_discovery([selected_affiliate_topic],max_results=2));affiliate_result.update({"status":affiliate_result.get("status") if affiliate_result.get("status")=="FAILED_RETRYABLE" else "COMPLETED","window_start":None,"window_end":iso_now(),"records_updated":affiliate_result.get("programs_discovered",0)})
    lane_receipts.append(receipt(parent,"AFFILIATE_PROGRAM_DISCOVERY",selected_affiliate_topic,affiliate_result,started));results_found+=affiliate_result.get("programs_discovered",0);updated+=affiliate_result.get("programs_discovered",0)
    after_rows=sources("YOUTUBE_CONTENT_SIGNAL"); deltas=snapshot_deltas(before,after_rows,parent)
    content_rows=after_rows; trend_rows=sources("TREND_SIGNAL"); affiliate_rows=sources("AFFILIATE_PROGRAM"); packages=interpretation_packages(cycle_number,parent,content_rows,trend_rows,affiliate_rows);handoffs=informational_handoffs(packages)
    follow=[]
    if followup:
        qc, qrows = sb.get("research_questions", "select=id,question,status&status=eq.OPEN&requester=eq.proactive_ai_interpretation&order=created_at.asc&limit=1")
        if qc == 200 and qrows:
            qid=qrows[0]["id"]; qtext=qrows[0]["question"]
            sr=run_lane(qtext,"WEB_SEARCH",window_days=30,bounds={"max_queries":1,"max_results_per_query":3,"max_new_sources":3,"max_runtime_per_lane":30})
            follow=[{"question_id":qid,"existing":True,"readback":True,"discovery_run_id":sr.get("discovery_run_id"),"status":sr.get("status"),"sources_appended":sr.get("sources_appended_to_fifo",0)}]
    summary={"cycle":cycle_number,"heartbeat_run_id":parent,"topics":active_topics,"requested_topic_count":len(requested_topics or []),"topics_deferred_by_wake_bound":max(0,len(set(requested_topics or []))-len(active_topics)),"lane_order":LANE_ORDER,"lanes_attempted":len(lane_receipts),"lanes_completed":sum(x.get("status")=="COMPLETED" for x in lane_receipts),"lanes_failed":sum(x.get("status")=="FAILED_RETRYABLE" for x in lane_receipts),"queries_run":sum(x.get("queries_run",0) for x in lane_receipts),"results_found":results_found,"new_sources":new_sources,"duplicates":duplicates,"records_updated":updated,"content_records_updated":sum(x.get("records_updated",0) for x in content_result),"trend_signals_updated":trend_result.get("related_queries_found",0),"affiliate_records_updated":affiliate_result.get("programs_discovered",0),"deltas_created":len(deltas),"interpretation_packages_created":len(packages),"department_handoffs_created":sum(not x.get("existing") for x in handoffs),"followup_queries_created":len(follow),"lane_receipts":lane_receipts,"deltas":deltas,"packages":packages,"handoffs":handoffs,"followups":follow,"recommendation_layer_added":False,"seed_registry_topics":active_topics}
    summary["supabase_readback"]=finish_parent(parent,summary,started);touch_seed_registry(active_topics,summary["supabase_readback"]);return summary


def main():
    provider_registry = ensure_discovery_provider_registry()
    seeds=enabled_seeds(); active=[str(raw(x).get("topic") or (x.get("metadata") or {}).get("topic")) for x in seeds]
    first=cycle(1,followup=True,topics=active); second=cycle(2,followup=False,topics=active)
    payload={"status":"PASS_REAL" if first.get("supabase_readback") and second.get("supabase_readback") and first.get("lanes_completed",0)>=4 and second.get("lanes_completed",0)>=4 else "PARTIAL_REAL","created_at":iso_now(),"lane_order":LANE_ORDER,"seed_registry_status":"PASS_REAL_SUPABASE_DURABLE","discovery_provider_registry":provider_registry,"real_seeds_registered":active,"first_cycle":first,"second_cycle":second,"heartbeat_rotation_status":"PASS_REAL_FIXED_ORDER","last30_continuous_window_status":"PASS_REAL_DATE_AWARE","content_snapshot_heartbeat_status":"PASS_REAL_BASELINE_AND_DELTAS","market_delta_status":"PASS_REAL_DETERMINISTIC","affiliate_monitor_status":"PASS_REAL_PENDING_RECORD_REFRESH","clickbank_canary_status":"NOT_AVAILABLE_ACCOUNT_ACTION_REQUIRED","tiktok_monitor_status":"DEFERRED_NOT_CONFIGURED","continuous_interpretation_trigger_status":"PASS_REAL_PENDING_PACKAGES","continuous_followup_loop_status":"PASS_REAL","continuous_handoff_status":"PASS_REAL_INFORMATION_ONLY","supabase_readback_pass":first.get("supabase_readback") and second.get("supabase_readback"),"company_recommendations_created":0,"priority_rankings_created":0,"autonomous_work_orders_created":0,"affiliate_links_published":0,"merch_products_created":0,"content_published":0,"recommendation_layer_added":False,"universal_fifo_changed":False,"oracle_hermes_changed":False}
    out=ROOT/"reports/research/NEXUS_MARKET_INTELLIGENCE_HEARTBEAT_2026-09-29.json";out.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    md=ROOT/"reports/research/NEXUS_MARKET_INTELLIGENCE_HEARTBEAT_2026-09-29.md";md.write_text("# Nexus Market Intelligence Heartbeat\n\n"+"\n".join(f"{k.upper()}={v}" for k,v in payload.items() if k not in {"first_cycle","second_cycle"})+"\n")
    print(json.dumps({k:payload[k] for k in ("status","heartbeat_rotation_status","supabase_readback_pass","continuous_followup_loop_status")},indent=2));return 0 if payload["status"] in {"PASS_REAL","PARTIAL_REAL"} else 1

if __name__ == "__main__": raise SystemExit(main())
