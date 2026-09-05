"""Bounded model-backed planning and review for safe internal objectives.

The model may recommend only a bounded internal verification.  It cannot
choose shell commands, paths, recipients, production mutations, or external
actions.  The caller supplies the allowlisted executor and persists the
result through the normal Active Operator receipt path.
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
    """Run one real model plan, one allowlisted executor, and one AI review."""
    started = _now()
    receipt_id = "aiwf_" + uuid.uuid4().hex
    objective = {
        "goal_id": finding.get("parent_goal"),
        "department": finding.get("department"),
        "question": finding.get("question"),
        "statement": finding.get("summary"),
        "authority": "INTERNAL_SAFE",
        "allowed_action": ALLOWED_ACTION,
        "external_actions": False,
    }
    plan_call = _call("nexus_ai_workforce_planner", [
        {"role": "system", "content": (
            "You are a bounded Nexus internal planning worker. Return JSON only with "
            "keys objective_id, next_action, rationale, completion_check, needs_human. "
            "next_action must be exactly internal.capability_verify. Do not claim completion, "
            "do not request shell, credentials, production changes, external messaging, or money."
        )},
        {"role": "user", "content": json.dumps(objective, sort_keys=True)},
    ])
    plan = _json_content(plan_call)
    usage = {"planning": plan_call.get("usage", {}), "review": {}}
    if plan_call.get("error") or not plan or plan.get("next_action") != ALLOWED_ACTION:
        receipt = {"schema_version": "nexus.ai-workforce-receipt.v1", "receipt_id": receipt_id,
                   "execution_mode": "REAL", "status": "FAILED", "failure_class": "INVALID_MODEL_PLAN",
                   "objective": objective, "model": plan_call.get("model", _model()),
                   "model_invocation": True, "plan": plan, "usage": usage,
                   "started_at": started, "completed_at": _now()}
        receipt["receipt_path"] = _write_receipt(receipt)
        return {"status": "FAILED", "action": "ai.plan_and_verify", "artifact_path": receipt["receipt_path"], "ai_workforce": receipt}

    executor_input = {**finding, "question": plan.get("next_action") + ": " + str(plan.get("rationale", finding.get("question", "")))}
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
               "plan": plan, "executor": "allowlisted:" + ALLOWED_ACTION, "execution": execution,
               "ai_review": review, "usage": usage, "remaining_work": review.get("remaining_work"),
               "started_at": started, "completed_at": _now(), "external_side_effects": False}
    receipt["receipt_path"] = _write_receipt(receipt)
    return {"status": receipt["status"], "action": "ai.plan_and_verify", "artifact_path": receipt["receipt_path"],
            "output_hash": receipt_id, "execution_mode": "REAL", "external_side_effects": False,
            "ai_model_invoked": True, "ai_plan": plan, "ai_review": review, "executor_result": execution,
            "receipt_path": receipt["receipt_path"]}
