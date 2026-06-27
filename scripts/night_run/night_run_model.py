"""Shared model for the Nexus night-run + monetization reports.

Mirrors the TS source-of-truth configs (goclearSubscriptionTiers.ts, onlineBusinessBankAffiliates.ts,
nexusRevenueStreams.ts, clientWorkflowMonetization.ts) and provides a JSON+MD report writer.
Deterministic, local-first, internal/report-only. No scraping, no external AI, no DB writes,
no publish/send/charge/contact.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME_DIR = ROOT / "reports" / "runtime"
MANUAL_DIR = ROOT / "reports" / "manual_publish"

SAFETY = {
    "external_action": False,
    "messages_sent": False,
    "client_contacted": False,
    "money_spent": False,
    "client_charged": False,
    "trade_placed": False,
    "letters_mailed": False,
    "disputes_submitted": False,
    "smartcredit_password_stored": False,
    "smartcredit_scraped": False,
    "docupost_sending": False,
    "live_client_vault_connected": False,
    "second_supabase_connected": False,
    "external_ai_on_client_data": False,
    "broad_scrape": False,
    "level_3_blocked": True,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_report(name: str, report: dict, md_lines: list[str]) -> tuple[Path, Path]:
    """Write reports/runtime/<name>.json + reports/manual_publish/<name>.md."""
    runtime = RUNTIME_DIR / f"{name}.json"
    manual = MANUAL_DIR / f"{name}.md"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    manual.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text(json.dumps(report, indent=2))
    header = [
        f"# {report.get('title', name)}",
        "",
        f"- timestamp: {report.get('generated_at')}",
        f"- status: {report.get('status', 'ok' if report.get('ok', True) else 'failed')}",
        f"- dry_run: {report.get('dry_run', True)}",
        "- external_action: false · money_spent: false · level_3_blocked: true",
        "",
    ]
    manual.write_text("\n".join(header + md_lines) + "\n")
    return runtime, manual


# ---- Curated monetization data (mirrors TS) ---------------------------------

MARKET_PRICE_BANDS = [
    {"category": "Credit repair (DIY/service)", "low": 19, "typical": 79, "high": 149},
    {"category": "Credit monitoring", "low": 10, "typical": 25, "high": 40},
    {"category": "Business credit monitoring", "low": 39, "typical": 79, "high": 149},
    {"category": "Business funding readiness/coaching", "low": 97, "typical": 199, "high": 497},
    {"category": "Business credit builder subscription", "low": 49, "typical": 99, "high": 199},
]

COMPETITOR_PLAN_FEATURES = [
    "credit report review", "dispute guidance", "credit monitoring", "score tracking", "portal access",
    "monthly updates", "letters/disputes", "creditor interventions", "business credit guidance",
    "funding preparation", "coaching/consultation", "reminders/follow-up", "document tracking",
]

GOCLEAR_TIERS = [
    {"tier_id": "credit_action_plan", "name": "Credit Monitoring & Action Plan", "band": "low",
     "recommended_monthly": 49, "range": [39, 69],
     "includes": ["credit report review", "score tracking (SmartCredit)", "dispute guidance", "monthly action plan", "portal access", "reminders"],
     "retention_reason": "Ongoing monitoring + monthly steps keep progress visible.", "next_tier": "credit_plus_business_setup"},
    {"tier_id": "credit_plus_business_setup", "name": "Credit + Business Setup", "band": "core",
     "recommended_monthly": 97, "range": [79, 129],
     "includes": ["everything in Action Plan", "business setup checklist", "affiliate/DIY choices", "letter packet tracking", "document tracking", "business credit guidance"],
     "retention_reason": "Clients keep building business credit after personal credit improves.", "next_tier": "funding_readiness"},
    {"tier_id": "funding_readiness", "name": "Funding Readiness", "band": "premium",
     "recommended_monthly": 197, "range": [149, 297],
     "includes": ["everything in Credit + Business Setup", "funding readiness tracking", "bankability scoring", "vendor accounts guidance", "funding preparation", "Ray-approved funding path"],
     "retention_reason": "Clients want to reach/maintain funding-ready status.", "next_tier": "post_funding_growth"},
    {"tier_id": "post_funding_growth", "name": "Post-Funding Growth", "band": "post_funding",
     "recommended_monthly": 149, "range": [99, 249],
     "includes": ["monthly financial readiness tracking", "business credit building", "vendor accounts", "grant/funding opportunity monitoring", "bankability maintenance"],
     "retention_reason": "After funding, clients keep growing credit and monitoring new opportunities.", "next_tier": None},
]

ONLINE_BANK_PARTNERS = [
    {"partner": "Bluevine", "fits": ["startup", "llc_owner", "funding_readiness"], "no_monthly_fee": True, "invoicing": True, "statements_for_funding": True},
    {"partner": "Mercury", "fits": ["startup", "llc_owner", "business_credit_building"], "no_monthly_fee": True, "invoicing": False, "statements_for_funding": True},
    {"partner": "Relay", "fits": ["llc_owner", "bookkeeping"], "no_monthly_fee": True, "invoicing": False, "statements_for_funding": True},
    {"partner": "Novo", "fits": ["startup", "llc_owner", "invoicing"], "no_monthly_fee": True, "invoicing": True, "statements_for_funding": True},
    {"partner": "Found", "fits": ["solopreneur", "startup"], "no_monthly_fee": True, "invoicing": True, "statements_for_funding": True},
    {"partner": "North One", "fits": ["small_business", "llc_owner"], "no_monthly_fee": False, "invoicing": False, "statements_for_funding": True},
    {"partner": "Lili", "fits": ["solopreneur", "startup"], "no_monthly_fee": True, "invoicing": True, "statements_for_funding": True},
]
ONLINE_BANK_PRIMARY = "Bluevine"
ONLINE_BANK_BACKUPS = ["Mercury", "Relay"]
ONLINE_BANK_DIY = "Client's own bank / local credit union (upload bank proof)"
ONLINE_BANK_COMPLIANCE = "Nexus does not open accounts automatically and does not submit applications. No guarantee of approval."

REVENUE_STREAMS = [
    {"stream_id": "readiness_review", "name": "GoClear/Apex Credit + Business Funding Readiness Review",
     "trigger": "New signup / profile created", "pricing": "Likely $97 readiness review (validate)",
     "approval_gate": "Client plan exposed only after Ray approval", "upsell": "Into monthly subscription"},
    {"stream_id": "monthly_subscription", "name": "Monthly GoClear Subscription",
     "trigger": "After readiness review / ongoing tracking", "pricing": "~$49 / ~$97 / ~$197 / ~$149 post-funding",
     "approval_gate": "No client charged automatically; billing separate approved step", "upsell": "Tier ladder to post-funding"},
    {"stream_id": "affiliate_partner_engine", "name": "Affiliate + Partner Recommendation Engine",
     "trigger": "A workflow task needs a tool/service", "pricing": "Commission/referral; no client charged by Nexus",
     "approval_gate": "Affiliate URLs activate only via approved partner_offers", "upsell": "Aligned to missing tasks"},
    {"stream_id": "funding_commission_pipeline", "name": "Funding Commission / Funding Readiness Pipeline",
     "trigger": "Client reaches funding-ready", "pricing": "Funding commission opportunity (tracked, not auto-applied)",
     "approval_gate": "Ray approves funding path; no auto-apply/auto-contact", "upsell": "Into Post-Funding Growth tier"},
]

AFFILIATE_STREAM_ITEMS = [
    ("credit_monitoring", "SmartCredit", "AnnualCreditReport.com (free)", 80),
    ("business_formation", "Formation partner", "State SoS + IRS.gov (free EIN)", 70),
    ("registered_agent", "Registered agent partner", "Self as agent", 40),
    ("business_address", "Virtual address partner", "Existing commercial address", 55),
    ("business_phone", "VoIP partner", "Any business line", 45),
    ("website_domain_email", "Website/domain partner", "Self-built site + domain email", 50),
    ("business_credit_profile", "Business credit tool", "Free DUNS from D&B", 65),
    ("online_business_bank_account", "Bluevine (primary)", "Client's own bank/credit union", 70),
    ("bookkeeping_accounting", "Bookkeeping partner", "DIY spreadsheet", 45),
    ("vendor_credit_accounts", "Vendor credit partner", "Net-30 vendors (DIY)", 60),
    ("online_mailing", "DocuPost", "USPS Certified Mail", 55),
]

# ---- Process inventory (mirrors the repo's safe processes) -------------------
# (name, category, status, script_or_module)
PROCESS_INVENTORY = [
    ("Automation Control Center", "automation", "ready_to_run", "scripts/automation/generate_automation_control_report.py"),
    ("Automation policy verification", "automation", "ready_to_run", "scripts/automation/verify_automation_policy.py"),
    ("High-risk guard verification", "automation", "ready_to_run", "scripts/automation/verify_high_risk_guards.py"),
    ("Scheduler approval candidates", "automation", "ready_to_run", "scripts/automation/generate_scheduler_approval_candidates.py"),
    ("AI department access verification", "ai_access", "ready_to_run", "scripts/ai_access/verify_ai_department_access.py"),
    ("AI agent runtime verification", "ai_access", "ready_to_run", "scripts/ai_access/verify_agent_runtime.py"),
    ("AI access report", "ai_access", "ready_to_run", "scripts/ai_access/generate_ai_access_report.py"),
    ("Credit Specialist contract report", "ai_access", "ready_to_run", "scripts/ai_access/generate_credit_specialist_contract_report.py"),
    ("Hermes redaction report", "ai_access", "ready_to_run", "scripts/ai_access/generate_hermes_redaction_report.py"),
    ("Client Vault contract report", "client_vault", "ready_to_run", "scripts/client_vault/generate_client_vault_contract_report.py"),
    ("Client Vault contract verification", "client_vault", "ready_to_run", "scripts/client_vault/verify_client_vault_contract.py"),
    ("Client workflow engine report", "client_workflow", "ready_to_run", "scripts/client_workflow/generate_client_workflow_report.py"),
    ("Affiliate recommendation report", "client_workflow", "ready_to_run", "scripts/client_workflow/generate_affiliate_recommendation_report.py"),
    ("Stuck-client report", "client_workflow", "ready_to_run", "scripts/client_workflow/generate_stuck_client_report.py"),
    ("Hermes client recommendations", "client_workflow", "ready_to_run", "scripts/client_workflow/generate_hermes_client_recommendations.py"),
    ("Client workflow policy verification", "client_workflow", "ready_to_run", "scripts/client_workflow/verify_client_workflow_policy.py"),
    ("SmartCredit/AnnualCreditReport source flow", "client_workflow", "ready_to_run", "config: clientWorkflow.ts"),
    ("Credit score/report analysis flow", "client_workflow", "ready_to_run", "lib: clientWorkflowEngine.ts"),
    ("Business setup workflow", "client_workflow", "ready_to_run", "config: clientWorkflow.ts"),
    ("DocuPost/USPS mailing workflow", "client_workflow", "ready_to_run", "config: clientWorkflow.ts"),
    ("Reminders/stuck-client engine", "client_workflow", "ready_to_run", "config: clientWorkflowReminders.ts"),
    ("GoClear subscription market research", "monetization", "ready_to_run", "scripts/night_run/generate_goclear_subscription_market_research.py"),
    ("Online business bank affiliate research", "monetization", "ready_to_run", "scripts/night_run/generate_online_business_bank_affiliate_research.py"),
    ("Four revenue streams", "monetization", "ready_to_run", "scripts/night_run/generate_revenue_streams.py"),
    ("Client workflow monetization", "monetization", "ready_to_run", "scripts/night_run/generate_client_workflow_monetization.py"),
    ("Hermes executive brief", "hermes", "ready_to_run", "scripts/night_run/generate_hermes_executive_brief.py"),
    ("SEO/affiliate scoring", "growth", "needs_data", "lib: seoKeywordScout.ts / affiliateOpportunityTracker.ts"),
    ("YouTube research foundation", "research", "needs_config", "config: youtubeChannelWatchlist.ts (API not configured by design)"),
    ("Trading paper-only research", "trading", "manual_only", "scripts/trading/*"),
    ("Approvals / Ray Review Queue", "approvals", "ready_to_run", "scripts/review/build_ray_review_queue.py"),
    ("Command Center / System Health", "system", "ready_to_run", "npm run nexus:watch"),
    ("Live Client Vault connection", "client_vault", "blocked_by_policy", "blocked: not_connected_by_design"),
    ("Sending/mailing/charging/contacting", "execution", "approval_required", "blocked until Ray approval"),
]
