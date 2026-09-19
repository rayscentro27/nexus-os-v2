"""Model-backed Research investigation and certified capability routing.

This is an orchestration seam above the existing queue and processors. It does
not acquire evidence itself: the model creates a bounded plan, a certified
adapter/processor executes it, and the model interprets the returned artifact.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/governed/research_worker_capability_certifications.jsonl"
RECEIPT_ROOT = ROOT / "data/runtime/research_ai_orchestration"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model() -> str:
    return os.environ.get("RESEARCH_AI_MODEL") or os.environ.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini"


def load_certified_executors() -> list[dict[str, Any]]:
    rows = []
    try:
        for line in REGISTRY.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("certification_status") in {"PASS_REAL", "PASS_REAL_BOUNDED"}:
                rows.append(row)
    except (OSError, ValueError):
        return []
    return rows


def _capabilities(row: dict[str, Any]) -> set[str]:
    blob = " ".join(str(row.get(k, "")) for k in ("worker_capability", "actual_executor_id", "capabilities_tested", "tools_used")).lower()
    out = set()
    if "last30" in blob or "demand radar" in blob or "demand discovery" in blob:
        out.add("LAST30DAYS_DEMAND")
    if "seo" in blob:
        out.add("SEO")
    if "youtube" in blob:
        out.add("YOUTUBE")
    if "web" in blob or "public" in blob or "source processor" in blob:
        out.add("WEB_ACQUISITION")
    if "alpha" in blob:
        out.add("ALPHA_REVIEW")
    return out


def _normalize_capability(value: Any) -> str:
    text = str(value or "").upper().replace("-", "_")
    if "SEO" in text:
        return "SEO"
    if "YOUTUBE" in text:
        return "YOUTUBE"
    if "LAST30" in text or "DEMAND_RADAR" in text:
        return "LAST30DAYS_DEMAND"
    if "WEB" in text or "SOURCE" in text or "PUBLIC" in text:
        return "WEB_ACQUISITION"
    if "ALPHA" in text:
        return "ALPHA_REVIEW"
    return text


def certified_capabilities() -> list[dict[str, Any]]:
    result = []
    for row in load_certified_executors():
        result.append({
            "executor_id": row.get("actual_executor_id"),
            "worker_capability": row.get("worker_capability"),
            "certification_status": row.get("certification_status"),
            "capabilities": sorted(_capabilities(row)),
            "limitations": row.get("limitations"),
        })
    return result


def _json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start:end + 1])
            return value if isinstance(value, dict) else None
        except Exception:
            return None


def _call(prompt: dict[str, Any], system: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    from alpha.alpha_live_research import http_json, load_runtime_env
    load_runtime_env()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = _model()
    meta = {"provider": "openrouter", "model": model, "model_calls": 0}
    if not key:
        return None, {**meta, "error": "missing_credential"}
    ok, status, data, error, latency = http_json(
        "POST", "https://openrouter.ai/api/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Research Investigator"},
        {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)}], "temperature": 0.1, "max_tokens": 1200},
        timeout=60,
    )
    text = ""
    try:
        text = str(data["choices"][0]["message"]["content"] or "")
    except Exception:
        pass
    return _json(text), {**meta, "model_calls": 1 if ok else 0, "http_status": status, "latency_ms": latency, "error": error}


def _persist(kind: str, payload: dict[str, Any]) -> str:
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_ROOT / f"{kind}_{payload['receipt_id']}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def write_monitor_snapshot(*, item: dict[str, Any], stage: str, plan: dict[str, Any] | None = None,
                           route_result: dict[str, Any] | None = None, interpretation: dict[str, Any] | None = None) -> str:
    """Publish a read-only snapshot for the existing Research operations monitor."""
    from nexus_agent_platform.research_work_queue import concurrency_limits, default_queue
    items = default_queue().load().get("items", [])
    counts: dict[str, int] = {}
    for row in items:
        status = str(row.get("status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    payload = {
        "schema_version": "nexus.research-ai-monitor.v1", "updated_at": now(),
        "stage": stage, "queue_counts": counts,
        "active_leases": [{"work_id": row.get("work_id"), "worker": row.get("claimed_by"), "expires_at": row.get("lease_expires_at")} for row in items if row.get("status") == "IN_PROGRESS"],
        "objective_id": item.get("objective_id"), "work_id": item.get("work_id"),
        "ai_plan_id": (plan or {}).get("plan_id") or item.get("ai_plan_id"),
        "required_capabilities": (route_result or {}).get("required_capabilities") or item.get("required_capabilities", []),
        "selected_executor_id": ((route_result or {}).get("selected_executor") or {}).get("executor_id") or item.get("selected_executor_id"),
        "alpha_return_items": sum(1 for row in items if row.get("alpha_followup_required") and row.get("status") not in {"COMPLETE", "PARKED", "BLOCKED_EXTERNAL", "FAILED_FINAL"}),
        "concurrency_limits": concurrency_limits(),
        "interpretation": interpretation or {},
    }
    path = RECEIPT_ROOT / "monitor_latest.json"
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def investigate(item: dict[str, Any], *, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    capabilities = certified_capabilities()
    prompt = {
        "work_id": item.get("work_id"), "objective_id": item.get("objective_id"), "parent_request_id": item.get("parent_request_id"),
        "work_class": item.get("work_class"), "question": item.get("question") or item.get("title") or item.get("source_url"),
        "known_evidence": evidence or item.get("evidence_refs", []), "evidence_gaps": item.get("evidence_gaps", []),
        "available_certified_capabilities": capabilities, "source_candidates": item.get("source_candidates", []),
        "prior_failures": item.get("last_result") if item.get("attempt_count") else [],
        "alpha_deficiency": item.get("alpha_deficiency"),
        "required_json_keys": ["investigation_goal", "questions_to_answer", "required_capabilities", "preferred_capability", "tool_selection_reason", "source_selection_strategy", "evidence_needed", "stop_condition", "followup_policy"],
    }
    plan, call = _call(prompt, "You are the Nexus Research Investigator. Create a bounded execution plan from the supplied objective. Select only certified capabilities. Do not claim evidence or perform tool work. Return JSON only.")
    if not plan:
        return {"status": "FAILED_REAL", "reason": call.get("error") or "invalid_model_plan", "model": call.get("model"), "model_calls": call.get("model_calls", 0)}
    required = [_normalize_capability(x) for x in plan.get("required_capabilities", []) if x]
    preferred = _normalize_capability(plan.get("preferred_capability") or (required[0] if required else "WEB_ACQUISITION"))
    if preferred not in required:
        required.insert(0, preferred)
    receipt = {"schema_version": "nexus.research-ai-investigation.v1", "receipt_id": f"rai_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}", "created_at": now(), "work_id": item.get("work_id"), "objective_id": item.get("objective_id"), "parent_request_id": item.get("parent_request_id"), "model": call.get("model"), "model_calls": call.get("model_calls", 0), "plan": {**plan, "required_capabilities": required, "preferred_capability": preferred}, "certified_executors": capabilities, "status": "PLAN_CREATED"}
    receipt["receipt_path"] = _persist("plan", receipt)
    return {"status": "PASS_REAL", "plan_id": receipt["receipt_id"], "plan": receipt["plan"], "receipt_path": receipt["receipt_path"], "model": call.get("model"), "model_calls": call.get("model_calls", 0), "certified_executors": capabilities}


def route(item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    required = {_normalize_capability(x) for x in plan.get("required_capabilities", [])}
    declared = {_normalize_capability(x) for x in item.get("required_capabilities", []) if x}
    if declared:
        required = declared
        preferred = _normalize_capability(next(iter(item.get("required_capabilities")), "WEB_ACQUISITION"))
    else:
        preferred = ""
    objective_text = " ".join(str(item.get(key) or "") for key in ("question", "title", "source_type", "lane_id")).lower()
    # A capability guard prevents a model's broad fallback suggestion from
    # silently routing a YouTube/SEO objective to an unrelated web worker.
    # This does not invent a worker; it only enforces the objective's explicit
    # source-family constraint against the certification registry.
    if declared:
        pass
    elif "youtube" in objective_text or "video" in objective_text:
        required = {"YOUTUBE"}
        preferred = "YOUTUBE"
    elif "seo" in objective_text or "search engine" in objective_text:
        required = {"SEO"}
        preferred = "SEO"
    elif "last30" in objective_text or "recent customer" in objective_text or "demand signal" in objective_text:
        required = {"LAST30DAYS_DEMAND"}
        preferred = "LAST30DAYS_DEMAND"
    elif "independent" in objective_text or "public evidence" in objective_text or "cross-source" in objective_text:
        required = {"WEB_ACQUISITION"}
        preferred = "WEB_ACQUISITION"
    else:
        preferred = _normalize_capability(plan.get("preferred_capability") or "WEB_ACQUISITION")
    candidates = []
    for executor in certified_capabilities():
        if required.intersection(executor["capabilities"]):
            candidates.append(executor)
    def fit(executor: dict[str, Any]) -> tuple[int, int, str]:
        name_cap = _normalize_capability(executor.get("worker_capability"))
        return (0 if preferred in executor["capabilities"] else 1, 0 if name_cap == preferred else 1, executor.get("executor_id") or "")
    candidates.sort(key=fit)
    selected = candidates[0] if candidates else None
    return {"status": "PASS_REAL" if selected else "FAILED_REAL", "work_id": item.get("work_id"), "objective_id": item.get("objective_id"), "required_capabilities": sorted(required), "candidates_considered": candidates, "selected_executor": selected, "why_selected": f"certified executor matches preferred capability {preferred}" if selected else "no certified executor matches plan", "plan_id": plan.get("plan_id")}


def interpret(item: dict[str, Any], plan: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    prompt = {"objective": item.get("question") or item.get("title") or item.get("source_url"), "plan": plan, "worker_result": result, "required_json_keys": ["information_gain", "objective_progress", "evidence_quality", "contradictions", "remaining_gaps", "recommended_followup", "next_capability", "ready_for_alpha"]}
    judgment, call = _call(prompt, "You are the Nexus Research Investigator interpreting a worker result. Use only supplied evidence. State what was learned, what remains missing, and whether follow-up or Alpha is warranted. Return JSON only.")
    if not judgment:
        return {"status": "FAILED_REAL", "reason": call.get("error") or "invalid_model_interpretation", "model": call.get("model"), "model_calls": call.get("model_calls", 0)}
    receipt = {"schema_version": "nexus.research-ai-interpretation.v1", "receipt_id": f"rai_int_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}", "created_at": now(), "work_id": item.get("work_id"), "objective_id": item.get("objective_id"), "model": call.get("model"), "model_calls": call.get("model_calls", 0), "interpretation": judgment, "status": "INTERPRETED"}
    receipt["receipt_path"] = _persist("interpretation", receipt)
    return {"status": "PASS_REAL", **judgment, "receipt_path": receipt["receipt_path"], "model": call.get("model"), "model_calls": call.get("model_calls", 0)}
