#!/usr/bin/env python3
"""Register a design inspiration source (reference only — NOT a dependency, no clone/import, no web fetch).
    python3 scripts/design/register_design_inspiration.py --source-name "..." --source-type image --category trust_metaphor --summary "..."
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

def register(source_type, source_name, category, summary="", source_url=None, usefulness=7, risk="low") -> str | None:
    st, ex = get("design_inspiration_sources", f"source_name=eq.{q(source_name)}&select=id&limit=1")
    if isinstance(ex, list) and ex:
        return ex[0]["id"]
    st, row = insert("design_inspiration_sources", {"source_type": source_type, "source_name": source_name,
        "source_url": source_url, "category": category, "summary": summary,
        "usefulness_score": usefulness, "risk_level": risk,
        "metadata": {"reference_only": True, "do_not_clone": True}})
    sid = row[0]["id"] if isinstance(row, list) and row else None
    event("monetization", "design_inspiration_registered", "success", f"Inspiration: {source_name}",
          f"category={category} · reference only", payload={"inspiration_id": sid})
    return sid

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-name", required=True); ap.add_argument("--source-type", default="reference")
    ap.add_argument("--category", required=True); ap.add_argument("--summary", default="")
    ap.add_argument("--source-url")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    sid = register(a.source_type, a.source_name, a.category, a.summary, a.source_url)
    print(f"Inspiration registered (reference only, not a dependency): {a.source_name} (id {sid})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
