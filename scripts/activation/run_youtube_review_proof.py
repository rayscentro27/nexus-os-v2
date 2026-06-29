#!/usr/bin/env python3
"""Prove the honest local state of Nexus YouTube research/review without network calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
from full_engine_common import SUPABASE, env_presence, read_json, record, write_json, write_report  # noqa: E402


def build() -> dict:
    channel_config = read_json(ROOT / "configs" / "youtube_research_channels.json", {})
    approved_targets = read_json(ROOT / "tests" / "fixtures" / "research" / "ray_watched_youtube_channels.json", [])
    approved_targets = [item for item in approved_targets if item.get("enabled") and item.get("approved_by_ray")]
    metadata_report = read_json(ROOT / "reports" / "runtime" / "youtube_metadata_check_latest.json", {})
    transcript_path = ROOT / "tests" / "fixtures" / "research" / "sample_youtube_transcript.txt"
    transcript = transcript_path.read_text(errors="ignore") if transcript_path.exists() else ""
    connector_present = env_presence("YOUTUBE_API_KEY")["YOUTUBE_API_KEY"]
    real_metadata = [item for item in metadata_report.get("candidates", []) if item.get("proof_source") not in {"not_configured_fallback", "sample", "fixture"}]
    sample_reviewed = bool(transcript.strip())
    review_items = []
    if sample_reviewed:
        keywords = [term for term in ("business profile", "EIN", "bank account", "vendor accounts", "documentation", "funding readiness") if term.lower() in transcript.lower()]
        review_items.append(record("youtube-fixture-review-1", "youtube_review_item", "Local sample transcript: Business Credit Readiness Checklist for New LLCs",
            status="generated_report_only", source="tests/fixtures/research/sample_youtube_transcript.txt", real_video=False,
            fixture_only=True, review_type="local_fixture_transcript", extracted_topics=keywords,
            summary="Deterministic review of a local sample fixture; this is not proof of a currently reviewed real YouTube video.",
            recommended_next_action="Replace with an approved real transcript or metadata record."))
    queued = [record(f"youtube-queue-{i+1}", "youtube_queue_item", target["resource_name"], status="queue_only_no_real_review",
        source=target["resource_url"], real_video=False, approved_by_ray=True, connector_missing=not connector_present,
        summary=target["notes"], recommended_next_action="Import bounded metadata/transcript through an approved connector or manual source.") for i, target in enumerate(approved_targets)]
    opportunities = [record("youtube-opportunity-fixture", "youtube_opportunity", "$97 Business Credit Readiness Checklist content angle",
        status="generated_report_only", source="local_sample_transcript", fixture_only=True, score=74,
        summary="Fixture-derived opportunity: checklist lead magnet and educational short video.",
        recommended_next_action="Do not publish; validate against a real approved source first.")]
    ideas = [record(f"youtube-content-idea-{i+1}", "youtube_content_idea", title, status="generated_report_only",
        source="local_sample_transcript", fixture_only=True, approval_required=True,
        recommended_next_action="Ray reviews after real-source validation.") for i, title in enumerate([
            "Business credit readiness checklist article", "Five documentation gaps before funding review", "Why new LLCs should review readiness before applying"
        ])]
    approvals = [record("youtube-approval-activate-real-source", "youtube_approval_card", "Approve first real YouTube metadata/transcript source",
        status="ready_for_Ray_review", priority="high", risk_level="medium", automation_level="approval_gated", approval_required=True,
        summary="Select one approved public video/channel and authorize bounded metadata or manual transcript intake—no media download.",
        recommended_next_action="Approve Credit Plug or another source plus intake method.")]
    for name, data in (("youtube_review_items_latest.json", review_items), ("youtube_opportunities_latest.json", opportunities),
                       ("youtube_approval_cards_latest.json", approvals), ("youtube_content_ideas_latest.json", ideas)):
        write_json(SUPABASE / name, data)
    report = {
        "ok": True, "status": "queue_only_no_real_review", "youtube_engine_found": True,
        "channels_configured": len(approved_targets), "videos_configured": 0, "metadata_available": bool(real_metadata),
        "transcripts_available": sample_reviewed, "real_source_transcripts_available": False,
        "api_or_connector_configured": connector_present, "real_video_review_performed": False,
        "review_mode": "queue_only_no_real_review", "reviewed_items_count": len(review_items),
        "reviewed_items_are_fixture_only": True, "queued_items_count": len(queued),
        "opportunities_created_count": len(opportunities), "content_ideas_created_count": len(ideas),
        "approval_cards_created_count": len(approvals),
        "blocked_reason": "Four real channel targets are approved, but no YouTube API/metadata connector or approved real transcript/video record is available. Existing metadata candidates are fallback placeholders.",
        "next_required_action": "Ray selects the first real source and approves bounded metadata intake or a manual transcript import.",
        "is_youtube_reviewing_videos_right_now": False,
        "exactly_reviewed": ["tests/fixtures/research/sample_youtube_transcript.txt (local fixture only)"],
        "queued_targets": [item["resource_name"] for item in approved_targets],
        "missing": ["YOUTUBE_API_KEY or approved metadata connector", "approved real video metadata/transcript record"],
        "external_action_performed": False, "public_content_published": False,
        "summary": "YouTube targets and review code exist, but no real video is being reviewed now; one local sample transcript was analyzed as fixture proof only."
    }
    write_json(SUPABASE / "youtube_research_queue_latest.json", queued)
    write_report("youtube_review_proof", "YouTube Review Proof", report, {"Reviewed": review_items, "Queued targets": queued, "Opportunities": opportunities})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = build(); print(json.dumps(report, indent=2) if args.json else report["summary"]); return 0


if __name__ == "__main__":
    raise SystemExit(main())
