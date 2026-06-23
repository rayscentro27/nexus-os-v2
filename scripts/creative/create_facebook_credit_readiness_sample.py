#!/usr/bin/env python3
"""Nexus OS v2 — seed a sample GoClear credit-readiness Facebook DESIGN brief end-to-end.

Creates a compliance-safe brief (open-gate / upward-path metaphor), 5 variants (>=3), scores
them, and compares to pick a winner — all deterministic, no external image generation, no
publishing. Idempotent.

    python3 scripts/creative/create_facebook_credit_readiness_sample.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _design
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, event  # noqa: E402


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    brief = _design.get_or_create_sample_brief()
    ids = _design.generate_variants(brief)
    _design.score_variants(brief["id"])
    res = _design.compare_variants(brief["id"])
    event("monetization", "fb_credit_readiness_sample", "success",
          "FB credit-readiness design sample built", res["summary"], payload={"design_brief_id": brief["id"]})
    print(f"Sample credit-readiness FB design: brief '{brief['title']}' · {len(ids)} variants · {res['summary']}")
    print(f"  next_action={res['next_action']} · approval required before any publish · footer enforced.")
    print(f"  compliance: no guaranteed funding/approval/deletions/score-increase; '{_design.FOOTER[:40]}...'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
