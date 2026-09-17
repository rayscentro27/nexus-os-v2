"""Canonical Research-lane registry and bounded fair selector."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data/runtime/research_lane_registry.json"
LANES = (
    ("BUSINESS_MARKET", "Business Market", "P1"),
    ("FUNDING_LENDER", "Funding and Lender", "P1"),
    ("GRANTS_GOVERNMENT", "Grants and Government", "P2"),
    ("AFFILIATE_REVENUE", "Affiliate Revenue", "P2"),
    ("SEO_SEARCH_DEMAND", "SEO Search Demand", "P2"),
    ("SOCIAL_CONTENT", "Social Content", "P2"),
    ("YOUTUBE_CONTENT", "YouTube Content", "P2"),
    ("COMPETITOR_INTELLIGENCE", "Competitor Intelligence", "P2"),
    ("TRADING_MARKETS", "Trading Markets", "P1"),
    ("GITHUB_TECHNOLOGY", "GitHub Technology", "P2"),
    ("PLATFORM_CAPABILITY_INTELLIGENCE", "Platform Capability Intelligence", "P1"),
)
PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
GOVERNED = ROOT / "data/governed"
LANE_TERMS = {
    "BUSINESS_MARKET": ("business", "market", "opportunity", "realestate", "ecommerce", "saas"),
    "FUNDING_LENDER": ("funding", "lender", "loan", "credit"),
    "GRANTS_GOVERNMENT": ("grant", "government", "regulat", "compliance"),
    "AFFILIATE_REVENUE": ("affiliate", "creator", "commission", "monetiz"),
    "SEO_SEARCH_DEMAND": ("seo", "search", "keyword", "content"),
    "SOCIAL_CONTENT": ("social", "community", "reddit", "creator"),
    "YOUTUBE_CONTENT": ("youtube", "video", "creator"),
    "COMPETITOR_INTELLIGENCE": ("competitor", "competition", "market"),
    "TRADING_MARKETS": ("trading", "forex", "market", "backtest"),
    "GITHUB_TECHNOLOGY": ("github", "software", "repository", "technical"),
    "PLATFORM_CAPABILITY_INTELLIGENCE": ("platform", "software", "api", "automation", "github"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read() -> list[dict[str, Any]]:
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, ValueError, TypeError):
        return []


def _read_governed(name: str) -> list[dict[str, Any]]:
    path = GOVERNED / f"{name}.jsonl"
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return rows


def _parse_age(value: Any, now: datetime) -> float:
    if not value:
        return 0.0
    try:
        return max(0.0, (now - datetime.fromisoformat(str(value).replace("Z", "+00:00"))).total_seconds())
    except (TypeError, ValueError):
        return 0.0


def _lane_context(lane_id: str, now: datetime) -> dict[str, Any]:
    """Read only current V2 work; legacy research_questions is not used."""
    terms = LANE_TERMS.get(lane_id, ())
    watched_sources = 0
    if lane_id == "YOUTUBE_CONTENT":
        try:
            config = json.loads((ROOT / "configs/youtube_research_channels.json").read_text(encoding="utf-8"))
            watched_sources = sum(1 for row in config.get("channels", [])
                                  if isinstance(row, dict) and row.get("enabled") and row.get("approved_by_ray"))
        except (OSError, ValueError, TypeError):
            watched_sources = 0

    def matches(row: dict[str, Any]) -> bool:
        text = " ".join(str(row.get(k, "")) for k in ("source_id", "title", "domain", "intent", "question", "research_intents")) .lower()
        return not terms or any(term in text for term in terms)

    questions = [r for r in _read_governed("research_v2_questions")
                 if str(r.get("status", "")).upper() in {"OPEN", "WAITING_ON_EVIDENCE", "ACTIVE"} and matches(r)]
    investigations = [r for r in _read_governed("research_v2_investigations")
                      if (str(r.get("status", "")).upper() in {"OPEN", "ACTIVE", "IN_PROGRESS", "RESEARCH_MORE"}
                          or (not r.get("status") and r.get("decision") == "RESEARCH_MORE")) and matches(r)]
    followups = [r for r in _read_governed("research_v2_follow_ups")
                 if str(r.get("status", "")).upper() in {"OPEN", "ACTIVE", "WAITING_ON_EVIDENCE"} and matches(r)]
    theses = [r for r in (_read_governed("research_v2_opportunities") + _read_governed("research_v2_strategies"))
              if str(r.get("status", "")).upper() not in {"COMPLETED", "ARCHIVED", "REJECTED"} and matches(r)]
    materialities = [str(r.get("materiality", "")).upper() for r in questions + investigations]
    high = sum(x == "HIGH" for x in materialities)
    medium = sum(x == "MEDIUM" for x in materialities)
    timestamps = [r.get("last_activity") or r.get("updated_at") or r.get("recorded_at") for r in questions + investigations + followups + theses]
    oldest_age = max((_parse_age(x, now) for x in timestamps), default=0.0)
    return {"high": high, "medium": medium, "questions": len(questions), "investigations": len(investigations),
            "followups": len(followups), "theses": len(theses), "oldest_age_seconds": oldest_age,
            "watched_sources": watched_sources}


def ensure_registry() -> list[dict[str, Any]]:
    prior = {str(row.get("lane_id")): row for row in _read() if isinstance(row, dict)}
    timestamp = _now().isoformat()
    rows = []
    for lane_id, name, priority in LANES:
        old = prior.get(lane_id, {})
        rows.append({**old, "schema_version": "nexus.research-lane.v1", "lane_id": lane_id,
                     "name": name, "priority": priority, "enabled": True,
                     "selection_count": int(old.get("selection_count", 0)),
                     "last_run_at": old.get("last_run_at"), "next_due_at": old.get("next_due_at"),
                     "open_work_count": int(old.get("open_work_count", 1)),
                     "last_selection_reason": old.get("last_selection_reason"), "updated_at": timestamp})
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows


def select_lane(*, reason: str = "due_fairness_rotation") -> dict[str, Any]:
    rows = [row for row in ensure_registry() if row.get("enabled")]
    now = _now()

    def age(row: dict[str, Any]) -> float:
        raw = row.get("last_run_at")
        if not raw:
            return 10**12
        try:
            return max(0.0, (now - datetime.fromisoformat(str(raw).replace("Z", "+00:00"))).total_seconds())
        except ValueError:
            return 10**12

    candidates = []
    for row in rows:
        backoff_until = row.get("backoff_until") or row.get("retry_after")
        if backoff_until and _parse_age(backoff_until, now) == 0.0:
            continue
        context = _lane_context(str(row["lane_id"]), now)
        last_age = age(row)
        age_signal = min(35.0, (last_age if last_age < 10**12 else 86400.0) / 3600.0 * 5.0)
        materiality_signal = min(60.0, context["high"] * 30.0 + context["medium"] * 15.0 + context["questions"] * 4.0)
        progression_signal = min(40.0, context["followups"] * 25.0 + context["theses"] * 20.0 + context["investigations"] * 5.0)
        # An approved monitored source is real scheduled work even before a
        # V2 question is attached to its next item. Four approved watchlist
        # channels therefore contribute up to 60 points, bounded like the
        # materiality signal, while fairness debt still prevents lane capture.
        monitored_source_signal = min(60.0, context.get("watched_sources", 0) * 15.0)
        candidates.append((row, context, materiality_signal + monitored_source_signal + progression_signal + age_signal,
                           materiality_signal + monitored_source_signal, progression_signal, age_signal))
    if not candidates:
        candidates = [(row, _lane_context(str(row["lane_id"]), now), 0.0, 0.0, 0.0, 0.0) for row in rows]
    max_count = max(int(row.get("selection_count", 0)) for row, *_ in candidates)
    scored = []
    for row, context, base_score, materiality_signal, progression_signal, age_signal in candidates:
        fairness_debt = min(40.0, max(0, max_count - int(row.get("selection_count", 0))) * 8.0)
        priority_signal = max(0.0, 30.0 - PRIORITY.get(str(row.get("priority", "P4")), 4) * 6.0)
        score = base_score + fairness_debt + priority_signal
        scored.append((score, row, context, materiality_signal, progression_signal, age_signal, fairness_debt))
    score, selected_row, context, materiality_signal, progression_signal, age_signal, fairness_debt = max(
        scored, key=lambda x: (x[0], -int(x[1].get("selection_count", 0)), str(x[1]["lane_id"])))
    selected = dict(selected_row)
    selected["selection_reason"] = reason
    selected["selected_work_class"] = "FOLLOW_UP_OR_THESIS" if context["followups"] or context["theses"] else "EVIDENCE_GAP" if context["high"] or context["medium"] or context["questions"] else "MONITORED_SOURCE" if context.get("watched_sources") else "DISCOVERY"
    selected["materiality_basis"] = {"high_items": context["high"], "medium_items": context["medium"], "open_questions": context["questions"], "watched_sources": context.get("watched_sources", 0)}
    selected["progression_basis"] = {"active_investigations": context["investigations"], "open_followups": context["followups"], "active_theses": context["theses"]}
    selected["age_basis"] = {"lane_age_seconds": round(age(selected), 3), "oldest_matching_item_seconds": round(context["oldest_age_seconds"], 3)}
    selected["fairness_basis"] = {"selection_count": int(selected.get("selection_count", 0)), "fairness_debt": round(fairness_debt, 3)}
    selected["alternatives_considered"] = [{"lane_id": row["lane_id"], "score": round(item_score, 3)} for item_score, row, *_ in sorted(scored, reverse=True, key=lambda x: x[0])[1:4]]
    selected["starvation_age_seconds"] = age(selected)
    selected["selection_score"] = round(score, 3)
    selected["selected_at"] = now.isoformat()
    selected["selection_count"] = int(selected.get("selection_count", 0)) + 1
    selected["last_run_at"] = selected["selected_at"]
    selected["next_due_at"] = (now + timedelta(seconds=30)).isoformat()
    selected["last_selection_reason"] = reason
    REGISTRY_PATH.write_text(json.dumps([selected if row["lane_id"] == selected["lane_id"] else row for row in rows], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return selected


def mark_lane_backoff(lane_id: str, reason: str, *, seconds: int = 1200) -> None:
    """Temporarily remove a failed lane from competition after a retryable error."""
    rows = ensure_registry()
    until = (_now() + timedelta(seconds=max(30, seconds))).isoformat()
    for row in rows:
        if row.get("lane_id") == lane_id:
            row["backoff_until"] = until
            row["last_failure_reason"] = str(reason)[:500]
            row["last_failure_at"] = _now().isoformat()
    REGISTRY_PATH.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
