#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import RUNTIME, SUPABASE_READY, now, read_json, write_json, write_report  # noqa: E402,F401


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def source(source_id: str, lane: str, title: str, source_ref: str, source_type: str, approved: bool = True, **extra) -> dict:
    return {
        "id": source_id,
        "tenant_id": "tenant_demo_goclear",
        "client_id": "synthetic_research_only",
        "lane": lane,
        "category": "research_source",
        "title": title,
        "source_ref": source_ref,
        "source_type": source_type,
        "approved_seed": approved,
        "status": "candidate_discovered" if approved else "approval_required",
        "client_visible": False,
        "approval_required": not approved,
        "created_at": now(),
        **extra,
    }


def discover_sources() -> list[dict]:
    items: list[dict] = []
    registry = read_json(ROOT / "configs/research_source_registry.json", {})
    for lane in registry.get("lanes", []):
        lane_id = lane.get("lane_id", "unknown")
        items.append(source(stable_id("lane", lane_id), lane_id, f"Approved {lane_id.replace('_', ' ')} research lane", f"configs/research_source_registry.json#{lane_id}", "approved_lane_registry", bool(lane.get("approved")), source_paths=lane.get("source_paths", [])))
    youtube_targets = read_json(ROOT / "configs/youtube_source_targets.json", {}).get("targets", [])
    youtube_channels = read_json(ROOT / "configs/youtube_research_channels.json", {}).get("channels", [])
    for item in youtube_targets + youtube_channels:
        if item.get("enabled") and (item.get("approved") or item.get("approved_by_ray")):
            ref = item.get("url") or item.get("video_id") or item.get("id")
            items.append(source(item.get("id", stable_id("youtube", ref)), "youtube", item.get("name", "Approved YouTube source"), ref, item.get("source_type", "channel"), True))
    for config_name, lane in (("repo_research_targets.json", "github"), ("payment_repo_targets.json", "payments")):
        for item in read_json(ROOT / "configs" / config_name, {}).get("targets", []):
            ref = item.get("url") or item.get("id")
            items.append(source(item.get("id", stable_id(lane, ref)), lane, item.get("name", ref), ref, item.get("type", "repository_seed"), True, concepts=item.get("concepts", [])))
    local_roots = [
        (ROOT / "data/sources/youtube_transcripts", "local_sources"),
        (ROOT / "data/sources/notebooklm_exports", "notebooklm"),
        (ROOT / "data/sources/notebooklm_notes", "notebooklm"),
        (ROOT / "data/sources/research_notes", "local_sources"),
        (ROOT / "data/sources/repo_notes", "local_sources"),
    ]
    for base, lane in local_roots:
        if not base.exists():
            continue
        for path in sorted(x for x in base.rglob("*") if x.is_file())[:100]:
            approved = "approved" in path.parts
            rel = str(path.relative_to(ROOT))
            items.append(source(stable_id("local", rel), lane, path.name, rel, path.suffix.lstrip(".") or "file", approved))
    legacy_root = Path.home() / "nexuslive"
    if legacy_root.exists():
        keywords = ("research", "source", "notebook", "credit", "funding", "grant", "trading", "payment", "seo")
        candidates = [p for p in legacy_root.rglob("*") if p.is_file() and any(k in p.name.lower() for k in keywords)]
        for path in sorted(candidates)[:120]:
            items.append(source(stable_id("legacy", str(path)), "old_nexus", path.name, str(path), "legacy_local_file", True))
    deduped = {item["id"]: item for item in items}
    return list(deduped.values())


def score_item(item: dict) -> dict:
    text = f"{item.get('title','')} {item.get('lane','')} {' '.join(item.get('concepts',[]))}".lower()
    def has(*words): return any(word in text for word in words)
    revenue = 72 if has("payment", "funding", "credit", "affiliate", "$97") else 50
    client = 78 if has("credit", "funding", "client", "readiness") else 48
    nexus = 75 if has("automation", "research", "source", "workflow", "notebook") else 55
    credit = 85 if has("credit", "funding", "grant", "lender") else 30
    content = 82 if has("youtube", "seo", "content", "transcript", "notebook") else 45
    partner = 78 if has("payment", "affiliate", "partner", "bank", "vendor") else 35
    actionability = 75 if item.get("approved_seed") else 35
    risk = "medium" if item.get("lane") in {"payments", "trading", "credit_funding_grants"} else "low"
    effort = "small" if item.get("source_type") in {"txt", "md", "json", "repository_seed", "github_topic"} else "medium"
    return {**item, "revenue_potential": revenue, "immediate_actionability": actionability, "client_value": client, "Nexus_upgrade_value": nexus, "credit_funding_value": credit, "content_value": content, "affiliate_partner_value": partner, "implementation_effort": effort, "risk_level": risk, "approval_required": item.get("approval_required", False) or risk == "medium", "recommended_next_action": "Review the source record and approve ingestion/adaptation before any external or client-facing use.", "score": round((revenue + actionability + client + nexus + credit + content + partner) / 7)}


def load_sources() -> list[dict]:
    return read_json(SUPABASE_READY / "research_sources_latest.json", [])


def load_scores() -> list[dict]:
    return read_json(SUPABASE_READY / "research_source_scores_latest.json", [])
