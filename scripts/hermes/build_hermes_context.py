#!/usr/bin/env python3
"""Nexus OS v2 — build a SAFE system-context snapshot for Hermes (CEO/Advisor).

Reads Supabase (service role) and assembles counts + recent items so Hermes understands Nexus
before speaking. NO secrets/tokens/raw env, NO client-sensitive data. Writes a JSON snapshot to
/tmp and a nexus_events row 'hermes_context_built'. This is NOT a model call.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/hermes/build_hermes_context.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, event  # noqa: E402

OUT = Path("/tmp/nexus_hermes_context.json")


def rows(table: str, query: str):
    st, r = get(table, query)
    return r if isinstance(r, list) else []


def count(table: str, where: str = "") -> int:
    return len(rows(table, f"select=id&limit=1000" + (f"&{where}" if where else "")))


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    ctx = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "note": "Safe system context for Hermes. No secrets, no tokens, no client-sensitive data.",
        "workspaces": [w["workspace_key"] for w in rows("workspaces", "select=workspace_key&order=workspace_key")],
        "agent_policies": [
            {"agent_key": a["agent_key"], "agent_class": a.get("agent_class"), "audience_type": a.get("audience_type"),
             "web": a.get("web_access_allowed"), "external_api": a.get("external_api_allowed"),
             "can_create_jobs": a.get("can_create_jobs"), "can_execute": a.get("can_execute_actions")}
            for a in rows("agent_registry", "select=agent_key,agent_class,audience_type,web_access_allowed,external_api_allowed,can_create_jobs,can_execute_actions&order=agent_key")
        ],
        "recent_events": [{"action": e["action"], "status": e["status"], "title": e.get("title")}
                          for e in rows("nexus_events", "select=action,status,title&order=created_at.desc&limit=10")],
        "jobs": {"queued": count("agent_jobs", "status=eq.queued"), "running": count("agent_jobs", "status=eq.running"),
                 "failed": count("agent_jobs", "status=eq.failed"), "blocked": count("agent_jobs", "status=eq.blocked"),
                 "done": count("agent_jobs", "status=eq.done")},
        "approvals_pending": count("approvals", "status=eq.pending"),
        "system_health": [{"component": h["component"], "status": h["status"]}
                          for h in rows("system_health", "select=component,status&order=created_at.desc&limit=40")][:12],
        "creative": {"campaigns": count("creative_campaigns"), "assets": count("creative_assets"),
                     "scores": count("creative_scores")},
        "social": {"posts": count("social_posts"), "drafts": count("social_posts", "status=eq.draft"),
                   "receipts": count("social_publish_receipts")},
        "monetization_opportunities": count("monetization_opportunities"),
        "trading_candidates": count("trading_strategy_candidates"),
        "seo_opportunities": count("seo_opportunities"),
        "ops_incidents_open": count("ops_incidents", "status=eq.open"),
        "improvement_candidates": count("improvement_candidates"),
        "model_routes": [r["route_key"] for r in rows("model_routes", "select=route_key&order=route_key")],
        "model_providers_enabled": count("model_providers", "enabled=eq.true"),
        "safety_boundaries": {
            "real_publish": "blocked unless token + publish_enabled + approval + --real-publish",
            "telegram": "dry-run guarded only", "trading": "disabled", "schedulers": "none",
            "client_agents": "approved_knowledge only, no web/external API",
        },
    }
    # de-dup latest system_health by component
    seen, sh = set(), []
    for h in ctx["system_health"]:
        if h["component"] not in seen:
            seen.add(h["component"]); sh.append(h)
    ctx["system_health"] = sh

    OUT.write_text(json.dumps(ctx, indent=2))
    event("communication", "hermes_context_built", "success", "Hermes context built",
          f"workspaces={len(ctx['workspaces'])} pending_approvals={ctx['approvals_pending']} queued_jobs={ctx['jobs']['queued']}")
    print(f"Hermes context built → {OUT} (no secrets). pending_approvals={ctx['approvals_pending']} "
          f"queued_jobs={ctx['jobs']['queued']} campaigns={ctx['creative']['campaigns']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
