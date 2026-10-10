"""Evidence-preserving viral/social trend signal model and routing."""
from __future__ import annotations
import hashlib, re
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit
from nexus_agent_platform.governed.persistence import append_record, new_id, read_records

PLATFORMS={"YOUTUBE","TIKTOK","INSTAGRAM","FACEBOOK","WEB_SEARCH"}
RELEVANCE={"CUSTOMER_NEED","CUSTOMER_COMPLAINT","BUSINESS_OPPORTUNITY","AFFILIATE_OPPORTUNITY","MARKETING_TREND","CREATIVE_TREND","TRADING_TREND","TECHNOLOGY_TREND","LOW_VALUE_ENTERTAINMENT","UNKNOWN"}

def _now(): return datetime.now(timezone.utc).isoformat()
def _canon(url: str | None) -> str | None:
    if not url:return None
    p=urlsplit(url.strip());return urlunsplit((p.scheme.lower() or "https",p.netloc.lower(),p.path.rstrip("/"),"", ""))
def _key(topic: str) -> str: return re.sub(r"[^a-z0-9]+","-",topic.lower()).strip("-")
def signal_record(data: Mapping[str,Any]) -> dict[str,Any]:
    platform=str(data.get("platform") or "UNKNOWN").upper()
    if platform not in PLATFORMS and platform!="UNKNOWN":raise ValueError("unsupported_platform")
    relevance=str(data.get("business_relevance") or "UNKNOWN").upper()
    if relevance not in RELEVANCE:raise ValueError("unsupported_business_relevance")
    metrics={key:data.get(key) for key in ("views","likes","comments","shares")}
    return {"schema_version":"nexus.viral-signal.v1","signal_id":str(data.get("signal_id") or new_id("viral")),"platform":platform,"source_url":_canon(data.get("source_url")),"creator_account":data.get("creator_account"),"topic":str(data.get("topic") or "").strip(),"topic_key":_key(str(data.get("topic") or "")),"hashtags":list(data.get("hashtags") or []),"published_at":data.get("published_at"),**metrics,"engagement_signal":data.get("engagement_signal"),"velocity_signal":data.get("velocity_signal"),"cross_platform_mentions":list(data.get("cross_platform_mentions") or []),"search_trend_evidence":list(data.get("search_trend_evidence") or []),"first_seen_at":data.get("first_seen_at") or _now(),"last_seen_at":data.get("last_seen_at") or _now(),"business_relevance":relevance,"trend_state":"UNKNOWN","metrics_missing":[key for key,value in metrics.items() if value is None],"source_evidence":data.get("source_evidence"),"evidence_mode":data.get("evidence_mode","LIVE_OR_IMPORTED")}

def classify_trend_state(signals: list[Mapping[str,Any]]) -> str:
    # A total view count is not a trend velocity signal. Require dated repeated observations or explicit normalized velocity.
    observed=[x for x in signals if x.get("velocity_signal") is not None]
    if not observed:return "UNKNOWN"
    velocities=[float(x["velocity_signal"]) for x in observed if isinstance(x.get("velocity_signal"),(int,float))]
    if not velocities:return "UNKNOWN"
    mean=sum(velocities)/len(velocities)
    return "ACCELERATING" if mean>=1.5 else "EMERGING" if mean>0 else "DECLINING" if mean<0 else "UNKNOWN"

def ingest_signal(data: Mapping[str,Any]) -> dict[str,Any]:
    row=signal_record(data); recent=read_records("research_market_intelligence",limit=500)
    duplicate=next((r for r in recent if row["source_url"] and r.get("source_url")==row["source_url"]),None)
    if duplicate:
        refreshed={**duplicate,"last_seen_at":row["last_seen_at"],"engagement_signal":row.get("engagement_signal") or duplicate.get("engagement_signal"),"velocity_signal":row.get("velocity_signal") if row.get("velocity_signal") is not None else duplicate.get("velocity_signal"),"novelty":"DUPLICATE_SOURCE_REFRESH","case_created":False}
        append_record("research_market_intelligence",refreshed)
        return {"status":"KNOWN_SIGNAL_UPDATED","signal":refreshed,"trend_cluster_id":duplicate.get("trend_cluster_id"),"case_created":False}
    if not row["topic"]:raise ValueError("topic_required")
    row["trend_cluster_id"]="trend_"+hashlib.sha256(row["topic_key"].encode()).hexdigest()[:16]
    existing=[r for r in recent if r.get("trend_cluster_id")==row["trend_cluster_id"]]
    row["novelty"]=("LOW_VALUE" if row["business_relevance"]=="LOW_VALUE_ENTERTAINMENT" else "KNOWN_TOPIC_NEW_EVIDENCE" if existing else "NEW_MEANINGFUL_TREND")
    row["cross_platform_count"]=len({r.get("platform") for r in existing+[row]})
    row["trend_state"]=classify_trend_state(existing+[row])
    row["destination_department"]={"CUSTOMER_NEED":"OPPORTUNITIES","CUSTOMER_COMPLAINT":"OPPORTUNITIES","BUSINESS_OPPORTUNITY":"OPPORTUNITIES","AFFILIATE_OPPORTUNITY":"OPPORTUNITIES","MARKETING_TREND":"MARKETING","CREATIVE_TREND":"CREATIVE_REFERENCE","TRADING_TREND":"TRADING","TECHNOLOGY_TREND":"LABS"}.get(row["business_relevance"],"RESEARCH")
    row["next_action"]="VERIFY_PLATFORM_MOMENTUM_AND_UNDERLYING_NEED" if row["trend_state"]=="UNKNOWN" else "DEEPEN_TREND_EVIDENCE_AND_ROUTE"
    append_record("research_market_intelligence",row)
    cluster={"schema_version":"nexus.viral-trend-cluster.v1","trend_cluster_id":row["trend_cluster_id"],"topic":row["topic"],"signal_ids":[x.get("signal_id") for x in existing]+[row["signal_id"]],"platforms":sorted({x.get("platform") for x in existing+[row]}),"cross_platform_count":row["cross_platform_count"],"trend_state":row["trend_state"],"business_relevance":row["business_relevance"],"destination_department":row["destination_department"],"case_created":row["novelty"]=="NEW_MEANINGFUL_TREND","next_action":row["next_action"],"updated_at":_now()}
    append_record("research_discovery_clusters",cluster)
    return {"status":"NEW_SIGNAL" if not existing else "KNOWN_TREND_NEW_EVIDENCE","signal":row,"cluster":cluster,"case_created":cluster["case_created"]}
