#!/usr/bin/env python3
"""Deterministic UI quality review → ui_quality_reviews. Idempotent by review_title.
    python3 scripts/design/review_ui_quality.py --sample
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

def review(title, subject_type="dashboard", scores=None) -> str | None:
    s = scores or {"layout_score":86,"readability_score":85,"brand_fit_score":88,"mobile_score":80,
                   "accessibility_score":74,"conversion_score":78,"compliance_score":92}
    overall = round(sum(s.values())/len(s))
    notes = []
    if s["accessibility_score"] < 80: notes.append("Improve color contrast + focus states for accessibility.")
    if s["mobile_score"] < 85: notes.append("Tighten mobile stacking + tap targets.")
    rec = "ship_with_minor_revisions" if overall >= 80 else "revise"
    st, ex = get("ui_quality_reviews", f"review_title=eq.{q(title)}&select=id&limit=1")
    if isinstance(ex, list) and ex: return ex[0]["id"]
    st, row = insert("ui_quality_reviews", {"subject_type": subject_type, "review_title": title,
        **s, "overall_score": overall, "recommendation": rec, "revision_notes": notes})
    rid = row[0]["id"] if isinstance(row, list) and row else None
    event("monetization", "ui_quality_reviewed", "success", f"UI review: {title}", f"overall {overall} · {rec}",
          payload={"ui_review_id": rid})
    return rid

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--title"); ap.add_argument("--subject-type", default="dashboard")
    ap.add_argument("--sample", action="store_true"); a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    title = a.title or "Nexus Command Center — UI quality review"
    rid = review(title, a.subject_type)
    print(f"UI quality review ready: {title} (id {rid})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
