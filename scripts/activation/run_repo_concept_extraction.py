#!/usr/bin/env python3
"""Extract structured concepts from local static seed records only.

Static seed research only. No GitHub network access performed.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs" / "repo_research_targets.json"
RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"
SUPABASE = RUNTIME / "supabase_ready"
NOTICE = "Static seed research only. No GitHub network access performed."


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify(concept: str) -> tuple[str, str, str, int]:
    text = concept.lower()
    if "automatic bureau contact" in text:
        return "credit_repair", "high", "blocked", 10
    if any(word in text for word in ("dispute", "letter", "goodwill", "debt validation", "repair")):
        return "credit_repair", "high", "approval_required", 95
    if any(word in text for word in ("utilization", "payment history", "inquiry", "credit age", "account mix", "score-factor", "readiness reasons")):
        return "credit_profile_readiness", "medium", "client_visible_safe", 94
    if any(word in text for word in ("receivable", "invoice", "financial record", "customer credit")):
        return "business_profile_readiness", "medium", "admin_review_required", 82
    if any(word in text for word in ("application", "eligibility", "underwriting", "approval criteria", "funding pipeline", "borrower")):
        return "funding_readiness", "high", "admin_review_required", 91
    if any(word in text for word in ("banking", "payment", "ecosystem", "fintech infrastructure")):
        return "partner_offers", "medium", "admin_review_required", 76
    if any(word in text for word in ("checklist", "documentation", "document")):
        return "client_tasks", "low", "client_visible_safe", 90
    if any(word in text for word in ("admin review", "dashboard", "decision status")):
        return "admin_review", "medium", "admin_review_required", 84
    if any(word in text for word in ("proof", "ledger", "compliance", "metro 2")):
        return "hermes_guidance", "medium", "admin_review_required", 78
    return "client_guide_guidance", "low", "client_visible_safe", 70


def build() -> dict[str, Any]:
    config = json.loads(CONFIG.read_text())
    created = now()
    sources, concepts, tasks = [], [], []
    for target in config["targets"]:
        sources.append({
            "id": target["id"], "tenant_id": "tenant_demo_goclear", "client_id": None,
            "category": "repo_static_seed", "title": target["name"], "summary": target["purpose"],
            "status": "static_seed_loaded", "score": 80, "priority": "medium", "risk_level": "low",
            "automation_level": "admin_review_required", "client_visible": False, "approval_required": False,
            "goclear_review_status": "not_required", "source": "local_static_config", "source_concept": target["id"],
            "url_reference_only": target["url"], "network_access_performed": False,
            "recommended_next_action": "Review extracted concepts locally.", "created_at": created,
        })
        for index, concept in enumerate(target.get("concepts", []), start=1):
            area, risk, automation, priority = classify(concept)
            item = {
                "id": f"concept-{target['id']}-{index}", "tenant_id": "tenant_demo_goclear", "client_id": None,
                "category": area, "title": concept.title(), "summary": f"Static concept seed: {concept}.",
                "status": "extracted_static_seed", "score": priority, "priority": "high" if priority >= 90 else "medium",
                "risk_level": risk, "automation_level": automation, "client_visible": automation == "client_visible_safe",
                "approval_required": automation in {"approval_required", "blocked"}, "goclear_review_status": "pending" if automation != "client_visible_safe" else "not_required",
                "source": target["name"], "source_concept": concept, "subscription_value": "high" if priority >= 85 else "medium",
                "implementation_priority": priority, "recommended_next_action": "Adapt as a local data/workflow pattern; do not import code.",
                "created_at": created, "github_network_access_performed": False,
            }
            concepts.append(item)
            tasks.append({
                **item, "id": f"adapt-{target['id']}-{index}", "category": "repo_adaptation_task",
                "title": f"Adapt concept: {concept}", "status": "queued_local_design",
                "client_visible": False, "automation_level": "admin_review_required" if automation != "blocked" else "blocked",
                "recommended_next_action": "Map the concept to Nexus schemas and safety gates before implementation.",
            })
    return {
        "ok": True, "generated_at": created, "mode": "static_seed_only", "notice": NOTICE,
        "github_network_access_performed": False, "sources": sources, "concepts": concepts,
        "adaptation_tasks": tasks, "counts": {"sources": len(sources), "concepts": len(concepts), "adaptation_tasks": len(tasks)},
        "external_action_performed": False, "real_client_data_used": False,
    }


def write(report: dict[str, Any]) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True); MANUAL.mkdir(parents=True, exist_ok=True); SUPABASE.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "repo_concept_extraction_latest.json").write_text(json.dumps(report, indent=2) + "\n")
    (SUPABASE / "repo_research_sources_latest.json").write_text(json.dumps(report["sources"], indent=2) + "\n")
    (SUPABASE / "repo_concepts_latest.json").write_text(json.dumps(report["concepts"], indent=2) + "\n")
    (SUPABASE / "repo_adaptation_tasks_latest.json").write_text(json.dumps(report["adaptation_tasks"], indent=2) + "\n")
    lines = ["# Repo Concept Extraction", "", NOTICE, "", f"- ok: {str(report['ok']).lower()}",
             "- github_network_access_performed: false", f"- sources: {report['counts']['sources']}",
             f"- concepts: {report['counts']['concepts']}", f"- adaptation_tasks: {report['counts']['adaptation_tasks']}",
             "", "## Product Areas"]
    for area in sorted({item["category"] for item in report["concepts"]}):
        lines.append(f"- {area}: {sum(1 for item in report['concepts'] if item['category'] == area)}")
    (MANUAL / "repo_concept_extraction_latest.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = build(); write(report)
    print(json.dumps(report, indent=2) if args.json else NOTICE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
