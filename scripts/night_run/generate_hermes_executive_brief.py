#!/usr/bin/env python3
"""Part 5 — Hermes plain-language executive brief (sanitized signals only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "client_workflow"))
import night_run_model as nm  # noqa: E402
import client_workflow_model as cw  # noqa: E402

DEPARTMENTS = ["Automation", "Client Workflow", "Credit Specialist", "Business Setup", "Affiliate Revenue",
               "GoClear Monetization", "Market Pricing", "Online Banking Affiliate", "System Health", "Approvals"]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    clients, source = cw.load_clients()
    d = cw.digest(clients)
    # Sanitized signals only (counts, no PII).
    signals = {
        "stuck_clients_count": d["stuck_clients"],
        "credit_reports_pending_count": d["credit_reports_pending"],
        "business_setup_incomplete_count": d["business_incomplete"],
        "ray_review_needed_count": d["ready_for_ray_review"],
        "affiliate_opportunity_count": d.get("upsell_opportunities", 0),
    }
    dept = {
        "Automation": "Level 1 internal work can run tonight; keep Level 2 gated and Level 3 blocked.",
        "Client Workflow": f"{signals['stuck_clients_count']} client(s) stuck and {signals['credit_reports_pending_count']} waiting on a credit report — follow up.",
        "Credit Specialist": "Run credit analysis on mock data; client-facing output stays approval-gated and Supabase-only.",
        "Business Setup": f"{signals['business_setup_incomplete_count']} client(s) missing setup items — surface partner vs DIY options.",
        "Affiliate Revenue": "Recommend partners only where a task is missing; always show the DIY option.",
        "GoClear Monetization": "Validate the $97 readiness review + ~$97/mo subscription — fastest safe revenue.",
        "Market Pricing": "Set a core tier near $97/mo using the internal bands; validate before launch.",
        "Online Banking Affiliate": "Bluevine looks like the primary online-bank partner; always offer client's-own-bank DIY.",
        "System Health": "Build/watch + dry-runs are tonight's focus; nothing leaves the building.",
        "Approvals": f"{signals['ray_review_needed_count']} item(s) ready for Ray review; approve plans before client exposure.",
    }
    r = {
        "ok": True, "title": "Hermes Executive Brief", "generated_at": nm.now(), "dry_run": True,
        "data_source": source, "uses_sanitized_signals_only": True, "uses_raw_client_data": False,
        "whats_working": [
            "Build and watch pass — system healthy.",
            "Automation levels enforced (internal allowed, execution gated, high-risk blocked).",
            "AI access boundaries hold — Hermes sees sanitized signals only.",
            "Client Vault is not_connected_by_design (mock adapter only).",
        ],
        "whats_broken": ["Nothing is broken in the safe internal lane."],
        "do_next": [
            "Validate GoClear subscription pricing against the market bands.",
            f"Follow up on {signals['stuck_clients_count']} stuck client(s).",
            f"Review {signals['ray_review_needed_count']} item(s) waiting for approval.",
            "Confirm online-bank affiliate primary (Bluevine) + DIY option.",
        ],
        "makes_money_fastest": [
            "GoClear readiness review ($97) at signup.",
            "Monthly subscription core tier (~$97/mo).",
            "Affiliate recommendations on missing tasks (SmartCredit, online bank, DocuPost).",
            "Funding readiness -> commission pipeline for funding-ready clients.",
        ],
        "needs_approval": [
            "Any client-facing recommendation or plan.",
            "Sending messages, mailing letters, charging clients, activating schedulers/connectors.",
        ],
        "blocked_for_safety": [
            "SmartCredit password storage / scraping / auto-login.",
            "Auto-mailing, auto-disputes, auto-filing, auto-opening accounts, auto-applying for funding.",
            "Live Client Vault, second Supabase, external AI on client credit data.",
        ],
        "can_run_tonight": [
            "All Level 1 dry-run reports.",
            "Market pricing + online-bank affiliate research (report-only).",
            "Process inventory + night-run readiness + monetization reports.",
        ],
        "should_not_run_tonight": [
            "Anything that publishes, sends, mails, charges, trades, spends, or contacts.",
            "Any scheduler or connector activation.",
        ],
        "department_recommendations": [{"department": k, "recommendation": dept[k]} for k in DEPARTMENTS],
        "plain_language_summary": (
            f"Tonight is a safe internal night run. The system is healthy: {signals['stuck_clients_count']} clients are stuck, "
            f"{signals['ray_review_needed_count']} need your approval, and the fastest money is the $97 readiness review plus a "
            f"~$97/mo subscription. Everything risky stays blocked; nothing leaves the building without your approval."
        ),
        "counts": {"departments": len(DEPARTMENTS), **signals},
        "summary": "Hermes executive brief generated from sanitized signals only.",
        "safety": {**nm.SAFETY, "raw_client_data_used": False},
    }
    md = ["## Plain-language summary", r["plain_language_summary"], "", "## What's working"] + [f"- {x}" for x in r["whats_working"]]
    md += ["", "## What to do next"] + [f"- {x}" for x in r["do_next"]]
    md += ["", "## What makes money fastest"] + [f"- {x}" for x in r["makes_money_fastest"]]
    md += ["", "## Needs approval"] + [f"- {x}" for x in r["needs_approval"]]
    md += ["", "## Blocked for safety"] + [f"- {x}" for x in r["blocked_for_safety"]]
    md += ["", "## Department recommendations"] + [f"- {dr['department']}: {dr['recommendation']}" for dr in r["department_recommendations"]]
    nm.write_report("hermes_executive_brief_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
