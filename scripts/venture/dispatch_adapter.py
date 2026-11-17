"""Section 29 — Venture Kernel <-> Durable Dispatcher integration adapter.

Thin, additive adapter. Creates NO new scheduler / queue / registry / ledger. It REUSES:
  * the existing durable dispatcher job store  (nexus_agent_platform.durable_jobs.DurableJobStore)
  * the certified Resource/Worker Router        (resource_directory.router)
  * the certified Venture Kernel stage logic    (venture.kernel) — deterministic, $0
  * the existing AI usage ledger (via resource_directory env usage events that reference it)

Responsibility split (never collapsed):
  Venture Kernel = WHAT next   | Resource Router = WHERE | Worker Router = WHO
  Harness select = HOW         | Durable Dispatcher = WHEN/queue/claim/retry/recover
  Worker = performs            | Usage ledger = records what happened

Governance: no silent paid spend (PAID_METERED beyond approved budget -> WAITING_FOR_RAY_APPROVAL,
venture stays resumable, never failed, never duplicated). Oracle never receives heavy workloads
even on total fallback. Unknown metrics stay UNKNOWN.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Reuse the LIVE durable dispatcher's job store (read its code; do not duplicate it).
_DISPATCH_RELEASE = os.environ.get(
    "NEXUS_DISPATCHER_RELEASE",
    str(Path.home() / ".nexus/releases/nexus-capability-actions-20261108-dispatcher-ai-usage-hook-v1"))
_DISPATCH_SCRIPTS = str(Path(_DISPATCH_RELEASE) / "scripts")
if _DISPATCH_SCRIPTS not in sys.path:
    sys.path.insert(0, _DISPATCH_SCRIPTS)

from nexus_agent_platform.durable_jobs import DurableJobStore  # existing dispatcher queue
from resource_directory import router as RR
from venture import kernel as VK
from opportunities import engine as opp

VENTURE_SOURCE = "venture_kernel"          # governance_context.source -> dispatch_once allowed_job_sources gate
ZERO_COST_BUDGET = {"max_requests": 20, "max_response_bytes": 2000000, "max_tokens": 0, "max_gpu_seconds": 0,
                    "max_runtime_seconds": 300, "max_resource_creations": 0, "max_estimated_cost": 0.0, "max_retries": 3}
HEAVY_WORKLOADS = {"research", "coding", "frontend_build", "gpu", "data_processing", "media_generation"}
ALLOWED_AUTONOMOUS_COST = {"FREE", "INCLUDED_SUBSCRIPTION", "INCLUDED_CREDIT"}

# venture stage -> (workload for routing, deterministic $0 handler name)
STAGE_WORKLOAD = {
    "RESEARCH": "research", "VALIDATE": "reasoning", "SCORE": "reasoning",
    "RESOURCE_MAP": "reasoning", "PREPARE": "reasoning", "FUNNEL_BUILD": "coding",
    "DEPLOY": "deployment", "CLUSTER": "data_processing",
}


# ---------------------------------------------------------------- Step 2: venture work contract
def build_work_unit(venture_id, opportunity_id, stage, *, objective="", department="BusinessOpportunities",
                    task_type="", required_capabilities=None, parent_work_item=None,
                    previous_receipt=None, max_cost=0.0) -> dict:
    return {
        "venture_id": venture_id, "opportunity_id": opportunity_id, "stage": stage,
        "objective": objective, "department": department,
        "task_type": task_type or stage.lower(),
        "required_capabilities": required_capabilities or [STAGE_WORKLOAD.get(stage, "reasoning")],
        "allowed_cost_classes": sorted(ALLOWED_AUTONOMOUS_COST), "max_cost": max_cost,
        "parent_work_item": parent_work_item, "previous_receipt": previous_receipt,
        "created_at": "UNKNOWN", "work_unit_id": "wu_" + uuid.uuid4().hex,
    }


# ---------------------------------------------------------------- Step 3/4/5/8: routing + governance
def route(work_unit: dict, *, approved_spend: float = 0.0, exclude_environments=None) -> dict:
    workload = STAGE_WORKLOAD.get(work_unit["stage"], "reasoning")
    rt = RR.route_task(work_unit["task_type"], workload=workload,
                       required_capabilities=work_unit["required_capabilities"],
                       approved_spend=approved_spend)
    ranked = [r for r in rt["ranked"] if r.get("eligible")
              and r["environment_id"] not in set(exclude_environments or [])]
    # Oracle protection: never allow heavy workloads on Oracle, even on total fallback.
    if workload in HEAVY_WORKLOADS:
        ranked = [r for r in ranked if r["environment_id"] != "oracle"]
    selected = ranked[0] if ranked else None
    wr = RR.route_worker(work_unit["required_capabilities"])
    # Harness flexibility (spec 8): for coding/browser/build work, surface all role-compatible
    # harnesses (not just those on the selected env) so no single harness is forced.
    coding_like = workload in {"coding", "frontend_build", "browser"} or \
        any(c in ("coding", "frontend", "backend", "reverse_engineering", "browser")
            for c in work_unit["required_capabilities"])
    if coding_like:
        candidate_h = [h["harness_id"] for h in wr["harness_candidates"]
                       if "CODING" in str(h.get("role") or "").upper() or "BROWSER" in str(h.get("role") or "").upper()]
    else:
        candidate_h = [h["harness_id"] for h in wr["harness_candidates"]
                       if selected and selected["environment_id"] in (h.get("environments") or [])]
    harnesses = candidate_h or [h["harness_id"] for h in wr["harness_candidates"]]
    # cost / approval governance
    requires_approval = False
    approval_reason = None
    env_rec = RR.get_environment(selected["environment_id"]) if selected else None
    if selected is None:
        requires_approval = True
        approval_reason = "NO_VALID_AUTHORIZED_ROUTE (free/included options unavailable; paid needs approval)"
    elif selected.get("cost_class") not in ALLOWED_AUTONOMOUS_COST and approved_spend <= 0:
        requires_approval = True
        approval_reason = f"Top route {selected['environment_id']} is {selected.get('cost_class')}; no approved budget."
    elif env_rec and env_rec.get("approval_required"):
        # publish/deploy/spend/DNS governance (e.g. Netlify, Cloudflare, Supabase, Modal, RunPod)
        requires_approval = True
        approval_reason = env_rec.get("approval_reason") or f"{selected['environment_id']} requires governed approval."
    return {
        "selected_environment": (selected or {}).get("environment_id"),
        "candidate_environments": [r["environment_id"] for r in ranked[:5]],
        "excluded_environments": [r["environment_id"] for r in rt["ranked"] if not r.get("eligible")][:6],
        "selected_worker": (wr["registered_workers_ranked"][0]["worker_id"] if wr["registered_workers_ranked"] else None),
        "candidate_workers": [w["worker_id"] for w in wr["registered_workers_ranked"][:3]],
        "selected_harness": harnesses[0] if harnesses else None,
        "candidate_harnesses": harnesses[:5],
        "cost_class": (selected or {}).get("cost_class", "UNKNOWN"),
        "estimated_cost_if_known": 0.0 if (selected or {}).get("cost_class") in ("FREE", "INCLUDED_SUBSCRIPTION") else "UNKNOWN",
        "quota_state": "UNKNOWN",
        "approval_required": requires_approval, "approval_reason": approval_reason,
        "routing_reasons": (selected or {}).get("reason"),
        "fallback_order": [r["environment_id"] for r in ranked[1:4]],
    }


# ---------------------------------------------------------------- Step 3: enqueue into EXISTING dispatcher
def enqueue_stage(store: DurableJobStore, work_unit: dict, routing: dict) -> dict:
    """Enqueue a venture stage into the existing durable queue. If approval is required,
    enqueue then immediately transition to WAITING (resumable; not failed, not duplicated)."""
    gov = {"source": VENTURE_SOURCE, "resource_class": "LIGHTWEIGHT_INTERNAL",
           "venture_id": work_unit["venture_id"], "opportunity_id": work_unit["opportunity_id"],
           "stage": work_unit["stage"], "routing": routing, "work_unit_id": work_unit["work_unit_id"]}
    job = store.enqueue(work_unit["department"], f"venture_stage:{work_unit['stage']}",
                        priority=50, parent_job_id=work_unit.get("parent_work_item"),
                        budget_envelope=ZERO_COST_BUDGET,
                        idempotency_key="venture:" + work_unit["work_unit_id"],
                        governance_context=gov)
    if routing.get("approval_required"):
        store.transition(job.job_id, "WAITING", error_code="WAITING_FOR_RAY_APPROVAL",
                         error_summary=(routing.get("approval_reason") or "approval boundary"))
    return {"job_id": job.job_id, "state": ("WAITING" if routing.get("approval_required") else "READY")}


# ---------------------------------------------------------------- deterministic $0 stage handlers
def execute_stage(work_unit: dict, *, db_path=None) -> dict:
    """Deterministic, zero-cost stage execution (reuses venture.kernel + engines). No model calls,
    no production actions. Returns a result dict; raises to trigger retry/recovery."""
    stage = work_unit["stage"]
    oid = work_unit.get("opportunity_id")
    if stage == "RESEARCH":
        # structure the objective into a durable opportunity (evidence marked, no fabrication)
        res = opp.submit({"title": work_unit["objective"][:120] or "Venture research",
                          "summary": work_unit["objective"][:3800], "opportunity_type": "DIGITAL_PRODUCT",
                          "delivery_model": "ONLINE_ONLY", "source_type": "RESEARCH_R10",
                          "verification_state": "UNVERIFIED", "target_customer": "UNKNOWN", "revenue_model": "UNKNOWN"},
                         database_path=db_path)
        return {"stage": stage, "opportunity_id": res.get("opportunity_id"), "created": res.get("created"),
                "duplicate": res.get("duplicate")}
    if stage in ("VALIDATE", "SCORE"):
        rec = opp.get(oid, database_path=db_path, include_internal_ids=True) or {}
        dims = VK._dimensions(rec, {"signals": ["online", "low_cost"]})
        sc = opp.score(oid, dims, database_path=db_path)
        return {"stage": stage, "overall_score": sc.get("overall_score"), "recommendation": sc.get("recommendation"),
                "challenger": VK.challenger(sc)}
    if stage == "RESOURCE_MAP":
        rmap = RR.opportunity_resource_map(["research", "frontend_build", "deployment", "data_processing"])
        return {"stage": stage, "coverage_percent": rmap["nexus_capability_coverage_percent"],
                "matched_environments": [m["environment"] for m in rmap["matched_environments"]],
                "approvals_required": rmap["approvals_required"]}
    if stage == "PREPARE":
        plan = VK.business_plan(oid, db_path=db_path)
        return {"stage": stage, "plan_sections": len([k for k in plan if plan.get(k) not in (None, "")]),
                "unknowns_preserved": plan.get("unknowns_preserved")}
    if stage == "FUNNEL_BUILD":
        pkg = VK.prepare_test_package(oid, db_path=db_path, funnel_db=work_unit.get("funnel_db"))
        return {"stage": stage, "venture_state": pkg.get("venture_state"), "published": pkg.get("published"),
                "free_offer": pkg.get("free_offer", {}).get("free_offer_name")}
    raise RuntimeError(f"NO_HANDLER_FOR_STAGE:{stage}")


# ---------------------------------------------------------------- Step 7: run one claim+execute+recover cycle
def run_worker_once(store: DurableJobStore, work_unit: dict, routing: dict, *, worker_id="venture-worker-1",
                    db_path=None, fail_injection=False, claim_now=None) -> dict:
    # Recovery re-dispatches the SAME failed work item via the dispatcher's native retry: a
    # FAILED_RETRYABLE job carries a backoff; claiming with a time past the backoff re-runs it.
    job = store.claim(worker_id, now=claim_now)
    if job is None:
        return {"claimed": False}
    store.transition(job.job_id, "RUNNING", worker_id=worker_id)
    try:
        if fail_injection:
            raise RuntimeError("INJECTED_WORKER_FAILURE")
        result = execute_stage(work_unit, db_path=db_path)
        receipt_ref = store.complete(job.job_id, worker_id, result)
        usage = RR.record_environment_usage({
            "job_id": job.job_id, "work_order_id": work_unit["work_unit_id"], "venture_case_id": work_unit["venture_id"],
            "opportunity_id": work_unit.get("opportunity_id"), "department": work_unit["department"],
            "worker_id": routing.get("selected_worker"), "harness_id": routing.get("selected_harness"),
            "environment_id": routing.get("selected_environment"), "task_type": work_unit["task_type"],
            "cost_class": routing.get("cost_class"), "actual_cost": 0, "status": "COMPLETED", "success": True,
            "ai_usage_ref": "ledger:deterministic:0"})
        return {"claimed": True, "job_id": job.job_id, "state": "COMPLETED", "result": result,
                "receipt_ref": receipt_ref, "usage_event_id": usage["usage_event_id"]}
    except Exception as exc:
        store.transition(job.job_id, "FAILED_RETRYABLE", worker_id=worker_id,
                         error_code="WORKER_ERROR", error_summary=str(exc)[:200])
        RR.record_environment_usage({"job_id": job.job_id, "venture_case_id": work_unit["venture_id"],
                                     "environment_id": routing.get("selected_environment"),
                                     "task_type": work_unit["task_type"], "status": "FAILED", "success": False,
                                     "failure_reason": str(exc)[:160], "ai_usage_ref": "ledger:deterministic:0"})
        return {"claimed": True, "job_id": job.job_id, "state": "FAILED_RETRYABLE", "error": str(exc)[:160]}


def recover_and_reroute(store: DurableJobStore, work_unit: dict, failed_routing: dict, *, approved_spend=0.0) -> dict:
    """Step 7 recovery: same work unit, next valid environment, preserve lineage. Never Oracle for heavy."""
    exclude = [failed_routing.get("selected_environment")]
    new_routing = route(work_unit, approved_spend=approved_spend, exclude_environments=exclude)
    return new_routing
