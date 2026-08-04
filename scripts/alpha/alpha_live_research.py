#!/usr/bin/env python3
"""Alpha live external research bridge.

Server-side only. Uses configured research/model providers, preserves source
provenance, and records structured results without exposing secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from nexus_runtime_env import load_runtime_env  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime"
DATA_DIR = ROOT / "data" / "alpha" / "live_research"
BRIEF_DIR = ROOT / "reports" / "alpha" / "briefs"
ADVISORY_PATH = ROOT / "reports" / "hermes" / "alpha_advisory_feed_latest.md"
PUBLIC_ALPHA_STATUS = ROOT / "public" / "runtime" / "alpha-live-research-status.json"

load_runtime_env()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def http_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> tuple[bool, int | None, Any, str | None, int]:
    start = time.monotonic()
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw or "{}")
            return True, resp.status, data, None, int((time.monotonic() - start) * 1000)
    except urllib.error.HTTPError as exc:
        return False, exc.code, {}, f"HTTP_{exc.code}", int((time.monotonic() - start) * 1000)
    except Exception as exc:  # noqa: BLE001
        return False, None, {}, exc.__class__.__name__, int((time.monotonic() - start) * 1000)


def clean_query(text: str) -> str:
    query = re.sub(r"^(?:/alpha\s+|@?alpha\s*[,:\-]?\s*)", "", text.strip(), flags=re.I).strip()
    query = re.sub(r"^(?:research|investigate|search(?:\s+the\s+web\s+for)?|find|look\s+up)\s+", "", query, flags=re.I).strip()
    return query or text.strip()


def provider_query(query: str) -> str:
    q = query.strip()
    q_lower = q.lower()
    if "goclear" in q_lower or "nexus" in q_lower:
        if "affiliate" in q_lower:
            return "affiliate programs for small business credit funding education financial services 2026"
        if any(x in q_lower for x in ("grant", "funding", "capital")):
            return "current small business grants funding readiness credit building business owners 2026"
        if any(x in q_lower for x in ("technology", "tool", "software")):
            return "AI automation tools for credit funding readiness small business client portal 2026"
        return "current business opportunities for credit funding readiness services small business owners 2026"
    return q


def category_for(query: str) -> str:
    q = query.lower()
    if any(x in q for x in ("grant", "funding", "loan", "capital", "procurement", "sbir", "sttr")):
        return "funding_opportunity"
    if any(x in q for x in ("affiliate", "referral", "partner", "commission")):
        return "affiliate_opportunity"
    if any(x in q for x in ("technology", "software", "tool", "open source", "github", "automation")):
        return "technology_improvement"
    if any(x in q for x in ("competitor", "market", "pricing")):
        return "market_research"
    if any(x in q for x in ("youtube", "video", "creator", "channel")):
        return "video_research"
    if any(x in q for x in ("trade", "trading", "forex", "market data")):
        return "trading_research"
    return "business_opportunity"


def confidence_value(label: Any) -> float:
    if isinstance(label, (int, float)):
        return max(0.0, min(float(label), 1.0))
    text = str(label or "").lower()
    if "high" in text:
        return 0.82
    if "low" in text:
        return 0.35
    return 0.62


def brave_search(query: str, count: int = 6) -> dict[str, Any]:
    key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        return {"ok": False, "provider": "brave", "error": "missing_credential", "sources": []}
    params = urllib.parse.urlencode({"q": query, "count": max(1, min(count, 10)), "search_lang": "en", "country": "US"})
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": key,
        "User-Agent": "NexusAlphaLiveResearch/1.0",
    }
    ok, status, data, error, latency = http_json("GET", f"https://api.search.brave.com/res/v1/web/search?{params}", headers, timeout=25)
    sources = []
    for item in ((data or {}).get("web") or {}).get("results", [])[:count]:
        url = item.get("url") or ""
        if not url:
            continue
        sources.append(
            {
                "title": item.get("title") or "Untitled source",
                "url": url,
                "source_name": urllib.parse.urlparse(url).netloc,
                "snippet": item.get("description") or "",
                "published_at": item.get("age") or None,
                "retrieved_at": utc_now(),
                "provider": "brave",
            }
        )
    return {"ok": ok and bool(sources), "provider": "brave", "status_code": status, "latency_ms": latency, "error": error, "sources": sources}


def youtube_search(query: str, count: int = 4) -> dict[str, Any]:
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        return {"ok": False, "provider": "youtube", "error": "missing_credential", "sources": []}
    q = query.lower()
    if not any(x in q for x in ("youtube", "video", "creator", "channel")):
        return {"ok": True, "provider": "youtube", "skipped": True, "sources": []}
    params = urllib.parse.urlencode({"part": "snippet", "q": query, "type": "video", "maxResults": max(1, min(count, 5)), "key": key})
    ok, status, data, error, latency = http_json("GET", f"https://www.googleapis.com/youtube/v3/search?{params}", timeout=25)
    sources = []
    for item in (data or {}).get("items", [])[:count]:
        video_id = ((item.get("id") or {}).get("videoId") or "").strip()
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        sources.append(
            {
                "title": snippet.get("title") or "YouTube result",
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "source_name": snippet.get("channelTitle") or "YouTube",
                "snippet": snippet.get("description") or "",
                "published_at": snippet.get("publishedAt"),
                "retrieved_at": utc_now(),
                "provider": "youtube",
            }
        )
    return {"ok": ok, "provider": "youtube", "status_code": status, "latency_ms": latency, "error": error, "sources": sources}


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def synthesize_with_openrouter(query: str, category: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = (
        os.environ.get("ALPHA_OPENROUTER_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or os.environ.get("HERMES_ALPHA_MODEL")
        or "openai/gpt-4o-mini"
    )
    if not key:
        return {"ok": False, "provider": "openrouter", "model": model, "error": "missing_credential", "analysis": deterministic_analysis(query, category, sources)}

    source_summary = [
        {
            "title": s.get("title"),
            "url": s.get("url"),
            "snippet": s.get("snippet", "")[:450],
            "source_name": s.get("source_name"),
            "published_at": s.get("published_at"),
        }
        for s in sources[:8]
    ]
    prompt = {
        "query": query,
        "category": category,
        "sources": source_summary,
        "required_json_keys": [
            "summary",
            "why_it_matters",
            "confidence",
            "revenue_potential",
            "estimated_effort",
            "estimated_cost",
            "strategic_fit",
            "risk",
            "recommended_next_action",
            "approval_requirement",
        ],
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are Hermes Alpha, Ray's independent research brain. Use only the supplied source summaries. Do not invent facts, client data, or URLs. Return compact JSON only.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
        "temperature": 0.2,
        "max_tokens": 700,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://goclearonline.cc",
        "X-Title": "Nexus Alpha Live Research",
    }
    ok, status, data, error, latency = http_json("POST", "https://openrouter.ai/api/v1/chat/completions", headers, payload, timeout=45)
    text = ""
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception:
        text = ""
    analysis = _extract_json(text) or deterministic_analysis(query, category, sources)
    return {"ok": ok and bool(text), "provider": "openrouter", "model": model, "status_code": status, "latency_ms": latency, "error": error, "analysis": analysis}


def deterministic_analysis(query: str, category: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    title = sources[0]["title"] if sources else query
    return {
        "summary": f"Alpha found current source evidence for {query}. Strongest source: {title}.",
        "why_it_matters": "This can become a bounded GoClear/Nexus opportunity only after Ray Review confirms fit and timing.",
        "confidence": "medium" if sources else "low",
        "revenue_potential": "medium",
        "estimated_effort": "low-to-medium",
        "estimated_cost": "low",
        "strategic_fit": "aligned with GoClear/Nexus if it improves lead flow, funding readiness, or internal leverage.",
        "risk": "requires source review, offer validation, and approval before external action.",
        "recommended_next_action": "Create a Ray Review item to validate the top source and decide whether to convert it into a work order.",
        "approval_requirement": "Ray Review required before execution.",
    }


def supabase_headers() -> dict[str, str]:
    base = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or ""
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        return {}
    return {"apikey": key, "authorization": f"Bearer {key}", "content-type": "application/json", "prefer": "return=representation"}


def rest_url(table: str, query: str = "") -> str:
    base = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or ""
    return f"{base.rstrip('/')}/rest/v1/{table}{query}" if base else ""


def supabase_insert(table: str, payload: dict[str, Any], query: str = "") -> tuple[bool, str | None, Any]:
    headers = supabase_headers()
    if not headers:
        return False, "supabase_service_missing", None
    ok, status, data, error, _ = http_json("POST", rest_url(table, query), headers, payload, timeout=25)
    if ok and status and 200 <= status < 300:
        return True, None, data
    return False, error or f"HTTP_{status}", data


def record_process_run(result: dict[str, Any]) -> dict[str, Any]:
    headers = {**supabase_headers(), "prefer": "resolution=merge-duplicates,return=representation"}
    if not headers.get("apikey"):
        return {"remote_registry_updated": False, "error": "supabase_service_missing"}
    process = {
        "process_key": "alpha_live_external_research",
        "name": "Alpha Live External Research",
        "description": "Brave/YouTube retrieval plus OpenRouter synthesis for Alpha Telegram research requests.",
        "system": "alpha",
        "entry_point": "scripts/alpha/alpha_live_research.py",
        "trigger_type": "telegram_or_manual",
        "enabled": True,
        "execution_mode": "bounded_live_provider_research",
        "owner": "Nexus Operations",
        "approval_policy": "ray_review_before_external_action",
        "is_mock": False,
        "metadata": {"runtime": "alpha_live_research_v1", "final_state": "ALPHA_LIVE_EXTERNAL_RESEARCH_ACTIVE"},
        "updated_at": utc_now(),
    }
    ok, _, data, error, _ = http_json("POST", rest_url("nexus_process_definitions", "?on_conflict=process_key"), headers, process, timeout=25)
    process_id = data[0].get("id") if ok and isinstance(data, list) and data else None
    if not process_id:
        return {"remote_registry_updated": False, "error": error or "definition_not_returned"}
    run_payload = {
        "process_id": process_id,
        "idempotency_key": f"alpha_live_external_research:{result['research_id']}",
        "status": "SUCCEEDED" if result.get("ok") else "FAILED",
        "started_at": result["started_at"],
        "completed_at": result["retrieved_at"],
        "heartbeat_at": result["retrieved_at"],
        "items_attempted": len(result.get("sources", [])),
        "items_succeeded": len(result.get("sources", [])) if result.get("ok") else 0,
        "items_failed": 0 if result.get("ok") else 1,
        "output_location": result.get("local_json"),
        "triggered_by": result.get("source", "alpha"),
        "trace_id": result["research_id"],
        "metadata": {
            "query": result["query"],
            "category": result["category"],
            "brave_ok": result["provider_results"]["brave"].get("ok"),
            "youtube_ok": result["provider_results"]["youtube"].get("ok"),
            "openrouter_ok": result["provider_results"]["openrouter"].get("ok"),
            "source_count": len(result.get("sources", [])),
        },
    }
    ok_run, err_run, _ = supabase_insert("nexus_process_runs", run_payload)
    return {"remote_registry_updated": ok_run, "process_id_present": True, "run_error": err_run}


def record_research_and_opportunity(result: dict[str, Any]) -> dict[str, Any]:
    run_payload = {
        "script_path": "scripts/alpha/alpha_live_research.py",
        "category": result["category"],
        "source_type": "brave_youtube_openrouter",
        "query_input": result["query"],
        "output_destination": "nexus_research_results,business_opportunities",
        "status": "SUCCEEDED" if result.get("ok") else "FAILED",
        "items_retrieved": len(result.get("sources", [])),
        "items_accepted": len(result.get("sources", [])),
        "items_rejected": 0,
        "metadata": {"research_id": result["research_id"], "telegram_ready": True},
        "started_at": result["started_at"],
        "completed_at": result["retrieved_at"],
    }
    ok, error, data = supabase_insert("nexus_research_runs", run_payload)
    research_run_id = data[0].get("id") if ok and isinstance(data, list) and data else None
    inserted = 0
    failures = []
    for source in result.get("sources", [])[:10]:
        payload = {
            "research_run_id": research_run_id,
            "category": result["category"],
            "title": source.get("title", "Alpha source")[:240],
            "summary": source.get("snippet", "")[:1000],
            "claim": result["analysis"].get("summary", "")[:1000],
            "source_url": source.get("url"),
            "source_name": source.get("source_name"),
            "published_at": None,
            "retrieved_at": result["retrieved_at"],
            "confidence": confidence_value(result["analysis"].get("confidence", "medium")),
            "score": result.get("score", 7),
            "duplicate_key": hashlib.sha256((result["query"] + source.get("url", "")).encode()).hexdigest()[:40],
            "status": "collected",
            "approval_state": result["analysis"].get("approval_requirement", "ray_review_required"),
            "downstream_destination": "business_opportunities" if result["is_opportunity"] else "alpha_research_archive",
            "metadata": {"research_id": result["research_id"], "provider": source.get("provider"), "confidence_label": result["analysis"].get("confidence", "medium")},
        }
        ok_item, err_item, _ = supabase_insert("nexus_research_results", payload)
        if ok_item:
            inserted += 1
        else:
            failures.append(err_item)
    opportunity = {"attempted": False, "stored": False, "error": None}
    if result["is_opportunity"]:
        opportunity_payload = {
            "external_id": result["research_id"],
            "tenant_id": "goclear",
            "category": result["category"],
            "title": (result.get("title") or result["query"])[:180],
            "summary": result["analysis"].get("summary", "")[:1000],
            "status": "RAY_REVIEW",
            "score": result.get("score", 7),
            "priority": "medium",
            "risk_level": "medium",
            "automation_level": "approval_gated",
            "client_visible": False,
            "approval_required": True,
            "goclear_review_status": "pending",
            "source": "alpha_live_external_research",
            "source_concept": result["query"],
            "recommended_next_action": result["analysis"].get("recommended_next_action", ""),
            "payload": result,
        }
        opportunity["attempted"] = True
        ok_opp, err_opp, _ = supabase_insert("business_opportunities", opportunity_payload)
        opportunity.update({"stored": ok_opp, "error": err_opp})
    return {"research_run_stored": ok, "research_run_id_present": bool(research_run_id), "research_inserted": inserted, "research_failures": failures[:5], "opportunity": opportunity, "run_error": error}


def write_outputs(result: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    PUBLIC_ALPHA_STATUS.parent.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / f"{result['research_id']}.json"
    md_path = BRIEF_DIR / f"{result['research_id']}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n")
    result["local_json"] = str(json_path)
    lines = [
        f"# Alpha Live Research: {result['query']}",
        "",
        f"- research_id: {result['research_id']}",
        f"- category: {result['category']}",
        f"- retrieved_at: {result['retrieved_at']}",
        f"- brave: {'PASS' if result['provider_results']['brave'].get('ok') else 'FAIL'}",
        f"- openrouter: {'PASS' if result['provider_results']['openrouter'].get('ok') else 'FAIL'}",
        f"- sources: {len(result['sources'])}",
        f"- opportunity_stored: {result.get('persistence', {}).get('opportunity', {}).get('stored', False)}",
        "",
        "## Summary",
        "",
        result["analysis"].get("summary", ""),
        "",
        "## Sources",
    ]
    for source in result.get("sources", [])[:8]:
        lines.append(f"- {source.get('title')} — {source.get('url')}")
    md_path.write_text("\n".join(lines) + "\n")
    (RUNTIME / "alpha_live_research_latest.json").write_text(json.dumps(result, indent=2) + "\n")
    PUBLIC_ALPHA_STATUS.write_text(json.dumps({
        "ok": result.get("ok"),
        "status": "ALPHA_LIVE_EXTERNAL_RESEARCH_ACTIVE" if result.get("ok") else "ALPHA_LIVE_EXTERNAL_RESEARCH_FAILED",
        "research_id": result["research_id"],
        "query": result["query"],
        "category": result["category"],
        "retrieved_at": result["retrieved_at"],
        "source_count": len(result.get("sources", [])),
        "brave_ok": result["provider_results"]["brave"].get("ok"),
        "youtube_ok": result["provider_results"]["youtube"].get("ok"),
        "openrouter_ok": result["provider_results"]["openrouter"].get("ok"),
        "opportunity_stored": result.get("persistence", {}).get("opportunity", {}).get("stored", False),
    }, indent=2) + "\n")
    ADVISORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADVISORY_PATH.write_text("\n".join(lines[:20]) + "\n")


def run_alpha_live_research(query_text: str, source: str = "telegram") -> dict[str, Any]:
    started_at = utc_now()
    query = clean_query(query_text)
    live_query = provider_query(query)
    category = category_for(query)
    brave = brave_search(live_query)
    youtube = youtube_search(live_query)
    sources = brave.get("sources", []) + youtube.get("sources", [])
    openrouter = synthesize_with_openrouter(query, category, sources)
    analysis = openrouter.get("analysis") or deterministic_analysis(query, category, sources)
    research_id = "alpha_live_" + hashlib.sha256(f"{query}:{started_at}".encode()).hexdigest()[:16]
    is_opportunity = category in {"business_opportunity", "funding_opportunity", "affiliate_opportunity", "technology_improvement", "market_research"}
    score = 8 if sources and openrouter.get("ok") else 6 if sources else 3
    result = {
        "ok": bool(brave.get("ok") and sources and openrouter.get("ok")),
        "research_id": research_id,
        "query": query,
        "provider_query": live_query,
        "category": category,
        "title": sources[0]["title"] if sources else query,
        "summary": analysis.get("summary", ""),
        "sources": sources,
        "source_dates": [s.get("published_at") for s in sources if s.get("published_at")],
        "retrieved_at": utc_now(),
        "started_at": started_at,
        "confidence": analysis.get("confidence", "medium"),
        "revenue_potential": analysis.get("revenue_potential", "medium"),
        "estimated_effort": analysis.get("estimated_effort", "medium"),
        "estimated_cost": analysis.get("estimated_cost", "low"),
        "strategic_fit": analysis.get("strategic_fit", ""),
        "risk": analysis.get("risk", ""),
        "recommended_next_action": analysis.get("recommended_next_action", ""),
        "approval_requirement": analysis.get("approval_requirement", "Ray Review required"),
        "analysis": analysis,
        "score": score,
        "is_opportunity": is_opportunity,
        "source": source,
        "provider_results": {"brave": brave, "youtube": youtube, "openrouter": openrouter},
        "client_data_used": False,
        "external_action_performed": False,
    }
    write_outputs(result)
    persistence = record_research_and_opportunity(result)
    result["persistence"] = persistence
    result["process_registry"] = record_process_run(result)
    write_outputs(result)
    return result


def format_alpha_live_research_response(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        brave = result.get("provider_results", {}).get("brave", {})
        model = result.get("provider_results", {}).get("openrouter", {})
        return (
            f"Alpha Live Research — LOOKUP FAILED\n\n"
            f"Query: {result.get('query', '')[:120]}\n"
            f"Brave: {'PASS' if brave.get('ok') else 'FAIL'} {brave.get('error') or ''}\n"
            f"OpenRouter: {'PASS' if model.get('ok') else 'FAIL'} {model.get('error') or ''}\n"
            f"Sources: {len(result.get('sources', []))}\n\n"
            "I did not produce a live research claim because the live retrieval/synthesis path did not fully pass."
        )
    analysis = result["analysis"]
    lines = [
        "Alpha Live Research",
        "",
        f"What Alpha found: {analysis.get('summary', result.get('summary', ''))[:650]}",
        "",
        f"Why it matters: {analysis.get('why_it_matters', result.get('strategic_fit', ''))[:450]}",
        "",
        "Evidence and sources:",
    ]
    for i, source in enumerate(result.get("sources", [])[:4], 1):
        title = source.get("title", "Source")
        url = source.get("url", "")
        lines.append(f"{i}. {title[:120]} — {url}")
    lines.extend([
        "",
        f"Revenue potential: {result.get('revenue_potential')}",
        f"Effort: {result.get('estimated_effort')}",
        f"Cost: {result.get('estimated_cost')}",
        f"Risk: {result.get('risk')}",
        "",
        f"Recommended next step: {result.get('recommended_next_action')}",
        f"Ray Review: {result.get('approval_requirement')}",
        "",
        f"Research ID: {result.get('research_id')}",
        f"Stored: research={'YES' if result.get('persistence', {}).get('research_inserted', 0) else 'NO'} | opportunity={'YES' if result.get('persistence', {}).get('opportunity', {}).get('stored') else 'NO'}",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--source", default="manual")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_alpha_live_research(args.query, source=args.source)
    if args.json:
        safe = {
            "ok": result["ok"],
            "research_id": result["research_id"],
            "query": result["query"],
            "category": result["category"],
            "sources": len(result["sources"]),
            "brave_ok": result["provider_results"]["brave"].get("ok"),
            "openrouter_ok": result["provider_results"]["openrouter"].get("ok"),
            "research_stored": result.get("persistence", {}).get("research_inserted", 0),
            "opportunity_stored": result.get("persistence", {}).get("opportunity", {}).get("stored", False),
            "process_registry": result.get("process_registry", {}).get("remote_registry_updated", False),
        }
        print(json.dumps(safe, indent=2))
    else:
        print(format_alpha_live_research_response(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
