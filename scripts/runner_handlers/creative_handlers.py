"""Creative job handlers — run the existing safe Day 4 creative scripts via subprocess."""
from __future__ import annotations

from ._base import run_script, ok, fail


def _campaign_args(job: dict) -> list[str]:
    ck = (job.get("input") or {}).get("campaign_key")
    return ["--campaign-key", ck] if ck else []


def generate_assets(job, ctx) -> dict:
    r = run_script("scripts/creative/generate_campaign_assets.py", _campaign_args(job))
    return ok({"script": "generate_campaign_assets", **r}) if r["returncode"] == 0 else fail("generate failed", r)


def score_assets(job, ctx) -> dict:
    r = run_script("scripts/creative/score_creative_assets.py", _campaign_args(job))
    return ok({"script": "score_creative_assets", **r}) if r["returncode"] == 0 else fail("score failed", r)


def create_approvals(job, ctx) -> dict:
    r = run_script("scripts/creative/create_creative_approvals.py", _campaign_args(job))
    return ok({"script": "create_creative_approvals", **r}) if r["returncode"] == 0 else fail("approvals failed", r)


def create_social_drafts(job, ctx) -> dict:
    r = run_script("scripts/creative/create_social_post_drafts.py", _campaign_args(job))
    return ok({"script": "create_social_post_drafts", **r}) if r["returncode"] == 0 else fail("drafts failed", r)


def revision_request(job, ctx) -> dict:
    # No external work — record the revision request as acknowledged (the asset/approval
    # already carries the feedback). A human/creative pass acts on it next.
    return ok({"note": "Revision request acknowledged and logged. No external work performed.",
               "approval_id": (job.get("input") or {}).get("approval_id")})
