#!/usr/bin/env python3
"""Part 1 — Night-run project review (dry-run, internal)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def build() -> dict:
    return {
        "ok": True, "title": "Nexus Night-Run Project Review", "generated_at": nm.now(), "dry_run": True,
        "what_exists": [
            "Automation Classification Control Center (levels, matrix, guards, action policy, scheduler candidates).",
            "AI Department Access Controls + AI Agent Runtime (runtime-enforced + audited).",
            "Client Vault contract + mock adapter (not_connected_by_design).",
            "Client workflow engine (stages, credit source flow, scoring, business setup, letters/mailing, reminders).",
            "Affiliate recommendation engine + GoClear revenue hub + Hermes client recommendations.",
        ],
        "what_to_reuse": [
            "scripts/research/common.py write_report + report conventions.",
            "rayReviewQueuePolicy + build_ray_review_queue.py for approval gating.",
            "clientWorkflow*, clientWorkflowHermes, sanitizedClientSignals, hermesClientDataRedaction.",
            "nexusActionPolicy + automation levels/guards for classification.",
        ],
        "what_is_missing": [
            "Plain-language Hermes executive brief (added).",
            "GoClear subscription market-research model + report (added).",
            "Online business bank affiliate research (added).",
            "Four revenue streams model + report (added).",
            "Client workflow monetization mapping (added).",
            "Night-run readiness + process inventory + approval/blocked reports (added).",
        ],
        "do_not_duplicate": [
            "No new approval/task/affiliate/proof systems — reuse existing.",
            "No live Client Vault / 2nd Supabase / real client data.",
            "No CRM integration (evaluation deferred).",
        ],
        "ready_for_night_run": [p[0] for p in nm.PROCESS_INVENTORY if p[2] == "ready_to_run"],
        "blocked_by_policy": [p[0] for p in nm.PROCESS_INVENTORY if p[2] == "blocked_by_policy"],
        "needs_ray_approval": [p[0] for p in nm.PROCESS_INVENTORY if p[2] == "approval_required"],
        "needs_config_later": [p[0] for p in nm.PROCESS_INVENTORY if p[2] in ("needs_config", "needs_data")],
        "counts": {
            "ready": sum(1 for p in nm.PROCESS_INVENTORY if p[2] == "ready_to_run"),
            "blocked": sum(1 for p in nm.PROCESS_INVENTORY if p[2] == "blocked_by_policy"),
            "approval_required": sum(1 for p in nm.PROCESS_INVENTORY if p[2] == "approval_required"),
        },
        "summary": "Strong foundation exists; this sprint adds plain-language Hermes, market/bank research, 4 revenue streams, and night-run readiness. Nothing leaves the building.",
        "safety": nm.SAFETY,
    }


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    r = build()
    md = ["## What exists"] + [f"- {x}" for x in r["what_exists"]]
    md += ["", "## Reuse"] + [f"- {x}" for x in r["what_to_reuse"]]
    md += ["", "## Missing (added this sprint)"] + [f"- {x}" for x in r["what_is_missing"]]
    md += ["", "## Ready for night run"] + [f"- {x}" for x in r["ready_for_night_run"]]
    md += ["", "## Blocked by policy"] + [f"- {x}" for x in r["blocked_by_policy"]]
    md += ["", "## Needs Ray approval"] + [f"- {x}" for x in r["needs_ray_approval"]]
    nm.write_report("night_run_project_review_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
