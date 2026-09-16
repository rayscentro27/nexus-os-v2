#!/usr/bin/env python3
"""Run one approved real YouTube video through the no-caption ASR fallback."""
from __future__ import annotations

import json

from youtube_full_pipeline import process_youtube_video


def main() -> int:
    result = process_youtube_video(
        {
            "video_id": "PVdS3r1EjrU",
            "url": "https://www.youtube.com/watch?v=PVdS3r1EjrU",
            "channel": "Credit Plug",
            "title": "The Key to Unlimited Funding The Real Hack",
        },
        metadata_override={
            "id": "PVdS3r1EjrU",
            "title": "The Key to Unlimited Funding The Real Hack",
            "channel": "Credit Plug",
            "description": "Approved real YouTube video selected from the Credit Plug research source.",
        },
        force_asr=True,
    )
    report = {
        "video_id": result.get("video_id"),
        "caption_result": "BYPASSED_EXPLICIT_ASR_CANARY",
        "audio_acquired": result.get("audio_acquired", False),
        "asr_backend": result.get("asr_backend", "NONE"),
        "asr_completed": result.get("audio_acquired", False) and result.get("transcript_acquired", False),
        "transcript_word_count": result.get("transcript_word_count"),
        "summary_created": result.get("summary_created", False),
        "structured_extraction_created": result.get("structured_extraction_created", False),
        "scored": result.get("scored", False),
        "artifacts_persisted": result.get("new_artifact_set_created", False),
        "final_status": result.get("processing_status"),
        "alpha_invoked": False,
        "opportunities_created": 0,
        "work_orders_created": 0,
        "result": result,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["final_status"] == "FULLY_PROCESSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
