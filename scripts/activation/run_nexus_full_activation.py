#!/usr/bin/env python3
"""Activate every safe, internal Nexus subsystem and refresh its report-backed UI data.

The runner is intentionally incapable of publishing, contacting clients, spending money,
submitting disputes, mailing letters, or placing live trades.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from activation_common import (  # noqa: E402
    DASHBOARD_DATA, MANUAL, PUBLIC_STATUS, RUNTIME, SAFETY, SUPABASE_READY,
    approval_card, ensure_dirs, now, rel, write_json, write_report,
)
import run_repo_research  # noqa: E402

SAFE_EXISTING_SCRIPTS = {
    "subscription": ["scripts/night_run/generate_goclear_subscription_market_research.py"],
    "credit": ["scripts/ai_access/generate_credit_specialist_contract_report.py"],
    "youtube": ["scripts/research/youtube_channel_watchlist.py", "scripts/research/run_youtube_metadata_check.py"],
    "research": ["scripts/research/generate_money_opportunity_research.py"],
    "keywords": ["scripts/research/seo_keyword_scout.py"],
    "content": ["scripts/communications/generate_revenue_offer_copy_drafts.py"],
    "social": ["scripts/creative/create_social_post_drafts.py"],
    "partners": ["scripts/partners/generate_partner_offers_report.py"],
    "trading": ["scripts/trading/vibe_trading_adapter.py"],
    "approvals": ["scripts/review/generate_revenue_launch_review_cards.py"],
}

SAFE_SCRIPT_ARGS = {
    "scripts/research/seo_keyword_scout.py": ["--input-file", "reports/seo/keyword_imports/sample_keywords.csv", "--dry-run", "--json"],
}

SKIP_EXISTING_SCRIPTS = {
    "scripts/creative/create_social_post_drafts.py": "May insert production Supabase drafts/events when credentials exist; local approval queue generated instead.",
}

PARTNERS = [
    "SmartCredit", "AnnualCreditReport.com", "Bank of America", "Chase", "Wells Fargo",
    "U.S. Bank", "PNC", "Truist", "local credit unions/community banks", "Bluevine",
    "Mercury", "Relay", "Northwest Registered Agent", "ZenBusiness", "Bizee", "iPostal1",
    "Grasshopper", "QuickBooks", "DocuPost", "USPS Certified Mail",
]


def process_feedback() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inbox = ROOT / "data" / "feedback" / "ray_feedback_inbox.md"
    processed_path = ROOT / "data" / "feedback" / "ray_feedback_processed.jsonl"
    text = inbox.read_text() if inbox.exists() else "# Ray Feedback Inbox\n\n---\n"
    stamp = now()
    processed = []
    for line in text.splitlines():
        match = re.match(r"\s*\*\s*\[new\]\s*(.+)", line, re.IGNORECASE)
        if match:
            processed.append({"processed_at": stamp, "feedback": match.group(1).strip(), "source": rel(inbox)})
    if processed:
        with processed_path.open("a") as handle:
            for item in processed:
                handle.write(json.dumps(item) + "\n")
        text = re.sub(r"(\*\s*)\[new\]", rf"\1[processed {stamp[:10]}]", text, flags=re.IGNORECASE)
        inbox.write_text(text)
    history = []
    if processed_path.exists():
        for line in processed_path.read_text().splitlines():
            try:
                history.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    priorities = [item["feedback"] for item in history[-10:]] or ["Subscription engine remains the top priority."]
    report = {
        "ok": True,
        "status": "feedback_processed" if processed else "no_new_feedback",
        "summary": f"Processed {len(processed)} new feedback item(s); preserved {len(history)} history item(s).",
        "new_feedback": processed,
        "feedback_processed": priorities,
        "current_operating_priorities": priorities[-5:],
        "hermes_pushback": "Defer low-value UI polish until the $97 offer and monthly member value loop have an approved sales path.",
        "next_action": "Add new feedback as a '* [new]' line in data/feedback/ray_feedback_inbox.md.",
        "feedback_file_path": rel(inbox),
        **SAFETY,
    }
    write_report("hermes_feedback", "Hermes Feedback Intake", report,
                 {"Current priorities": report["current_operating_priorities"], "New feedback": processed})
    return processed, report


def subscription_model() -> dict[str, Any]:
    monthly_loop = [
        "Credit/profile check", "Business profile check", "Readiness score update", "Task progress review",
        "Missing document check", "Next best action", "Partner/tool recommendation if useful",
        "Funding-readiness update", "Monthly education/reminder", "Referral/upgrade trigger",
    ]
    tiers = [
        {"name": "Funding / Credit Readiness Review", "price": 97, "billing": "one_time", "role": "entry offer"},
        {"name": "Assisted Readiness Plan", "price": 297, "billing": "one_time_or_upgrade", "role": "assisted upgrade"},
        {"name": "Higher-Touch Package", "price": 497, "billing": "one_time_or_upgrade", "role": "concierge upgrade"},
        {"name": "Readiness Membership", "price": "pending Ray approval", "billing": "monthly", "role": "recurring core"},
    ]
    return {
        "ok": True, "status": "active_internal_model", "priority": 1,
        "summary": "GoClear/Apex monthly subscription is the primary Nexus money engine; the $97 review is the entry conversion event.",
        "target_customer": "People improving personal credit and small-business owners building a fundable business profile.",
        "offer_promise": "A clear, educational readiness plan with monthly progress tracking; no score, deletion, or funding guarantees.",
        "subscription_tiers": tiers, "monthly_value_loop": monthly_loop,
        "client_stages": ["lead", "readiness review", "onboarding", "credit improvement", "business profile", "document readiness", "funding ready", "retained/referral"],
        "onboarding_workflow": ["consent and scope", "safe intake", "baseline checklists", "first readiness score", "30-day plan"],
        "credit_workflow": ["profile checklist", "factor review", "task plan", "monthly progress"],
        "business_profile_workflow": ["entity/EIN", "contact footprint", "banking", "proof documents", "vendor readiness"],
        "funding_readiness_workflow": ["readiness dimensions", "blockers", "documents", "lender path education", "next best action"],
        "retention_triggers": ["new score factor", "completed task", "monthly readiness movement", "new document need", "education milestone"],
        "referral_triggers": ["readiness score improvement", "funding-ready milestone", "30/60/90-day progress recap"],
        "churn_risk_triggers": ["no task progress in 14 days", "missing report/check-in", "unclear next action", "no monthly value delivered"],
        "upgrade_triggers": ["needs assisted execution", "complex derogatory review", "business profile gaps", "time-sensitive funding plan"],
        "ray_review_cards": ["approve offer language", "approve membership tiers", "approve onboarding promise"],
        "next_money_action": "Approve the $97 Readiness Review offer and first landing-page copy so Ray can begin manual sales conversations.",
        **SAFETY,
    }


def credit_model(repo_targets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ok": True, "status": "active_safe_internal", "summary": "Credit improvement workflow is active for education, checklists, analysis notes, and draft queues only.",
        "stages": ["intake", "credit report path", "personal credit profile checklist", "score factor review", "utilization tasks", "payment history tasks", "derogatory item review", "dispute candidate review", "dispute strategy notes", "letter draft queue", "goodwill letter drafts", "debt validation draft queue", "education tasks", "client next steps", "Ray approval queue", "monthly member progress"],
        "repo_concepts": [t["name"] for t in repo_targets if "credit" in (t["name"] + t["purpose"]).lower()],
        "safe_outputs": ["educational checklist", "score-factor explanation", "draft letter for Ray review", "monthly progress summary"],
        "blocked": ["automatic dispute submission", "automatic bureau/creditor/collector contact", "SmartCredit password storage or scraping", "guaranteed removals", "external AI on raw private reports"],
        "recommended_next_action": "Package the baseline credit checklist into the $97 Readiness Review deliverable.",
        **SAFETY,
    }


def business_model() -> dict[str, Any]:
    fields = ["LLC/entity", "EIN", "Secretary of State status", "NAICS", "business address", "business phone", "business email/domain", "website", "DUNS/business bureau profile", "business bank account", "vendor accounts", "business credit card readiness", "proof docs", "revenue docs", "bank statements", "funding blockers", "next best action"]
    return {
        "ok": True, "status": "active_internal_checklist", "summary": "Business Profile Builder now tracks the complete fundability footprint without filing or applying on the client's behalf.",
        "tracked_fields": fields, "concept_sources": ["moov-io/awesome-fintech", "credit-management topic", "chandachewe10/loan-management-system"],
        "blocked": ["filing LLC/EIN/state documents", "opening accounts", "funding applications"],
        "recommended_next_action": "Add the business-profile gap score to the $97 review worksheet.", **SAFETY,
    }


def funding_model() -> dict[str, Any]:
    dimensions = ["personal credit readiness", "business profile readiness", "banking readiness", "documentation readiness", "revenue/proof readiness", "lender path readiness", "risk flags", "next best action"]
    return {
        "ok": True, "status": "active_internal_scoring_model", "summary": "Funding readiness scoring is active as educational guidance, not underwriting or a funding guarantee.",
        "score_dimensions": [{"name": x, "weight": 15 if i < 6 else 5} for i, x in enumerate(dimensions)],
        "concept_sources": ["loan-management-system", "loan-approval-system topic", "moov-io/awesome-fintech"],
        "blocked": ["lender application submission", "guaranteed approval claims", "client-facing recommendation without Ray review"],
        "recommended_next_action": "Use the readiness score as the before/after value metric for monthly membership retention.", **SAFETY,
    }


def youtube_model() -> dict[str, Any]:
    config_path = ROOT / "configs" / "youtube_research_channels.json"
    if not config_path.exists():
        config_path = ROOT / "config" / "youtube_sources_allowlist.json"
    config = json.loads(config_path.read_text())
    slots = config.get("channel_slots") or config.get("sources") or []
    queue = [{"id": f"youtube-{i+1}", "category": item.get("category", item.get("name", "research")), "status": item.get("status", "metadata_check_queued"), "transcript_needed": True, "download_video": False, "next_action": "Select an allowed public channel and capture metadata only."} for i, item in enumerate(slots)]
    return {
        "ok": True, "status": "active_metadata_queue", "summary": f"Prepared {len(queue)} source-category queues without downloading media or bypassing platform controls.",
        "queue": queue, "rules": ["metadata and allowed transcript review only", "no video/audio download", "no aggressive scraping", "no reused-content publishing"],
        "recommended_next_action": "Select one reputable credit education channel and one business funding channel for metadata review.", **SAFETY,
    }


def opportunities() -> list[dict[str, Any]]:
    seeds = [
        ("credit-profile-checklist", "Personal Credit Profile Checklist", "credit profile checklist", "credit improvement members", "Unclear credit factors", "$97 review to monthly membership", 95, "lead magnet + review worksheet"),
        ("business-fundability-checklist", "Business Fundability Profile Checklist", "business funding readiness checklist", "small-business owners", "Business looks unprepared to lenders", "$97 review and $297 assisted plan", 94, "landing page + checklist"),
        ("monthly-readiness-score", "Monthly Funding Readiness Score", "funding readiness score", "current members", "Progress is hard to see", "membership retention and referrals", 93, "member report template"),
        ("utilization-education", "Credit Utilization Action Plan", "lower credit utilization", "credit-improvement leads", "High balances suppress readiness", "$97 review conversion", 89, "video + email"),
        ("llc-bank-readiness", "LLC to Business Bank Readiness", "business bank account requirements", "new LLC owners", "Missing profile and documents", "$297 assisted upgrade", 88, "SEO article + checklist"),
        ("funding-warning", "Seven Funding Readiness Red Flags", "business funding red flags", "funding seekers", "Applying too early creates risk", "$97 review", 91, "short video series"),
        ("local-credit-help", "Phoenix Credit and Funding Readiness", "Phoenix business credit help", "Phoenix small businesses", "Generic advice lacks local relevance", "local $97 review leads", 86, "local SEO page"),
        ("partner-toolkit", "Best Tools by Readiness Stage", "credit and business funding tools", "members", "Tool choices are confusing", "retention first; disclosed affiliate second", 82, "member resource guide"),
    ]
    return [{
        "id": sid, "title": title, "keyword_topic": keyword, "audience": audience, "pain_point": pain,
        "money_path": money, "subscription_fit": "high", "offer_fit": "$97 review + monthly membership",
        "score": score, "recommended_asset": asset, "approval_required": True,
        "next_action": "Draft internally, then route exact public/client-facing copy to Ray Review."
    } for sid, title, keyword, audience, pain, money, score, asset in seeds]


def content_assets() -> dict[str, list[dict[str, Any]]]:
    themes = [
        ("$97 Funding Readiness Review", "Know what is blocking your credit and business funding profile before you apply."),
        ("Monthly Readiness Membership", "Get a monthly credit, business-profile, document, and funding-readiness action plan."),
        ("Credit Improvement Education", "Understand utilization, payment history, and derogatory-item review without guaranteed outcomes."),
        ("Business Profile Checklist", "Build the entity, contact, banking, and proof footprint lenders expect to evaluate."),
        ("Funding Readiness Warning", "Do not apply blindly; identify readiness gaps first."),
        ("Business Banking Path", "Match your business stage to the right account and documentation path."),
        ("Member Referral", "Share your progress framework with another business owner who needs clarity."),
        ("Partner Tools", "Use the best-fit free or paid tool; affiliate payout never overrides client outcome."),
    ]
    def asset(kind: str, index: int, theme: str, hook: str) -> dict[str, Any]:
        return {"id": f"{kind}-{index+1}", "type": kind, "title": theme, "headline": hook,
                "cta": "Request the $97 Funding / Credit Readiness Review",
                "draft_only": True, "approval_required": True, "public_content_published": False}
    return {
        "content_drafts": [asset("content", i, *theme) for i, theme in enumerate(themes)],
        "landing_page_drafts": [asset("landing_page", i, *theme) for i, theme in enumerate(themes[:2])],
        "social_drafts": [asset("social_post", i, themes[i % len(themes)][0], f"{themes[i % len(themes)][1]} Step {i+1}: start with the next best action, not another blind application.") for i in range(10)],
        "video_script_drafts": [asset("video_script", i, *theme) for i, theme in enumerate(themes[:6])],
        "email_drafts": [asset("email", i, *theme) for i, theme in enumerate(themes[:5])],
    }


def partner_model() -> dict[str, Any]:
    items = []
    for name in PARTNERS:
        items.append({"name": name, "status": "not_connected", "recommendation_rule": "best client funding outcome first; disclosed affiliate payout second; free/DIY option visible", "approval_required": True})
    return {"ok": True, "status": "active_internal_registry", "summary": f"Tracked {len(items)} partner/tool options with outcome-first and disclosure rules.", "offers": items, "first_recommended_path": "AnnualCreditReport.com free report path before paid monitoring when appropriate.", "recommended_next_action": "Ray should add verified partner URLs and disclosures only after reviewing client fit.", **SAFETY}


def approval_cards(repo_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = [
        ("approve-first-landing-page", "Approve first $97 landing page", "landing_page", "Approve exact draft for manual publication.", "Enable the first lead-conversion asset.", "medium"),
        ("approve-social-10", "Approve first 10 social posts", "social", "Approve/revise the exact account and post queue; publishing remains manual.", "Create a safe lead-generation content queue.", "medium"),
        ("approve-email-sequence", "Approve first email sequence", "email", "Approve copy, recipients, and sending tool separately.", "Create a follow-up path for interested leads.", "high"),
        ("approve-subscription-offer", "Approve subscription offer and monthly value loop", "subscription", "Approve tier/pricing language and scope.", "Make recurring revenue sellable.", "medium"),
        ("approve-partners", "Approve partner recommendations", "partners", "Approve exact tools, URLs, disclosures, and free alternatives.", "Support outcomes and later affiliate revenue.", "medium"),
        ("approve-credit-letters", "Review credit letter drafts", "credit", "Review client-specific facts and approve manual use; do not auto-send.", "Support compliant assisted readiness work.", "high"),
        ("approve-funding-guidance", "Review funding recommendations", "funding", "Approve any client-facing lender/path recommendation.", "Prevent premature or unsuitable applications.", "high"),
        ("approve-scheduler", "Approve local safe-loop scheduler installation", "scheduler", "Review launchd draft and explicitly approve loading it.", "Keep internal reports refreshed.", "medium"),
        ("approve-supabase-plan", "Approve Supabase insertion plan", "data", "Review schema, privacy, and RLS before production inserts.", "Connect generated reports safely.", "high"),
        ("approve-oanda-demo", "Approve Oanda demo action design", "trading", "Confirm practice environment, credentials, instrument, bounds, and safe executor before any demo order.", "Permit a controlled demo proof only.", "high"),
    ]
    return [approval_card(*item) for item in base] + repo_cards


def run_existing(active: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ran, skipped = [], []
    for system, scripts in SAFE_EXISTING_SCRIPTS.items():
        for script in scripts:
            path = ROOT / script
            if system not in active:
                skipped.append({"command": script, "reason": "subsystem not selected"})
                continue
            if script in SKIP_EXISTING_SCRIPTS:
                skipped.append({"command": f"python3 {script}", "reason": SKIP_EXISTING_SCRIPTS[script]})
                continue
            if not path.exists():
                skipped.append({"command": script, "reason": "script not found"})
                continue
            script_args = SAFE_SCRIPT_ARGS.get(script, ["--dry-run", "--json"])
            cmd = [sys.executable, str(path), *script_args]
            try:
                proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
                ran.append({"command": f"python3 {script} {' '.join(script_args)}", "exit_code": proc.returncode,
                            "ok": proc.returncode == 0, "stderr": proc.stderr[-400:]})
            except Exception as exc:  # noqa: BLE001
                ran.append({"command": f"python3 {script} {' '.join(script_args)}", "exit_code": -1, "ok": False, "error": str(exc)})
    return ran, skipped


def run_local_backtests() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results, commands = [], []
    engines = [ROOT.parent / "nexus-ai" / "trading-engine", ROOT.parent / "nexuslive" / "trading-engine"]
    for engine in engines:
        backtester = engine / "backtest" / "backtester.py"
        signals = engine / "backtest" / "sample_signals.json"
        if not (backtester.exists() and signals.exists()):
            continue
        output = RUNTIME / "backtests" / f"{engine.parent.name}_{engine.name}_latest.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(backtester), "--signals", str(signals), "--balance", "10000", "--output", str(output)]
        try:
            proc = subprocess.run(cmd, cwd=engine, capture_output=True, text=True, timeout=120)
            data = json.loads(output.read_text()) if proc.returncode == 0 and output.exists() else {}
            summary = data.get("summary", {})
            results.append({"engine": str(engine), "mode": "bounded_backtest", "paper_only": True,
                            "new_trade_placed": False, **summary})
            commands.append({"command": f"python3 {rel(backtester)} --signals {rel(signals)} --balance 10000 --output {rel(output)}",
                             "exit_code": proc.returncode, "ok": proc.returncode == 0, "stderr": proc.stderr[-400:]})
        except Exception as exc:  # noqa: BLE001
            commands.append({"command": f"python3 {backtester} --signals {signals}", "exit_code": -1, "ok": False, "error": str(exc)})
    return results, commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--continuous-cycle", action="store_true")
    for name in ("subscription", "credit", "business-profile", "funding-readiness", "youtube", "repo-research", "research", "keywords", "content", "social", "partners", "trading-demo", "approvals", "dashboard-data", "feedback", "safety"):
        parser.add_argument(f"--run-{name}", action="store_true")
    parser.add_argument("--hermes-brief", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ensure_dirs()
    all_systems = {"subscription", "credit", "business-profile", "funding-readiness", "youtube", "repo-research", "research", "keywords", "content", "social", "partners", "trading-demo", "approvals", "dashboard-data", "feedback", "safety"}
    selected = {name.replace("_", "-") for name, value in vars(args).items() if name.startswith("run_") and name != "run_all" and value}
    active = all_systems if args.run_all or not selected else selected
    started_at = now()

    processed_feedback, feedback = process_feedback()
    repo = run_repo_research.build_report()
    write_report("repo_research_activation", "GitHub Repo Research Activation", repo,
                 {"Research targets": repo["targets"], "Adaptation tasks": repo["adaptation_tasks"]})
    write_json(SUPABASE_READY / "repo_research_sources_latest.json", repo["targets"])
    write_json(SUPABASE_READY / "repo_adaptation_tasks_latest.json", repo["adaptation_tasks"])

    sub = subscription_model()
    credit = credit_model(repo["targets"])
    business = business_model()
    funding = funding_model()
    youtube = youtube_model()
    opps = opportunities()
    assets = content_assets()
    partners = partner_model()
    cards = approval_cards(repo["approval_cards"])

    reports_created: list[str] = []
    supabase_files: list[str] = [
        "reports/runtime/supabase_ready/repo_research_sources_latest.json",
        "reports/runtime/supabase_ready/repo_adaptation_tasks_latest.json",
    ]
    def report(stem: str, title: str, data: dict[str, Any], sections: dict[str, Any] | None = None) -> None:
        runtime_path, manual_path = write_report(stem, title, data, sections)
        reports_created.extend([runtime_path, manual_path])
    def export(name: str, data: Any) -> None:
        supabase_files.append(write_json(SUPABASE_READY / name, data))

    inventory = {
        "ok": True, "status": "inventory_complete", "summary": "Nexus has mature local report generators and safety policies; UI and continuous activation were partial before this pass.",
        "systems_found": sorted(all_systems | {"Supabase", "Netlify", "Hermes", "paper trading", "Ray Review"}),
        "systems_already_active": ["local report generation", "research scoring", "draft generation", "approval policies", "Supabase frontend client"],
        "systems_mock_only": ["previous redesigned admin dashboard values", "browser file write-back", "payment activation"],
        "systems_safe_to_run_continuously": sorted(all_systems - {"trading-demo"}) + ["paper backtests"],
        "systems_requiring_credentials": ["Supabase production inserts", "social publishers", "email/SMS", "Oanda demo"],
        "systems_requiring_ray_approval": ["publishing", "sending", "client-facing guidance", "scheduler install", "demo order", "production inserts"],
        "systems_blocked": ["real-money trading", "paid actions", "automatic disputes/contact", "SmartCredit login/scraping", "private client vault", "destructive database actions"],
        "ui_files_classes_found": ["src/admin/NexusAdminUI.jsx", "src/admin/nexusAdminUI.css", ".os-root", ".app-shell", ".content", ".page-content", ".command-layout", ".workspace", ".side-stack"],
        "activation_plan": ["lock desktop shell", "generate report-backed dashboard snapshot", "activate safe domain models", "process feedback", "run bounded cycle", "verify safety/build/preview", "commit and push"], **SAFETY,
    }
    report("continuous_activation_inventory", "Continuous Activation Inventory", inventory, {"Activation plan": inventory["activation_plan"], "Blocked": inventory["systems_blocked"]})
    report("subscription_engine_activation", "Subscription Engine Activation", sub, {"Subscription tiers": sub["subscription_tiers"], "Monthly value loop": sub["monthly_value_loop"]})
    export("subscription_membership_model_latest.json", sub)
    report("credit_repair_workflow_activation", "Credit Repair / Improvement Workflow Activation", credit, {"Workflow stages": credit["stages"], "Blocked": credit["blocked"]})
    export("credit_workflow_latest.json", credit)
    report("business_profile_builder_activation", "Business Profile Builder Activation", business, {"Tracked fields": business["tracked_fields"], "Blocked": business["blocked"]})
    export("business_profile_tasks_latest.json", business)
    report("funding_readiness_activation", "Funding Readiness Activation", funding, {"Score dimensions": funding["score_dimensions"], "Blocked": funding["blocked"]})
    export("funding_readiness_latest.json", funding)
    report("youtube_source_activation", "YouTube / Source Activation", youtube, {"Research queue": youtube["queue"], "Rules": youtube["rules"]})
    export("research_sources_latest.json", youtube["queue"])
    export("youtube_research_queue_latest.json", youtube["queue"])
    money = {"ok": True, "status": "active_internal_scoring", "summary": f"Generated {len(opps)} scored money/keyword opportunities with subscription-first routing.", "opportunities": opps, "keyword_opportunities": opps, "recommended_next_action": opps[0]["next_action"], **SAFETY}
    report("research_money_engine", "Research + Keyword Money Engine", money, {"Opportunities": opps})
    export("money_opportunities_latest.json", opps)
    export("keyword_opportunities_latest.json", opps)
    content = {"ok": True, "status": "draft_only_active", "summary": f"Generated {sum(map(len, assets.values()))} approval-gated content assets.", "assets": assets, "recommended_next_action": "Review the first $97 landing page and 10-post social set in Ray Review.", **SAFETY}
    report("content_activation", "Content Creation Activation", content, {"Draft sets": {k: len(v) for k, v in assets.items()}})
    for name, values in assets.items():
        export(f"{name}_latest.json", values)
    social = {"ok": True, "status": "approval_queue_only", "summary": "Social pipeline prepared 10 drafts; no publisher was invoked.", "connected_platforms": [], "configured_accounts": [], "available_scripts": ["scripts/creative/create_social_post_drafts.py", "scripts/social/facebook_publisher.py"], "missing_tokens": ["platform access token", "confirmed owned account id"], "approval_gates": ["exact copy", "exact account", "scheduled time"], "first_recommended_platform": "Ray's strongest owned business account after explicit approval", "first_10_draft_posts": assets["social_drafts"], **SAFETY}
    report("social_media_activation", "Social Media Activation", social, {"First 10 drafts": social["first_10_draft_posts"]})
    export("social_publish_queue_latest.json", social["first_10_draft_posts"])
    demo_env = os.getenv("OANDA_ENVIRONMENT", "").lower()
    demo_creds = bool(os.getenv("OANDA_API_TOKEN") and os.getenv("OANDA_ACCOUNT_ID"))
    safe_demo_path = False
    demo_allowed = demo_env in {"practice", "demo", "sandbox"} and demo_creds and safe_demo_path
    backtest_results, backtest_commands = run_local_backtests()
    trading = {"ok": all(c["ok"] for c in backtest_commands), "status": "paper_backtest_only", "summary": f"Ran {len(backtest_results)} bounded local backtests; no confirmed bounded Oanda demo executor exists in this repo.", "strategies": [{"id": "local-risk-managed-sample", "mode": "paper", "engines": len(backtest_results)}, {"id": "half-trend-forex", "mode": "paper_research", "status": "inventory"}], "backtest_results": backtest_results, "oanda_demo_environment_confirmed": demo_env in {"practice", "demo", "sandbox"}, "oanda_demo_credentials_present": demo_creds, "safe_demo_order_path_present": safe_demo_path, "demo_trade_allowed": demo_allowed, "demo_trade_placed": False, "paper_trade_placed": False, "recommended_next_action": "Keep paper/backtest mode; separately design and approve a bounded practice-only Oanda executor before any demo order.", **SAFETY}
    report("trading_activation", "Trading Engine Activation", trading, {"Strategies": trading["strategies"], "Backtest results": trading["backtest_results"]})
    export("trading_strategies_latest.json", trading["strategies"])
    export("backtest_results_latest.json", trading["backtest_results"])
    report("partner_offers_activation", "Partner Offers Activation", partners, {"Partner registry": partners["offers"]})
    export("partner_offers_latest.json", partners["offers"])
    review = {"ok": True, "status": "queue_ready", "summary": f"Generated {len(cards)} exact decision cards; no external action was taken.", "approval_cards": cards, "recommended_next_action": "Approve or revise the subscription offer and first landing page before lower-value work.", **SAFETY}
    report("ray_review_queue", "Ray Review Queue", review, {"Approval cards": cards})
    export("approval_cards_latest.json", cards)

    scheduler = {"ok": True, "status": "draft_not_installed", "scheduler_installed": False, "scheduler_activated": False, "what_runs": sorted(all_systems - {"trading-demo"}) + ["paper backtests"], "frequency": "30 minutes", "proof_paths": ["reports/runtime/continuous_loop_status_latest.json", "reports/runtime/continuous_loop_history.jsonl"], "feedback_file_path": "data/feedback/ray_feedback_inbox.md", "start_command": "launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nexus.continuous-loop.plist", "stop_command": "launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.nexus.continuous-loop.plist", "rollback_command": "rm ~/Library/LaunchAgents/com.nexus.continuous-loop.plist", "recommended_next_action": "Review the plist; do not install until Ray explicitly approves local daemon activation.", **SAFETY}
    report("scheduler_activation", "Continuous Scheduler Activation", scheduler, {"Scheduled internal systems": scheduler["what_runs"]})

    commands_run, commands_skipped = run_existing({x.replace("-profile", "").replace("-readiness", "").replace("-demo", "") for x in active})
    commands_run = backtest_commands + commands_run
    failed_commands = [c for c in commands_run if not c["ok"]]
    hermes = {
        "ok": not failed_commands, "status": "current_report_backed_brief", "generated_at": now(),
        "last_cycle_summary": f"Refreshed subscription, credit, business profile, funding, research, drafts, approvals, and safety data. {len(failed_commands)} optional existing script(s) failed without stopping the cycle.",
        "recommendation": sub["next_money_action"],
        "single_next_money_action": sub["next_money_action"],
        "what_makes_money_fastest": "Sell the $97 Readiness Review manually after approving its exact promise and landing-page copy.",
        "subscription_blockers": ["offer/pricing language needs Ray approval", "landing page remains draft-only", "payment collection is intentionally not activated", "monthly membership price needs final approval"],
        "content_ready": {k: len(v) for k, v in assets.items()}, "approvals_ready": len(cards),
        "trading_status": trading["status"], "repo_next": repo["next_action"],
        "feedback_processed": feedback["feedback_processed"],
        "changed_from_feedback": ["subscription ranked first", "credit/business workflows modeled as monetizable", "continuous loop created", "Hermes pushback enabled", "viewport layout lock added"],
        "stay_manual": ["publishing/sending", "client-facing credit/funding guidance", "disputes and letters", "payments", "partner applications", "demo orders"],
        "not_built_enough": ["browser-to-file feedback write-back", "production payment path", "private client vault", "bounded Oanda demo executor"],
        "pushback": feedback["hermes_pushback"], **SAFETY,
    }
    report("hermes_current_brief", "Hermes Current Brief", hermes, {"Subscription blockers": hermes["subscription_blockers"], "What stays manual": hermes["stay_manual"]})

    dashboard = {
        "generatedAt": hermes["generated_at"], "mode": "continuous_full_activation_safe_internal",
        "loopStatus": "cycle_complete", "subscriptionStatus": sub["status"], "creditStatus": credit["status"],
        "businessProfileStatus": business["status"], "fundingStatus": funding["status"],
        "systemsActivated": sorted(active), "opportunityCount": len(opps),
        "draftCount": sum(map(len, assets.values())), "approvalCount": len(cards),
        "blockerCount": len(hermes["subscription_blockers"]), "repoTargetCount": len(repo["targets"]),
        "feedbackProcessed": feedback["feedback_processed"], "nextMoneyAction": sub["next_money_action"],
        "hermesRecommendation": hermes["recommendation"], "hermesPushback": hermes["pushback"],
        "lastCycleSummary": hermes["last_cycle_summary"], "tradingStatus": trading["status"],
        "safety": SAFETY, "reportPath": "reports/manual_publish/hermes_current_brief_latest.md"
    }
    dashboard_files = [write_json(DASHBOARD_DATA, dashboard), write_json(PUBLIC_STATUS, dashboard)]
    reports_created.extend(["reports/runtime/repo_research_activation_latest.json", "reports/manual_publish/repo_research_activation_latest.md",
                            "reports/runtime/hermes_feedback_latest.json", "reports/manual_publish/hermes_feedback_latest.md"])
    report("nexus_daily_internal", "Nexus Daily Internal Activation", {"ok": not failed_commands, "status": "safe_internal_cycle_complete", "summary": hermes["last_cycle_summary"], "commands_run": commands_run, "commands_skipped": commands_skipped, **SAFETY}, {"Commands run": commands_run, "Commands skipped": commands_skipped})

    blocked = [
        "public publishing and outbound messaging", "payment collection activation", "production Supabase inserts pending schema/privacy review",
        "automatic disputes and bureau/creditor/collector contact", "real-money and funded trading", "Oanda demo order without a confirmed bounded practice executor",
        "SmartCredit password storage/scraping", "live private client vault", "launchd installation without Ray approval",
    ]
    summary = {
        "ok": not failed_commands,
        "mode": "continuous_full_activation_safe_internal",
        "started_at": started_at, "completed_at": now(),
        **SAFETY,
        "demo_trade_allowed": demo_allowed,
        "systems_activated": sorted(active),
        "systems_skipped": sorted(all_systems - active),
        "commands_run": commands_run,
        "commands_skipped": commands_skipped,
        "reports_created": sorted(set(reports_created)),
        "supabase_ready_files": sorted(set(supabase_files)),
        "dashboard_data_files": dashboard_files,
        "approval_cards_created": [c["id"] for c in cards],
        "feedback_processed": processed_feedback,
        "blocked_items": blocked,
        "hermes_brief_path": "reports/manual_publish/hermes_current_brief_latest.md",
        "next_money_action": sub["next_money_action"],
        "counts": {"opportunities": len(opps), "drafts": sum(map(len, assets.values())), "approval_cards": len(cards), "repo_targets": len(repo["targets"]), "command_failures": len(failed_commands)},
    }
    full_runtime, full_manual = write_report("nexus_full_activation", "Nexus Full Activation", summary,
                                             {"Systems activated": summary["systems_activated"], "Blocked items": blocked, "Commands run": commands_run})
    summary["reports_created"] = sorted(set(summary["reports_created"] + [full_runtime, full_manual]))
    write_json(RUNTIME / "nexus_full_activation_latest.json", {"title": "Nexus Full Activation", "generated_at": now(), **summary})
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Nexus safe activation complete: {len(active)} systems, {len(opps)} opportunities, {len(cards)} approvals.")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
