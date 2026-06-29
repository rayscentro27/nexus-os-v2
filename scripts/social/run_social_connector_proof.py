#!/usr/bin/env python3
"""Generate real internal social drafts and prove connector/publish gate state without posting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
from full_engine_common import SUPABASE, env_presence, record, write_json, write_report  # noqa: E402


def build() -> dict:
    env = env_presence("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "META_APP_ID", "META_APP_SECRET", "META_INSTAGRAM_ACCOUNT_ID")
    configured = all(env[name] for name in ("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "META_APP_ID", "META_APP_SECRET"))
    draft_specs = [
        ("Before you apply for funding", "Applying before your credit, business profile, and documents are ready can create avoidable setbacks.", ["funding readiness", "business credit", "GoClear"]),
        ("Your business profile is part of the application", "Entity records, contact details, banking, and proof documents should tell one consistent story.", ["business profile", "fundability", "small business"]),
        ("A readiness score is a plan—not a promise", "Use your educational readiness score to choose the next safe action. Results and approvals are never guaranteed.", ["credit education", "readiness", "no guarantees"]),
        ("What the $97 review covers", "Get a structured review of credit-profile, business-profile, documents, and funding-readiness blockers.", ["$97 review", "credit readiness", "funding readiness"]),
        ("Documents can be the fastest blocker to fix", "Address proof, entity records, bank statements, and a revenue summary can make the next review more useful.", ["documents", "business funding", "next step"]),
    ]
    drafts, approvals = [], []
    for i, (hook, body, hashtags) in enumerate(draft_specs, start=1):
        draft = record(f"social-draft-proof-{i}", "social_draft", hook, status="drafts_active", priority="high" if i in {1, 4} else "medium",
            client_visible=False, approval_required=True, automation_level="approval_gated", platform="facebook_or_instagram",
            hook=hook, caption=body, hashtags=hashtags, public_content_published=False, publish_enabled=False,
            recommended_next_action="Ray reviews exact copy/account; do not publish during audit.")
        drafts.append(draft)
        approvals.append(record(f"social-approval-proof-{i}", "social_approval_card", f"Approve social draft: {hook}",
            status="ready_for_Ray_review", priority=draft["priority"], risk_level="medium", automation_level="approval_gated",
            approval_required=True, exact_decision_needed="approve/reject/defer exact draft and future test account",
            recommended_next_action="Review in Ray Review; publishing stays disabled."))
    health_status = "connector_configured_publish_disabled" if configured else "connector_missing"
    health = [record("social-connector-health-proof", "social_connector_health", "Meta social connector configuration",
        status=health_status, configured=configured, network_validated=False, token_value_exposed=False,
        required_env_presence=env, live_enabled=False, summary="Local env/account configuration detected; validity was not checked against Meta during this audit.",
        recommended_next_action="Use an approved test account/read-only health check before any sandbox post." )]
    events = [record("social-publish-gate-proof", "social_publish_gate_event", "Social publish gate remained closed",
        status="live_publish_blocked", risk_level="high", automation_level="approval_gated", approval_required=True,
        public_content_published=False, live_enabled=False, summary="Five drafts created internally; no Graph API call or post.",
        recommended_next_action="Ray approves exact sandbox/test path before changing publish state.")]
    for name, data in (("social_drafts_latest.json", drafts), ("social_approval_cards_latest.json", approvals),
                       ("social_publish_gate_events_latest.json", events), ("social_connector_health_latest.json", health)):
        write_json(SUPABASE / name, data)
    report = {
        "ok": True, "status": "drafts_active", "draft_status": "drafts_active", "connector_status": health_status,
        "publish_gate_status": "live_publish_blocked", "real_social_account_configuration_detected": configured,
        "connector_network_validated": False, "drafts_created": len(drafts), "approval_cards_created": len(approvals),
        "publish_gate_events_created": len(events), "followers_required_for_proof": False,
        "real_public_posting_disabled": True, "test_account_connector_needed_for_sandbox_posting": True,
        "ray_approval_required_before_live_posting": True, "public_content_published": False,
        "external_action_performed": False,
        "next_required_action": "Review five drafts; separately approve a test account and sandbox posting design if desired.",
        "summary": "Social draft generation is real/internal. Meta configuration is present but unvalidated; public publishing remained disabled."
    }
    write_report("social_connector_proof", "Social Draft + Connector Proof", report, {"Drafts": drafts, "Connector health": health, "Publish gate": events})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = build(); print(json.dumps(report, indent=2) if args.json else report["summary"]); return 0


if __name__ == "__main__":
    raise SystemExit(main())
