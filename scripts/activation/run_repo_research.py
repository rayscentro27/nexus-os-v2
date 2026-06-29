#!/usr/bin/env python3
"""Build a safe concept-research queue from approved GitHub targets.

This script never clones repositories, imports code, or executes repository content.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from activation_common import SAFETY, SUPABASE_READY, approval_card, ensure_dirs, now, write_json, write_report  # noqa: E402


def classify(target: dict) -> tuple[str, int, list[str], list[str]]:
    blob = f"{target['name']} {target['purpose']}".lower()
    score = 78
    helps = ["monthly subscription value", "dashboard workflow concepts"]
    risks = ["license review required before code import", "security review required before running code"]
    classification = "use as concept"
    if "credit repair" in blob:
        score += 10
        helps.extend(["credit repair workflow", "letter/checklist design"])
        risks.extend(["automatic disputes blocked", "bureau/creditor contact blocked"])
    if "credit scoring" in blob:
        score += 7
        helps.extend(["credit score-factor explanations", "funding readiness scoring"])
        risks.append("models must not be presented as lender decisions")
    if "fintech" in blob:
        score += 5
        helps.extend(["business profile workflow", "funding infrastructure patterns", "partner offers"])
    if "loan" in blob:
        score += 4
        helps.extend(["funding readiness workflow", "eligibility and document tracking"])
    if target["name"] == "Wadprog/RepairCredit-":
        classification = "blocked/risky for automation; use as concept only"
    elif target["type"] == "github_repository":
        classification = "possible code import after license/security review"
    return classification, min(score, 96), sorted(set(helps)), sorted(set(risks))


def build_report() -> dict:
    config = json.loads((ROOT / "configs" / "repo_research_targets.json").read_text())
    sources, tasks, approvals = [], [], []
    for target in config["targets"]:
        classification, score, helps, risks = classify(target)
        source = {
            **target,
            "source_type": "github_research_target",
            "status": "concept_review_queued",
            "nexus_fit_score": score,
            "classification": classification,
            "helps": helps,
            "compliance_security_risks": risks,
            "cloned": False,
            "code_executed": False,
            "approval_required_for_import": True,
        }
        sources.append(source)
        tasks.append({
            "id": f"adapt-{target['id']}",
            "title": f"Extract safe workflow concepts from {target['name']}",
            "source_id": target["id"],
            "status": "queued_internal_research",
            "deliverables": helps,
            "next_action": "Review public metadata, README, license, and architecture without cloning or executing code.",
            "approval_required": False,
        })
        if target["type"] == "github_repository":
            approvals.append(approval_card(
                f"repo-import-{target['id']}", f"Decide whether to inspect/import {target['name']}", "repo_adaptation",
                "Approve a bounded license and security review; do not import code yet.",
                "Determine whether a safe, licensed component can reduce Nexus build time.", "medium"))
    return {
        "ok": True,
        "mode": "metadata_and_concept_research_only",
        "summary": f"Queued {len(sources)} GitHub targets for concept extraction; no repositories cloned or executed.",
        "targets": sources,
        "adaptation_tasks": tasks,
        "approval_cards": approvals,
        "counts": {"targets": len(sources), "tasks": len(tasks), "approval_cards": len(approvals)},
        "next_action": "Study credit-repair-tools first for subscription checklist and letter-draft workflow concepts.",
        **SAFETY,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    ensure_dirs()
    report = build_report()
    write_report("repo_research_activation", "GitHub Repo Research Activation", report,
                 {"Research targets": report["targets"], "Adaptation tasks": report["adaptation_tasks"]})
    write_json(SUPABASE_READY / "repo_research_sources_latest.json", report["targets"])
    write_json(SUPABASE_READY / "repo_adaptation_tasks_latest.json", report["adaptation_tasks"])
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
