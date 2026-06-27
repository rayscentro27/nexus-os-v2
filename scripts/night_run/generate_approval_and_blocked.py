#!/usr/bin/env python3
"""Part 16 — Approval-needed + blocked/high-risk reports (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402

APPROVAL_NEEDED = [
    "Expose any client-facing recommendation or action plan.",
    "Send email/SMS/DM or contact a client/lead.",
    "Publish public content.",
    "Activate a recurring scheduler.",
    "Activate a sensitive connector.",
    "Mail letters (DocuPost or USPS).",
    "Submit disputes.",
    "Apply for funding / route a funding path.",
    "Spend money or charge a client.",
    "Production deployment.",
    "Set/launch GoClear subscription billing.",
]

BLOCKED_HIGH_RISK = [
    "Store SmartCredit passwords.",
    "Scrape SmartCredit.",
    "Auto-submit disputes.",
    "Auto-mail letters.",
    "Auto-contact bureaus/creditors/collectors/lenders.",
    "Auto-file LLC/EIN/state documents.",
    "Auto-open accounts.",
    "Auto-apply for funding.",
    "Use external AI on private/client credit data.",
    "Broad scraping.",
    "Credential changes / destructive database actions.",
    "Live trading / broker execution.",
    "Connect live Client Vault / add production credentials / add real client data.",
    "Connect a second live Supabase project.",
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    approval = {"ok": True, "title": "Nexus Approval Needed", "generated_at": nm.now(), "dry_run": True,
                "items": APPROVAL_NEEDED, "counts": {"items": len(APPROVAL_NEEDED)},
                "summary": f"{len(APPROVAL_NEEDED)} action types require Ray approval before execution. None executed.",
                "safety": nm.SAFETY}
    nm.write_report("nexus_approval_needed_latest", approval, ["## Requires Ray approval"] + [f"- {x}" for x in APPROVAL_NEEDED])

    blocked = {"ok": True, "title": "Nexus Blocked / High-Risk", "generated_at": nm.now(), "dry_run": True,
               "items": BLOCKED_HIGH_RISK, "default_state": "blocked", "counts": {"items": len(BLOCKED_HIGH_RISK)},
               "summary": f"{len(BLOCKED_HIGH_RISK)} high-risk actions remain blocked by default (Level 3). None ran.",
               "safety": {**nm.SAFETY, "level_3_blocked": True}}
    nm.write_report("nexus_blocked_high_risk_latest", blocked, ["## Blocked / high-risk (Level 3)"] + [f"- {x}" for x in BLOCKED_HIGH_RISK])

    out = {"ok": True, "approval_items": len(APPROVAL_NEEDED), "blocked_items": len(BLOCKED_HIGH_RISK)}
    print(json.dumps(out, indent=2) if a.json else f"approval={out['approval_items']} blocked={out['blocked_items']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
