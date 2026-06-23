#!/usr/bin/env python3
"""Nexus OS v2 — Day 6 idempotent seed: AI agent permission boundaries + approved knowledge.

Upserts agent_registry policies (hermes_advisor, two client agents, creative_worker,
nexus_runner), seeds approved_knowledge for funding readiness, and queues one hermes_command
proof job. No publish/trading/Telegram.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day6_agent_boundaries.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, get, insert, rest, event  # noqa: E402

AGENTS = [
    {"agent_key": "hermes_advisor", "name": "Hermes (Advisor)", "role": "ceo_advisor",
     "audience_type": "ray_private", "agent_class": "hermes_advisor",
     "allowed_data_sources": ["supabase_system_context", "approved_internal_memory", "research_sources", "web_research_later"],
     "web_access_allowed": True, "external_api_allowed": True, "can_create_jobs": True,
     "can_create_approvals": True, "can_execute_actions": False,
     "requires_approval_for": ["publish_social", "send_telegram", "send_email", "trade", "deploy", "schema_change", "paid_api_use", "client_claims"],
     "cost_policy": "controlled_model_router", "compliance_policy": "private_strategy_not_client_answer",
     "communication_channel": "dashboard_now_telegram_later", "risk_level": "medium", "status": "active",
     "system_prompt_summary": "Ray's private operator/advisor. Researches, compares vs Nexus strategy, recommends, queues jobs/approvals. Never executes risky actions directly."},
    {"agent_key": "client_funding_assistant", "name": "Client Funding Assistant", "role": "client_agent",
     "audience_type": "client", "agent_class": "client_agent",
     "allowed_data_sources": ["approved_knowledge", "client_profile", "funding_readiness", "partner_offers", "approved_education"],
     "web_access_allowed": False, "external_api_allowed": False, "can_create_jobs": False,
     "can_create_approvals": False, "can_execute_actions": False,
     "requires_approval_for": ["any_public_claim", "any_external_action"],
     "cost_policy": "supabase_first_minimize_api", "compliance_policy": "funding_credit_no_guarantees",
     "communication_channel": "client_portal", "risk_level": "low", "status": "active",
     "system_prompt_summary": "Answers ONLY from approved knowledge. No web, no external API, no guarantees."},
    {"agent_key": "client_credit_readiness_assistant", "name": "Client Credit Readiness Assistant", "role": "client_agent",
     "audience_type": "client", "agent_class": "client_agent",
     "allowed_data_sources": ["approved_knowledge", "client_profile", "funding_readiness", "approved_education"],
     "web_access_allowed": False, "external_api_allowed": False, "can_create_jobs": False,
     "can_create_approvals": False, "can_execute_actions": False,
     "requires_approval_for": ["any_public_claim", "any_external_action"],
     "cost_policy": "supabase_first_minimize_api", "compliance_policy": "funding_credit_no_guarantees",
     "communication_channel": "client_portal", "risk_level": "low", "status": "active",
     "system_prompt_summary": "Credit-readiness education only, from approved knowledge. No guarantees."},
    {"agent_key": "creative_worker", "name": "Creative Worker", "role": "internal_worker",
     "audience_type": "internal", "agent_class": "internal_worker",
     "allowed_data_sources": ["creative_tables", "job_payload"],
     "web_access_allowed": False, "external_api_allowed": False, "can_create_jobs": False,
     "can_create_approvals": False, "can_execute_actions": False,
     "requires_approval_for": [], "cost_policy": "controlled", "compliance_policy": "default",
     "communication_channel": "dashboard", "risk_level": "low", "status": "stubbed",
     "system_prompt_summary": "Reads job payloads + Supabase creative tables. No external actions."},
    {"agent_key": "nexus_runner", "name": "Nexus Runner", "role": "execution_layer",
     "audience_type": "system", "agent_class": "runner",
     "allowed_data_sources": ["agent_jobs", "allowlisted_handlers"],
     "web_access_allowed": False, "external_api_allowed": False, "can_create_jobs": False,
     "can_create_approvals": False, "can_execute_actions": True,
     "requires_approval_for": ["publish_social", "trade", "send_telegram", "deploy"],
     "cost_policy": "controlled", "compliance_policy": "default", "communication_channel": "cli",
     "risk_level": "medium", "status": "active",
     "system_prompt_summary": "Executes ONLY allowlisted job handlers; risky/real actions need flags + approvals."},
]

KNOWLEDGE = [
    {"knowledge_key": "funding_readiness_basics", "title": "What funding readiness means",
     "category": "funding_readiness", "audience_type": "client", "status": "approved",
     "compliance_notes": "No guarantees.",
     "body": ("Funding readiness is how prepared your business looks to a lender before you apply. "
              "Lenders check signals: entity + EIN consistency, a business phone and address, a real web "
              "presence and domain email, the right NAICS code, clean/seasoned bank statements, and "
              "credit readiness. Getting these consistent first changes the conversation.")},
    {"knowledge_key": "no_guarantee_policy", "title": "On guarantees",
     "category": "compliance", "audience_type": "client", "status": "approved",
     "compliance_notes": "Core compliance stance.",
     "body": ("No one can honestly guarantee business funding, approval, credit repair, or a score "
              "increase. We focus on readiness and education so you apply prepared.")},
]


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    out = []

    for a in AGENTS:
        rest("POST", "agent_registry?on_conflict=agent_key", body=[a],
             prefer="resolution=merge-duplicates,return=minimal")
        out.append(f"agent {a['agent_key']}: upserted")

    for k in KNOWLEDGE:
        rest("POST", "approved_knowledge?on_conflict=knowledge_key", body=[k],
             prefer="resolution=merge-duplicates,return=minimal")
        out.append(f"knowledge {k['knowledge_key']}: upserted")

    # hermes_command proof job (idempotent)
    st, ex = get("agent_jobs", "job_type=eq.hermes_command&input->>seed_key=eq.day6&select=id&limit=1")
    if not (isinstance(ex, list) and ex):
        insert("agent_jobs", {"lane": "hermes", "job_type": "hermes_command", "status": "queued",
               "input": {"command": "Find a niche for GoClear/Apex, but do not publish anything.", "seed_key": "day6"}},
               prefer="return=minimal")
        out.append("hermes_command job: queued")
    else:
        out.append("hermes_command job: exists")

    if not (get("nexus_events", "action=eq.day6_agent_boundaries_seeded&select=id&limit=1")[1] or []):
        event("system", "day6_agent_boundaries_seeded", "success", "Day 6 agent boundaries seeded",
              "Agent policies + approved knowledge + hermes_command proof job.")
        out.append("nexus_event: inserted")
    else:
        out.append("nexus_event: exists")

    print("Day 6 agent boundaries seed complete (no publish/trading/Telegram).")
    for m in out:
        print("  -", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
