#!/usr/bin/env python3
"""Persist the bounded, synthetic state required by the controlled pilot.

This helper is called by replay after the existing credit fixture seed.  It
uses stable synthetic keys and approval-gated states so replay is idempotent;
it does not call external services or create mail/DocuPost work.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reset_synthetic_credit_case import (  # noqa: E402
    PERSONA_EMAILS,
    envfile,
    query,
    resolve_scope,
    rest,
)

FIXTURE_VERSION = "controlled-pilot-v1"
ENGINE_VERSION = "outcome-analytics-v1.3"


def stable_id(scope, label):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nexus-controlled-pilot:{scope['persona']}:{scope['client_id']}:{label}"))


def upsert(url, key, table, row):
    result = rest(
        url,
        key,
        f"/rest/v1/{table}",
        method="POST",
        body=row,
        headers={"Prefer": "resolution=merge-duplicates,return=representation"},
    )
    return result[0] if isinstance(result, list) and result else row


def first(url, key, table, select, filters):
    rows = query(url, key, table, select, filters)
    return rows[0] if rows else None


def ensure_document(url, key, scope, kind):
    persona = scope["persona"]
    title = (
        f"synthetic_persona_{persona}_three_bureau_report_v3.pdf"
        if kind == "initial"
        else f"synthetic_persona_{persona}_three_bureau_report_followup_v3.pdf"
    )
    existing = first(url, key, "client_documents", "id,title", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "title": f"eq.{title}",
    })
    if existing:
        return existing["id"]
    document_id = stable_id(scope, f"document:{kind}")
    upsert(url, key, "client_documents", {
        "id": document_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "category": "credit_report",
        "title": title,
        "summary": f"Synthetic controlled pilot {kind} report fixture for Persona {persona.upper()}",
        "status": "uploaded",
        "priority": "normal",
        "risk_level": "low",
        "automation_level": "automatic_analysis_queue",
        "client_visible": True,
        "approval_required": False,
        "goclear_review_status": "not_required",
        "source": "client_portal_upload",
        "source_concept": "controlled_tester_pilot",
        "recommended_next_action": "Review the persisted synthetic readiness state.",
    })
    return document_id


def ensure_parser(url, key, scope, document_id, kind):
    existing = first(url, key, "credit_report_parser_results", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
        "parser_version": "eq.controlled-pilot-v1",
    })
    parser_id = existing["id"] if existing else stable_id(scope, f"parser:{kind}")
    account_name = f"Synthetic {scope['persona'].upper()} Card"
    if scope["persona"] == "b":
        account_name = "Synthetic B Ambiguous Account"
    accounts = [{"name": account_name, "type": "revolving", "balance": 2500 if kind == "initial" else 2300}]
    upsert(url, key, "credit_report_parser_results", {
        "id": parser_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "document_id": document_id,
        "source_file_name": f"synthetic_persona_{scope['persona']}_{kind}_v3.pdf",
        "parser_version": "controlled-pilot-v1",
        "extraction_mode": "structured",
        "extraction_success": True,
        "text_length": 5000,
        "confidence": "low" if scope["persona"] == "b" else "high",
        "bureaus_detected": json.dumps(["experian", "equifax", "transunion"]),
        "accounts": json.dumps(accounts),
        "inquiries": json.dumps([]),
        "status": "reviewed",
        "needs_specialist_review": scope["persona"] == "b",
    })
    return parser_id


def ensure_canonical(url, key, scope, document_id, parser_id, kind):
    furnisher = {"a": "Chase", "b": "Capital One", "c": "Discover"}[scope["persona"]]
    existing = first(url, key, "credit_canonical_accounts", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
        "parser_result_id": f"eq.{parser_id}",
        "normalized_creditor_label": f"eq.{furnisher}",
    })
    account_id = existing["id"] if existing else stable_id(scope, f"canonical:{kind}")
    ambiguous = scope["persona"] == "b"
    upsert(url, key, "credit_canonical_accounts", {
        "id": account_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "document_id": document_id,
        "parser_result_id": parser_id,
        "normalized_creditor_label": furnisher,
        "normalized_account_type": "revolving",
        "canonical_status": "ambiguous" if ambiguous else "current",
        "match_confidence": 0.4 if ambiguous else 0.85,
        "match_tier": "ambiguous" if ambiguous else "high_confidence",
        "match_reasons": ["synthetic controlled pilot fixture"],
        "conflict_reasons": ["cross-bureau values require specialist review"] if ambiguous else [],
        "review_requirement": "exception_required" if ambiguous else "not_required",
        "threshold_version": "controlled-pilot-v1",
        "matching_engine_version": "canonical-v1",
    })
    return account_id


def ensure_discrepancy(url, key, scope, document_id, parser_id, account_id, kind):
    disc_type = {"a": "balance_mismatch", "b": "status_mismatch", "c": "duplicate_possible"}[scope["persona"]]
    existing = first(url, key, "credit_report_discrepancies", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
        "discrepancy_type": f"eq.{disc_type}",
    })
    discrepancy_id = existing["id"] if existing else stable_id(scope, f"discrepancy:{kind}")
    upsert(url, key, "credit_report_discrepancies", {
        "id": discrepancy_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "document_id": document_id,
        "parser_result_id": parser_id,
        "canonical_account_id": account_id,
        "discrepancy_type": disc_type,
        "involved_tradeline_ids": [],
        "bureau_values": {"synthetic": True, "kind": kind},
        "confidence": "low" if scope["persona"] == "b" else "high",
        "severity": "high" if scope["persona"] == "b" else "medium",
        "detection_rule": f"controlled_pilot_{disc_type}",
        "ruleset_version": "controlled-pilot-v1",
        "explanation": "Synthetic cross-bureau observation requiring the documented review path.",
        "client_confirmation_required": scope["persona"] != "b",
        "exception_review_required": scope["persona"] == "b",
        "status": "detected",
    })
    return discrepancy_id


def ensure_workflow(url, key, scope, document_id, parser_id):
    existing = first(url, key, "credit_document_workflows", "id,analysis_status", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
    })
    workflow_id = existing["id"] if existing else stable_id(scope, f"workflow:{document_id}")
    is_exception = scope["persona"] == "b"
    workflow_update = {
        "document_status": "uploaded",
        "strategy_status": "blocked" if is_exception else "ready",
        "client_action_status": "waiting_for_client" if scope["persona"] == "c" else "ready",
        "exception_review_status": "required" if is_exception else "not_required",
        "mail_status": "not_requested",
        "exception_code": "ambiguous_account_match" if is_exception else None,
        "exception_reason": "Ambiguous synthetic cross-bureau account requires specialist review." if is_exception else None,
        "latest_parser_result_id": parser_id,
    }
    # The workflow trigger requires legal analysis transitions; a direct
    # queued→complete update is intentionally rejected by the database.
    current_status = existing.get("analysis_status") if existing else "not_queued"
    workflow_path = {"not_queued": ["queued", "processing", "complete"], "queued": ["processing", "complete"], "processing": ["complete"]}
    if current_status in workflow_path:
        for next_status in workflow_path[current_status]:
            rest(url, key, f"/rest/v1/credit_document_workflows?id=eq.{workflow_id}", method="PATCH", body={
                "analysis_status": next_status,
                **(workflow_update if next_status == "complete" else {}),
            })
            current_status = next_status
    elif current_status != "complete":
        raise RuntimeError(f"workflow is in unsupported analysis state: {current_status}")
    if current_status == "complete":
        rest(url, key, f"/rest/v1/credit_document_workflows?id=eq.{workflow_id}", method="PATCH", body=workflow_update)
    # The upload trigger may have queued one job for a newly-created synthetic
    # document. Mark that bounded fixture job complete so replay leaves no
    # active duplicate work behind.
    jobs = query(url, key, "credit_analysis_jobs", "id,status", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
    })
    for job in jobs:
        job_id = job.get("id")
        if not job_id:
            continue
        rest(url, key, f"/rest/v1/credit_analysis_jobs?id=eq.{job_id}", method="PATCH", body={
            "status": "complete",
            "parser_result_id": parser_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })


def ensure_system_review(url, key, scope, document_id, persona):
    existing = first(url, key, "credit_report_system_reviews", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
    })
    review_id = existing["id"] if existing else stable_id(scope, "system-review")
    exception = persona == "b"
    upsert(url, key, "credit_report_system_reviews", {
        "id": review_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "document_id": document_id,
        "status": "approved_summary",
        "summary": {
            "facts": ["Three-bureau synthetic report is present", "Coverage is recorded for three bureaus"],
            "uncertainty": "Specialist review is required before strategy selection." if exception else "Some client-provided evidence remains outstanding.",
        },
        "utilization_actions": ["Review utilization and supporting statements."],
        "report_item_reviews": ["Review the documented discrepancy and confirm supporting evidence."],
        "evidence_needed": ["Supporting account documentation"],
        "recommended_next_steps": ["Complete the next guided evidence task."],
        "tier_1_impact": {"status": "action_needed", "reason": "Evidence and review completeness affect readiness."},
        "tier_2_impact": {"status": "insufficient_information", "reason": "No approval prediction is made from this snapshot."},
        "needs_specialist_review": exception,
        "client_visible": True,
    })


def ensure_exception(url, key, scope, document_id, discrepancy_id):
    existing = first(url, key, "credit_strategy_exceptions", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "exception_code": "eq.ambiguous_account_match",
    })
    exception_id = existing["id"] if existing else stable_id(scope, "exception")
    upsert(url, key, "credit_strategy_exceptions", {
        "id": exception_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "report_id": document_id,
        "discrepancy_id": discrepancy_id,
        "exception_code": "ambiguous_account_match",
        "reason": "The synthetic account cannot be treated as a resolved match from the available evidence.",
        "confidence": "low",
        "risk": "high",
        "recommended_action": "Route to specialist review and request clarifying documentation.",
        "status": "required",
        "assigned_reviewer": "specialist_review",
    })


def ensure_match_and_recommendation(url, key, scope, document_id, account_id, discrepancy_id, strategy_id):
    match = first(url, key, "credit_strategy_matches", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "report_id": f"eq.{document_id}",
        "discrepancy_id": f"eq.{discrepancy_id}",
        "strategy_id": f"eq.{strategy_id}",
    })
    match_id = match["id"] if match else stable_id(scope, "strategy-match")
    # Persona B may see the approved, uncertainty-labeled strategy card; the
    # persisted exception/workflow remains blocking and no unsafe action is
    # exposed or authorized.
    client_visible = True
    upsert(url, key, "credit_strategy_matches", {
        "id": match_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "report_id": document_id,
        "canonical_account_id": account_id,
        "discrepancy_id": discrepancy_id,
        "strategy_id": strategy_id,
        "strategy_version": 1,
        "match_score": 40 if scope["persona"] == "b" else 85,
        "match_reasons": ["objective synthetic discrepancy", "approved reusable strategy"],
        "exclusion_reasons": ["low confidence; specialist review required"] if scope["persona"] == "b" else [],
        "status": "presented",
        "ruleset_version": "controlled-pilot-v1",
        "client_visible": client_visible,
    })
    recommendation = first(url, key, "credit_strategy_recommendations", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "document_id": f"eq.{document_id}",
        "discrepancy_id": f"eq.{discrepancy_id}",
        "strategy_id": f"eq.{strategy_id}",
    })
    recommendation_id = recommendation["id"] if recommendation else stable_id(scope, "recommendation")
    title = {
        "a": "Cross-Bureau Balance Review",
        "b": "Cross-Bureau Status Review",
        "c": "Purchased Debt Documentation Review",
    }[scope["persona"]]
    upsert(url, key, "credit_strategy_recommendations", {
        "id": recommendation_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "document_id": document_id,
        "canonical_account_id": account_id,
        "discrepancy_id": discrepancy_id,
        "strategy_id": strategy_id,
        "strategy_version": 1,
        "status": "generated",
        "client_visible": client_visible,
        "confidence": "low" if scope["persona"] == "b" else "high",
        "payload": {
            "primaryStrategy": title,
            "rationale": "The structured synthetic discrepancy matches this approved strategy.",
            "requiredEvidence": ["Relevant report pages", "Supporting account documentation"],
            "clientConfirmationQuestions": ["Please confirm the documented account facts."],
            "availableTools": ["evidence_checklist"],
            "discrepancy": {"differenceSummary": "Synthetic cross-bureau observation", "fundingImpact": "May affect readiness review."},
            "documentId": document_id,
        },
    })
    return match_id, recommendation_id


def ensure_selection_and_draft(url, key, scope, document_id, account_id, discrepancy_id, strategy_id, match_id, recommendation_id):
    existing = first(url, key, "credit_strategy_client_selections", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "report_id": f"eq.{document_id}",
        "strategy_id": f"eq.{strategy_id}",
    })
    selection_id = existing["id"] if existing else stable_id(scope, "selection")
    selection_state = "evidence_requested" if scope["persona"] == "c" else "draft_ready"
    selection = {
        "id": selection_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "report_id": document_id,
        "canonical_account_id": account_id,
        "discrepancy_id": discrepancy_id,
        "strategy_id": strategy_id,
        "strategy_version": 1,
        "match_id": match_id,
        "selected_option": "document_review",
        "client_answers": {"synthetic": True},
        "evidence_references": ["Supporting account documentation"],
        "status": selection_state,
        "consent_state": "not_requested",
        "authorization_state": "not_authorized",
        "revision": 1,
        "actor": "client",
    }
    upsert(url, key, "credit_strategy_client_selections", selection)
    upsert(url, key, "credit_strategy_selection_history", {
        "id": stable_id(scope, "selection-history"),
        "selection_id": selection_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "revision": 1,
        "previous_state": {},
        "new_state": selection,
        "actor_type": "client",
        "reason": "Synthetic controlled pilot fixture",
    })
    upsert(url, key, "credit_strategy_evidence_links", {
        "id": stable_id(scope, "evidence-link"),
        "selection_id": selection_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "document_id": document_id,
        "report_id": document_id,
        "discrepancy_id": discrepancy_id,
        "status": "requested",
        "review_reason": "Supporting synthetic documentation is required before a client-authorized draft can proceed.",
    })
    upsert(url, key, "credit_strategy_client_decisions", {
        "id": stable_id(scope, "decision"),
        "recommendation_id": recommendation_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "actor_type": "client",
        "decision": "evidence_requested" if scope["persona"] == "c" else "selected",
        "notes": "Synthetic pilot decision state; no external action authorized.",
        "previous_state": {},
        "new_state": {"selection_id": selection_id, "status": selection_state},
    })
    # The portal reads recommendations and decisions; the draft remains a
    # safe, client-review-required artifact with mail permanently disabled.
    upsert(url, key, "credit_strategy_drafts", {
        "id": stable_id(scope, "draft"),
        "selection_id": selection_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "strategy_id": strategy_id,
        "strategy_version": 1,
        "template_version": "research-to-clyde-v1",
        "output_type": "evidence_request_draft",
        "content": {"text": "Synthetic draft for client review; no message is sent.", "accountReference": "masked synthetic reference"},
        "status": "draft_ready",
        "safety_result": {"safe": True, "guarantees": False, "legal_conclusions": False},
        "client_review_required": True,
        "client_authorized": False,
        "mail_created": False,
        "actor_type": "client",
        "provenance": {"source": "controlled_pilot_fixture", "synthetic": True},
    })


def ensure_comparison(url, key, scope, prior_id, later_id, account_id):
    existing = first(url, key, "credit_report_comparison_runs", "id", {
        "tenant_id": f"eq.{scope['tenant_id']}",
        "client_id": f"eq.{scope['client_id']}",
        "prior_report_id": f"eq.{prior_id}",
        "later_report_id": f"eq.{later_id}",
        "comparison_engine_version": f"eq.{ENGINE_VERSION}",
    })
    run_id = existing["id"] if existing else stable_id(scope, "comparison-run")
    upsert(url, key, "credit_report_comparison_runs", {
        "id": run_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "prior_report_id": prior_id,
        "later_report_id": later_id,
        "status": "complete",
        "comparison_engine_version": ENGINE_VERSION,
        "confidence": "low" if scope["persona"] == "b" else "medium",
        "summary": {"observation_count": 1, "causal": False, "synthetic": True},
    })
    upsert(url, key, "credit_report_comparison_results", {
        "id": stable_id(scope, "comparison-result"),
        "comparison_run_id": run_id,
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "prior_report_id": prior_id,
        "later_report_id": later_id,
        "canonical_account_id": account_id,
        "observation_type": "uncertain_comparison" if scope["persona"] == "b" else "no_measurable_change",
        "observation_value": {"causal": False, "synthetic": True},
        "observation_source": "structured_report_comparison",
        "confidence": "low" if scope["persona"] == "b" else "medium",
        "notes": "Observed synthetic report sequence; not a causal conclusion.",
    })
    upsert(url, key, "strategy_outcome_observations", {
        "id": stable_id(scope, "outcome-observation"),
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "report_id": later_id,
        "prior_report_id": prior_id,
        "canonical_account_id": account_id,
        "observation_type": "uncertain_comparison" if scope["persona"] == "b" else "no_measurable_change",
        "observation_value": {"causal": False, "synthetic": True},
        "observation_source": "structured_report_comparison",
        "confidence": "low" if scope["persona"] == "b" else "medium",
        "comparison_engine_version": ENGINE_VERSION,
        "notes": "Observed synthetic report sequence; not a causal conclusion.",
    })
    upsert(url, key, "credit_readiness_history", {
        "id": stable_id(scope, "readiness-history"),
        "tenant_id": scope["tenant_id"],
        "client_id": scope["client_id"],
        "report_id": later_id,
        "prior_report_id": prior_id,
        "credit_profile_status": "action_needed",
        "tier_1_status": "action_needed",
        "tier_2_status": "insufficient_information",
        "requirements": ["Complete the next documented evidence task"],
        "source": "controlled_pilot_fixture",
    })


def ensure_persona(url, key, persona):
    scope = resolve_scope(url, key, persona)
    initial_id = ensure_document(url, key, scope, "initial")
    followup_id = ensure_document(url, key, scope, "followup")
    initial_parser = ensure_parser(url, key, scope, initial_id, "initial")
    followup_parser = ensure_parser(url, key, scope, followup_id, "followup")
    initial_account = ensure_canonical(url, key, scope, initial_id, initial_parser, "initial")
    followup_account = ensure_canonical(url, key, scope, followup_id, followup_parser, "followup")
    discrepancy = ensure_discrepancy(url, key, scope, initial_id, initial_parser, initial_account, "initial")
    ensure_workflow(url, key, scope, initial_id, initial_parser)
    ensure_workflow(url, key, scope, followup_id, followup_parser)
    ensure_system_review(url, key, scope, initial_id, persona)
    strategy_id = {"a": "cross_bureau_balance_review", "b": "cross_bureau_status_review", "c": "purchased_debt_documentation"}[persona]
    match_id, recommendation_id = ensure_match_and_recommendation(
        url, key, scope, initial_id, initial_account, discrepancy, strategy_id
    )
    if persona == "b":
        ensure_exception(url, key, scope, initial_id, discrepancy)
    else:
        if not recommendation_id:
            raise RuntimeError("synthetic recommendation missing after fixture seed")
        ensure_selection_and_draft(url, key, scope, initial_id, initial_account, discrepancy, strategy_id, match_id, recommendation_id)
    ensure_comparison(url, key, scope, initial_id, followup_id, followup_account)
    return {
        "documents": 2,
        "parser_results": 2,
        "canonical_accounts": 2,
        "comparison_runs": 1,
        "readiness_history": 1,
        "draft": persona != "b",
        "exception": persona == "b",
    }


def main():
    parser_persona = sys.argv[1] if len(sys.argv) > 1 else None
    if parser_persona not in {"a", "b", "c"}:
        print("ERROR: persona a, b, or c is required")
        return 2
    env = {**envfile(ROOT / ".env"), **envfile(ROOT / ".env.e2e.local"), **os.environ}
    url = env.get("SUPABASE_URL") or env.get("VITE_SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: server-side Supabase credentials unavailable")
        return 1
    try:
        result = ensure_persona(url, key, parser_persona)
        print(json.dumps({"persona": parser_persona.upper(), "fixture_version": FIXTURE_VERSION, **result}))
        return 0
    except Exception as error:
        print(f"ERROR: synthetic pilot state failed for Persona {parser_persona.upper()}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
