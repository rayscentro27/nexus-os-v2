#!/usr/bin/env python3
"""Nexus OS v2 — capture a pasted transcript/idea into intake_events.

Does NOT fetch web, scrape, or call external models. Accepts pasted text or a local file.

    python3 scripts/intake/capture_intake_event.py --title "..." --source-type transcript --text "..."
    python3 scripts/intake/capture_intake_event.py --title "..." --file ./notes.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title")
    ap.add_argument("--source-type", default="manual")
    ap.add_argument("--source-url")
    ap.add_argument("--note")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--workspace")
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    text = args.text
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"file not found: {args.file}"); return 1
        text = p.read_text(errors="ignore")

    workspace_id = None
    if args.workspace:
        st, rows = get("workspaces", f"workspace_key=eq.{q(args.workspace)}&select=id&limit=1")
        workspace_id = rows[0]["id"] if isinstance(rows, list) and rows else None

    st, row = insert("intake_events", {
        "source_type": args.source_type, "source_url": args.source_url,
        "title": args.title or "(untitled intake)", "raw_text": text, "note": args.note,
        "status": "new", "workspace_id": workspace_id,
    })
    eid = row[0]["id"] if isinstance(row, list) and row else None
    event("automation", "intake_event_captured", "success",
          f"Intake captured: {args.title or 'untitled'}",
          f"source={args.source_type} · {len(text or '')} chars · no web/model call",
          payload={"intake_event_id": eid})
    print(f"Intake event captured (id {eid}). No web fetch, no model call.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
