#!/usr/bin/env python3
"""Run one bounded, read-only Alpha proactive discovery cycle.

The CLI is intentionally explicit about URLs and bounded inputs so scheduled
operation cannot become an unbounded crawler. Provider-specific discovery can
feed the same records through this contract.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from alpha.alpha_discovery import (bounded_budget, claim_record, content_record, create_research, digest,
                                   persist_claim, persist_content, persist_registry, route_finding, youtube_transcript, retrieve_page,
                                   evidence_score, classify_claim)
from nexus_agent_platform.governed.persistence import append_record, read_records

def run(theme: str, question: str, youtube_url: str | None, page_urls: list[str], forum_urls: list[str], github_urls: list[str], support_urls: list[str], contrary_urls: list[str], window: str) -> dict:
    persist_registry(); contents=[]; claims=[]; retrieval=[]
    urls=[]
    if youtube_url: urls.append((youtube_url, "YOUTUBE"))
    urls += [(u, "FORUM" if any(x in u.lower() for x in ("reddit.", "forum", "discussion")) else "PUBLIC_WEB") for u in page_urls + forum_urls]
    urls += [(u, "GITHUB") for u in github_urls]
    for url, kind in urls[:bounded_budget()["MAX_DISCOVERY_RESULTS"]]:
        if kind == "YOUTUBE":
            result = youtube_transcript(url); retrieval.append({"kind": kind, "url": url, **{k:v for k,v in result.items() if k != "excerpt"}})
            if not result.get("ok"): continue
            content = content_record(url, "youtube_video", result.get("video_id", url), transcript_hash=result.get("transcript_hash"), transcript_status=result.get("status"), transcript_provenance="yt-dlp caption retrieval", excerpt=result.get("excerpt", ""), content_hash=result.get("transcript_hash"), discovery_window=window)
            claim_text = result.get("excerpt", "")[:600] or "Video content was retrieved; specific performance claims require independent verification."
        else:
            result = retrieve_page(url); retrieval.append({"kind": kind, "url": url, **{k:v for k,v in result.items() if k != "excerpt"}})
            if not result.get("ok"): continue
            content = content_record(url, "forum" if kind == "FORUM" else ("github_repo" if kind == "GITHUB" else "web_page"), result.get("title", url), published_at=None, excerpt=result.get("excerpt", ""), content_hash=result.get("text_hash"), discovery_window=window, evidence_class="COMMUNITY_EXPERIENCE" if kind == "FORUM" else "RETRIEVED_SOURCE")
            claim_text = result.get("excerpt", "")[:600]
        content.update({"discovery_priority_score": .72, "independence_group": content.get("source_family"), "retrieval_status": "RETRIEVED"})
        persist_content(content); contents.append(content)
        claim = claim_record(content["content_id"], claim_text, "discovered_claim", evidence_score=0.0, evidence_status="UNVERIFIED", source_type=kind, independence_group=content.get("independence_group"))
        persist_claim(claim); claims.append(claim)
    support = []
    contrary = []
    for url in support_urls[:2]:
        result = retrieve_page(url); retrieval.append({"kind": "VERIFICATION_SUPPORT", "url": url, **{k:v for k,v in result.items() if k != "excerpt"}})
        if result.get("ok"): support.append({"url": url, "source_family": result.get("url", url).split('/')[2], "authority": "retrieved"})
    for url in contrary_urls[:2]:
        result = retrieve_page(url); retrieval.append({"kind": "VERIFICATION_CONTRARY", "url": url, **{k:v for k,v in result.items() if k != "excerpt"}})
        if result.get("ok"): contrary.append({"url": url, "source_family": result.get("url", url).split('/')[2], "authority": "retrieved"})
    for claim in claims:
        claim["supporting_sources"] = support; claim["contrary_sources"] = contrary
        claim["evidence_score"] = evidence_score(authority=.65 if support else .2, independence=min(1, len({x['source_family'] for x in support}) / 2), currentness=.9, directness=.7 if support else .2, methodology=.6, conflict=.5 if contrary else 0)
        claim["verification_status"] = classify_claim(claim, support, contrary)
    research = create_research(theme, question, contents, claims, window)
    route = route_finding(theme, research["research_id"], question) if contents else None
    research["routing"] = route
    append_record("alpha_discovery_queue", {"queue_id": digest(research["research_id"], "queue"), "research_id": research["research_id"], "state": "ROUTED" if route else "REJECTED", "content_ids": [x["content_id"] for x in contents], "created_at": research["created_at"]})
    return {"ok": bool(contents), "theme": theme, "window": window, "question": question, "research": research, "content_count": len(contents), "claim_count": len(claims), "retrieval": retrieval, "budget": bounded_budget(), "no_external_action": True}

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--theme", choices=["TRADING","BUSINESS","MARKETING","AI_NEXUS"], required=True); p.add_argument("--question", required=True); p.add_argument("--youtube-url"); p.add_argument("--page-url", action="append", default=[]); p.add_argument("--forum-url", action="append", default=[]); p.add_argument("--github-url", action="append", default=[]); p.add_argument("--support-url", action="append", default=[]); p.add_argument("--contrary-url", action="append", default=[]); p.add_argument("--window", default="LAST_30_DAYS"); p.add_argument("--json", action="store_true"); a=p.parse_args(); result=run(a.theme,a.question,a.youtube_url,a.page_url,a.forum_url,a.github_url,a.support_url,a.contrary_url,a.window); print(json.dumps(result,indent=2) if a.json else f"Alpha discovery {'PASS' if result['ok'] else 'NO_CONTENT'}: {result['research']['research_id']}"); return 0 if result["ok"] else 2
if __name__ == "__main__": raise SystemExit(main())
