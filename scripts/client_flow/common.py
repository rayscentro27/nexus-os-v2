#!/usr/bin/env python3
"""Local-only demo data builders for the Nexus client portal."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"
SUPABASE = RUNTIME / "supabase_ready"
TENANT = "tenant_demo_goclear"
CLIENT = "client_demo_001"

SAFETY = {
    "local_only": True,
    "github_network_access_performed": False,
    "external_action_performed": False,
    "client_contacted": False,
    "public_content_published": False,
    "real_client_data_used": False,
    "service_role_key_used": False,
    "disputes_submitted": False,
    "applications_submitted": False,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def base(record_id: str, category: str, title: str, **extra: Any) -> dict[str, Any]:
    data = {
        "id": record_id, "tenant_id": TENANT, "client_id": CLIENT, "category": category,
        "title": title, "summary": title, "status": "open", "score": None, "priority": "medium",
        "risk_level": "low", "automation_level": "client_visible_safe", "client_visible": True,
        "approval_required": False, "goclear_review_status": "not_required", "source": "local_demo_seed",
        "source_concept": "client_portal_backend", "recommended_next_action": "Review the next safe portal task.",
        "created_at": now(),
    }
    data.update(extra)
    return data


def repo_records(filename: str) -> list[dict[str, Any]]:
    path = SUPABASE / filename
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def build_client_portal_data() -> dict[str, list[dict[str, Any]]]:
    profiles = [base("client-demo-001", "client_profile", "Alex Morgan (Demo)", status="active_demo",
        summary="Placeholder client profile for local portal testing; not a real person.", membership_tier="GoClear Readiness Membership",
        current_goal="Improve readiness before a reviewed funding application", subscription_status="active_demo",
        next_review_date="2026-07-15", advisor_name="GoClear Review Team", overall_status="building_readiness")]
    flow = [base(f"portal-stage-{i+1}", "client_portal_flow", title, status=status, priority="high" if i < 3 else "medium") for i, (title, status) in enumerate([
        ("Onboarding and consent", "complete"), ("Credit repair review", "in_progress"), ("Credit profile readiness", "in_progress"),
        ("Business profile readiness", "in_progress"), ("Document readiness", "needs_attention"),
        ("Funding readiness review", "pending"), ("GoClear approval", "pending"),
    ])]
    documents = [
        base("doc-formation", "client_document", "Formation documents", status="uploaded_demo", document_status="complete"),
        base("doc-ein", "client_document", "EIN confirmation", status="uploaded_demo", document_status="complete"),
        base("doc-statements", "client_document", "Three months demo bank statements", status="uploaded_demo", document_status="complete"),
        base("doc-address", "client_document", "Current address proof", status="missing", priority="high", document_status="missing"),
        base("doc-revenue", "client_document", "Revenue summary", status="missing", priority="high", document_status="missing"),
        base("doc-account", "client_document", "Demo account statement", status="under_review", risk_level="medium", automation_level="admin_review_required", goclear_review_status="pending"),
    ]
    messages = [
        base("message-1", "client_message", "GoClear review update", status="approved_demo", summary="Two demo documents still need attention.", source="approved_client_guidance"),
        base("message-2", "client_message", "Monthly readiness refresh", status="approved_demo", summary="Your educational Nexus Readiness Scores were refreshed from demo records."),
        base("message-3", "client_message", "Draft review pending", status="approved_demo", summary="Three drafts remain internal until all required reviews are complete.", risk_level="medium"),
    ]
    return {"client_profiles_latest.json": profiles, "client_portal_flow_latest.json": flow,
            "client_documents_latest.json": documents, "client_messages_latest.json": messages}


def build_credit_repair() -> dict[str, list[dict[str, Any]]]:
    stages = ["intake", "report connected/uploaded", "negative items identified", "item classification", "document request",
              "draft letter prepared", "GoClear review", "client approval if needed", "manual/send after approval", "track update"]
    templates = [base(f"credit-template-{i+1}", "credit_workflow_template", stage.title(), status="template",
        risk_level="high" if any(x in stage for x in ("letter", "send", "review", "approval")) else "medium",
        automation_level="blocked" if stage == "manual/send after approval" else "approval_required" if any(x in stage for x in ("letter", "review", "approval")) else "admin_review_required",
        client_visible=stage not in {"item classification", "manual/send after approval"}, approval_required=any(x in stage for x in ("letter", "approval", "send")),
        goclear_review_status="pending" if i >= 5 else "not_required",
        recommended_next_action="Continue only after the recorded review gate; never contact a bureau, creditor, or collector automatically.") for i, stage in enumerate(stages)]
    workflow = [
        base("repair-item-1", "credit_repair", "Demo revolving account review", status="in_review", score=58, risk_level="high", automation_level="admin_review_required", goclear_review_status="pending"),
        base("repair-item-2", "credit_repair", "Demo collection documentation review", status="needs_documents", score=42, risk_level="high", automation_level="admin_review_required", goclear_review_status="pending"),
        base("repair-item-3", "credit_repair", "Demo goodwill draft", status="draft_ready_not_sent", score=65, priority="high", risk_level="high", automation_level="approval_required", approval_required=True, goclear_review_status="pending", recommended_next_action="GoClear and client review are required; no letter has been sent."),
    ]
    return {"credit_workflow_templates_latest.json": templates, "credit_repair_workflow_latest.json": workflow}


def build_credit_profile() -> dict[str, list[dict[str, Any]]]:
    factors = [("payment_history", 30), ("utilization", 22), ("credit_age", 10), ("account_mix", 8), ("inquiries", 8),
               ("derogatory_burden", 12), ("recent_activity", 5), ("documentation_completeness", 5)]
    rules = [base(f"credit-rule-{i+1}", "credit_profile_readiness_rule", name.replace("_", " ").title(), status="active_demo_rule",
        score=weight, summary=f"Educational readiness factor weighted at {weight}; this is not FICO or a lender model.",
        source_concept=name, recommended_next_action="Explain how this factor may affect readiness without promising a score change.") for i, (name, weight) in enumerate(factors)]
    scores = [base("credit-score-demo", "credit_profile_readiness_score", "Nexus Credit Profile Readiness", status="good_progress", score=72,
        summary="Educational Nexus Readiness Score; not FICO and not a lender decision.", priority="high",
        recommended_next_action="Reduce utilization where practical, avoid unnecessary new applications, and complete requested documentation.")]
    return {"credit_profile_readiness_rules_latest.json": rules, "credit_profile_readiness_scores_latest.json": scores}


def build_business_profile() -> dict[str, list[dict[str, Any]]]:
    fields = ["LLC/entity", "EIN", "Secretary of State status", "NAICS", "business address", "business phone", "business email/domain", "website", "DUNS/business bureau profile", "business bank account", "vendor accounts", "proof documents", "revenue documents", "bank statements"]
    missing = {"NAICS", "business email/domain", "website", "DUNS/business bureau profile", "business bank account", "vendor accounts"}
    requirements = [base(f"business-req-{i+1}", "business_profile_requirement", name, status="missing_or_in_progress" if name in missing else "complete", priority="high" if name in missing else "medium", recommended_next_action=f"{'Complete and document' if name in missing else 'Maintain'} {name}.") for i, name in enumerate(fields)]
    tasks = [base(f"business-task-{i+1}", "business_profile_task", f"Complete {name}", status="open", priority="high", source_concept="business fundability checklist") for i, name in enumerate(sorted(missing))]
    scores = [base("business-score-demo", "business_profile_readiness_score", "Business Profile Readiness", status="good_start", score=64,
        summary="Six core items complete; profile consistency and supporting records still need work.", priority="high",
        recommended_next_action="Complete professional email/domain and review DUNS/business-bureau options with GoClear.")]
    return {"business_profile_requirements_latest.json": requirements, "business_profile_tasks_latest.json": tasks,
            "business_profile_readiness_scores_latest.json": scores}


def build_funding_readiness() -> dict[str, list[dict[str, Any]]]:
    dimensions = ["personal credit readiness", "business profile readiness", "banking readiness", "document readiness", "revenue/proof readiness", "lender path readiness"]
    rules = [base(f"funding-rule-{i+1}", "funding_readiness_rule", name.title(), status="active_demo_rule", score=weight,
        risk_level="high", automation_level="admin_review_required", client_visible=True, goclear_review_status="pending",
        recommended_next_action="Use for readiness explanation only; lender-specific recommendations require GoClear review.") for i, (name, weight) in enumerate(zip(dimensions, [25, 20, 15, 15, 15, 10]))]
    scores = [base("funding-score-demo", "funding_readiness_score", "Funding Readiness", status="almost_ready", score=68,
        priority="high", risk_level="high", automation_level="admin_review_required", goclear_review_status="pending",
        summary="Almost Ready. Avoid applications until blockers are resolved and GoClear approves a reviewed path.",
        recommended_next_action="Upload current address proof and revenue summary for GoClear review.")]
    return {"funding_readiness_rules_latest.json": rules, "funding_readiness_scores_latest.json": scores}


def build_business_opportunities() -> dict[str, list[dict[str, Any]]]:
    opportunities = ["Business Credit Builder", "Starter Funding Path", "Vendor Account Setup", "Banking Upgrade", "Grant Watchlist", "Credit Union Path", "Business Card Path", "Community Bank Path", "SBA Prep Path", "Partner Offers"]
    items = [base(f"opportunity-{i+1}", "business_opportunity", title, status="matched_demo", score=max(60, 94 - i * 3),
        priority="high" if i < 3 else "medium", risk_level="high" if any(x in title for x in ("Funding", "Card", "SBA")) else "medium",
        automation_level="admin_review_required", goclear_review_status="pending",
        recommended_next_action="Review readiness and fit with GoClear before selecting or applying.") for i, title in enumerate(opportunities)]
    partner_names = ["SmartCredit", "AnnualCreditReport.com", "Bank of America", "Chase", "Wells Fargo", "U.S. Bank", "PNC", "Truist", "local credit unions/community banks", "Bluevine", "Mercury", "Relay", "Northwest Registered Agent", "ZenBusiness", "Bizee", "iPostal1", "Grasshopper", "QuickBooks", "DocuPost", "USPS Certified Mail"]
    partners = [base(f"partner-{i+1}", "partner_offer", title, status="not_connected", score=None, risk_level="medium",
        automation_level="admin_review_required", client_visible=False, approval_required=True, goclear_review_status="pending",
        summary="Best client outcome first; affiliate opportunity second; free/DIY option must remain visible.",
        recommended_next_action="Verify fit, current terms, disclosure, and a free/DIY alternative before client visibility.") for i, title in enumerate(partner_names)]
    return {"business_opportunities_latest.json": items, "partner_offers_latest.json": partners}


def build_client_tasks() -> dict[str, list[dict[str, Any]]]:
    tasks = [
        base("task-1", "client_task", "Upload current address proof", status="open", priority="high", due_date="2026-07-03", goclear_review_status="pending"),
        base("task-2", "client_task", "Review utilization action plan", status="in_progress", priority="high", due_date="2026-07-05"),
        base("task-3", "client_task", "Review draft letter packet", status="pending_review", priority="high", due_date="2026-07-08", risk_level="high", automation_level="approval_required", approval_required=True, goclear_review_status="pending", recommended_next_action="Review only; nothing has been sent."),
        base("task-4", "client_task", "Complete professional domain email", status="open", due_date="2026-07-10"),
    ]
    return {"client_tasks_latest.json": tasks}


def build_admin_review() -> dict[str, list[dict[str, Any]]]:
    card_data = [
        ("review-credit-guidance", "Credit-sensitive recommendation", "Approve client-safe explanation", "high"),
        ("review-letter-drafts", "Dispute/letter drafts", "Approve, reject, or defer draft review; no sending", "high"),
        ("review-funding-path", "Funding recommendation", "Approve client-visible readiness path", "high"),
        ("review-partner-fit", "Partner recommendation", "Approve fit, disclosure, and free alternative", "medium"),
        ("review-client-next-step", "Client-facing next step", "Approve exact client guidance", "medium"),
        ("review-documents", "Document review", "Confirm demo document status", "high"),
        ("review-subscription", "Subscription upgrade/referral opportunity", "Approve whether this is appropriate to show", "medium"),
        ("review-escalation", "Client question/escalation", "Answer or defer client question", "high"),
    ]
    cards = [base(card_id, "approval_card", title, status="pending", priority="high", risk_level=risk,
        automation_level="approval_required", client_visible=False, approval_required=True, goclear_review_status="pending",
        reason=title, exact_decision_needed=decision, options=["approve", "reject", "defer"],
        client_visible_after_approval=True, external_action_performed=False,
        recommended_next_action=decision) for card_id, title, decision, risk in card_data]
    queue = [{**item, "category": "admin_review", "source_concept": item["category"]} for item in cards]
    return {"approval_cards_latest.json": cards, "admin_review_queue_latest.json": queue}


def build_client_guide() -> dict[str, list[dict[str, Any]]]:
    responses = {
        "what_do_i_do_next": "Upload current address proof and your revenue summary.",
        "why_not_funding_ready": "Readiness blockers and two missing documents still need GoClear review.",
        "how_to_improve_credit": "Focus on payment consistency, manageable utilization, and avoiding unnecessary applications; results are not guaranteed.",
        "business_profile_next_step": "Complete professional email/domain and review the DUNS path with GoClear.",
        "documents_needed": "Current address proof and a revenue summary are still needed in the demo checklist.",
        "what_goclear_is_reviewing": "GoClear is reviewing draft materials, a demo statement, and funding-readiness blockers; nothing has been sent.",
        "can_i_apply_for_funding_now": "Not yet. GoClear has not approved an application path.",
        "what_opportunity_should_i_focus_on": "Start with the Business Credit Builder workflow and complete profile gaps.",
    }
    templates = [base(f"guide-template-{i+1}", "client_bot_response_template", key, status="approved_demo_template", summary=value,
        source="approved_client_guidance", source_concept=key) for i, (key, value) in enumerate(responses.items())]
    approved = [{**item, "id": item["id"].replace("guide-template", "approved-guidance"), "category": "approved_client_guidance"} for item in templates]
    questions = [base("client-question-demo", "client_question", "What should I do next?", status="answered_from_approved_template", summary=responses["what_do_i_do_next"], source="client_portal_demo")]
    escalations = [base("client-escalation-template", "client_escalation", "Question requires GoClear judgment", status="template_not_submitted", risk_level="high", automation_level="approval_required", client_visible=False, approval_required=True, goclear_review_status="pending", recommended_next_action="Create an admin review item only after a real approved intake path exists.")]
    return {"client_bot_response_templates_latest.json": templates, "approved_client_guidance_latest.json": approved,
            "client_questions_latest.json": questions, "client_escalations_latest.json": escalations}


def build_client_hermes() -> dict[str, list[dict[str, Any]]]:
    bridge = [base("bridge-guidance-1", "client_hermes_guidance", "Approved document next step", status="approved_demo", summary="Upload current address proof and revenue summary.", source="hermes_admin_review", source_concept="approved_client_guidance"),
              base("bridge-guidance-2", "client_hermes_guidance", "Approved funding warning", status="approved_demo", summary="Complete blockers and request GoClear review before applying.", risk_level="high", source="ray_review", source_concept="approved_client_guidance")]
    notes = [base("hermes-note-1", "hermes_admin_note", "Keep Hermes private", status="active_policy", client_visible=False, automation_level="admin_review_required", summary="Hermes remains admin-only and cannot message clients directly."),
             base("hermes-note-2", "hermes_admin_note", "Structured bridge only", status="active_policy", client_visible=False, automation_level="admin_review_required", summary="Only approved_client_guidance crosses into Nexus Guide responses.")]
    return {"client_hermes_guidance_latest.json": bridge, "hermes_admin_notes_latest.json": notes}


def build_subscription() -> dict[str, list[dict[str, Any]]]:
    model = [base("membership-demo", "subscription_membership_model", "GoClear Readiness Membership", status="active_demo", priority="high", summary="Monthly educational credit, business-profile, document, and funding-readiness value loop.")]
    steps = ["Credit/profile check", "Business profile check", "Readiness score update", "Task progress review", "Missing document check", "Next best action", "Partner/tool recommendation if useful", "Funding-readiness update", "Monthly education/reminder", "Referral/upgrade trigger"]
    loop = [base(f"value-loop-{i+1}", "subscription_value_loop", title, status="active_demo_step", priority="high" if i < 6 else "medium") for i, title in enumerate(steps)]
    return {"subscription_membership_model_latest.json": model, "subscription_value_loop_latest.json": loop}


def build_proof() -> dict[str, list[dict[str, Any]]]:
    return {"proof_events_latest.json": [base("proof-client-build", "proof_event", "Client portal backend built locally", status="success", client_visible=False, summary="Generated demo-only Supabase-ready records without network or external action."),
                                         base("proof-guide-boundary", "proof_event", "Nexus Guide separated from Hermes", status="success", client_visible=False, summary="Structured approved-guidance bridge enforced in data model.")]}


BUILDERS: dict[str, Callable[[], dict[str, list[dict[str, Any]]]]] = {
    "client_portal_data": build_client_portal_data,
    "credit_repair": build_credit_repair,
    "credit_profile_readiness": build_credit_profile,
    "business_profile_readiness": build_business_profile,
    "funding_readiness": build_funding_readiness,
    "business_opportunities": build_business_opportunities,
    "client_tasks": build_client_tasks,
    "admin_review": build_admin_review,
    "client_guide_guidance": build_client_guide,
    "client_hermes_guidance": build_client_hermes,
}


def write_exports(exports: dict[str, list[dict[str, Any]]]) -> list[str]:
    SUPABASE.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, records in exports.items():
        path = SUPABASE / filename
        path.write_text(json.dumps(records, indent=2) + "\n")
        paths.append(str(path.relative_to(ROOT)))
    return paths


def attach_repo_concepts(exports: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    concepts = repo_records("repo_concepts_latest.json")
    aliases = {
        "credit_workflow_template": "credit_repair", "credit_repair": "credit_repair",
        "credit_profile_readiness_rule": "credit_profile_readiness", "credit_profile_readiness_score": "credit_profile_readiness",
        "business_profile_requirement": "business_profile_readiness", "business_profile_task": "business_profile_readiness",
        "business_profile_readiness_score": "business_profile_readiness", "funding_readiness_rule": "funding_readiness",
        "funding_readiness_score": "funding_readiness", "business_opportunity": "business_opportunities",
        "partner_offer": "partner_offers", "client_task": "client_tasks", "approval_card": "admin_review",
        "admin_review": "admin_review", "client_bot_response_template": "client_guide_guidance",
        "approved_client_guidance": "client_guide_guidance", "client_hermes_guidance": "hermes_guidance",
    }
    by_area: dict[str, list[dict[str, Any]]] = {}
    for concept in concepts:
        by_area.setdefault(concept.get("category", ""), []).append(concept)
    for records in exports.values():
        for index, item in enumerate(records):
            area = aliases.get(item.get("category", ""))
            matches = by_area.get(area or "", [])
            if matches:
                item["source_concept"] = matches[index % len(matches)]["id"]
                item["source"] = "local_static_repo_concept_seed"
    return exports


def write_builder_report(name: str, exports: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    exports = attach_repo_concepts(exports)
    paths = write_exports(exports)
    count = sum(len(records) for records in exports.values())
    report = {"ok": True, "builder": name, "generated_at": now(), "records_created": count,
              "supabase_ready_files_created": paths, **SAFETY}
    RUNTIME.mkdir(parents=True, exist_ok=True); MANUAL.mkdir(parents=True, exist_ok=True)
    stem = "client_flow_admin_review" if name == "admin_review" else f"client_flow_{name}"
    (RUNTIME / f"{stem}_latest.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [f"# Client Flow: {name.replace('_', ' ').title()}", "", f"- ok: true", f"- records_created: {count}",
             "- local_only: true", "- github_network_access_performed: false", "- external_action_performed: false",
             "- client_contacted: false", "- real_client_data_used: false", "", "## Supabase-ready files"]
    lines += [f"- `{path}`" for path in paths]
    (MANUAL / f"{stem}_latest.md").write_text("\n".join(lines) + "\n")
    return report


def run_builder(name: str) -> dict[str, Any]:
    if name not in BUILDERS:
        raise ValueError(f"Unknown builder: {name}")
    return write_builder_report(name, BUILDERS[name]())


def cli(name: str) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = run_builder(name)
    print(json.dumps(report, indent=2) if args.json else f"{name}: {report['records_created']} records")
    return 0
