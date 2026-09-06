"""Bounded model-backed planning, delivery, and review for safe objectives.

The model may recommend only an action supplied by the governed caller. It
cannot choose shell commands, paths, recipients, production mutations, or
external actions.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "reports/runtime/ai_workforce_receipts"
ALLOWED_ACTION = "internal.capability_verify"
PRODUCTIVE_ACTION = "internal.create_bounded_work_artifact"
ALLOWED_ACTIONS = {ALLOWED_ACTION, PRODUCTIVE_ACTION}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model() -> str:
    return os.environ.get("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")


def _json_content(result: Dict[str, Any]) -> Dict[str, Any] | None:
    content = str(result.get("content") or "").strip()
    if not content:
        return None
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


async def _completion(agent_id: str, messages: list[dict[str, str]], max_tokens: int = 300) -> Dict[str, Any]:
    # Active Operator is launched by the supervisor, not the interactive Nova
    # shell. Reuse the canonical runtime loader so provider credentials and
    # model configuration are available without printing or broadening them.
    try:
        from nexus_agent_platform.phase15.common import load_runtime_env
        load_runtime_env()
    except Exception:
        pass
    return await LlmGatewayAdapter(agent_id=agent_id).completion(
        model=_model(), messages=messages, temperature=0.2, max_tokens=max_tokens,
        timeout=30, request_timeout=30,
    )


def _call(agent_id: str, messages: list[dict[str, str]], max_tokens: int = 300) -> Dict[str, Any]:
    return asyncio.run(_completion(agent_id, messages, max_tokens=max_tokens))


def _write_receipt(receipt: Dict[str, Any]) -> str:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{receipt['receipt_id']}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def run_ai_planned_verification(finding: Dict[str, Any], executor: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """Run one real model plan, one governed executor, and one AI review."""
    started = _now()
    receipt_id = "aiwf_" + uuid.uuid4().hex
    required_action = str(finding.get("productive_action") or ALLOWED_ACTION)
    if required_action not in ALLOWED_ACTIONS:
        required_action = ALLOWED_ACTION
    objective = {
        "goal_id": finding.get("parent_goal"),
        "department": finding.get("department"),
        "question": finding.get("question"),
        "statement": finding.get("summary"),
        "authority": "INTERNAL_SAFE",
        "allowed_action": required_action,
        "success_criteria": finding.get("success_criteria", []),
        "missing_criteria": finding.get("missing_criteria", []),
        "current_evidence": finding.get("current_evidence", []),
        "current_next_action": finding.get("objective_next_action"),
        "external_actions": False,
    }
    plan_call = _call("nexus_ai_workforce_planner", [
        {"role": "system", "content": (
            "You are a bounded Nexus internal planning worker. Return JSON only with "
            "keys objective_id, next_action, rationale, completion_check, needs_human. "
            "next_action must be exactly " + required_action + ". If the action is "
            "internal.create_bounded_work_artifact, also return deliverable_type, "
            "deliverable_title, deliverable_summary, deliverable_content, evidence_refs, "
            "and recommended_next_action. Evidence refs must be copied only from "
            "the supplied current_evidence/evidence_refs; never invent sources, "
            "interviews, metrics, URLs, or findings. Do not claim completion, request shell, "
            "credentials, production changes, external messaging, or money."
        )},
        {"role": "user", "content": json.dumps(objective, sort_keys=True)},
    ])
    plan = _json_content(plan_call)
    usage = {"planning": plan_call.get("usage", {}), "review": {}}
    if plan_call.get("error") or not plan or plan.get("next_action") != required_action:
        receipt = {"schema_version": "nexus.ai-workforce-receipt.v1", "receipt_id": receipt_id,
                   "execution_mode": "REAL", "status": "FAILED", "failure_class": "INVALID_MODEL_PLAN",
                   "objective": objective, "model": plan_call.get("model", _model()),
                   "model_invocation": True, "plan": plan, "usage": usage,
                   "started_at": started, "completed_at": _now()}
        receipt["receipt_path"] = _write_receipt(receipt)
        return {"status": "FAILED", "action": "ai.plan_and_verify", "artifact_path": receipt["receipt_path"], "ai_workforce": receipt}

    executor_input = {**finding, "ai_plan": plan,
                      "question": plan.get("next_action") + ": " + str(plan.get("rationale", finding.get("question", "")))}
    execution = executor(executor_input)
    review_call = _call("nexus_ai_workforce_reviewer", [
        {"role": "system", "content": (
            "You are a bounded Nexus result reviewer. Return JSON only with keys "
            "result_quality, verified, remaining_work, pushback. Do not claim a parent "
            "goal is complete from one child result."
        )},
        {"role": "user", "content": json.dumps({"objective": objective, "plan": plan, "execution": execution}, sort_keys=True, default=str)},
    ])
    review = _json_content(review_call) or {"result_quality": "UNKNOWN", "verified": False, "remaining_work": "Review output was not valid JSON", "pushback": "MODEL_REVIEW_PARSE_FAILURE"}
    usage["review"] = review_call.get("usage", {})
    receipt = {"schema_version": "nexus.ai-workforce-receipt.v1", "receipt_id": receipt_id,
               "execution_mode": "REAL", "status": "PASS" if execution.get("status") == "PASS" else "FAILED",
               "objective": objective, "model": plan_call.get("model", _model()),
               "model_invocation": True, "model_worker": "nexus_ai_workforce",
               "plan": plan, "executor": "allowlisted:" + required_action, "execution": execution,
               "ai_review": review, "usage": usage, "remaining_work": review.get("remaining_work"),
               "started_at": started, "completed_at": _now(), "external_side_effects": False}
    receipt["receipt_path"] = _write_receipt(receipt)
    return {"status": receipt["status"], "action": "ai.plan_and_verify", "artifact_path": receipt["receipt_path"],
            "output_hash": receipt_id, "execution_mode": "REAL", "external_side_effects": False,
            "ai_model_invoked": True, "ai_plan": plan, "ai_review": review, "executor_result": execution,
            "next_action": plan.get("recommended_next_action") or plan.get("next_action"),
            "receipt_path": receipt["receipt_path"]}
