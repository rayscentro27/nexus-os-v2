#!/usr/bin/env python3
"""Build the complete local/demo Nexus client portal backend export set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    BUILDERS, MANUAL, ROOT, RUNTIME, SAFETY, SUPABASE, attach_repo_concepts,
    build_proof, build_subscription, now, repo_records, write_builder_report, write_exports,
)

REQUIRED_FILES = [
    "client_profiles_latest.json", "client_portal_flow_latest.json", "client_tasks_latest.json",
    "client_documents_latest.json", "client_messages_latest.json", "client_hermes_guidance_latest.json",
    "client_questions_latest.json", "client_escalations_latest.json", "approved_client_guidance_latest.json",
    "client_bot_response_templates_latest.json", "hermes_admin_notes_latest.json", "credit_workflow_templates_latest.json",
    "credit_repair_workflow_latest.json", "credit_profile_readiness_rules_latest.json", "credit_profile_readiness_scores_latest.json",
    "business_profile_requirements_latest.json", "business_profile_tasks_latest.json", "business_profile_readiness_scores_latest.json",
    "funding_readiness_rules_latest.json", "funding_readiness_scores_latest.json", "business_opportunities_latest.json",
    "partner_offers_latest.json", "approval_cards_latest.json", "admin_review_queue_latest.json",
    "proof_events_latest.json", "subscription_membership_model_latest.json", "subscription_value_loop_latest.json",
    "repo_concepts_latest.json", "repo_adaptation_tasks_latest.json",
]


def build() -> dict:
    SUPABASE.mkdir(parents=True, exist_ok=True); RUNTIME.mkdir(parents=True, exist_ok=True); MANUAL.mkdir(parents=True, exist_ok=True)
    all_exports = {}
    builder_reports = []
    for name, builder in BUILDERS.items():
        exports = attach_repo_concepts(builder())
        all_exports.update(exports)
        builder_reports.append(write_builder_report(name, exports))
    for exports in (build_subscription(), build_proof()):
        all_exports.update(attach_repo_concepts(exports))
    write_exports(all_exports)

    repo_concepts = repo_records("repo_concepts_latest.json")
    repo_tasks = repo_records("repo_adaptation_tasks_latest.json")
    # The concept extractor owns these two files; preserve and count them in the complete build.
    all_records = [record for records in all_exports.values() for record in records]
    client_visible = [record for record in all_records if record.get("client_visible") is True]
    admin_review = [record for record in all_records if record.get("automation_level") in {"admin_review_required", "approval_required"}]
    blocked = [record for record in all_records + repo_concepts if record.get("automation_level") == "blocked"]
    created = [f"reports/runtime/supabase_ready/{filename}" for filename in REQUIRED_FILES if (SUPABASE / filename).exists()]
    missing = [filename for filename in REQUIRED_FILES if not (SUPABASE / filename).exists()]

    report = {
        "ok": not missing,
        "generated_at": now(),
        **SAFETY,
        "supabase_ready_files_created": created,
        "client_visible_records": [record["id"] for record in client_visible],
        "admin_review_records": [record["id"] for record in admin_review],
        "blocked_records": [record["id"] for record in blocked],
        "repo_concepts_used": len(repo_concepts),
        "repo_adaptation_tasks_available": len(repo_tasks),
        "missing_required_files": missing,
        "builder_reports": builder_reports,
        "next_money_action": "Review the client portal demo and approve the Supabase schema/RLS insertion plan before connecting production client data.",
    }
    (RUNTIME / "client_portal_backend_build_latest.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Client Portal Backend Build", "", f"- ok: {str(report['ok']).lower()}", "- local_only: true",
             "- github_network_access_performed: false", "- external_action_performed: false", "- client_contacted: false",
             "- public_content_published: false", "- real_client_data_used: false", f"- supabase_ready_files_created: {len(created)}",
             f"- client_visible_records: {len(client_visible)}", f"- admin_review_records: {len(admin_review)}",
             f"- blocked_records: {len(blocked)}", f"- repo_concepts_used: {len(repo_concepts)}", "",
             "## Next Money Action", "", report["next_money_action"], "", "## Supabase-ready Files", ""]
    lines += [f"- `{path}`" for path in created]
    (MANUAL / "client_portal_backend_build_latest.md").write_text("\n".join(lines) + "\n")

    plan = {
        "ok": True, "generated_at": now(), "current_entry": "src/main.tsx -> src/app/App.tsx",
        "admin_mount": "/", "client_mount": "/client and /client/*", "react_router_used": False,
        "routing_strategy": "pathname/history API; no new package", "admin_auth_preserved": True,
        "client_preview_direct_access": True, "best_mount_point": "src/app/App.tsx",
        "github_network_access_performed": False,
    }
    inventory = {
        "ok": True, "generated_at": now(), "prototype_files_found": ["package.json", "index.html", "README.md", "src/main.jsx", "src/App.jsx", "src/styles.css"],
        "components_found": ["Sidebar", "Topbar", "ScoreCard", "StatCard", "Factor", "BotBlock", "LineChart", "ActionLine", "ListBox", "ProgressCard", "Summary"],
        "pages_found": ["Dashboard", "Business Opportunities", "Credit Repair", "Credit Profile Readiness", "Business Profile Readiness", "Funding Readiness"],
        "styles_found": ["fixed viewport shell", "sidebar/topbar", "glass cards", "progress rings", "responsive grids"],
        "dependencies": ["react", "react-dom", "lucide-react", "vite"], "dependency_conflicts": [],
        "reused": ["visual shell", "navigation hierarchy", "score cards", "progress rings", "workflow strips", "lists/tables", "dark visual system"],
        "adapted": ["scoped CSS", "pathname routes", "Nexus Guide separation", "safe wording", "Documents/Messages/Settings completed", "shared data model"],
        "github_network_access_performed": False,
    }
    (RUNTIME / "client_portal_prototype_integration_plan_latest.json").write_text(json.dumps(plan, indent=2) + "\n")
    (RUNTIME / "client_portal_prototype_inventory_latest.json").write_text(json.dumps(inventory, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = build()
    print(json.dumps(report, indent=2) if args.json else f"Client portal backend build ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
