"""Intake / orientation job handlers — run the Day 8 deterministic scripts via subprocess.
No external model calls, no publishing."""
from __future__ import annotations

from ._base import run_script, ok, fail


def transcript_intake_review(job, ctx) -> dict:
    inp = job.get("input") or {}
    if inp.get("intake_event_id"):
        args = ["--intake-event-id", str(inp["intake_event_id"])]
    elif inp.get("text"):
        args = ["--text", str(inp["text"]), "--title", str(inp.get("title", "intake transcript"))]
    else:
        args = ["--sample"]
    r = run_script("scripts/intake/review_transcript.py", args)
    return ok({"script": "review_transcript", **r}) if r["returncode"] == 0 else fail("review failed", r)


def claim_risk_classify(job, ctx) -> dict:
    text = (job.get("input") or {}).get("text", "")
    if not text:
        return fail("no text in job input")
    r = run_script("scripts/compliance/classify_claim_risk.py", ["--text", str(text)])
    return ok({"script": "classify_claim_risk", **r}) if r["returncode"] == 0 else fail("classify failed", r)


def service_opportunity_extract(job, ctx) -> dict:
    inp = job.get("input") or {}
    if inp.get("review_id"):
        args = ["--review-id", str(inp["review_id"])]
    elif inp.get("text"):
        args = ["--text", str(inp["text"]), "--name", str(inp.get("name", "Service Opportunity"))]
    else:
        args = ["--sample"]
    r = run_script("scripts/intake/extract_service_opportunity.py", args)
    return ok({"script": "extract_service_opportunity", **r}) if r["returncode"] == 0 else fail("extract failed", r)
