#!/usr/bin/env python3
"""Day 1 proof seed — writes the first ledger event, system_health rows, and one approval
placeholder into Supabase using the SERVICE ROLE key (server-side only).

Reads SUPABASE_URL (or VITE_SUPABASE_URL) + SUPABASE_SERVICE_ROLE_KEY from .env / env.
Never prints the key. Dependency-free (urllib → PostgREST).

Usage:
    python3 scripts/seed_day1_event.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict:
    env = dict(os.environ)
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def insert(url: str, key: str, table: str, rows: list[dict]) -> int:
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status


def main() -> int:
    env = load_env()
    url = (env.get("SUPABASE_URL") or env.get("VITE_SUPABASE_URL") or "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("SETUP NEEDED: set SUPABASE_URL (or VITE_SUPABASE_URL) and "
              "SUPABASE_SERVICE_ROLE_KEY in .env, then re-run. (key not printed)")
        return 2

    try:
        insert(url, key, "nexus_events", [{
            "lane": "communication",
            "source": "day1_seed",
            "action": "nexus_os_v2_initialized",
            "status": "success",
            "title": "Nexus OS v2 initialized",
            "summary": "Supabase event ledger and dashboard shell created.",
            "severity": "info",
        }])
        insert(url, key, "system_health", [
            {"component": c, "status": s, "summary": msg}
            for c, s, msg in [
                ("dashboard", "ok", "7-tab shell live"),
                ("supabase", "ok", "ledger reachable"),
                ("social", "partial", "accounts seeded; publish off until approved"),
                ("trading", "rebuild_needed", "executor wired Day 6"),
                ("telegram", "ok", "guard ported Day 2"),
                ("hermes", "partial", "snapshot fallback; live AI optional"),
            ]
        ])
        insert(url, key, "approvals", [{
            "lane": "social",
            "item_type": "social_publish_test",
            "status": "pending",
            "title": "Approve first Facebook publish test after Day 3",
            "summary": "Publisher + queue land Day 3; approve one item before any real post.",
        }])
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        body = body.replace(key, "<redacted>") if key else body
        print(f"Supabase insert failed: HTTP {e.code} {body[:300]}")
        return 1
    except Exception as exc:
        print(f"Supabase insert failed: {str(exc)[:200]}")
        return 1

    print("Day 1 seed complete: 1 event + 6 health rows + 1 approval. (no secrets printed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
