"""Shared helpers for Nexus research/content growth engine.

All helpers are deterministic and local-first. They do not scrape broadly, call external AI,
publish, send, trade, deploy, start schedulers, or touch v1 workers.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

RESOURCE_TYPES = [
    "youtube_channel",
    "youtube_playlist",
    "youtube_video",
    "rss_feed",
    "affiliate_website",
    "affiliate_program_page",
    "competitor_website",
    "seo_blog",
    "credit_repair_resource",
    "business_funding_resource",
    "business_credit_resource",
    "online_business_opportunity_resource",
    "ai_tools_directory",
    "ai_automation_blog_channel",
    "trading_strategy_resource",
    "newsletter_archive",
    "manual_url_list",
]

TOPIC_ROUTES = {
    "credit repair": ("credit_funding_readiness", "goclear", "GoClear/Apex Revenue Hub"),
    "business credit": ("credit_funding_readiness", "goclear", "GoClear/Apex Revenue Hub"),
    "business funding": ("credit_funding_readiness", "goclear", "GoClear/Apex Revenue Hub"),
    "grants": ("funding_research", "opportunities", "Opportunity Lab"),
    "online business opportunities": ("online_business", "opportunities", "Opportunity Lab"),
    "ai tools": ("ai_tooling", "ops", "Ops & Improvements"),
    "ai automation": ("ai_automation", "ops", "Ops & Improvements"),
    "seo": ("seo_marketing", "seo", "SEO / Marketing"),
    "affiliate marketing": ("affiliate_partner", "opportunities", "Opportunity Lab"),
    "trading strategies": ("trading_research", "trading", "Trading Lab"),
    "content monetization": ("content_monetization", "seo", "SEO / Marketing"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, (int, float, bool)):
        return str(value)
    return fallback


def num(value: Any, fallback: float | None = None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("$", "")
        try:
            return float(cleaned)
        except ValueError:
            return fallback
    return fallback


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def route_for_topic(topic: str) -> tuple[str, str, str]:
    lowered = topic.lower().replace("_", " ").strip()
    for key, route in TOPIC_ROUTES.items():
        if key in lowered or lowered in key:
            return route
    return "public_research", "intake", "Source Intake"


def score_research_text(text_blob: str, topic: str = "") -> dict[str, int]:
    blob = f"{text_blob} {topic}".lower()
    money = 20
    if any(t in blob for t in ("revenue", "affiliate", "funding", "$97", "offer", "commission", "lead")):
        money += 22
    if any(t in blob for t in ("credit", "business funding", "business credit", "goclear", "apex")):
        money += 16
    seo = 20 + (20 if any(t in blob for t in ("keyword", "seo", "blog", "search", "content")) else 0)
    affiliate = 20 + (28 if any(t in blob for t in ("affiliate", "partner", "commission", "vendor")) else 0)
    content = 25 + (25 if any(t in blob for t in ("youtube", "script", "video", "article", "carousel", "newsletter")) else 0)
    compliance = 20 if any(t in blob for t in ("credit repair", "funding guarantee", "trade", "trading", "broker")) else 8
    testability = 30 + (20 if any(t in blob for t in ("checklist", "template", "guide", "tool", "workflow", "test")) else 0)
    uniqueness = 35 + (15 if any(t in blob for t in ("new", "2026", "automation", "ai")) else 0)
    urgency = 35 + (15 if any(t in blob for t in ("today", "now", "update", "latest")) else 0)
    difficulty = 40 + (15 if any(t in blob for t in ("api", "integration", "automation", "backend")) else 0)
    overall = clamp_score((money * 1.7 + seo + affiliate + content + testability + uniqueness + urgency - compliance - difficulty * 0.3) / 6)
    return {
        "money_potential": clamp_score(money),
        "goclear_apex_relevance": clamp_score(70 if any(t in blob for t in ("credit", "funding", "goclear", "apex")) else 25),
        "seo_potential": clamp_score(seo),
        "affiliate_potential": clamp_score(affiliate),
        "content_potential": clamp_score(content),
        "implementation_difficulty": clamp_score(difficulty),
        "compliance_risk": clamp_score(compliance),
        "urgency": clamp_score(urgency),
        "uniqueness": clamp_score(uniqueness),
        "testability": clamp_score(testability),
        "overall_score": overall,
    }


def enrichment(title: str, summary: str, topic: str, source: str = "deterministic") -> dict[str, Any]:
    category, owner_tab, destination = route_for_topic(topic)
    scores = score_research_text(f"{title} {summary}", topic)
    risks = []
    if scores["compliance_risk"] >= 20:
        risks.append("compliance_review")
    if owner_tab == "trading":
        risks.extend(["paper_only_required", "live_trading_blocked"])
    recommendation = f"Route to {destination} for review and smallest safe experiment planning."
    if owner_tab == "trading":
        recommendation = "Review as paper-only strategy research. Live trading remains blocked."
    return {
        "enrichment_status": "scored",
        "enrichment_source": source,
        "summary": summary,
        "score": scores["overall_score"],
        "score_label": "high" if scores["overall_score"] >= 75 else "medium" if scores["overall_score"] >= 50 else "low",
        "category": category,
        "destination": destination,
        "pros": [f"{destination} relevance detected.", f"Overall score: {scores['overall_score']}/100."],
        "cons": ["Needs Ray review before public/client-facing use."] if risks else ["Needs validation with a small manual test."],
        "recommendation": recommendation,
        "proposed_schedule": "Manual review in the next department digest; scheduler remains disabled.",
        "next_action": "Create a safe experiment card or park after review.",
        "confidence": 0.7,
        "risk_triggers": risks,
        "approval_required": bool(risks),
        "hermes_memory_summary": f"{title}: {category} -> {destination}; score={scores['overall_score']}/100.",
        "source_summary": summary,
        "scores": scores,
        "paper_only": owner_tab == "trading",
        "live_trading_blocked": owner_tab == "trading",
        "enriched_at": now(),
    }


def candidate(title: str, url: str, topic: str, source_type: str = "web", proof_source: str = "sample") -> dict[str, Any]:
    e = enrichment(title, f"Research candidate for {topic}: {title}.", topic)
    _category, owner_tab, destination = route_for_topic(topic)
    return {
        "title": title,
        "source_url": url,
        "source_type": source_type,
        "category": e["category"],
        "department_destination": destination,
        "owner_tab": owner_tab,
        "score": e["score"],
        "summary": e["summary"],
        "recommendation": e["recommendation"],
        "next_action": e["next_action"],
        "risk_level": "medium" if e["risk_triggers"] else "low",
        "proof_source": proof_source,
        "project_enrichment": e,
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def write_report(report: dict[str, Any], runtime: Path, manual: Path, explicit_path: str = "") -> None:
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text(json.dumps(report, indent=2))
    lines = [
        f"# {report.get('title', 'Nexus Research Report')}",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- dry_run: {report.get('dry_run')}",
        f"- ok: {report.get('ok')}",
        "- scheduler_started: false",
        "- capture_run: false",
        "- external_ai_called: false",
        "- publish_send_trade_deploy: false",
        "",
        "## Summary",
        report.get("summary", "No summary."),
        "",
        "## Counts",
    ]
    for key, value in report.get("counts", {}).items():
        lines.append(f"- {key}: {value}")
    manual.parent.mkdir(parents=True, exist_ok=True)
    manual.write_text("\n".join(lines) + "\n")
    if explicit_path:
        p = Path(explicit_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2) if p.suffix.lower() == ".json" else "\n".join(lines) + "\n")


def task_payload(item: dict[str, Any], task_type: str, feeder_id: str, project_type: str) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "requested_by": feeder_id,
        "sensitivity": "internal_summary",
        "allowed_data_scope": ["public", "internal_summary"],
        "forbidden_data": ["customer_private", "credit_sensitive", "funding_sensitive", "auth_sensitive", "secrets"],
        "assigned_worker_type": "research_review_worker",
        "hermes_visibility": "summary",
        "status": "proposed",
        "payload": {
            "feeder_id": feeder_id,
            "unique_key": item.get("unique_key") or f"{feeder_id}:{item.get('source_url') or item.get('title')}",
            "title": item["title"],
            "department": "trading_lab" if item.get("owner_tab") == "trading" else "opportunity_lab" if item.get("owner_tab") in {"opportunities", "goclear"} else item.get("department_destination", "source_intake"),
            "owner_tab": item.get("owner_tab", "intake"),
            "project_type": project_type,
            "source_url": item.get("source_url"),
            "source_title": item.get("title"),
            "summary": item.get("summary"),
            "recommendation": item.get("recommendation"),
            "next_action": item.get("next_action"),
            "score": item.get("score"),
            "risk_triggers": item.get("project_enrichment", {}).get("risk_triggers", []),
            "approval_required": item.get("project_enrichment", {}).get("approval_required", False),
            "project_enrichment": item.get("project_enrichment"),
            "proof_source": item.get("proof_source"),
            "source": feeder_id,
        },
        "result_summary": item.get("recommendation", "")[:500],
    }


def duplicate_task(task_type: str, unique_key: str) -> dict[str, Any] | None:
    query = f"select=id,status,payload&task_type=eq.{sb.q(task_type)}&payload->>unique_key=eq.{sb.q(unique_key)}&limit=1"
    _status, rows = sb.get("task_requests", query)
    return rows[0] if isinstance(rows, list) and rows else None


def write_live_tasks(items: list[dict[str, Any]], task_type: str, feeder_id: str, project_type: str, limit: int) -> dict[str, Any]:
    counts = {"created": 0, "duplicates": 0, "failed": 0}
    results = []
    if not sb.configured():
        return {"ok": False, "error": "supabase_not_configured", **counts, "results": results}
    for item in items[: max(1, min(limit, 5))]:
        payload = task_payload(item, task_type, feeder_id, project_type)
        unique_key = payload["payload"]["unique_key"]
        dup = duplicate_task(task_type, unique_key)
        if dup:
            counts["duplicates"] += 1
            results.append({"title": item["title"], "status": "duplicate", "task_request_id": dup.get("id")})
            continue
        _status, rows = sb.insert("task_requests", payload)
        task_id = rows[0]["id"] if isinstance(rows, list) and rows else None
        if not task_id:
            counts["failed"] += 1
            results.append({"title": item["title"], "status": "failed"})
            continue
        _status, events = sb.insert("nexus_events", {
            "lane": payload["payload"]["owner_tab"],
            "source": feeder_id,
            "action": f"{task_type}_created",
            "status": "pending",
            "title": item["title"][:80],
            "summary": f"score {item.get('score')} · {item.get('recommendation', '')[:140]}",
            "payload": {
                "event_type": f"{task_type}_created",
                "task_request_id": task_id,
                "unique_key": unique_key,
                "score": item.get("score"),
                "no_external_ai": True,
            },
        })
        event_id = events[0]["id"] if isinstance(events, list) and events else None
        counts["created"] += 1
        results.append({"title": item["title"], "status": "created", "task_request_id": task_id, "proof_event_id": event_id})
    return {"ok": True, **counts, "results": results}
