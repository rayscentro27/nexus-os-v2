#!/usr/bin/env python3
"""Nexus OS v2 — Creative engine: generate platform-specific draft assets from a campaign+brief.

Deterministic/template generation (NO external AI calls — honest about that). Each asset ties
to workspace + campaign + brief + offer + audience + pain point + hook + platform + CTA +
compliance notes + money goal. Idempotent per (campaign, asset_type) via payload.gen_key.

Usage:
    python3 scripts/creative/generate_campaign_assets.py [--campaign-key goclear_funding_readiness_review]
    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/creative/generate_campaign_assets.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

DEFAULT_CAMPAIGN = "goclear_funding_readiness_review"
DISCLAIMER = "No guaranteed funding or approval — this is a readiness review, education only."


def _builders(brief: dict, offer: str) -> dict:
    pain = brief.get("pain_point") or "applying for funding before being bank-ready"
    cta = brief.get("cta") or "Check your funding readiness before applying."
    hook = brief.get("hook") or "Your LLC is not enough to get business funding."
    aud = brief.get("audience") or "small business owners seeking funding"

    return {
        "facebook_post": {
            "platform": "facebook",
            "title": "FB: LLC is not enough",
            "hook": hook,
            "body": (f"{hook}\n\nLenders look at readiness signals before they look at your dream: "
                     "entity + EIN consistency, a business phone and address, a real web presence, "
                     "clean bank statements, the right NAICS, and credit readiness. Most denials aren't "
                     "about your idea — they're about an unfinished profile.\n\n"
                     f"{cta}\n\n{DISCLAIMER}\nComment READY for the readiness checklist."),
            "cta": "Comment READY for the readiness checklist.",
        },
        "instagram_caption": {
            "platform": "instagram",
            "title": "IG: readiness before applying",
            "hook": hook,
            "body": (f"{hook} 👀\n\nBefore you apply, a lender quietly checks your readiness signals. "
                     "Fix those first and the conversation changes.\n\n"
                     f"{cta}\n{DISCLAIMER}\nDM READY for the checklist."),
            "cta": "DM READY for the checklist.",
        },
        "reel_script": {
            "platform": "reel",
            "title": "Reel/TikTok: readiness signals",
            "hook": hook,
            "body": (
                "HOOK (0-2s): “Your LLC is not enough to get business funding.”\n"
                "SCENE 1 (2-6s) — talking to camera: “Lenders look at readiness signals before your dream.”\n"
                "  [text overlay: ENTITY · EIN · PHONE · ADDRESS · WEBSITE]\n"
                "SCENE 2 (6-12s) — b-roll of paperwork: VO: “Mismatched address, no business phone, thin web "
                "presence, weak bank statements — that's what gets you denied.”\n"
                "  [text overlay: “It's not your idea. It's your profile.”]\n"
                "SCENE 3 (12-18s) — back to camera: VO: “Get funding-ready before you apply.”\n"
                f"CTA (18-20s): “{cta}”  [text overlay: COMMENT READY]\n"
                f"DISCLAIMER (on-screen, small): {DISCLAIMER}"),
            "cta": cta,
        },
        "carousel_outline": {
            "platform": "carousel",
            "title": "Carousel: the bankability stack",
            "hook": hook,
            "body": (
                "Slide 1 (cover): “Your LLC is not enough to get business funding.”\n"
                "Slide 2: “Lenders check readiness signals first.”\n"
                "Slide 3: “Entity + EIN consistency. Do they match everywhere?”\n"
                "Slide 4: “Business phone, address, website, domain email.”\n"
                "Slide 5: “Bank statements + NAICS + credit readiness.”\n"
                "Slide 6: “Most denials = unfinished profile, not a bad idea.”\n"
                f"Slide 7 (CTA): “{cta}”  + “{DISCLAIMER}”"),
            "cta": cta,
        },
        "lead_magnet_outline": {
            "platform": "lead_magnet",
            "title": "Lead magnet: Funding Readiness Checklist",
            "hook": "The Funding Readiness Checklist (free)",
            "body": (
                "Funding Readiness Checklist — 9 things lenders check before they fund you:\n"
                "1) Entity details consistent everywhere  2) EIN  3) Business phone  4) Business address\n"
                "5) Website + domain email  6) NAICS code  7) Bank statements (clean, seasoned)\n"
                "8) Business profile/web presence  9) Credit readiness gaps organized\n\n"
                f"Next step: {cta}\n{DISCLAIMER}"),
            "cta": cta,
        },
        "podcast_audio_overview_script": {
            "platform": "audio",
            "title": "Audio overview: Why ready beats eager",
            "hook": "Why being funding-ready beats being funding-eager",
            "body": (
                "INTRO: “Welcome back. Today: why business owners get denied even with a great idea — and "
                "how to fix it before you apply.”\n"
                "POINT 1: The LLC myth — an entity is one line in a much bigger stack.\n"
                "POINT 2: Readiness signals lenders actually check (entity/EIN, phone, address, web, bank, NAICS).\n"
                "POINT 3: The quiet killers — mismatched details and thin profiles.\n"
                "POINT 4: What ‘ready’ looks like — a clean, consistent, fundable profile.\n"
                "CLIENT-FRIENDLY EXPLANATION: “Think of it like a credit interview for your business.”\n"
                f"CTA: “{cta}”\n"
                f"DISCLAIMER: {DISCLAIMER}"),
            "cta": cta,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-key", default=DEFAULT_CAMPAIGN)
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    st, rows = get("creative_campaigns", f"campaign_key=eq.{q(args.campaign_key)}&limit=1")
    if not (isinstance(rows, list) and rows):
        print(f"BLOCKER: campaign '{args.campaign_key}' not found — run seed_day4_creative_studio.py first.")
        return 1
    camp = rows[0]
    st, brows = get("creative_briefs", f"campaign_id=eq.{camp['id']}&order=created_at.asc&limit=1")
    brief = brows[0] if isinstance(brows, list) and brows else {}
    workspace_id = camp.get("workspace_id")
    offer = camp.get("offer") or ""

    made = []
    for asset_type, a in _builders(brief, offer).items():
        gen_key = f"{args.campaign_key}:{asset_type}"
        st, existing = get("creative_assets", f"payload->>gen_key=eq.{q(gen_key)}&limit=1")
        if isinstance(existing, list) and existing:
            made.append(f"{asset_type}: exists"); continue
        insert("creative_assets", {
            "asset_type": asset_type, "title": a["title"], "platform": a["platform"],
            "content": a["body"], "body": a["body"], "hook": a["hook"], "cta": a["cta"],
            "offer": offer, "status": "draft", "campaign_id": camp["id"],
            "brief_id": brief.get("id"), "workspace_id": workspace_id,
            "payload": {"gen_key": gen_key, "campaign_key": args.campaign_key,
                        "money_goal": camp.get("goal"), "audience": brief.get("audience"),
                        "compliance_notes": brief.get("compliance_notes") or DISCLAIMER,
                        "generator": "deterministic_template_v1"},
        }, prefer="return=minimal")
        made.append(f"{asset_type}: created")

    event("monetization", "creative_assets_generated", "success",
          f"Generated creative assets for {args.campaign_key}",
          ", ".join(made), payload={"campaign_key": args.campaign_key})
    print(f"Creative generation complete for {args.campaign_key} (deterministic templates, no AI call).")
    for m in made:
        print("  -", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
