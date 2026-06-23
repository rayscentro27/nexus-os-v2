#!/usr/bin/env python3
"""Nexus OS v2 — Creative QA scorer (broader than the Day 3 social check).

Scores each creative_asset on hook_strength, clarity, money_alignment, platform_fit, brand_fit,
compliance_safety, cta_strength, uniqueness, overall_score. Writes a creative_scores row, sets
creative_assets.score + status (scored / blocked_compliance / needs_revision), and a nexus_event.

Penalizes guaranteed approval/funding/credit-repair/profit claims. Trading assets must not claim
profit/signal performance. No external calls, no publishing.

Usage: python3 scripts/creative/score_creative_assets.py [--campaign-key ...]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, update, event, q  # noqa: E402

# Positive guarantee CLAIMS (not the negated "no guarantees" disclaimer).
BANNED = [
    r"(?<!no )guaranteed (funding|approval|results?|returns?|profit|credit repair|deletions?)",
    r"\bwe guarantee\b", r"\bwill (get|be) approved\b", r"\b100% approval\b",
    r"erase your debt", r"delete (any|all) (debt|items)", r"risk[- ]free", r"get rich",
    r"\bguaranteed (signals?|wins?|pips?)\b", r"\bcan'?t lose\b",
]
CTA = [r"\bcomment\b", r"\bdm\b", r"\bcheck\b", r"\blearn\b", r"\bstart\b", r"\bget (the|your)\b", r"\bbook\b", r"\bjoin\b"]
SPECIFIC = ["ein", "naics", "bank statement", "entity", "address", "website", "readiness", "credit"]


def score(asset: dict, workspace_key: str) -> dict:
    text = " ".join(str(asset.get(k) or "") for k in ("hook", "body", "content", "title", "cta")).lower()
    words = len(text.split())
    banned = [b for b in BANNED if re.search(b, text)]
    has_disclaimer = bool(re.search(r"no guarantee|not a guarantee|education only|readiness review", text))
    cta = any(re.search(c, text) for c in CTA)
    specific_hits = sum(1 for s in SPECIFIC if s in text)
    is_trading = workspace_key == "trading_lab"

    hook_strength = 88 if asset.get("hook") and len(str(asset["hook"])) > 12 else 55
    clarity = 90 if 20 <= words <= 220 else (70 if words else 0)
    money_alignment = min(95, 55 + specific_hits * 8) if re.search(r"fund|credit|readiness|offer|review", text) else 50
    platform_fit = 88
    brand_fit = 85 if specific_hits >= 2 else 65
    compliance_safety = 15 if banned else (95 if has_disclaimer else 78)
    if is_trading and re.search(r"profit|returns?|win rate|signals?", text) and not has_disclaimer:
        compliance_safety = min(compliance_safety, 40)
    cta_strength = 88 if cta else 45
    uniqueness = 82 if specific_hits >= 3 else 60
    overall = round((hook_strength + clarity + money_alignment + platform_fit + brand_fit
                     + compliance_safety + cta_strength + uniqueness) / 8)
    decision = "blocked_compliance" if banned else ("scored" if overall >= 72 else "needs_revision")
    return {"hook_strength": hook_strength, "clarity": clarity, "money_alignment": money_alignment,
            "platform_fit": platform_fit, "brand_fit": brand_fit, "compliance_safety": compliance_safety,
            "cta_strength": cta_strength, "uniqueness": uniqueness, "overall_score": overall,
            "banned": banned, "decision": decision}


def workspace_key_for(asset: dict) -> str:
    wid = asset.get("workspace_id")
    if not wid:
        return ""
    st, rows = get("workspaces", f"id=eq.{wid}&select=workspace_key&limit=1")
    return rows[0]["workspace_key"] if isinstance(rows, list) and rows else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-key")
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    query = "select=*&order=created_at.desc&limit=100"
    if args.campaign_key:
        query += f"&payload->>campaign_key=eq.{q(args.campaign_key)}"
    st, assets = get("creative_assets", query)
    if not isinstance(assets, list):
        print("could not load creative_assets"); return 1

    done = []
    for a in assets:
        # skip if already scored (idempotent)
        st, existing = get("creative_scores", f"creative_asset_id=eq.{a['id']}&select=id&limit=1")
        if isinstance(existing, list) and existing:
            done.append(f"{a['asset_type']}: already scored"); continue
        wk = workspace_key_for(a)
        s = score(a, wk)
        st, row = insert("creative_scores", {
            "creative_asset_id": a["id"], "campaign_id": a.get("campaign_id"),
            "hook_strength": s["hook_strength"], "clarity": s["clarity"], "money_alignment": s["money_alignment"],
            "platform_fit": s["platform_fit"], "brand_fit": s["brand_fit"], "compliance_safety": s["compliance_safety"],
            "cta_strength": s["cta_strength"], "uniqueness": s["uniqueness"], "overall_score": s["overall_score"],
            "notes": s["decision"] + (f" · banned: {', '.join(s['banned'])}" if s["banned"] else ""),
        })
        score_id = row[0]["id"] if isinstance(row, list) and row else None
        update("creative_assets", f"id=eq.{a['id']}",
               {"score": s["overall_score"], "status": s["decision"], "score_id": score_id,
                "payload": {**(a.get("payload") or {}), "score_summary": {"overall": s["overall_score"], "decision": s["decision"]}}})
        done.append(f"{a['asset_type']}: {s['overall_score']}/100 {s['decision']}")

    event("monetization", "creative_assets_scored", "success", "Creative QA scored assets",
          ", ".join(done) or "nothing to score", payload={"campaign_key": args.campaign_key})
    print("Creative scoring complete.")
    for d in done:
        print("  -", d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
