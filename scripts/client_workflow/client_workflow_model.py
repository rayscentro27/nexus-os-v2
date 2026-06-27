"""Shared Client Workflow model for dry-run report generators.

Deterministic, local-first. Mirrors src/config/clientWorkflow.ts + src/lib/clientWorkflow*.ts.
Provides sample clients so dry-runs pass without any DB or external service. Live data, when
Supabase is configured, is read read-only; no writes happen in dry-run.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

STAGES = [
    "signup_started", "profile_created", "credit_report_source_needed", "credit_report_pending",
    "credit_report_received", "credit_analysis_ready", "business_setup_needed",
    "business_setup_in_progress", "business_analysis_ready", "letters_needed", "letters_ready",
    "mailing_needed", "funding_readiness_pending", "ray_review_needed",
    "approved_client_plan_ready", "client_plan_visible", "funding_ready",
]

# Action -> automation level (mirrors CLIENT_WORKFLOW_ACTION_LEVELS).
ACTION_LEVELS = {
    "workflow_status_update": "autonomous_internal",
    "credit_analysis": "autonomous_internal",
    "business_bankability_scoring": "autonomous_internal",
    "funding_readiness_scoring": "autonomous_internal",
    "reminder_draft_generation": "autonomous_internal",
    "stuck_client_detection": "autonomous_internal",
    "hermes_prep_brief": "autonomous_internal",
    "affiliate_opportunity_scoring": "autonomous_internal",
    "send_client_message": "approval_gated",
    "contact_client_or_lead": "approval_gated",
    "publish_client_plan": "approval_gated",
    "activate_connector": "approval_gated",
    "activate_scheduler": "approval_gated",
    "mail_letters": "approval_gated",
    "submit_dispute": "approval_gated",
    "apply_for_funding": "approval_gated",
    "expose_client_recommendation": "approval_gated",
    "store_smartcredit_password": "blocked_high_risk",
    "scrape_smartcredit": "blocked_high_risk",
    "auto_submit_disputes": "blocked_high_risk",
    "auto_mail_letters": "blocked_high_risk",
    "auto_contact_bureaus_creditors": "blocked_high_risk",
    "auto_file_llc_ein_state": "blocked_high_risk",
    "auto_open_accounts": "blocked_high_risk",
    "auto_apply_funding": "blocked_high_risk",
    "external_ai_on_client_credit_data": "blocked_high_risk",
}

REMINDER_TIMINGS = {"urgent_blocker_hours": 24, "incomplete_setup_days": 3, "stuck_task_days": 7, "escalation_days": 14}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def progress_percentage(stage: str) -> int:
    idx = STAGES.index(stage) if stage in STAGES else 0
    return round((idx / (len(STAGES) - 1)) * 100)


def revenue_risk(days_stuck: int) -> str:
    if days_stuck >= REMINDER_TIMINGS["escalation_days"]:
        return "critical"
    if days_stuck >= REMINDER_TIMINGS["stuck_task_days"]:
        return "high"
    if days_stuck >= REMINDER_TIMINGS["incomplete_setup_days"]:
        return "medium"
    return "low"


def escalation(days_stuck: int) -> str:
    if days_stuck >= REMINDER_TIMINGS["escalation_days"]:
        return "ray"
    if days_stuck >= REMINDER_TIMINGS["stuck_task_days"]:
        return "hermes"
    return "none"


def _client(cid, label, stage, days_stuck, source, score_available, funding_score, signals=None):
    return {
        "client_id": cid,
        "client_label": label,
        "current_stage": stage,
        "days_stuck": days_stuck,
        "progress_percentage": progress_percentage(stage),
        "selected_credit_report_source": source,
        "score_available": score_available,
        "funding_readiness_impact": funding_score,
        "revenue_risk_level": revenue_risk(days_stuck),
        "ray_review_status": "pending_review" if stage == "ray_review_needed" else "not_needed",
        "report_upload_status": "received" if STAGES.index(stage) >= STAGES.index("credit_report_received") else "pending",
        "report_import_status": "not_started",
        "signals": signals or {},
    }


def sample_clients() -> list[dict]:
    """Deterministic sample clients covering each interesting state."""
    return [
        _client("c1", "Client A", "credit_report_pending", 9, "smartcredit", False, 30,
                {"smartcredit_incomplete": True}),
        _client("c2", "Client B", "credit_report_pending", 2, "annualcreditreport", False, 25,
                {"no_score": True}),
        _client("c3", "Client C", "business_setup_in_progress", 5, "smartcredit", True, 55,
                {"business_missing_items": ["Business Bank Account", "DUNS / Business Credit Profile"]}),
        _client("c4", "Client D", "mailing_needed", 8, "smartcredit", True, 50,
                {"letters_ready_not_mailed": True, "mailing_proof_missing": True}),
        _client("c5", "Client E", "funding_readiness_pending", 3, "smartcredit", True, 68,
                {"high_utilization": True, "funding_blockers": ["High credit utilization (>30%)"]}),
        _client("c6", "Client F", "ray_review_needed", 1, "smartcredit", True, 80, {}),
        _client("c7", "Client G", "funding_readiness_pending", 16, "annualcreditreport", False, 40,
                {"do_not_send_to_lenders": True}),
    ]


def load_clients() -> tuple[list[dict], str]:
    """Read clients from Supabase if configured (read-only); else sample. Returns (clients, source)."""
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "social"))
        import _supabase as sb  # noqa: E402
        if sb.configured():
            _status, rows = sb.get("client_profiles", "select=*&order=updated_at.desc&limit=200")
            if isinstance(rows, list) and rows:
                clients = []
                for r in rows:
                    stage = r.get("current_stage", "signup_started")
                    clients.append({
                        "client_id": str(r.get("id")),
                        "client_label": r.get("client_label", "Client"),
                        "current_stage": stage,
                        "days_stuck": int(r.get("days_stuck") or 0),
                        "progress_percentage": int(r.get("progress_percentage") or progress_percentage(stage)),
                        "selected_credit_report_source": r.get("selected_credit_report_source"),
                        "score_available": bool(r.get("score_available")),
                        "funding_readiness_impact": int(r.get("funding_readiness_impact") or 0),
                        "revenue_risk_level": r.get("revenue_risk_level", "low"),
                        "ray_review_status": r.get("ray_review_status", "not_needed"),
                        "report_upload_status": r.get("report_upload_status", "not_started"),
                        "report_import_status": r.get("report_import_status", "not_started"),
                        "signals": (r.get("metadata") or {}).get("signals", {}),
                    })
                return clients, "supabase_live_readonly"
    except Exception:
        pass
    return sample_clients(), "deterministic_sample"


def hermes_recommendations(clients: list[dict]) -> list[dict]:
    recs = []
    for p in clients:
        s = p.get("signals", {})
        base = {"client_id": p["client_id"], "client_label": p["client_label"], "internal_only": True,
                "revenue_risk_level": p["revenue_risk_level"]}
        if p["days_stuck"] >= REMINDER_TIMINGS["stuck_task_days"]:
            recs.append({**base, "kind": "stuck_client", "approval_required": False,
                         "message": f'{p["client_label"]} stuck {p["days_stuck"]} days at "{p["current_stage"]}".'})
        if p["current_stage"] == "credit_report_pending":
            recs.append({**base, "kind": "credit_report_pending", "approval_required": False,
                         "message": f'{p["client_label"]} still needs to provide a credit report.'})
        if s.get("smartcredit_incomplete"):
            recs.append({**base, "kind": "smartcredit_incomplete", "approval_required": False,
                         "message": f'{p["client_label"]} selected SmartCredit but has not completed signup/import.'})
        if s.get("no_score"):
            recs.append({**base, "kind": "no_score_available", "approval_required": False,
                         "message": f'{p["client_label"]} used AnnualCreditReport.com (no score). Recommend SmartCredit for score tracking or enter a score manually.'})
        if s.get("business_missing_items"):
            recs.append({**base, "kind": "business_setup_incomplete", "approval_required": False,
                         "message": f'{p["client_label"]} missing: {", ".join(s["business_missing_items"][:3])}.'})
        if s.get("letters_ready_not_mailed"):
            recs.append({**base, "kind": "letters_unmailed", "approval_required": False,
                         "message": f'{p["client_label"]} has approved letters not yet mailed.'})
        if s.get("mailing_proof_missing"):
            recs.append({**base, "kind": "mailing_proof_missing", "approval_required": False,
                         "message": f'{p["client_label"]} mailed letters but no proof uploaded.'})
        if s.get("funding_blockers"):
            recs.append({**base, "kind": "funding_blocker", "approval_required": False,
                         "message": f'{p["client_label"]} funding blockers: {", ".join(s["funding_blockers"][:3])}.'})
        if p["current_stage"] == "ray_review_needed" or p["ray_review_status"] == "pending_review":
            recs.append({**base, "kind": "ready_for_ray_review", "approval_required": True,
                         "message": f'{p["client_label"]} has a full action plan ready for Ray review.'})
        score = p["funding_readiness_impact"]
        if 60 <= score < 75:
            recs.append({**base, "kind": "near_funding_ready", "approval_required": False,
                         "message": f'{p["client_label"]} near funding-ready ({score}/100).'})
            recs.append({**base, "kind": "upsell_opportunity", "approval_required": False,
                         "message": f'{p["client_label"]} is a future commission opportunity once blockers clear.'})
        if score < 60 and p["current_stage"] in ("funding_readiness_pending", "funding_ready"):
            recs.append({**base, "kind": "do_not_send_to_lenders", "approval_required": False,
                         "message": f'{p["client_label"]} NOT funding-ready ({score}/100). Do not route to lenders.'})
        if p["revenue_risk_level"] in ("high", "critical"):
            recs.append({**base, "kind": "revenue_risk", "approval_required": False,
                         "message": f'{p["client_label"]} is a {p["revenue_risk_level"]} revenue risk (stuck {p["days_stuck"]} days).'})
    return recs


def digest(clients: list[dict]) -> dict:
    recs = hermes_recommendations(clients)

    def c(kind):
        return sum(1 for r in recs if r["kind"] == kind)

    ray_ready = c("ready_for_ray_review")
    stuck = c("stuck_client")
    top = (f"{ray_ready} client(s) ready for Ray review." if ray_ready else
           f"{stuck} client(s) stuck — follow up to protect revenue." if stuck else
           "No urgent client workflow actions.")
    return {
        "total_clients": len(clients),
        "stuck_clients": stuck,
        "credit_reports_pending": c("credit_report_pending"),
        "smartcredit_incomplete": c("smartcredit_incomplete"),
        "no_score": c("no_score_available"),
        "business_incomplete": c("business_setup_incomplete"),
        "letters_unmailed": c("letters_unmailed"),
        "mailing_proof_missing": c("mailing_proof_missing"),
        "ready_for_ray_review": ray_ready,
        "upsell_opportunities": c("upsell_opportunity"),
        "near_funding_ready": c("near_funding_ready"),
        "revenue_risk_clients": c("revenue_risk"),
        "do_not_send_to_lenders": c("do_not_send_to_lenders"),
        "recommendations": recs,
        "top_recommendation": top,
    }
