"""Nexus Resource Directory + Adaptive Router.

Reuse-first resource-intelligence layer. Loads the EXISTING registries and adds the
missing environment/harness records + a deterministic policy router. Creates NO new
DB (JSON registries, matching Nexus convention), NO duplicate ledger (environment usage
events wrap — do not duplicate — the existing AI usage ledger's model/token accounting).

Reused authorities:
  - data/runtime/nexus_environment_registry.json   (NEW first-class entity added this task)
  - data/runtime/nexus_worker_registry.json         (existing — reused/extended)
  - data/runtime/nexus_capability_registry.json     (existing — reused)
  - data/runtime/nexus_credential_registry.json     (existing — secret references only)
  - scripts/nexus_agent_platform/runtime/ai_usage_ledger.py (existing — model/token accounting, cost_class_for)

Zero model/provider calls; routing is deterministic. No silent paid fallback: a route that
needs incremental paid spend beyond approved limits returns WAITING_FOR_RAY_APPROVAL.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_RUNTIME = _SCRIPTS.parent / "data/runtime"
# Testability + relocation hook (lets cert simulate quota/offline on an isolated copy).
ENV_REGISTRY = Path(os.environ.get("NEXUS_ENV_REGISTRY_PATH", _RUNTIME / "nexus_environment_registry.json"))
WORKER_REGISTRY = _RUNTIME / "nexus_worker_registry.json"
CAP_REGISTRY = _RUNTIME / "nexus_capability_registry.json"
ENV_USAGE_EVENTS = Path.home() / ".nexus/state/resource_directory/environment_usage_events.jsonl"

PAUSE_STATE = "WAITING_FOR_RAY_APPROVAL"
COST_CLASS_RANK = {"FREE": 0, "INCLUDED_SUBSCRIPTION": 1, "INCLUDED_CREDIT": 2, "PAID_METERED": 5, "UNKNOWN": 3}
HEALTHY = {"HEALTHY", "PASS_REAL", "CERTIFIED_BOUNDED", "PASS_REAL_BOUNDED", "ACTIVE", "AVAILABLE"}
UNHEALTHY = {"OFFLINE", "BLOCKED", "RETIRED", "DEPRECATED"}
LIVE_STATUSES = {"ACTIVE", "AVAILABLE", "EXPERIMENTAL"}

# workload -> keyword set matched against an environment's allowed/prohibited_workloads
_WORKLOAD_KEYWORDS = {
    "research": ["research", "evidence"],
    "reasoning": ["reasoning", "nova", "hermes", "coordination", "approvals"],
    "control": ["routing", "approvals", "coordination", "health", "nova", "hermes"],
    "coding": ["coding", "autonomous_coding", "app_build", "repo_test", "isolated_build", "prototype", "build_verification"],
    "frontend_build": ["landing_page", "website", "app_build", "coding"],
    "browser": ["browser_automation", "browser"],
    "gpu": ["gpu", "bounded_gpu", "gpu_heavy", "model_workload"],
    "data_processing": ["data_processing", "clustering", "embeddings", "ml", "batch_analysis", "python", "data_analysis"],
    "deployment": ["approved_deploy", "deployment_dependency", "validation_funnel", "landing_page"],
    "dns": ["dns", "tunnel", "alias", "edge_routing"],
    "structured_data": ["structured_data", "auth", "coordination"],
    "media_generation": ["media_generation", "visual_concept", "video_concept", "avatar", "media"],
    "knowledge": ["dossier", "opportunity_notebook", "source_grounded_analysis", "transcript"],
    "artifact_storage": ["report_storage", "export", "deliverable", "archive", "media_storage"],
    "qa": ["qa", "test_worker"],
    "trading_test": ["paper_trade", "strategy_test"],
    "model_inference": ["model_inference_free", "model_inference_paid_governed"],
}


def _load(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def environments():
    return _load(ENV_REGISTRY).get("environments", [])


def harnesses():
    return _load(ENV_REGISTRY).get("harnesses", [])


def workers():
    return _load(WORKER_REGISTRY).get("workers", [])


def capabilities():
    return _load(CAP_REGISTRY).get("capabilities", [])


def get_environment(env_id):
    return next((e for e in environments() if e.get("environment_id") == env_id), None)


# ----------------------------------------------------------- health / quota helpers
def env_available(env: dict) -> bool:
    return (env.get("status") in LIVE_STATUSES
            and env.get("health_status") not in UNHEALTHY
            and str(env.get("quota_remaining")).upper() not in {"0", "EXHAUSTED"})


def quota_exhausted(env: dict) -> bool:
    return str(env.get("quota_remaining")).upper() in {"0", "EXHAUSTED"} or str(env.get("health_status")).upper() == "QUOTA_EXHAUSTED"


# ----------------------------------------------------------- adaptive history (spec 19)
def _history_stats(env_id: str) -> dict:
    jobs = succ = 0
    if ENV_USAGE_EVENTS.exists():
        for line in ENV_USAGE_EVENTS.read_text().splitlines():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("environment_id") == env_id:
                jobs += 1
                if ev.get("success"):
                    succ += 1
    return {"jobs": jobs, "success_rate": (succ / jobs) if jobs else None}


# ----------------------------------------------------------- RESOURCE ROUTER (spec 16/17)
def route_task(task_type: str, *, workload: str, required_capabilities=None,
               data_sensitivity: str = "INTERNAL", needs_persistence: bool = False,
               approved_spend: float = 0.0) -> dict:
    """Return ranked environment candidates with a deterministic ROUTE_SCORE + explanation.
    No silent paid fallback: if the top viable route needs paid spend beyond approved_spend,
    surface WAITING_FOR_RAY_APPROVAL alongside the ranking."""
    kws = _WORKLOAD_KEYWORDS.get(workload, [workload])
    ranked = []
    for env in environments():
        allowed = set(env.get("allowed_workloads") or [])
        prohibited = set(env.get("prohibited_workloads") or [])
        reasons = []
        # hard exclude: prohibited workload or unhealthy
        prohibit_hit = any(k in " ".join(prohibited) for k in kws) or workload in prohibited \
            or (workload == "research" and "heavy_research" in prohibited) \
            or (workload == "gpu" and "gpu" in prohibited)
        if prohibit_hit:
            ranked.append({"environment_id": env["environment_id"], "score": -999, "eligible": False,
                           "reason": f"PROHIBITED workload '{workload}' on {env['environment_id']}"})
            continue
        if env.get("status") in UNHEALTHY or env.get("health_status") in UNHEALTHY or env.get("status") == "RETIRED":
            ranked.append({"environment_id": env["environment_id"], "score": -500, "eligible": False,
                           "reason": f"unavailable (status={env.get('status')}, health={env.get('health_status')})"})
            continue
        score = 0.0
        cap_match = any(k in allowed for k in kws) or any(any(k in a for k in kws) for a in allowed)
        if cap_match:
            score += 40; reasons.append("capability_match")
        else:
            score -= 20; reasons.append("weak_capability_match")
        # health
        if env.get("health_status") in HEALTHY:
            score += 15; reasons.append("healthy")
        elif env.get("health_status") in ("UNKNOWN", None):
            score += 2; reasons.append("health_unknown")
        # included capacity / cost
        cc = env.get("cost_class", "UNKNOWN")
        score += max(0, 15 - COST_CLASS_RANK.get(cc, 3) * 3)
        reasons.append(f"cost_class={cc}")
        if cc == "PAID_METERED":
            score -= 15; reasons.append("cost_penalty")
        # quota
        if quota_exhausted(env):
            score -= 40; reasons.append("quota_exhausted")
        # approval
        approval = env.get("approval_required")
        needs_paid = cc in {"PAID_METERED", "INCLUDED_CREDIT"} and env.get("can_spend")
        if approval:
            score -= 8; reasons.append("approval_required")
        # persistence requirement vs non-persistent envs
        if needs_persistence and env.get("environment_id") in {"kaggle", "colab", "antigravity"}:
            score -= 10; reasons.append("low_persistence")
        # data sensitivity
        if data_sensitivity.upper() in [str(x).upper() for x in (env.get("data_classification_prohibited") or [])]:
            score -= 50; reasons.append("data_classification_prohibited")
        # canonical fit bonus for control/research
        if workload in ("control", "reasoning") and env.get("environment_id") == "oracle":
            score += 25; reasons.append("canonical_control_plane")
        if workload == "research" and env.get("environment_id") == "mac_mini":
            score += 25; reasons.append("canonical_research_host")
        # adaptive history
        h = _history_stats(env["environment_id"])
        if h["success_rate"] is not None:
            score += 10 * h["success_rate"]; reasons.append(f"history_success={h['success_rate']:.2f}(n={h['jobs']})")
        ranked.append({"environment_id": env["environment_id"], "score": round(score, 1),
                       "eligible": score > 0, "cost_class": cc, "approval_required": bool(approval),
                       "needs_paid_spend": bool(needs_paid), "reason": ", ".join(reasons)})
    ranked.sort(key=lambda r: r["score"], reverse=True)
    top = next((r for r in ranked if r["eligible"]), None)
    decision = {"task_type": task_type, "workload": workload, "ranked": ranked[:8], "selected": top}
    # no-silent-paid-fallback gate (spec 26)
    if top and top.get("needs_paid_spend") and approved_spend <= 0:
        decision["venture_state"] = PAUSE_STATE
        decision["approval_reason"] = f"Top route {top['environment_id']} is {top['cost_class']} and needs incremental spend; no approved budget."
    return decision


# ----------------------------------------------------------- WORKER ROUTER (spec 18)
def route_worker(required_capabilities, *, prefer_cost: bool = True) -> dict:
    req = set(c.lower() for c in (required_capabilities or []))
    ranked = []
    for w in workers():
        caps = set(str(c).lower() for c in (w.get("capabilities") or []))
        overlap = req & caps
        score = 30 * len(overlap)
        health = str(w.get("health") or "").upper()
        if health in {"PASS_REAL", "PASS_REAL_BOUNDED", "CERTIFIED_BOUNDED"}:
            score += 15
        elif "OFFLINE" in health or "FAIL" in health:
            score -= 100
        if str(w.get("availability") or "").upper() in {"OFFLINE", "BUSY"}:
            score -= 20
        ranked.append({"worker_id": w.get("worker_id"), "environment": w.get("environment"),
                       "health": w.get("health"), "capability_overlap": sorted(overlap), "score": score})
    ranked.sort(key=lambda r: r["score"], reverse=True)
    # also surface harness-based coding/browser workers from the harness registry (capability-typed)
    harness_workers = [{"harness_id": h["harness_id"], "role": h.get("role"), "environments": h.get("environments"),
                        "native_worker_capability": h.get("native_worker_capability")}
                       for h in harnesses()]
    return {"required_capabilities": sorted(req), "registered_workers_ranked": ranked[:6],
            "harness_candidates": harness_workers}


# ----------------------------------------------------------- ENVIRONMENT USAGE EVENT (spec 13)
def record_environment_usage(event: dict) -> dict:
    """Append an ENVIRONMENT_USAGE_EVENT (execution tracking AROUND the AI usage ledger).
    Does NOT duplicate model/token accounting — link to the AI ledger via ai_usage_ref.
    Unknown metrics stay UNKNOWN; never fabricate provider-native metrics."""
    ENV_USAGE_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    import uuid
    rec = {
        "usage_event_id": "envusage_" + uuid.uuid4().hex,
        "job_id": event.get("job_id", "UNKNOWN"), "work_order_id": event.get("work_order_id", "UNKNOWN"),
        "venture_case_id": event.get("venture_case_id"), "opportunity_id": event.get("opportunity_id"),
        "department": event.get("department"), "worker_id": event.get("worker_id"),
        "harness_id": event.get("harness_id"), "environment_id": event.get("environment_id"),
        "task_type": event.get("task_type"), "started_at": event.get("started_at", "UNKNOWN"),
        "completed_at": event.get("completed_at", "UNKNOWN"), "duration": event.get("duration", "UNKNOWN"),
        "cost_class": event.get("cost_class", "UNKNOWN"), "estimated_cost": event.get("estimated_cost", "UNKNOWN"),
        "actual_cost": event.get("actual_cost", "UNKNOWN"), "compute_units": event.get("compute_units", "UNKNOWN"),
        "gpu_time": event.get("gpu_time", "UNKNOWN"), "status": event.get("status", "UNKNOWN"),
        "success": bool(event.get("success")), "failure_reason": event.get("failure_reason"),
        "ai_usage_ref": event.get("ai_usage_ref"),  # link to existing AI ledger entry (not duplicated)
        "quality_score": event.get("quality_score", "UNKNOWN"), "artifact_ref": event.get("artifact_ref"),
    }
    with open(ENV_USAGE_EVENTS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def environment_usage_summary(env_id: str, period: str = "all") -> dict:
    stats = _history_stats(env_id)
    return {"environment_id": env_id, "period": period, "jobs": stats["jobs"],
            "success_rate": stats["success_rate"] if stats["success_rate"] is not None else "UNKNOWN",
            "note": "policy defaults in use until sufficient real history accrues (spec 19)"}


# ----------------------------------------------------------- BUSINESS OPPORTUNITY MAPPING (spec 20)
def opportunity_resource_map(required_capabilities, *, data_sensitivity="INTERNAL") -> dict:
    req = [c.lower() for c in (required_capabilities or [])]
    matched_envs, missing = [], []
    for cap in req:
        workload = cap if cap in _WORKLOAD_KEYWORDS else "coding"
        route = route_task(f"opportunity_cap:{cap}", workload=workload, required_capabilities=[cap],
                           data_sensitivity=data_sensitivity)
        sel = route.get("selected")
        if sel and sel.get("eligible"):
            matched_envs.append({"capability": cap, "environment": sel["environment_id"],
                                 "cost_class": sel.get("cost_class"), "needs_paid": sel.get("needs_paid_spend")})
        else:
            missing.append(cap)
    wmap = route_worker(req)
    included = [m for m in matched_envs if m["cost_class"] in ("FREE", "INCLUDED_SUBSCRIPTION", "INCLUDED_CREDIT")]
    paid = [m for m in matched_envs if m.get("needs_paid")]
    pct = round(100 * len(matched_envs) / max(1, len(req)), 1)
    return {
        "required_capabilities": req,
        "matched_capabilities": [m["capability"] for m in matched_envs],
        "matched_environments": matched_envs,
        "matched_workers": wmap["registered_workers_ranked"][:3],
        "new_capabilities_required": missing,
        "new_environments_required": [],
        "included_capacity_available": [m["environment"] for m in included],
        "expected_incremental_cost": ("APPROVAL_REQUIRED" if paid else 0),
        "human_work_required": "UNKNOWN",
        "approvals_required": sorted({m["environment"] for m in paid}) or [],
        "nexus_capability_coverage_percent": pct,
    }


# ----------------------------------------------------------- VENTURE KERNEL INTERFACE (spec 22 — prepare, do not activate)
def venture_router_interface(required_capabilities, *, approved_spend: float = 0.0) -> dict:
    """Read-only interface the venture kernel can later call. Does NOT wire into any scheduler."""
    rmap = opportunity_resource_map(required_capabilities)
    needs_approval = bool(rmap["approvals_required"]) and approved_spend <= 0
    return {
        "capabilities_present": rmap["matched_capabilities"],
        "capabilities_missing": rmap["new_capabilities_required"],
        "workers_available": [w["worker_id"] for w in rmap["matched_workers"]],
        "environments_available": [m["environment"] for m in rmap["matched_environments"]],
        "expected_incremental_cost": rmap["expected_incremental_cost"],
        "new_spend_requires_approval": needs_approval,
        "venture_state": PAUSE_STATE if needs_approval else "READY",
        "interface_version": "resource-router-v1", "scheduler_wired": False,
    }
