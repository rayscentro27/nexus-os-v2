#!/usr/bin/env python3
"""Bounded, real-source Alpha heartbeat.

The heartbeat seeds Ray's registry once, checks a small deterministic slice of
the monitored sources, persists evidence/claims, and creates governed
downstream candidates. It never publishes, installs, or creates accounts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from alpha.alpha_discovery import claim_record, content_record, persist_claim, persist_content  # noqa: E402
from nexus_agent_platform.governed.persistence import append_record, read_records  # noqa: E402

REGISTRY = ROOT / "data" / "runtime" / "alpha_source_registry.json"
ACTIVITY = ROOT / "reports" / "runtime" / "alpha_research_activity_latest.json"
REPAIR_RECEIPT = ROOT / "reports" / "runtime" / "alpha_registry_repair_latest.json"
RAY_YOUTUBE = [
    "https://www.youtube.com/@sharbelxyz/videos", "https://www.youtube.com/@Buildonaut-AI/videos",
    "https://www.youtube.com/@StedmanWaiters/videos", "https://www.youtube.com/@Codacus/videos",
    "https://www.youtube.com/@JulianGoldieSEO/videos", "https://www.youtube.com/@Successwithstephensmith/videos",
    "https://www.youtube.com/@CreditWithColin/videos", "https://www.youtube.com/@thebuildai/videos",
    "https://www.youtube.com/@JTHustlez/videos", "https://www.youtube.com/@LYFEAccounting/videos",
    "https://www.youtube.com/@creditplug/videos", "https://www.youtube.com/@marvinfrancois1/videos",
    "https://www.youtube.com/@jaredrhod/videos", "https://www.youtube.com/@LuukAlleman/videos",
    "https://www.youtube.com/@MonicaMain/videos", "https://www.youtube.com/@alecdelpuech/videos",
    "https://www.youtube.com/@moneytalkrashad/videos", "https://www.youtube.com/@RobertsTechToolbox/videos",
    "https://www.youtube.com/@TheMovingAverage/videos", "https://www.youtube.com/@TradingStrategyTesting/videos",
]
RAY_GITHUB = ["https://github.com/mvanhorn/last30days-skill", "https://github.com/sushantkarn/SEO-engine"]


def iso() -> str: return datetime.now(timezone.utc).isoformat()
def digest(value: Any) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def seed_registry() -> list[dict[str, Any]]:
    prior = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else []
    # The canonical registry has existed in both the original `url` shape and
    # the safer source-intake `url_or_safe_identifier` shape. Normalize at this
    # boundary instead of allowing one malformed/ newer row to kill Alpha.
    by_url: dict[str, dict[str, Any]] = {}
    repaired = 0
    skipped = 0
    for row in prior:
        if not isinstance(row, dict):
            skipped += 1
            continue
        source_url = row.get("url") or row.get("source_url") or row.get("url_or_safe_identifier")
        if not isinstance(source_url, str) or not source_url.strip():
            skipped += 1
            continue
        source_url = source_url.strip()
        normalized = dict(row)
        if normalized.get("url") != source_url:
            normalized["url"] = source_url
            repaired += 1
        by_url[source_url] = normalized
    urls = [(url, "GITHUB_REPO", "AI_NEXUS") for url in RAY_GITHUB] + [(url, "YOUTUBE_CHANNEL", "BUSINESS") for url in RAY_YOUTUBE]
    for url, source_type, lane in urls:
        by_url.setdefault(url, {"source_id": "src_" + digest(url), "source_type": source_type, "url": url,
                                 "name": url.rstrip("/").split("/")[-1], "added_by": "RAY_CURATED",
                                 "added_at": iso(), "priority": "P0_RAY_DIRECT", "monitoring_enabled": True,
                                 "last_checked": None, "last_processed_item": None, "status": "ACTIVE",
                                 "research_lane": lane, "baseline_limit": 10 if source_type == "YOUTUBE_CHANNEL" else None})
    records = list(by_url.values()); REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(records, indent=2) + "\n")
    REPAIR_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    REPAIR_RECEIPT.write_text(json.dumps({
        "schema_version": "nexus.alpha-registry-repair.v1",
        "timestamp": iso(),
        "input_rows": len(prior),
        "output_rows": len(records),
        "rows_normalized": repaired,
        "rows_skipped": skipped,
        "parent_process": "alpha_research_heartbeat",
        "failure_class": "MALFORMED_PRIOR_REGISTRY_SHAPE",
        "continuation": "ALPHA_RETRY_ALLOWED",
        "no_external_action": True,
    }, indent=2) + "\n")
    return records


def fetch_github(url: str) -> dict[str, Any]:
    slug = url.removeprefix("https://github.com/").strip("/")
    req = urllib.request.Request("https://api.github.com/repos/" + slug, headers={"User-Agent": "NexusAlphaResearch/1.0", "Accept": "application/vnd.github+json"})
    try:
        try:
            with urllib.request.urlopen(req, timeout=20) as response: data = json.loads(response.read().decode())
        except Exception:
            api = subprocess.run(["curl", "-L", "--fail", "--max-time", "20", "-A", "NexusAlphaResearch/1.0", "-sS", "https://api.github.com/repos/" + slug], capture_output=True, timeout=25, check=False)
            if api.returncode != 0: raise RuntimeError("github_api_unavailable")
            data = json.loads(api.stdout.decode("utf-8", "replace"))
        readme_req = urllib.request.Request("https://raw.githubusercontent.com/" + slug + "/HEAD/README.md", headers={"User-Agent": "NexusAlphaResearch/1.0"})
        try:
            with urllib.request.urlopen(readme_req, timeout=20) as response: readme = response.read(20000).decode("utf-8", "replace")
        except Exception:
            raw = subprocess.run(["curl", "-L", "--fail", "--max-time", "20", "-A", "NexusAlphaResearch/1.0", "-sS", "https://raw.githubusercontent.com/" + slug + "/HEAD/README.md"], capture_output=True, timeout=25, check=False)
            readme = raw.stdout.decode("utf-8", "replace")[:20000] if raw.returncode == 0 else "README unavailable"
        return {"ok": True, "url": url, "title": data.get("full_name", slug), "excerpt": readme[:1600], "sha": data.get("pushed_at"), "stars": data.get("stargazers_count"), "retrieved_at": iso(), "source_type": "GITHUB_REPO"}
    except Exception as exc: return {"ok": False, "url": url, "error": type(exc).__name__, "retrieved_at": iso(), "source_type": "GITHUB_REPO"}


def fetch_youtube_channel(url: str) -> dict[str, Any]:
    command = ["/usr/local/bin/yt-dlp", "--flat-playlist", "--playlist-end", "10", "--dump-single-json", "--skip-download", "--no-warnings", "--no-progress", url]
    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=75, check=False)
        if proc.returncode != 0: return {"ok": False, "url": url, "error": "yt_dlp_exit_" + str(proc.returncode), "retrieved_at": iso(), "source_type": "YOUTUBE_CHANNEL"}
        data = json.loads(proc.stdout)
        entries = [{"video_id": item.get("id"), "title": item.get("title"), "url": item.get("url") or ("https://www.youtube.com/watch?v=" + item.get("id", "")), "published_at": item.get("timestamp") or item.get("upload_date")} for item in (data.get("entries") or []) if item.get("id")]
        return {"ok": True, "url": url, "title": data.get("title", url), "entries": entries[:10], "retrieved_at": iso(), "source_type": "YOUTUBE_CHANNEL"}
    except Exception as exc: return {"ok": False, "url": url, "error": type(exc).__name__, "retrieved_at": iso(), "source_type": "YOUTUBE_CHANNEL"}


def persist_finding(source: dict[str, Any], result: dict[str, Any], item: dict[str, Any] | None = None) -> dict[str, Any]:
    url = item.get("url") if item else result["url"]
    excerpt = (item.get("title") if item else result.get("excerpt", "")) or ""
    content = content_record(url, "youtube_video" if item else result["source_type"].lower(), excerpt or result.get("title", url),
                             source_id=source["source_id"], source_url=source["url"], retrieved_at=result["retrieved_at"],
                             content_hash=digest([url, excerpt]), evidence_class="RAY_CURATED_SOURCE", retrieval_status="RETRIEVED",
                             published_at=item.get("published_at") if item else result.get("sha"))
    stored = persist_content(content)
    claim = claim_record(content["content_id"], excerpt[:1200] or "Source was checked; no specific claim extracted.",
                         "source_observation", source_id=source["source_id"], category=source["research_lane"], importance="LOW",
                         evidence=[{"url": url, "retrieved_at": result["retrieved_at"], "support_or_contradict": "OBSERVATION", "independence": "single_source", "recency": "CURRENT", "confidence": "MEDIUM"}],
                         model_output_not_evidence=True)
    claim["verification_status"] = "UNVERIFIED"
    claim["unknowns"] = ["independent verification and commercial outcome remain unknown"]
    claim["recommended_next_test"] = "Obtain an independent source before promotion."
    claim_stored = persist_claim(claim)
    return {"url": url, "content_id": content["content_id"], "content_stored": stored["stored"], "claim_id": claim["claim_id"], "claim_stored": claim_stored["stored"], "new": stored["stored"]}


def run(max_channels: int = 4) -> dict[str, Any]:
    registry = [source for source in seed_registry() if not source.get("url", "").startswith("https://example/")]; checked = []; findings = []
    active = [x for x in registry if x["monitoring_enabled"]]
    for source in [x for x in active if x["source_type"] == "GITHUB_REPO"]:
        result = fetch_github(source["url"]); checked.append(result)
        if result.get("ok"):
            finding = persist_finding(source, result)
            if finding["new"]: findings.append(finding)
        source["last_checked"] = result.get("retrieved_at")
        source["last_processed_item"] = result.get("sha") or source.get("last_processed_item")
    for source in [x for x in active if x["source_type"] == "YOUTUBE_CHANNEL"][:max_channels]:
        result = fetch_youtube_channel(source["url"]); checked.append(result)
        if result.get("ok"):
            for item in result.get("entries", [])[:10]:
                finding = persist_finding(source, result, item)
                if finding["new"]: findings.append(finding)
            source["last_processed_item"] = (result.get("entries") or [{}])[0].get("video_id")
        source["last_checked"] = result.get("retrieved_at")
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n")
    chain_id = "chain_" + digest(findings[:3])
    if findings:
        append_record("alpha_research", {"research_id": "research_" + digest(findings), "theme": "AI_NEXUS", "question": "What current source signals can reduce Nexus uncertainty?", "source_refs": [x["url"] for x in findings[:8]], "claims": [x["claim_id"] for x in findings[:8]], "status": "CHALLENGED", "chain_id": chain_id, "support": [], "contrary_evidence": [], "unknowns": ["independent verification pending"], "created_at": iso()})
        append_record("alpha_outcomes", {"outcome_id": "handoff_" + digest(chain_id), "research_id": "research_" + digest(findings), "route": "growth_experiment_candidate", "handoff_type": "EVIDENCE_PACKET", "hypothesis": "Current source observations may reveal bounded testable improvements; this is not a business verdict.", "unknown_variables": ["market response", "independent source support"], "improvement_challenge": "Can Growth improve this hypothesis enough to justify a no-spend test?", "status": "CANDIDATE", "lineage_id": chain_id, "created_at": iso()})
    activity = {"generated_at": iso(), "sources_monitored": len(active), "sources_checked": len(checked), "new_items_discovered": len(findings), "items_processed": len(findings), "unchanged_items_skipped": max(0, sum((len(x.get("entries", [])) if x.get("source_type") == "YOUTUBE_CHANNEL" else 1) for x in checked) - len(findings)), "baseline_backlog": "latest_10_per_youtube_channel", "research_chains_opened": 1 if findings else 0, "claims_extracted": len(findings), "claims_supported": 0, "claims_contradicted": 0, "claims_unresolved": len(findings), "hypotheses_produced": 1 if findings else 0, "handoffs_created": 1 if findings else 0, "priority_order": ["P0_RAY_DIRECT", "P1_ACTIVE_RESEARCH_CHAIN", "P2_NEW_SOURCE_DELTA", "P3_BASELINE_BACKLOG", "P4_DISCOVERED_SOURCE_EXPANSION"], "no_queue_does_not_mean_no_research": True, "real_external_sources": True}
    ACTIVITY.parent.mkdir(parents=True, exist_ok=True); ACTIVITY.write_text(json.dumps(activity, indent=2) + "\n")
    return {"ok": any(result.get("ok") for result in checked), "activity": activity, "checked": checked, "findings": findings, "registry": str(REGISTRY), "no_external_action": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--max-channels", type=int, default=4); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    result = run(args.max_channels)
    print(json.dumps(result, indent=2)); raise SystemExit(0 if result.get("ok") else 2)
