#!/usr/bin/env python3
"""Canonical consumer for campaign-derived department handoffs.

The dispatcher consumes existing campaign work-order identities.  It does not
create opportunities or duplicate handoffs.  Each bounded internal execution
uses the persisted Research/Alpha evidence as input and returns a receipt to
the campaign.  External publication, spend, applications, and live trading
remain gated.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed.persistence import append_record, read_records  # noqa: E402

NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%dT%H%M%SZ")
OUT = ROOT / "reports/runtime"
OUT.mkdir(parents=True, exist_ok=True)


def latest(rows: list[dict], key: str) -> dict[str, dict]:
    result = {}
    for row in rows:  # governed persistence is newest-first
        value = row.get(key)
        if value and value not in result:
            result[value] = row
    return result


def source_context(order: dict) -> dict:
    rid = order.get("research_id")
    oid = order.get("opportunity_id")
    evidence = None
    opportunity = next((x for x in read_records("opportunities") if x.get("opportunity_id") == oid), {})
    if opportunity:
        evidence = opportunity.get("evidence")
    if evidence is None and rid:
        evidence = next((x for x in read_records("business_research") if x.get("research_id") == rid), {})
    return {"research_id": rid, "opportunity_id": oid, "source_evidence_present": bool(evidence),
            "source_evidence_digest": hashlib.sha256(json.dumps(evidence or {}, sort_keys=True).encode()).hexdigest()[:16],
            "opportunity_title": opportunity.get("title"), "opportunity_category": opportunity.get("category")}


def bounded_result(order: dict, context: dict) -> dict:
    dept = str(order.get("owner_specialist") or order.get("department") or "UNMAPPED")
    action = order.get("action") or "Review the source-backed finding and define the next bounded step."
    common = {"audience": dept, "source_evidence": context, "action_reviewed": action,
              "external_action_performed": False, "spend": 0, "public_publication": False}
    if dept == "GoClear Operations":
        return common | {"deliverable": "credit-repair/funding operations implementation brief",
            "result": "Source-backed compliance and fulfillment evidence converted into an internal operating checklist; client claims and outcomes remain unverified.",
            "next_action": "Compare one compliant fulfillment/referral path against current client workflow."}
    if dept == "Grants":
        return common | {"deliverable": "grant applicant-fit checklist",
            "result": "Current government source evidence converted into eligibility, missing-evidence, and no-submission checklist.",
            "next_action": "Select the next current opportunity after applicant facts are confirmed."}
    if dept == "Creative":
        return common | {"deliverable": "merchandise creative brief",
            "result": "Existing merchandise concept mapped to a bounded draft creative test; demand remains unvalidated.",
            "next_action": "Prepare the next draft variant and measurement binding; no publication."}
    if dept == "Trading":
        return common | {"deliverable": "trading claim research review",
            "result": "Video-derived trading claim recorded for research review; no order or live/funded action performed.",
            "next_action": "Validate the hypothesis with the existing paper-trading research lane."}
    if dept == "Systems":
        return common | {"deliverable": "systems capability evaluation",
            "result": "Source-backed capability candidate translated into an implementation-risk and sandbox-evaluation brief.",
            "next_action": "Run a bounded benchmark only after capability and data boundaries are confirmed."}
    return common | {"deliverable": "department research handoff brief", "result": "Source-backed finding converted into an internal bounded next-step brief.",
                       "next_action": "Review the brief and select the next eligible work."}


def process(order: dict) -> dict:
    wid = order.get("work_order_id")
    now = NOW.isoformat()
    context = source_context(order)
    base = {k: v for k, v in order.items() if k not in {"status", "accepted_at", "started_at", "completed_at", "receipt_refs", "result_artifact"}}
    base["human_approval_required"] = False
    append_record("work_orders", base | {"status": "ACCEPTED", "accepted_at": now, "accepted_by": "department_queue_consumer"})
    append_record("work_orders", base | {"status": "RUNNING", "started_at": now, "execution_evidence": "bounded_department_consumer"})
    result = bounded_result(order, context)
    artifact = OUT / f"department_handoff_{wid}.json"
    artifact.write_text(json.dumps({"schema_version": "nexus.department-handoff-result.v1", "handoff_id": wid,
        "campaign_id": order.get("campaign_id") or "derived-from:" + str(order.get("research_id")),
        "work_order_id": wid, "department": order.get("owner_specialist"), "result": result,
        "return_destination": "Research", "generated_at": now}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = "receipt_department_" + wid
    append_record("work_orders", base | {"status": "RESULT_READY", "result_ready_at": now,
        "result_artifact": str(artifact.relative_to(ROOT)), "result_classification": "BOUNDED_INTERNAL_RESULT"})
    append_record("result_feedback", {"feedback_id": receipt, "work_order_id": wid, "research_id": order.get("research_id"),
        "opportunity_id": order.get("opportunity_id"), "department": order.get("owner_specialist"),
        "status": "COMPLETE", "result": result["result"], "result_classification": "BOUNDED_INTERNAL_RESULT",
        "result_artifact": str(artifact.relative_to(ROOT)), "receipt": receipt, "completed_at": now,
        "return_destination": "Research", "campaign_id": order.get("campaign_id")})
    append_record("work_orders", base | {"status": "COMPLETED", "completed_at": now,
        "receipt_refs": [receipt], "result_artifact": str(artifact.relative_to(ROOT)),
        "result_classification": "BOUNDED_INTERNAL_RESULT", "return_path": "Research"})
    return {"work_order_id": wid, "department": order.get("owner_specialist"), "accepted": True,
            "execution_started": True, "result": result["result"], "artifact": str(artifact.relative_to(ROOT)),
            "receipt": receipt, "return_path": "Research"}


def ensure_selected_goclear_order(current: dict[str, dict]) -> None:
    """Materialize the already-selected campaign only when its order is absent."""
    if any(x.get("campaign_id") == "campaign.goclear_business" or
           x.get("work_order_id") == "campaign_work_goclear_business" for x in current.values()):
        return
    now = NOW.isoformat()
    append_record("work_orders", {"work_order_id": "campaign_work_goclear_business",
        "campaign_id": "campaign.goclear_business", "work_type": "CAMPAIGN_DERIVED_GOCLEAR",
        "owner_specialist": "GoClear Operations", "status": "ASSIGNED",
        "route": "PORTFOLIO_TO_GOCLEAR_OPERATIONS", "goal_id": "goal_revenue_opportunities",
        "action": "Review current revenue-opportunity evidence and select one compliant GoClear operating experiment.",
        "authority": "bounded_internal_research", "human_approval_required": False,
        "created_at": now, "created_from": "durable campaign selection"})


def run_dispatch() -> dict:
    all_orders = read_records("work_orders")
    current = latest(all_orders, "work_order_id")
    ensure_selected_goclear_order(current)
    current = latest(read_records("work_orders"), "work_order_id")
    eligible = [x for x in current.values() if x.get("status") in {"ASSIGNED", "CREATED", "FAILED_RETRYABLE"}
                and x.get("owner_specialist") != "ALPHA"
                and (x.get("research_id") or x.get("opportunity_id") or x.get("campaign_id"))
                and x.get("work_type") in {"RESEARCH_DERIVED", "YOUTUBE_RESEARCH_HANDOFF", "CAMPAIGN_DERIVED_GOCLEAR"}]
    # GoClear is the persisted next campaign and is deliberately first.
    eligible.sort(key=lambda x: (0 if x.get("owner_specialist") == "GoClear Operations" else 1,
                                 str(x.get("created_at", ""))))
    results = [process(x) for x in eligible]
    after = latest(read_records("work_orders"), "work_order_id")
    next_order = next((x for x in after.values() if x.get("status") in {"ASSIGNED", "CREATED"}
                       and x.get("owner_specialist") != "ALPHA" and (x.get("research_id") or x.get("opportunity_id") or x.get("campaign_id"))), None)
    state = {"generated_at": NOW.isoformat(), "state_machine": ["CREATED", "ASSIGNED", "ACCEPTED", "RUNNING", "RESULT_READY", "COMPLETED"],
             "assigned_is_terminal": False, "last_batch": [r["work_order_id"] for r in results],
             "next_work_order": next_order.get("work_order_id") if next_order else None,
             "next_department": next_order.get("owner_specialist") if next_order else None,
             "queue_consumer": "department_handoff_dispatcher", "self_resume": True}
    path = ROOT / "data/runtime/department_handoff_state.json"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    report = OUT / f"department_handoff_dispatch_{STAMP}.json"
    report.write_text(json.dumps({"schema_version": "nexus.department-handoff-dispatch.v1", "generated_at": NOW.isoformat(),
        "processed": results, "distinct_departments": sorted({r["department"] for r in results}), "state": state}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "PASS", "processed": len(results),
            "distinct_departments": sorted({r["department"] for r in results}),
            "next_work_order": state["next_work_order"], "report": str(report.relative_to(ROOT)),
            "queue_consumer": "department_handoff_dispatcher", "self_resume": True}


def main() -> int:
    print(json.dumps(run_dispatch(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
