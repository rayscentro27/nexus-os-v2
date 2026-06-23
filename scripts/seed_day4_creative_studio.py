#!/usr/bin/env python3
"""Nexus OS v2 — Day 4 idempotent seed: the flagship GoClear/Apex Funding Readiness campaign.

Seeds campaign + brief + one studio_output (audio overview) + a creative pipeline job stub +
proof event. Generated assets, scores, and approvals are produced by the creative scripts
(generate_campaign_assets.py -> score_creative_assets.py -> create_creative_approvals.py).

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day4_creative_studio.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, get, insert, rest, event, q  # noqa: E402

CK = "goclear_funding_readiness_review"
DISCLAIMER = "No guaranteed funding. No guaranteed approval. Education and readiness only."


def find_one(table, query):
    st, rows = get(table, query + "&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    out = []

    ws = find_one("workspaces", "workspace_key=eq.goclear_apex")
    workspace_id = ws["id"] if ws else None

    # campaign (upsert by campaign_key)
    rest("POST", "creative_campaigns?on_conflict=campaign_key", body=[{
        "campaign_key": CK, "workspace_id": workspace_id, "name": "Funding Readiness Review",
        "goal": "Drive paid funding readiness reviews and partner-tool engagement",
        "audience": "Small business owners who want funding but don't know why they may get denied",
        "offer": "GoClear/Apex Funding Readiness Review", "status": "active",
        "compliance_notes": DISCLAIMER,
    }], prefer="resolution=merge-duplicates,return=minimal")
    camp = find_one("creative_campaigns", f"campaign_key=eq.{CK}")
    out.append("campaign: upserted")

    # brief (idempotent by title within campaign)
    brief = find_one("creative_briefs", f"campaign_id=eq.{camp['id']}&title=eq." + q("Funding readiness before applying"))
    if not brief:
        st, row = insert("creative_briefs", {
            "campaign_id": camp["id"], "workspace_id": workspace_id,
            "title": "Funding readiness before applying", "platform": "multi",
            "audience": "Small business owners who apply before they are bank-ready",
            "pain_point": "Business owners apply for funding before they are bank-ready",
            "hook": "Your LLC is not enough to get business funding.",
            "angle": "Lenders look at readiness signals before they look at your dream.",
            "cta": "Check your funding readiness before applying.",
            "compliance_notes": DISCLAIMER, "status": "approved",
        })
        brief = row[0] if isinstance(row, list) and row else None
        out.append("brief: inserted")
    else:
        out.append("brief: exists")

    # studio output (audio overview) (idempotent by title+campaign)
    so = find_one("studio_outputs", f"campaign_id=eq.{camp['id']}&output_type=eq.audio_overview")
    if not so:
        insert("studio_outputs", {
            "campaign_id": camp["id"], "workspace_id": workspace_id, "output_type": "audio_overview",
            "title": "Audio overview: Why ready beats eager",
            "summary": "Client-friendly podcast script on funding readiness vs eagerness.",
            "script_text": ("INTRO → The LLC myth → Readiness signals lenders check → The quiet killers "
                            "→ What 'ready' looks like → CTA: Check your funding readiness before applying → "
                            f"DISCLAIMER: {DISCLAIMER}"),
            "status": "draft",
        }, prefer="return=minimal")
        out.append("studio_output: inserted")
    else:
        out.append("studio_output: exists")

    # pipeline job stub (idempotent)
    job = find_one("agent_jobs", "job_type=eq.creative_generate_assets&input->>seed_key=eq.day4_creative")
    if not job:
        insert("agent_jobs", {"lane": "creative", "job_type": "creative_generate_assets", "status": "queued",
                              "input": {"campaign_key": CK, "seed_key": "day4_creative"}}, prefer="return=minimal")
        out.append("agent_job: inserted")
    else:
        out.append("agent_job: exists")

    if not find_one("nexus_events", "action=eq.day4_creative_studio_seeded"):
        event("monetization", "day4_creative_studio_seeded", "success", "Day 4 creative studio seeded",
              "GoClear Funding Readiness campaign + brief + audio overview + pipeline job.",
              payload={"campaign_key": CK})
        out.append("nexus_event: inserted")
    else:
        out.append("nexus_event: exists")

    print("Day 4 creative studio seed complete (no publish, no Telegram, no trading).")
    for m in out:
        print("  -", m)
    print("Next: generate_campaign_assets.py -> score_creative_assets.py -> create_creative_approvals.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
