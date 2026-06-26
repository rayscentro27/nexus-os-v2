"""Shared Nexus automation model for control/verification scripts.

Mirrors src/config/nexusAutomationLevels.ts, nexusAutomationCategoryMatrix.ts, and
nexusHighRiskGuards.ts. Deterministic and local-first: no scraping, no external AI, no publish,
send, trade, deploy, scheduler activation, or v1 worker touches.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# ---- Levels -----------------------------------------------------------------

LEVELS: dict[str, dict[str, Any]] = {
    "autonomous_internal": {
        "level_number": 1,
        "label": "Autonomous Internal Automation",
        "approval_required": False,
        "ray_review_required": False,
        "special_contract_required": False,
        "rollback_required": False,
        "default_state": "enabled_internal",
    },
    "approval_gated": {
        "level_number": 2,
        "label": "Approval-Gated Automation",
        "approval_required": True,
        "ray_review_required": True,
        "special_contract_required": False,
        "rollback_required": True,
        "default_state": "prepare_only",
    },
    "blocked_high_risk": {
        "level_number": 3,
        "label": "Blocked / High-Risk Automation",
        "approval_required": True,
        "ray_review_required": True,
        "special_contract_required": True,
        "rollback_required": True,
        "default_state": "blocked",
    },
}

# ---- Deterministic classifier (mirrors nexusAutomationPolicy.ts) -------------

_BLOCKED = [
    r"live[ _-]?trad", r"\bbroker\b", r"funded[ _-]?account", r"auto_executor",
    r"\bpayment\b", r"\bcharge\b", r"\brefund\b", r"ad[ _-]?spend",
    r"production[ _-]?deploy", r"\brls\b", r"\bdestructive\b", r"drop[ _-]?table",
    r"secret", r"\.env\b", r"broad[ _-]?scrap", r"media[ _-]?download",
    r"youtube.*download|download.*youtube", r"bulk[ _-]?send", r"\bspam\b",
    r"tenant[ _-]?isolation[ _-]?bypass", r"client[ _-]?data[ _-]?exposure",
    r"external[ _-]?ai.*(sensitive|private|customer)|(sensitive|private|customer).*external[ _-]?ai",
]
_GATED = [
    r"\bpublish", r"\bsend\b", r"\bemail\b", r"\bsms\b", r"\bdm\b", r"\bsocial\b",
    r"\bpost\b", r"\bcampaign\b", r"\bcontact\b", r"\blead\b", r"\bclient\b",
    r"\bdeploy\b", r"\bproduction\b", r"\bscheduler\b", r"\bcron\b", r"\blaunchd\b",
    r"\bsystemd\b", r"\bconnector\b", r"\boauth\b", r"\bactivate\b", r"\bspend\b",
]


def classify_automation_level(action: str) -> str:
    text = action or ""
    if any(re.search(p, text, re.I) for p in _BLOCKED):
        return "blocked_high_risk"
    if any(re.search(p, text, re.I) for p in _GATED):
        return "approval_gated"
    return "autonomous_internal"


# ---- Category matrix (mirrors nexusAutomationCategoryMatrix.ts) --------------

def _c(cid, name, dept, l1, l2, l3, risk, nxt):
    return {
        "category_id": cid,
        "category_name": name,
        "owner_department": dept,
        "level_1_allowed_actions": l1,
        "level_2_approval_gated_actions": l2,
        "level_3_blocked_actions": l3,
        "risk_notes": risk,
        "next_recommended_action": nxt,
    }


CATEGORY_MATRIX: list[dict[str, Any]] = [
    _c("research_source_intake", "Research / Source Intake", "source_intake",
       ["source intake enrichment", "scoring", "routing", "internal cards", "internal reports"],
       ["connector activation for live source pulls", "scheduler activation"],
       ["broad scraping", "external AI on sensitive/private/customer data"],
       "Internal research is safe; broad scraping and sensitive external AI are blocked.",
       "Keep enrichment/scoring autonomous; leave live connectors and scheduler as approval-gated."),
    _c("youtube_research", "YouTube Research", "source_intake",
       ["metadata check (placeholder/fallback)", "transcript review from local samples", "scoring/routing", "internal reports", "Hermes prep brief"],
       ["metadata connector activation", "scheduler activation", "publish of derived content"],
       ["YouTube media downloads", "broad scraping"],
       "Metadata-only is safe; media downloads are blocked. Connector is currently not_configured.",
       "Run metadata/transcript dry-runs; keep connector + scheduler approval-gated."),
    _c("seo_marketing", "SEO / Marketing", "growth",
       ["SEO keyword scoring", "opportunity scoring", "internal cards/reports"],
       ["publishing to site", "site/production change", "scheduler activation"],
       ["production deploy of site changes", "external AI on sensitive data"],
       "Scoring is internal; publishing/site changes leave the building.",
       "Keep keyword scoring autonomous; gate any publish/site change."),
    _c("affiliate_marketing", "Affiliate Marketing", "opportunity_lab",
       ["affiliate opportunity scoring", "partner research", "internal cards/reports"],
       ["publishing affiliate content", "outbound partner contact"],
       ["spend/commitment actions", "broad scraping of partner sites"],
       "Scoring is internal; outbound partner contact and publishing are gated.",
       "Keep opportunity scoring autonomous; gate outbound/publish."),
    _c("content_opportunity_lab", "Content Opportunity Lab", "growth",
       ["content opportunity scoring", "experiment cards", "internal reports"],
       ["publishing content", "sending content", "scheduler activation"],
       ["external AI on sensitive/customer data"],
       "Idea/experiment work is internal; publishing/sending are gated.",
       "Keep experiment cards autonomous; gate publish/send."),
    _c("creative_studio", "Creative Studio", "creative_studio",
       ["draft creative generation", "internal review cards", "internal reports"],
       ["publishing creative", "sending creative to clients", "ad creative activation"],
       ["external AI on sensitive/customer data", "spend on paid creative tools"],
       "Drafts are internal until publish/send; then gated.",
       "Keep drafting autonomous; gate publish/send/client delivery."),
    _c("design_library", "Design Library", "design_library",
       ["design library organization", "tagging", "internal cards/reports"],
       ["publishing assets externally", "client delivery"],
       ["external AI on sensitive/customer data"],
       "Organization is internal; external delivery is gated.",
       "Keep organizer autonomous; gate external delivery."),
    _c("goclear_revenue_hub", "GoClear Revenue Hub", "opportunity_lab",
       ["internal revenue metric cards", "internal reports", "scoring"],
       ["lead contact", "payment-link creation", "campaign publishing", "scheduler activation"],
       ["payment/spend actions", "destructive DB writes"],
       "Internal cards are safe; lead contact and payment links leave the building.",
       "Keep revenue cards autonomous; gate lead contact and payment links."),
    _c("goclear_apex_client_intake", "GoClear / Apex Client Intake", "opportunity_lab",
       ["lead scoring", "readiness checklist", "internal cards/reports"],
       ["client notification", "client contact", "client-facing scheduling"],
       ["client data exposure externally", "external AI on customer data"],
       "Scoring/checklists are internal; client contact is gated; client data exposure is blocked.",
       "Keep scoring/checklists autonomous; gate client contact."),
    _c("credit_repair_funding_guidance", "Credit Repair / Funding Guidance", "opportunity_lab",
       ["internal guidance research", "scoring", "internal reports"],
       ["client-facing guidance delivery", "client contact"],
       ["compliance-sensitive claims published without review", "external AI on credit-sensitive data"],
       "High compliance risk. Research internal; client delivery gated; sensitive external AI blocked.",
       "Keep research autonomous; gate all client-facing delivery; compliance review required."),
    _c("opportunity_lab", "Opportunity Lab", "opportunity_lab",
       ["opportunity research", "scoring", "routing", "internal cards/reports"],
       ["outbound contact", "publishing", "scheduler activation"],
       ["broad scraping", "external AI on sensitive data"],
       "Research is internal; outbound/publish gated; broad scraping blocked.",
       "Keep opportunity research autonomous; gate outbound/publish."),
    _c("agent_jobs", "Agent Jobs", "agent_jobs",
       ["job status reporting", "internal cards", "internal reports"],
       ["scheduler activation", "enabling persistent jobs"],
       ["raw auto_executor exposure", "destructive job actions"],
       "Status is internal; persistent jobs gated; raw auto_executor blocked.",
       "Keep status feeder autonomous; gate scheduler/persistent jobs."),
    _c("integrations", "Integrations", "integrations",
       ["integration status reporting", "internal cards/reports"],
       ["connector activation", "OAuth setup", "credential connection"],
       ["credential changes without review", "connecting sensitive systems", "secret printing"],
       "Status is internal; connector activation gated; credential changes blocked.",
       "Keep status feeder autonomous; gate connector activation."),
    _c("events_feed_proof_ledger", "Events Feed / Proof Ledger", "events_feed",
       ["internal proof events", "internal reports", "ledger reads"],
       [],
       ["destructive ledger writes", "tampering with proof history"],
       "Proof logging is internal and append-only; destructive ledger writes are blocked.",
       "Keep proof logging autonomous; never allow destructive ledger writes."),
    _c("approvals", "Approvals", "approvals",
       ["approvals reporting (read-only)", "internal decision briefs"],
       ["Ray decision execution of an approved item"],
       ["auto-approving high-risk items", "bypassing approval gates"],
       "Reporting is internal; the Ray decision itself is gated; auto-approval blocked.",
       "Keep approvals reporting autonomous; require Ray for each decision."),
    _c("ray_review_queue", "Ray Review Queue", "command_center",
       ["queue building from true decisions", "internal reports"],
       ["marking an item approved/executed"],
       ["auto-executing queued items"],
       "Building the queue is internal; execution requires Ray; auto-execute blocked.",
       "Keep queue builder autonomous; never auto-execute queued items."),
    _c("hermes_jarvis", "Hermes / Jarvis", "command_center",
       ["internal recommendations", "prep briefs", "summaries", "internal reports"],
       ["Mac/computer-control bridge activation", "outbound actions on Ray behalf"],
       ["raw command execution from browser", "external AI on sensitive data"],
       "Recommendations are internal; bridge/outbound gated; raw command execution blocked.",
       "Keep Hermes recommendations autonomous; gate any bridge/outbound execution."),
    _c("trading_lab", "Trading Lab", "trading_lab",
       ["paper-only strategy research", "backtest imports (local)", "scoring", "internal reports"],
       [],
       ["live trading", "broker execution", "funded account actions", "raw auto_executor exposure"],
       "Paper-only research is internal. Live trading/broker/funded actions are BLOCKED Level 3.",
       "Keep paper-only research autonomous; live execution stays blocked under its own contract."),
    _c("scheduler_automation", "Scheduler / Automation", "ops_improvements",
       ["scheduler candidate proposals (proposal-only)", "internal reports"],
       ["scheduler activation", "enabling persistent automation"],
       ["cron/launchd/systemd creation without approval"],
       "Proposals are internal; activation is gated; unapproved persistent jobs blocked.",
       "Generate candidates only; never activate a scheduler without Ray approval."),
    _c("production_deployment", "Production / Deployment", "ops_improvements",
       ["deploy readiness reports (internal)"],
       ["production change proposal"],
       ["production deploys", "destructive production actions"],
       "Readiness reporting internal; production deploys blocked unless separately approved.",
       "Keep readiness reporting autonomous; deploys stay blocked/gated."),
    _c("email_sms_dm_social", "Email / SMS / DM / Social", "growth",
       ["draft messages", "internal review cards"],
       ["sending email/SMS/DM", "social posting", "campaign publishing"],
       ["bulk send", "spam automation"],
       "Drafts internal; sending is gated; bulk/spam send blocked.",
       "Keep drafting autonomous; gate every send; block bulk/spam."),
    _c("ads_spend", "Ads / Spend", "growth",
       ["ad opportunity research", "internal cards/reports"],
       ["ad campaign activation proposal"],
       ["ad spend activation", "payment charges"],
       "Research internal; spend blocked. No money leaves without separate approval.",
       "Keep ad research autonomous; spend stays blocked/gated."),
    _c("database_supabase", "Database / Supabase", "ops_improvements",
       ["read-only queries", "internal schema reports"],
       ["schema change proposal"],
       ["destructive DB writes", "RLS weakening", "tenant isolation bypass"],
       "Reads internal; destructive writes / RLS weakening blocked.",
       "Keep reads autonomous; block destructive DB and RLS changes."),
    _c("files_reports_imports", "Files / Reports / Imports", "ops_improvements",
       ["local report generation", "safe local imports", "internal cards"],
       [],
       ["committing .env/secrets", "broad scraping into imports"],
       "Local reports/imports internal; secret commits and broad-scrape imports blocked.",
       "Keep local report generation autonomous; never commit secrets."),
    _c("notebooklm_research_library", "NotebookLM / Research Library", "source_intake",
       ["library organization", "internal summaries", "internal reports"],
       ["connector activation"],
       ["external AI on sensitive/customer data"],
       "Library organization internal; connector gated; sensitive external AI blocked.",
       "Keep library organization autonomous; gate connector activation."),
    _c("grants_funding_opportunities", "Grants / Funding Opportunities", "opportunity_lab",
       ["grant opportunity research", "scoring", "internal cards/reports"],
       ["application submission", "outbound contact"],
       ["spend/commitment actions"],
       "Research internal; submissions/outbound gated.",
       "Keep grant research autonomous; gate submissions/outbound."),
    _c("business_credit_vendor_accounts", "Business Credit / Vendor Accounts", "opportunity_lab",
       ["vendor research", "scoring", "internal cards/reports"],
       ["account application", "outbound vendor contact"],
       ["credential changes", "spend/commitment actions"],
       "Research internal; applications/contact gated; credential changes blocked.",
       "Keep vendor research autonomous; gate applications/contact."),
    _c("client_portal", "Client Portal", "opportunity_lab",
       ["internal portal content drafts", "internal reports"],
       ["client-facing portal publishing", "client notification"],
       ["client data exposure externally", "external AI on customer data"],
       "Drafts internal; client-facing publishing gated; client data exposure blocked.",
       "Keep portal drafts autonomous; gate client-facing publishing."),
    _c("admin_tenants_users", "Admin / Tenants / Users", "ops_improvements",
       ["internal admin reporting (read-only)"],
       ["tenant/user configuration change proposal"],
       ["tenant isolation bypass", "destructive admin actions", "credential changes"],
       "Reporting internal; config changes gated; isolation bypass blocked.",
       "Keep admin reporting autonomous; gate config changes; block isolation bypass."),
    _c("monitoring_health", "Monitoring / Health", "ops_improvements",
       ["health checks", "internal status reports", "proof events"],
       [],
       ["destructive remediation without approval"],
       "Monitoring is internal; destructive auto-remediation blocked.",
       "Keep monitoring autonomous; gate any destructive remediation."),
]

SCHEDULE_READY = {
    "research_source_intake", "youtube_research", "seo_marketing", "affiliate_marketing",
    "content_opportunity_lab", "goclear_revenue_hub", "trading_lab", "monitoring_health",
}
CONNECTOR_REQUIRED = {
    "youtube_research", "integrations", "notebooklm_research_library", "email_sms_dm_social", "goclear_revenue_hub",
}
EXTERNAL_API_REQUIRED = {
    "youtube_research", "integrations", "email_sms_dm_social", "ads_spend", "trading_lab",
}

# ---- High-risk guards (mirrors nexusHighRiskGuards.ts) -----------------------

HIGH_RISK_GUARDS: list[dict[str, Any]] = [
    {"action": "live_trade", "label": "Live trading", "why_blocked": "Real money at risk; irreversible market actions.", "guard_note": "Trading Lab is paper-only; no live execution path."},
    {"action": "broker_order", "label": "Broker order execution", "why_blocked": "Direct broker orders move real funds.", "guard_note": "No broker API wired for execution."},
    {"action": "funded_account_execution", "label": "Funded account actions", "why_blocked": "Funded accounts can lose real capital.", "guard_note": "No funded-account execution path."},
    {"action": "auto_executor_exposure", "label": "Raw auto_executor exposure", "why_blocked": "Raw executor could run arbitrary risky actions.", "guard_note": "auto_executor never exposed to UI/feeders."},
    {"action": "payment_charge", "label": "Payment charge", "why_blocked": "Spends real money / charges customers.", "guard_note": "No payment-charge path enabled."},
    {"action": "payment_refund", "label": "Payment refund", "why_blocked": "Moves real money out.", "guard_note": "No refund path enabled."},
    {"action": "ad_spend_activation", "label": "Ad spend activation", "why_blocked": "Spends real money on ads.", "guard_note": "Ad research only; no spend activation."},
    {"action": "production_deploy", "label": "Production deploy", "why_blocked": "Can break the live system.", "guard_note": "Deploys manual; out of scope for automation."},
    {"action": "rls_weaken", "label": "RLS weakening", "why_blocked": "Could expose tenant/customer data.", "guard_note": "RLS never weakened by automation."},
    {"action": "destructive_db_write", "label": "Destructive DB write", "why_blocked": "Data loss / corruption risk.", "guard_note": "Only append/insert of internal cards + proof events."},
    {"action": "secret_print", "label": "Secret printing", "why_blocked": "Leaks credentials/tokens/cookies.", "guard_note": "Scripts never print secrets."},
    {"action": "env_commit", "label": ".env commit", "why_blocked": "Leaks secrets into git history.", "guard_note": ".env is gitignored; commits assert no .env staged."},
    {"action": "broad_scrape", "label": "Broad scraping", "why_blocked": "Legal/ToS risk and resource abuse.", "guard_note": "Only local samples / metadata placeholders."},
    {"action": "youtube_media_download", "label": "YouTube media download", "why_blocked": "Copyright/ToS risk and heavy I/O.", "guard_note": "Metadata/transcript-only; no media download path."},
    {"action": "external_ai_sensitive_data", "label": "External AI on sensitive data", "why_blocked": "Leaks private/customer/credit data.", "guard_note": "External AI disabled for sensitive data."},
    {"action": "bulk_send", "label": "Bulk send", "why_blocked": "Mass outbound can spam.", "guard_note": "No bulk-send path; sends individually gated."},
    {"action": "spam_automation", "label": "Spam automation", "why_blocked": "Abusive automated outreach.", "guard_note": "No spam automation path."},
    {"action": "client_data_exposure", "label": "Client data exposure", "why_blocked": "Exposes private client data externally.", "guard_note": "Client data stays internal."},
    {"action": "tenant_isolation_bypass", "label": "Tenant isolation bypass", "why_blocked": "Cross-tenant data leakage.", "guard_note": "Tenant isolation enforced; no bypass path."},
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()
