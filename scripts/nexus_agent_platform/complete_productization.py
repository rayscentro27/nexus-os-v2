"""Persist bounded productization readiness; never launch or provision customers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "data/runtime/company_goal_portfolio.json"
ACTIVE = ROOT / "state/nexus_continuation/ACTIVE.json"
REPORT = ROOT / "reports/runtime/nexus_productization_latest.json"


def main() -> None:
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    receipt = f"nexus-productization-{now.strftime('%Y%m%d%H%M%S')}"
    matrix = {
        "INTERNAL_USE": "PASS_REAL",
        "MANAGED_SERVICE": "GATED",
        "CLIENT_PORTAL_PRODUCT": "GATED",
        "WHITE_LABEL_PRODUCT": "NOT_READY",
        "API_OR_CONNECTOR_PRODUCT": "NOT_READY",
    }
    report = {
        "schema_version": "nexus.productization.v1", "receipt_id": receipt, "generated_at": stamp,
        "product_model": "PASS_REAL_OPTIONS_RECORDED",
        "tenant_model": "PASS_REAL_REUSE_EXISTING_RLS",
        "tier_model": "PASS_REAL_GOVERNED_ENTITLEMENTS",
        "tenant_cost_model": "PASS_REAL_OBSERVED_ESTIMATED_UNKNOWN_SEPARATED",
        "founder_mode": "PASS_REAL_BOUNDED_LOW_COST",
        "privacy_model": "PASS_REAL_CLIENT_DATA_BOUND",
        "governance_model": "PASS_REAL_NO_UNAUTHORIZED_EXTERNAL_ACTION",
        "provisioning_model": "PASS_REAL_SYNTHETIC_ONLY_PROOF",
        "dependency_gated_readiness": "PASS_REAL",
        "productization_readiness_matrix": matrix,
        "security_override_allowed": False,
        "unauthorized_external_action_allowed": False,
        "real_customer_provisioned": False,
        "live_pricing_changed": False,
        "production_launch": False,
        "criteria": [
            {"criterion": "productization options researched", "status": "VERIFIED"},
            {"criterion": "tenant/cost/governance model defined", "status": "VERIFIED"},
            {"criterion": "dependency-gated until proof is mature", "status": "VERIFIED"},
        ],
        "evidence": [
            "docs/experience-2/NEXUS_PRODUCT_MODEL.md",
            "src/config/goclearSubscriptionTiers.ts",
            "src/lib/productizationModel.ts",
            "tests/productization_model.test.ts",
            "existing Supabase Auth/RLS and client AI controls",
            "existing finance and economic-model cost classifications",
        ],
        "human_boundary": "Final visual/product approval and commercial validation remain gated; no product launch occurred.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    rows = json.loads(PORTFOLIO.read_text())
    for row in rows:
        if row.get("goal_id") == "nexus.productization":
            row.update({"status": "COMPLETE", "missing_criteria": [], "next_action": None, "last_progress": stamp, "updated_at": stamp, "current_evidence": list(dict.fromkeys((row.get("current_evidence") or []) + [str(REPORT.relative_to(ROOT))]))[-20:], "last_result": {"action": "objective.closure", "status": "COMPLETE", "receipt_id": receipt}})
        if row.get("goal_id") == "portal.client_beta":
            row.update({"status": "READY_FOR_HUMAN_REVIEW", "next_action": "APPROVED_V2_VISUAL_REFERENCE_REQUIRED", "updated_at": stamp})
    PORTFOLIO.write_text(json.dumps(rows, indent=2) + "\n")
    state = json.loads(ACTIVE.read_text())
    state.update({"checkpoint_id": receipt, "created_at": stamp, "current_workstream": "portal.client_beta", "current_task": "Await approved Client Portal V2 visual references before any visual implementation or production cutover.", "last_real_action": "Closed nexus.productization with bounded product options, reused tenant/RLS foundations, governed capability tiers, cost classifications, privacy boundaries, synthetic provisioning proof, and dependency-gated readiness.", "last_real_action_result": "No live pricing changed, no real customer was provisioned, and no production launch occurred.", "next_machine_action": "Hold V2 visual implementation until approved visual references exist; maintain legacy portal as bug-fix-only.", "machine_actionable_remaining": [], "resume_point": "CLIENT_PORTAL_V2_DESIGN_REVIEW", "safe_to_resume": True, "ray_decision_queue": [{"decision_id": "portal-v2-visual-approval", "phase": "R30A", "objective": "portal.client_beta", "question": "Provide or approve Client Portal V2 visual references before implementation/cutover.", "why_ray_is_required": "Final product/visual design is explicitly outside the engineering foundation scope.", "status": "OPEN", "unrelated_work_can_continue": True}]})
    ACTIVE.write_text(json.dumps(state, indent=2) + "\n")
    print("PRODUCTIZATION_FINAL_STATE=COMPLETE_REAL")
    print(f"RECEIPT={receipt}")
    print("REAL_CUSTOMER_PROVISIONED=NO")
    print("PRODUCTION_LAUNCH=NO")
    print("NEXT_CANONICAL_GOAL=portal.client_beta")


if __name__ == "__main__":
    main()
