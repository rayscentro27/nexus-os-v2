#!/usr/bin/env python3
"""Build a synthetic $97 readiness-review onboarding package; never inserts it."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
from same_day_common import SUPABASE_READY, now, write_json, write_report  # noqa:E402

TENANT = "tenant_test_goclear"
CLIENT = "client_test_julius_erving"

def row(record_id: str, category: str, title: str, **extra):
    value = {"id": record_id, "tenant_id": TENANT, "client_id": CLIENT, "category": category,
             "title": title, "status": "test_ready", "priority": "high", "risk_level": "low",
             "automation_level": "dry_run", "client_visible": False, "approval_required": False,
             "goclear_review_status": "test_pending", "source": "manual_test_customer",
             "test_client": True, "do_not_contact": True, "do_not_charge": True,
             "do_not_submit_applications": True, "external_action_performed": False,
             "created_at": now()}
    value.update(extra)
    return value

def build():
    profile = row(CLIENT, "client_profile", "Julius Erving", email="ray@goclearonline.com",
                  business_name="Doctor J LLC", business_type="delivery driver", state="AZ",
                  primary_goal="all", package="$97 readiness review", status="synthetic_test_pending_payment")
    groups = {
      "client_profiles": [profile],
      "subscription_memberships": [row("membership_test_97", "subscription_membership", "$97 readiness review", amount_cents=9700, cadence="one_time", status="test_not_paid")],
      "payments_status": [row("payment_test_97", "payment_status", "$97 Stripe test payment", amount_cents=9700, currency="usd", provider="stripe_test", status="not_created", approval_required=True)],
      "readiness_scores": [row("readiness_test_initial", "readiness_score", "Initial Nexus readiness baseline", score=None, status="awaiting_test_intake")],
      "client_tasks": [row("task_test_intake", "client_task", "Complete synthetic readiness intake"), row("task_test_docs", "client_task", "Review test document checklist")],
      "client_documents": [row("document_test_identity", "client_document", "Synthetic identity verification placeholder", status="not_uploaded"), row("document_test_business", "client_document", "Synthetic business formation placeholder", status="not_uploaded")],
      "approval_cards": [row("approval_test_persist", "approval_card", "Approve fake customer persistent Supabase insertion", approval_required=True, risk_level="medium", exact_decision_needed="Approve/reject/defer test-tenant insertion only")],
      "admin_review_queue": [row("review_test_customer", "admin_review", "Review synthetic customer package", approval_required=True, risk_level="medium")],
      "approved_client_guidance": [row("guidance_test_next", "approved_client_guidance", "Complete the test intake and document checklist", status="test_template")],
      "client_questions": [row("question_test_next", "client_question", "What should I do next?", status="synthetic_not_submitted")],
      "client_escalations": [row("escalation_test_review", "client_escalation", "Request GoClear test review", status="synthetic_not_submitted", approval_required=True)],
      "proof_events": [row("proof_test_package", "proof_event", "Synthetic customer package generated locally", status="success")],
    }
    package = {"test_client": True, "profile": profile, "record_groups": groups,
               "safety": {"live_database_inserted": False, "real_charge_created": False,
                          "client_contacted": False, "applications_submitted": False}}
    write_json(SUPABASE_READY / "fake_customer_test_client_latest.json", [profile])
    write_json(SUPABASE_READY / "fake_customer_onboarding_records_latest.json", package)
    report = {"ok": True, "generated_at": now(), "status": "synthetic_test_package_ready",
              "package": "$97 readiness review", "test_client": True,
              "record_groups_created": len(groups), "records_created": sum(map(len, groups.values())),
              "live_records_inserted": False, "real_charge_created": False, "client_contacted": False,
              "external_action_performed": False}
    write_report("fake_customer_test_package", "Synthetic Test Customer Package", report, {"Record groups": list(groups)})
    return report

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--json", action="store_true"); a=p.parse_args(); r=build(); print(json.dumps(r, indent=2) if a.json else r)
