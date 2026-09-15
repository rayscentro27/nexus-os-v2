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
                                   evidence_score, classify_claim, extract_evidence_spans, extract_related_links, extract_named_entities, generated_questions,
                                   extract_forum_thread, source_adapter_for_url)
from nexus_agent_platform.governed.persistence import append_record, read_records
from nexus_agent_platform.research_alpha_pipeline import evaluate_pending
from alpha.youtube_provenance import persist_asr_required, persist_transcript_artifact, persist_validation

def run(theme: str, question: str, youtube_url: str | None, page_urls: list[str], forum_urls: list[str], github_urls: list[str], support_urls: list[str], contrary_urls: list[str], window: str) -> dict:
    persist_registry(); contents=[]; claims=[]; retrieval=[]
    urls=[]
    if youtube_url: urls.append((youtube_url, "YOUTUBE"))
    urls += [(u, "FORUM" if any(x in u.lower() for x in ("reddit.", "forum", "discussion")) else "PUBLIC_WEB") for u in page_urls + forum_urls]
    urls += [(u, "GITHUB") for u in github_urls]
    for url, kind in urls[:bounded_budget()["MAX_DISCOVERY_RESULTS"]]:
        if kind == "YOUTUBE":
            result = youtube_transcript(url); retrieval.append({"kind": kind, "url": url, **{k:v for k,v in result.items() if k != "excerpt"}})
            if kind == "YOUTUBE" and not result.get("ok"):
                persist_asr_required(video={"video_id": result.get("video_id"), "video_url": url, "channel_name": result.get("channel"), "created_at": result.get("retrieved_at"), "next_attempt_at": result.get("retrieved_at")}, failure_reason=str(result.get("status") or "CAPTION_UNAVAILABLE"))
            if not result.get("ok"): continue
            source_id = digest(url, "source")
            video_text = result.get("transcript") or result.get("excerpt", "")
            description = result.get("description", "")
            video = {"video_id": result.get("video_id"), "video_url": url, "video_title": result.get("title") or result.get("video_id"), "channel_name": result.get("channel"), "published_at": result.get("upload_date")}
            transcript = persist_transcript_artifact(ROOT, video=video, result=result)
            content = content_record(url, "youtube_video", result.get("video_id", url), transcript_hash=result.get("transcript_hash"), transcript_status=result.get("status"), transcript_provenance=("local faster-whisper ASR fallback" if result.get("transcript_method") == "LOCAL_ASR" else "yt-dlp caption retrieval"), transcript_method=result.get("transcript_method", "AUTO_CAPTION"), transcript_artifact=result.get("transcript_artifact"), excerpt=video_text, content_hash=result.get("transcript_hash"), evidence_spans=extract_evidence_spans(video_text, source_id=source_id, source_url=url, title=result.get("video_id", url), fetched_at=result.get("retrieved_at"), content_hash=result.get("transcript_hash")), related_source_candidates=extract_related_links(description, source_id, lane=theme), named_entities=extract_named_entities(video_text + " " + description), description=description, discovery_window=window)
            content.update({"video_id": result.get("video_id"), "channel_name": result.get("channel"), "video_title": result.get("title") or result.get("video_id"), "published_at": result.get("upload_date"), **transcript, "review_status": "REVIEW_IN_PROGRESS"})
            claim_text = result.get("excerpt", "")[:600] or "Video content was retrieved; specific performance claims require independent verification."
        else:
            result = retrieve_page(url); retrieval.append({"kind": kind, "url": url, "source_adapter": source_adapter_for_url(url), **{k:v for k,v in result.items() if k != "excerpt"}})
            if not result.get("ok"): continue
            thread = extract_forum_thread(result.get("raw_html", ""), result.get("url", url), fetched_at=result.get("retrieved_at")) if kind == "FORUM" else None
            source_text = (thread.get("text") if thread else result.get("text", result.get("excerpt", ""))) or ""
            source_title = (thread.get("thread_title") if thread else result.get("title", url)) or url
            content = content_record(url, "forum_thread" if kind == "FORUM" else ("github_repo" if kind == "GITHUB" else "web_page"), source_title, published_at=None, excerpt=source_text[:1600], content_hash=result.get("text_hash"), evidence_spans=extract_evidence_spans(source_text, source_id=digest(result.get("url", url), "source"), source_url=result.get("url", url), title=source_title, fetched_at=result.get("retrieved_at"), content_hash=result.get("text_hash")), related_source_candidates=extract_related_links(result.get("raw_html", ""), digest(result.get("url", url), "source"), lane=theme), discovery_window=window, evidence_class="COMMUNITY_EXPERIENCE" if kind == "FORUM" else "RETRIEVED_SOURCE", source_adapter=source_adapter_for_url(url), thread_structure=thread)
            claim_text = result.get("excerpt", "")[:600]
        content.update({"discovery_priority_score": .72, "independence_group": content.get("source_family"), "retrieval_status": "RETRIEVED"})
        persist_content(content); contents.append(content)
        spans = content.get("evidence_spans") or []
        claim = claim_record(content["content_id"], claim_text, "discovered_claim", source_id=content["source_id"], source_url=content["canonical_url"], source_title=content["title"], evidence=spans[:2], evidence_text=(spans[0].get("evidence_text") if spans else claim_text), evidence_score=0.0, evidence_status="PENDING_VALIDATION", verification_status="PENDING_VALIDATION", source_type=kind, independence_group=content.get("independence_group"), video_id=content.get("video_id"), source_transcript_path=content.get("transcript_artifact_path"), source_timestamp_or_segment=(spans[0].get("evidence_start") if spans else None), extracted_at=content.get("transcript_fetched_at"), extraction_method="bounded_transcript_excerpt")
        persist_claim(claim); claims.append(claim)
        for generated_question in generated_questions(content=content, spans=spans, related=content.get("related_source_candidates") or []):
            append_record("research_questions", generated_question)
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
        claim.update(persist_validation(claim=claim, video={"video_id": claim.get("video_id")}, supporting=support, contradicting=contrary, at=claim.get("extracted_at") or __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
        claim["claims_extracted_count"] = 1
        for content in contents:
            if content.get("content_id") == claim.get("content_id"):
                content["review_status"] = "REVIEW_COMPLETE" if claim.get("validation_result") == "VALIDATED" else "FOLLOW_UP_REQUIRED"
                content["validation_attempted"] = True
                content["validation_result"] = claim.get("validation_result")
                content["evidence_source_count"] = claim.get("evidence_source_count", 0)
                persist_content(content)
                break
        persist_claim(claim)
        if support or contrary:
            append_record("research_cross_checks", {"cross_check_id": digest({"claim_id": claim["claim_id"], "support": support, "contrary": contrary}, "crosscheck"), "claim_id": claim["claim_id"], "primary_source_id": claim.get("source_id"), "secondary_sources": support + contrary, "verification_status": claim["verification_status"], "evidence_1": claim.get("evidence", [])[:1], "evidence_2": support + contrary, "confidence_before": 0.2, "confidence_after": claim.get("evidence_score", 0.0), "created_at": claim.get("created_at", "") or __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()})
    research = create_research(theme, question, contents, claims, window)
    alpha_result = evaluate_pending(max_items=max(1, len(contents))) if contents else {"evaluations_created": [], "evaluated_count": 0}
    evaluations = [row for row in alpha_result.get("evaluations_created", []) if row.get("research_id") == research.get("research_id")]
    route = next((row.get("next_route") for row in evaluations if row.get("next_route")), None)
    research["routing"] = route
    state = "ROUTED" if route else ("EVALUATED_REJECTED" if evaluations and evaluations[0].get("decision") == "REJECTED" else "AWAITING_ALPHA")
    append_record("alpha_discovery_queue", {"queue_id": digest(research["research_id"], "queue"), "research_id": research["research_id"], "state": state, "content_ids": [x["content_id"] for x in contents], "created_at": research["created_at"], "alpha_evaluation_ids": [row.get("evaluation_id") for row in evaluations]})
    zero_output = bool(urls) and not contents
    return {"ok": bool(contents), "theme": theme, "window": window, "question": question, "research": research, "content_count": len(contents), "claim_count": len(claims), "retrieval": retrieval, "budget": bounded_budget(), "alpha": alpha_result, "no_external_action": True, "zero_output_anomaly": zero_output, "zero_output_recovery": {"caption_failures": sum(1 for x in retrieval if x.get("caption_failure_type")), "asr_attempts": sum(1 for x in retrieval if x.get("transcript_method") == "LOCAL_ASR"), "media_retrieval_failures": sum(1 for x in retrieval if x.get("status") in {"MEDIA_RETRIEVAL_FAILED", "MEDIA_FORMAT_DISCOVERY_FAILED"}), "ffmpeg_failures": sum(1 for x in retrieval if x.get("status") == "FFMPEG_FAILED"), "asr_failures": sum(1 for x in retrieval if str(x.get("status", "")).startswith("ASR_") )}}

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--theme", choices=["TRADING","BUSINESS","MARKETING","AI_NEXUS"], required=True); p.add_argument("--question", required=True); p.add_argument("--youtube-url"); p.add_argument("--page-url", action="append", default=[]); p.add_argument("--forum-url", action="append", default=[]); p.add_argument("--github-url", action="append", default=[]); p.add_argument("--support-url", action="append", default=[]); p.add_argument("--contrary-url", action="append", default=[]); p.add_argument("--window", default="LAST_30_DAYS"); p.add_argument("--json", action="store_true"); a=p.parse_args(); result=run(a.theme,a.question,a.youtube_url,a.page_url,a.forum_url,a.github_url,a.support_url,a.contrary_url,a.window); print(json.dumps(result,indent=2) if a.json else f"Alpha discovery {'PASS' if result['ok'] else 'NO_CONTENT'}: {result['research']['research_id']}"); return 0 if result["ok"] else 2
if __name__ == "__main__": raise SystemExit(main())
