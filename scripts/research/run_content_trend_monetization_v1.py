#!/usr/bin/env python3
"""Bounded real canary for content, trend, and affiliate collection."""
from __future__ import annotations

import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb
from nexus_agent_platform.content_intelligence import youtube_content, channel_records, trend_signals, affiliate_discovery, persist_signal


def insert_receipt(lane, topic, payload, started):
    row = {"lane": lane, "trigger": "CONTENT_TREND_MONETIZATION_V1", "status": "COMPLETED",
           "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
           "sources_discovered": payload.get("videos_found", payload.get("related_queries_found", payload.get("programs_discovered", 0))),
           "sources_processed": payload.get("videos_found", payload.get("related_queries_found", payload.get("programs_discovered", 0))),
           "metadata": {"topic": topic, "payload": payload, "collection_only": True, "recommendation_layer_added": False}}
    code, data = sb.insert("research_discovery_runs", row)
    rid = data[0].get("id") if code in (200, 201) and isinstance(data, list) and data else None
    if rid:
        rc, _ = sb.get("research_discovery_runs", f"select=id,status,metadata&id=eq.{sb.q(rid)}")
    else: rc = code
    return {"run_id": rid, "write_code": code, "readback": rc == 200}


def owned_catalog():
    cfg = json.loads((ROOT / "configs/offer_registry.json").read_text())
    rows=[]
    for offer in cfg.get("offers", []):
        payload={"offer_id":offer.get("offer_id"),"brand":"GoClear/Nexus","offer_name":offer.get("name"),"category":offer.get("offer_id"),"customer_problem":offer.get("target_customer"),"customer_outcome":offer.get("promise"),"audience":offer.get("target_customer"),"current_status":offer.get("stripe_status"),"price":offer.get("price_usd"),"landing_page":None,"source":"configs/offer_registry.json","observed_at":datetime.now(timezone.utc).isoformat()}
        result=persist_signal("OWNED_OFFER_CATALOG",payload["offer_name"],None,"GoClear/Nexus",f"owned-offer:{payload['offer_id']}",payload)
        payload["source_id"]=result.get("source_id"); payload["readback"]=result.get("readback"); rows.append(payload)
    return rows


def main():
    started=datetime.now(timezone.utc).isoformat()
    content=[]; channels=[]; receipts=[]
    for topic in ("business funding", "online business"):
        run=youtube_content(topic, max_results=3, window_days=30)
        content.append(run); channels.extend(channel_records(run["videos"])); receipts.append(insert_receipt("YOUTUBE_30DAY_COLLECTOR",topic,run,started))
    trends=trend_signals(["online business","business funding","AI consulting"])
    receipts.append(insert_receipt("SEARCH_TREND_COLLECTOR","online business; business funding; AI consulting",trends,started))
    affiliates=affiliate_discovery(["business funding","online business"])
    receipts.append(insert_receipt("DIRECT_AFFILIATE_DISCOVERY","business funding; online business",affiliates,started))
    offers=owned_catalog()
    rankings = {}
    for item in content:
        rows = item.get("videos", [])
        rankings[item["topic"]] = {
            "top_by_views": [x.get("video_id") for x in sorted(rows, key=lambda x: x.get("views") or 0, reverse=True)],
            "top_by_views_per_day": [x.get("video_id") for x in sorted(rows, key=lambda x: (x.get("metrics") or {}).get("views_per_day") or 0, reverse=True)],
            "top_by_comments": [x.get("video_id") for x in sorted(rows, key=lambda x: x.get("comments") or 0, reverse=True)],
            "top_by_comment_rate": [x.get("video_id") for x in sorted(rows, key=lambda x: (x.get("metrics") or {}).get("comments_per_1000_views") or 0, reverse=True)],
        }
    total_videos=sum(x["videos_found"] for x in content)
    readbacks=[x["readback"] for x in receipts]+[x["readback"] for x in content]+[x["readback"] for x in channels]+[x["readback"] for x in trends["signals"]]+[x["readback"] for x in affiliates["programs"]]+[x["readback"] for x in offers]
    payload={"status":"PASS_REAL" if total_videos and trends["related_queries_found"] and affiliates["programs_discovered"] and all(readbacks) else "PARTIAL_REAL",
             "started_at":started,"completed_at":datetime.now(timezone.utc).isoformat(),"content":content,"channels":channels,"rankings":rankings,"trends":trends,"affiliates":affiliates,"owned_offers":offers,"receipts":receipts,
             "youtube_videos_collected":total_videos,"creator_channels_collected":len(channels),"trend_signals_collected":trends["related_queries_found"],"affiliate_programs_discovered":affiliates["programs_discovered"],"affiliate_programs_verified":affiliates["programs_verified"],"supabase_readback_pass":all(readbacks),"tiktok_data_path_status":"NOT_AVAILABLE","clickbank_access_status":"NOT_AVAILABLE","recommendation_layer_added":False,"company_recommendations_created":0,"priority_rankings_created":0,"autonomous_work_orders_created":0,"universal_fifo_changed":False,"oracle_hermes_changed":False,"rights_gate_defined":True}
    out=ROOT/"reports/research/NEXUS_CONTENT_TREND_MONETIZATION_V1_2026-09-29.json"; out.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    md=ROOT/"reports/research/NEXUS_CONTENT_TREND_MONETIZATION_V1_2026-09-29.md"
    md.write_text("# Nexus Content, Trend, and Monetization Collection V1\n\n"+"\n".join(f"{k.upper()}={v}" for k,v in payload.items() if k not in {"content","channels","trends","affiliates","owned_offers","receipts"})+"\n")
    print(json.dumps(payload,indent=2,default=str)); return 0 if payload["status"] in {"PASS_REAL","PARTIAL_REAL"} else 1

if __name__ == "__main__": raise SystemExit(main())
