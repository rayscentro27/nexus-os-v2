#!/usr/bin/env python3
"""Nexus OS v2 — Day 7 idempotent seed for the policy-gated Model Router.

Upserts model_routes (by route_key). NO external calls are enabled. Public/candidate routes
are active=false until explicitly enabled + approved. Sensitive routes never allow public cloud.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day7_model_router.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, rest, event  # noqa: E402

ROUTES = [
    {"route_key": "deterministic_nexus_scripts", "task_type": "routing", "route_type": "deterministic",
     "provider_key": "nexus", "sensitive_data_allowed": True, "external_call_allowed": False,
     "requires_approval": False, "cost_tier": "free", "active": True, "priority": 10,
     "notes": "Deterministic local script handling — no model call."},
    {"route_key": "manual_claude_code", "task_type": "reasoning", "route_type": "manual",
     "provider_key": "anthropic_manual", "sensitive_data_allowed": True, "external_call_allowed": False,
     "requires_approval": True, "cost_tier": "manual_subscription", "active": True, "priority": 30,
     "notes": "Ray pastes the prompt packet into Claude Code manually; Nexus does not call it."},
    {"route_key": "manual_opencode", "task_type": "implementation", "route_type": "manual",
     "provider_key": "opencode_manual", "external_call_allowed": False, "requires_approval": True,
     "cost_tier": "manual_subscription", "active": True, "priority": 35, "notes": "Manual OpenCode route."},
    {"route_key": "manual_codex", "task_type": "implementation", "route_type": "manual",
     "provider_key": "codex_manual", "external_call_allowed": False, "requires_approval": True,
     "cost_tier": "manual_subscription", "active": True, "priority": 36, "notes": "Manual Codex route."},
    {"route_key": "ollama_local_private", "task_type": "reasoning", "route_type": "local_private",
     "provider_key": "ollama", "sensitive_data_allowed": True, "external_call_allowed": False,
     "requires_approval": False, "cost_tier": "free", "active": False, "status": "candidate", "priority": 20,
     "notes": "Candidate only until local hardware benchmark passes."},
    {"route_key": "lm_studio_local_private", "task_type": "reasoning", "route_type": "local_private",
     "provider_key": "lm_studio", "sensitive_data_allowed": True, "external_call_allowed": False,
     "requires_approval": False, "cost_tier": "free", "active": False, "status": "candidate", "priority": 21,
     "notes": "Candidate only until local hardware benchmark passes."},
    {"route_key": "openrouter_free_public_research", "task_type": "research", "route_type": "free_public_cloud",
     "provider_key": "openrouter", "sensitive_data_allowed": False, "client_data_allowed": False,
     "credit_data_allowed": False, "funding_data_allowed": False, "public_research_allowed": True,
     "external_call_allowed": False, "requires_approval": True, "cost_tier": "free", "active": False,
     "status": "candidate", "priority": 50,
     "notes": "No real call until NEXUS_ALLOW_EXTERNAL_MODEL_CALLS=true AND approval exist."},
    {"route_key": "blocked_sensitive_public_cloud", "task_type": "policy", "route_type": "blocked",
     "provider_key": "policy", "external_call_allowed": False, "requires_approval": True, "active": True,
     "priority": 99, "notes": "Sensitive data cannot go to public/free cloud models."},
]


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    for r in ROUTES:
        rest("POST", "model_routes?on_conflict=route_key", body=[r],
             prefer="resolution=merge-duplicates,return=minimal")
        print(f"  - route {r['route_key']}: upserted ({r['route_type']}, active={r['active']})")
    event("system", "day7_model_router_seeded", "success", "Day 7 model router seeded",
          "8 routes upserted; external calls OFF; public cloud candidate-only.")
    print("Day 7 model router seed complete (no external calls enabled).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
