"""Nexus OS v2 — social copy quality + compliance check (adapted from v1 social_copy_quality_check.py).

Heuristic, offline scorer (no external APIs, no publishing). Scores a social_posts row on
clarity, compliance safety, CTA strength, platform fit, money alignment, and no-guarantee
language. Writes the result into the post's payload and a nexus_events row. If the post links
a creative_asset, also writes a creative_scores row.

Usage:
    python3 scripts/social/social_quality_check.py --post-id <uuid>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _supabase import configured, get, insert, update, event, q  # noqa: E402

# Banned guarantee *claims* (positive promises). NOTE: do NOT flag the compliant disclaimer
# "no guarantees" — only guarantee claims that are not negated.
BANNED = [
    r"(?<!no )guaranteed (funding|approval|results?|returns?|credit repair|deletions?)",
    r"\bwe guarantee\b", r"\bwill (get|be) approved\b", r"\b100% approval\b",
    r"erase your debt", r"delete (any|all) (debt|items)", r"risk[- ]free", r"get rich",
]
CTA = [r"\bcomment\b", r"\bdm\b", r"\bcheck\b", r"\blearn\b", r"\bstart\b", r"\bget the\b", r"\bbook\b", r"\bjoin\b"]


def score_text(text: str) -> dict:
    t = (text or "").lower()
    words = len(t.split())
    banned_hits = [b for b in BANNED if re.search(b, t)]
    has_no_guarantee = bool(re.search(r"no guarantee|not a guarantee|no guarantees", t))
    cta = any(re.search(c, t) for c in CTA)
    money = bool(re.search(r"fund|credit|readiness|business|capital|\$\d|review|offer", t))

    clarity = 90 if 12 <= words <= 80 else (70 if words else 0)
    compliance_safety = 20 if banned_hits else (95 if has_no_guarantee else 80)
    cta_strength = 85 if cta else 45
    platform_fit = 85 if words <= 120 else 60
    money_alignment = 85 if money else 50
    no_guarantee = 95 if has_no_guarantee else (40 if re.search(r"fund|credit|approv", t) else 75)
    overall = round((clarity + compliance_safety + cta_strength + platform_fit + money_alignment + no_guarantee) / 6)

    return {
        "clarity": clarity, "compliance_safety": compliance_safety, "cta_strength": cta_strength,
        "platform_fit": platform_fit, "money_alignment": money_alignment, "no_guarantee": no_guarantee,
        "overall_score": overall, "banned_hits": banned_hits,
        "decision": "blocked_compliance" if banned_hits else ("pass" if overall >= 70 else "needs_revision"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-id", required=True)
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    st, rows = get("social_posts", f"id=eq.{q(args.post_id)}&limit=1")
    if not (isinstance(rows, list) and rows):
        print("social_post not found"); return 1
    post = rows[0]
    s = score_text(post.get("content") or "")

    update("social_posts", f"id=eq.{q(args.post_id)}",
           {"score": s["overall_score"], "reason": s["decision"],
            "payload": {**(post.get("payload") or {}), "quality": s}})

    asset_id = (post.get("payload") or {}).get("creative_asset_id")
    if asset_id:
        insert("creative_scores", {
            "creative_asset_id": asset_id, "clarity": s["clarity"], "money_alignment": s["money_alignment"],
            "platform_fit": s["platform_fit"], "compliance_safety": s["compliance_safety"],
            "cta_strength": s["cta_strength"], "overall_score": s["overall_score"],
            "notes": s["decision"],
        }, prefer="return=minimal")

    event("monetization", "social_quality_check", "success" if s["decision"] != "blocked_compliance" else "failed",
          f"Quality check: {s['decision']} ({s['overall_score']}/100)",
          f"banned: {', '.join(s['banned_hits']) or 'none'}", payload={"post_id": args.post_id})
    print(f"score={s['overall_score']} decision={s['decision']} banned={s['banned_hits']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
