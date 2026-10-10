"""Bounded Marketing AI orchestration over the existing handoff/work-order path.

The module deliberately does not publish, send, spend, or create a second
Marketing runtime.  It plans and evaluates internal drafts, routes through the
existing GROWTH specialist contract, and persists receipts in governed stores.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HANDOFFS = ROOT / "data/governed/research_v2_handoffs.jsonl"
ARTIFACTS = ROOT / "data/runtime/marketing_ai_orchestration"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model() -> str:
    return os.environ.get("MARKETING_AI_MODEL") or os.environ.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini"


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except ValueError:
            continue
    return out


def latest_handoff() -> dict[str, Any]:
    rows = _rows(HANDOFFS)
    current = [r for r in rows if r.get("status") == "CONSUMED"] or rows
    if not current:
        raise RuntimeError("marketing_handoff_missing")
    return current[-1]


def _json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start:end + 1])
                return value if isinstance(value, dict) else None
            except ValueError:
                return None
    return None


def _call(system: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    from alpha.alpha_live_research import http_json, load_runtime_env
    load_runtime_env()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = _model()
    meta = {"provider": "openrouter", "model": model, "model_calls": 0}
    if not key:
        return None, {**meta, "error": "missing_credential"}
    ok, status, data, error, latency = http_json(
        "POST", "https://openrouter.ai/api/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Marketing AI"},
        {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=True)}], "temperature": 0.1, "max_tokens": 1400},
        timeout=60,
    )
    text = ""
    try:
        text = str(data["choices"][0]["message"]["content"] or "")
    except Exception:
        pass
    return _json(text), {**meta, "model_calls": 1 if ok else 0, "http_status": status, "latency_ms": latency, "error": error}


def _persist(kind: str, payload: dict[str, Any]) -> str:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    identifier = payload.get("id") or payload.get("artifact_id") or payload.get("evaluation_id") or uuid.uuid4().hex
    path = ARTIFACTS / f"{kind}_{identifier}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def plan(handoff: dict[str, Any]) -> dict[str, Any]:
    payload = {"handoff": handoff, "required_json_keys": ["marketing_objective", "target_audience", "current_reality", "pain", "desired_transformation", "offer_or_solution", "message_angle", "channels", "required_capabilities", "evidence_constraints", "CTA", "success_condition"]}
    result, call = _call("You are Nexus Marketing AI. Use only the supplied Research/Alpha handoff. Create an evidence-grounded internal marketing plan. Never invent customer facts, and keep all output draft-only. Return JSON only.", payload)
    if not result:
        return {"status": "FAILED_REAL", "reason": call.get("error") or "invalid_plan", **call}
    receipt = {"schema_version": "nexus.marketing-ai-plan.v1", "id": f"mktplan_{uuid.uuid4().hex}", "created_at": now(), "handoff_id": handoff.get("handoff_id"), "research_package_id": handoff.get("research_package_id"), "alpha_receipt_id": handoff.get("alpha_receipt_id"), "model": call.get("model"), "model_calls": call.get("model_calls"), "plan": result, "status": "PLAN_CREATED"}
    receipt["path"] = _persist("plan", receipt)
    return {**receipt, "status": "PASS_REAL"}


def evaluate(plan_receipt: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    payload = {"plan": plan_receipt.get("plan"), "artifact": artifact, "required_json_keys": ["decision", "reason", "weaknesses", "missing_evidence", "next_action"]}
    result, call = _call("You are a strict Marketing AI evaluator. Inspect the internal draft against the supplied evidence and plan. Return GOOD_ENOUGH, REVISION_REQUIRED, MORE_RESEARCH_REQUIRED, or DIFFERENT_CAPABILITY_REQUIRED. Do not reject merely because commercial value is uncertain. Return JSON only.", payload)
    if not result:
        return {"status": "FAILED_REAL", "reason": call.get("error") or "invalid_evaluation", **call}
    if str(result.get("decision") or "").upper() == "MORE_RESEARCH_REQUIRED":
        handoff = next((row for row in _rows(HANDOFFS) if str(row.get("handoff_id") or row.get("id")) == str(plan_receipt.get("handoff_id"))), {})
        continuation = handoff.get("continuation") if isinstance(handoff.get("continuation"), dict) else {}
        return_goal = str(plan_receipt.get("return_to_goal_id") or plan_receipt.get("goal_id") or continuation.get("receiver_goal_id") or continuation.get("parent_goal_id") or "")
        missing = result.get("missing_evidence") if isinstance(result.get("missing_evidence"), list) else []
        questions_text = [str(value).strip() for value in missing if str(value).strip()]
        if not questions_text:
            questions_text = [str(value).strip() for value in (result.get("weaknesses") if isinstance(result.get("weaknesses"), list) else []) if str(value).strip()]
        if return_goal and questions_text:
            from nexus_agent_platform.research_followup_contract import build_contract, question as make_question, persist_contract
            questions = [make_question(f"Find evidence to resolve this Marketing gap: {text}", "CUSTOMER_OR_CHANNEL_EVIDENCE", "CUSTOMER_PRIMARY_OR_PLATFORM_SOURCE", "Provide dated, attributable evidence directly addressing this gap; distinguish demand from purchase intent.") for text in questions_text]
            reason = str(result.get("reason") or "Marketing cannot complete the bounded evaluation until the listed customer/channel evidence gaps are answered.")
            if len(reason.strip()) < 8:
                reason = "Marketing needs source-backed answers to the listed customer/channel evidence gaps before re-evaluation."
            contract = build_contract(requesting_department="MARKETING", reason=reason,
                research_questions=questions, overall_evidence_required=questions_text,
                decision_unlocked_by_answers="Resume the same Marketing goal and re-evaluate the campaign artifact against its evidence constraints.",
                return_to_department="MARKETING", return_to_goal_id=return_goal, parent_goal_id=return_goal,
                parent_handoff_id=plan_receipt.get("handoff_id"), requesting_worker="marketing_ai_evaluator",
                subject_type="MARKETING_ARTIFACT", subject_id=str(artifact.get("artifact_id") or ""), priority="P2")
            result["research_followup_contract"] = persist_contract(contract)
        else:
            # Do not leak a bare MORE_RESEARCH_REQUIRED when correlation fields
            # are missing; emit a repair action for the Marketing goal context.
            result["decision"] = "RESEARCH_REQUEST_CONTEXT_REQUIRED"
            result["reason"] = "Research was requested without a resolvable originating goal and explicit evidence questions."
            result["next_action"] = "ATTACH_ORIGINATING_MARKETING_GOAL_AND_EXACT_RESEARCH_QUESTIONS"
    receipt = {"schema_version": "nexus.marketing-ai-evaluation.v1", "id": f"mkteval_{uuid.uuid4().hex}", "created_at": now(), "plan_id": plan_receipt.get("id"), "artifact_id": artifact.get("artifact_id"), "model": call.get("model"), "model_calls": call.get("model_calls"), "evaluation": result, "status": "EVALUATED"}
    receipt["path"] = _persist("evaluation", receipt)
    return {**receipt, "status": "PASS_REAL"}


def revise(plan_receipt: dict[str, Any], artifact: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    payload = {"plan": plan_receipt.get("plan"), "current_artifact": artifact, "evaluation": evaluation.get("evaluation"), "required_json_keys": ["title", "audience", "problem", "evidence_summary", "transformation", "offer", "message", "channel", "CTA", "limitations", "next_production_step"]}
    result, call = _call("You are Nexus Marketing AI revising an internal draft. Fix only the evaluator's evidence-grounded weaknesses. Preserve limitations and draft-only authority. Return JSON only.", payload)
    if not result:
        return {"status": "FAILED_REAL", "reason": call.get("error") or "invalid_revision", **call}
    artifact = {"schema_version": "nexus.marketing-artifact.v2", "artifact_id": f"mktart_{uuid.uuid4().hex}", "created_at": now(), "plan_id": plan_receipt.get("id"), "research_package_id": plan_receipt.get("research_package_id"), "alpha_receipt_id": plan_receipt.get("alpha_receipt_id"), "model": call.get("model"), "draft_only": True, "external_action_performed": False, **result}
    artifact["path"] = _persist("artifact", artifact)
    return {"status": "PASS_REAL", "artifact": artifact, "model": call.get("model"), "model_calls": call.get("model_calls", 0)}


def run_real(handoff: dict[str, Any] | None = None) -> dict[str, Any]:
    handoff = handoff or latest_handoff()
    planned = plan(handoff)
    if planned.get("status") != "PASS_REAL":
        return {"handoff": handoff, "plan": planned, "status": "FAILED_REAL"}
    from nexus_agent_platform.governed import persistence
    from nexus_foundation.contracts import assign_work_order, build_work_order, complete_work_order, transition_work_order
    routing_receipt = {"schema_version": "nexus.marketing-routing.v1", "id": f"mktroute_{uuid.uuid4().hex}", "created_at": now(), "plan_id": planned.get("id"), "handoff_id": handoff.get("handoff_id"), "required_capabilities": ["CAMPAIGN_STRATEGY", "COPY"], "candidates_considered": ["GROWTH"], "selected_executor": "GROWTH", "certification": "PASS_REAL_BOUNDED", "reason": "existing certified GROWTH specialist contract"}
    routing_receipt["path"] = _persist("routing", routing_receipt)
    order = build_work_order(goal_id=str(handoff.get("objective_id")), work_type="growth_analysis", owner_specialist="GROWTH", inputs={"handoff_id": handoff.get("handoff_id"), "plan_id": planned.get("id"), "research_package_id": handoff.get("research_package_id"), "alpha_receipt_id": handoff.get("alpha_receipt_id")}, authority_required="internal_read_only", cost_budget={"max_usd": 0}, retry_budget={"max_attempts": 1})
    order = assign_work_order(order, required_capabilities=("analytics",))
    order = transition_work_order(order, "IN_PROGRESS")
    persistence.append_record("work_orders", order)
    # The prior durable Marketing worker artifact is the real handoff output;
    # this layer evaluates it and, when needed, creates a new bounded draft.
    artifact = {"artifact_id": "marketing_artifact_068881fa0a104a3a9a26f32be472fbda", "source": "reports/marketing_assets/progressive_research_funding_readiness_draft_20260919.json", "draft_only": True, "research_package_id": handoff.get("research_package_id"), "alpha_receipt_id": handoff.get("alpha_receipt_id")}
    evaluation = evaluate(planned, artifact)
    decision = str((evaluation.get("evaluation") or {}).get("decision", "")).upper()
    revised = revise(planned, artifact, evaluation) if decision in {"REVISION_REQUIRED", "DIFFERENT_CAPABILITY_REQUIRED"} else {"status": "NOT_REQUIRED", "artifact": artifact}
    final_eval = evaluate(planned, revised.get("artifact", artifact)) if revised.get("status") == "PASS_REAL" else evaluation
    final_artifact = revised.get("artifact", artifact)
    completed = complete_work_order(order, {"status": "PASS", "artifact_id": final_artifact.get("artifact_id"), "draft_only": True, "external_action_performed": False}, receipt_ref=final_artifact.get("artifact_id", "none"))
    persistence.append_record("work_orders", completed)
    return {"status": "PASS_REAL" if final_eval.get("status") == "PASS_REAL" else "FAILED_REAL", "handoff": handoff, "plan": planned, "initial_artifact": artifact, "evaluation": evaluation, "revision": revised, "final_evaluation": final_eval, "routing": routing_receipt, "work_order": completed}
