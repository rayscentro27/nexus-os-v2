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
FINAL_ACTION = "internal.assemble_final_deliverable"
TOOL_ACTIONS = {"modal.health_probe", "modal.bounded_job", "modal.inspect_execution_controls", "research.refresh"}
ALLOWED_ACTIONS = {ALLOWED_ACTION, PRODUCTIVE_ACTION, FINAL_ACTION, *TOOL_ACTIONS}


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


def _evidence_context(refs: list[Any], limit: int = 24000) -> str:
    """Expose bounded contents of canonical evidence to the internal worker.

    Objective state historically carried only paths.  That was safe for
    reference validation but left the model unable to assemble a truthful
    deliverable.  Read only repository-relative files, cap each excerpt and
    the aggregate, and label unavailable evidence instead of guessing.
    """
    chunks: list[str] = []
    total = 0
    # Newest evidence is appended to the canonical list.  Read it first so
    # a bounded prompt does not crowd the latest artifact out with historical
    # heartbeat receipts.
    seen: set[str] = set()
    for raw in reversed(refs):
        ref = str(raw or "")
        if ref in seen:
            continue
        seen.add(ref)
        if not ref or ref.startswith(("/", "~")) or ".." in Path(ref).parts:
            continue
        path = ROOT / ref
        try:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")[:6000]
        except OSError:
            continue
        chunk = f"EVIDENCE_REF: {ref}\n{text}"
        if total + len(chunk) > limit:
            break
        chunks.append(chunk)
        total += len(chunk)
    return "\n\n".join(chunks) or "NO_READABLE_EVIDENCE_CONTENT"


def _finalization_failure_report(objective: Dict[str, Any], plan: Dict[str, Any] | None,
                                 execution: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a failed final package into criterion-level repair work."""
    plan = plan or {}
    criteria = [str(x) for x in objective.get("success_criteria") or []]
    satisfied = {str(x) for x in plan.get("criteria_satisfied") or []}
    remaining = review.get("remaining_work")
    remaining_items = [str(x) for x in remaining] if isinstance(remaining, list) else ([str(remaining)] if remaining else [])
    base_reason = str(execution.get("error") or review.get("pushback") or "Criterion evidence was not sufficient.")
    failure_class = str(execution.get("failure_class") or "INCOMPLETE_FINAL_DELIVERABLE")
    content = str(plan.get("deliverable_content") or "").strip()
    items = []
    for criterion in criteria:
        if criterion in satisfied and not remaining_items:
            continue
        matching = next((x for x in remaining_items if criterion.lower() in x.lower() or x.lower() in criterion.lower()), None)
        items.append({
            "criterion": criterion,
            "status": "SATISFIED" if criterion in satisfied and not matching else "UNSATISFIED",
            "pass_or_fail": "PASS" if criterion in satisfied and not matching else "FAIL",
            "reason": matching or ("Criterion was not listed in criteria_satisfied." if criterion not in satisfied else base_reason),
            "expected_condition": criterion,
            "observed_condition": ("Criterion listed as satisfied and present in the proposed content." if criterion in satisfied and not matching
                                    else (content[:500] if content else "No deliverable content was produced.")),
            "delta": matching or ("Criterion absent from criteria_satisfied." if criterion not in satisfied else base_reason),
            "required_repair": "internal.create_bounded_work_artifact",
            "evidence_required": f"Evidence-backed content explicitly addressing: {criterion}",
        })
    if not items and (execution.get("status") != "PASS" or review.get("verified") is not True):
        items.append({"criterion": "final package verification", "status": "UNSATISFIED", "reason": base_reason,
                      "required_repair": "internal.create_bounded_work_artifact",
                      "evidence_required": "A complete evidence-bound package and successful final review"})
    return {"failure_class": failure_class, "repairable": failure_class in {"INCOMPLETE_FINAL_DELIVERABLE", "UNSUPPORTED_EVIDENCE_REFERENCE", "INVALID_DELIVERABLE"},
            "reason": base_reason, "criteria": items, "required_repair": "internal.create_bounded_work_artifact",
            "source_action": objective.get("allowed_action"), "recorded_at": _now()}


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
        "evidence_context": _evidence_context(
            list(finding.get("current_evidence") or []) + list(finding.get("evidence_refs") or [])
        ),
        "current_next_action": finding.get("objective_next_action"),
        "rework_context": finding.get("rework_context") or {},
        "external_actions": False,
    }
    plan_call = _call("nexus_ai_workforce_planner", [
        {"role": "system", "content": (
            "You are a bounded Nexus internal planning worker. Return JSON only with "
            "keys objective_id, next_action, rationale, completion_check, needs_human. "
            "next_action must be exactly " + required_action + ". If the action is "
            "internal.create_bounded_work_artifact or internal.assemble_final_deliverable, "
            "also return deliverable_type, deliverable_title, deliverable_summary, "
            "deliverable_content, evidence_refs, criteria_satisfied, human_action, "
            "and recommended_next_action. Evidence refs must be copied only from "
            "the supplied current_evidence/evidence_refs; never invent sources, "
            "interviews, metrics, URLs, or findings. Do not claim completion, request shell, "
            "credentials, production changes, external messaging, or money. If rework_context "
            "is present, address those exact deficiencies before attempting final assembly. "
            "Use the supplied evidence_context to write substantive, evidence-grounded "
            "deliverable_content; do not return a plan describing what a future report "
            "would contain. If the context cannot support a criterion, leave it unsatisfied."
        )},
        {"role": "user", "content": json.dumps(objective, sort_keys=True)},
    ], max_tokens=900 if required_action in {FINAL_ACTION, PRODUCTIVE_ACTION} else 300)
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
    failure_report = _finalization_failure_report(objective, plan, execution, review)
    for item in failure_report.get("criteria", []):
        criterion_id = "criterion_" + __import__("hashlib").sha256(str(item.get("criterion", "")).encode()).hexdigest()[:12]
        item.update({
            "failure_id": "failure_" + __import__("hashlib").sha256((receipt_id + criterion_id).encode()).hexdigest()[:18],
            "goal_id": objective.get("goal_id"), "finalization_attempt_id": receipt_id,
            "criterion_id": criterion_id, "criterion_text": str(item.get("criterion", "")),
            "criterion_type": "success_criterion", "pass_or_fail": "FAIL",
            "missing_component": str(item.get("criterion", "")),
            "missing_information": str(item.get("delta") or item.get("reason") or ""),
            "unsupported_claims": [], "quality_gap": str(item.get("reason") or ""),
            "format_gap": "", "source_gap": "", "validation_gap": "Final reviewer did not verify the criterion.",
            "repairable_by_nexus": bool(failure_report.get("repairable")),
            "repair_strategy": "criterion_specific_repair",
            "acceptance_test": f"Final package explicitly satisfies criterion: {item.get('criterion')}",
            "blocker_type": "NEXUS_REPAIRABLE" if failure_report.get("repairable") else "UNRESOLVED_LIMITATION",
        })
    if required_action == FINAL_ACTION and execution.get("status") == "PASS":
        artifact_path = execution.get("artifact_path")
        criteria = {str(x) for x in objective.get("success_criteria") or []}
        satisfied = {str(x) for x in plan.get("criteria_satisfied") or []}
        remaining = str(review.get("remaining_work") or "").strip().lower()
        if artifact_path and criteria.issubset(satisfied) and review.get("verified") is True and remaining in {"", "none", "no remaining work", "no remaining work."}:
            try:
                path = ROOT / str(artifact_path)
                artifact = json.loads(path.read_text(encoding="utf-8"))
                artifact.update({"status": "READY_FOR_HUMAN_REVIEW", "criteria_satisfied": sorted(satisfied),
                                 "final_evaluation": {"verified": True, "result_quality": review.get("result_quality"), "pushback": review.get("pushback"), "reviewed_at": _now()},
                                 "human_action": plan.get("human_action") or "Review the internal deliverable before any external use."})
                path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                execution["finalized"] = True
            except (OSError, ValueError, TypeError):
                execution["finalized"] = False
    usage["review"] = review_call.get("usage", {})
    receipt = {"schema_version": "nexus.ai-workforce-receipt.v1", "receipt_id": receipt_id,
               "execution_mode": "REAL", "status": "PASS" if execution.get("status") == "PASS" else "FAILED",
               "objective": objective, "model": plan_call.get("model", _model()),
               "model_invocation": True, "model_worker": "nexus_ai_workforce",
               "plan": plan, "executor": "allowlisted:" + required_action, "execution": execution,
               "ai_review": review, "usage": usage, "remaining_work": review.get("remaining_work"),
               "started_at": started, "completed_at": _now(), "external_side_effects": False}
    if execution.get("status") != "PASS" or (required_action == FINAL_ACTION and not execution.get("finalized")) or review.get("verified") is not True:
        receipt["finalization_failure"] = failure_report
    receipt["receipt_path"] = _write_receipt(receipt)
    return {"status": receipt["status"], "action": "ai.plan_and_verify", "artifact_path": receipt["receipt_path"],
            "output_hash": receipt_id, "execution_mode": "REAL", "external_side_effects": False,
            "ai_model_invoked": True, "ai_plan": plan, "ai_review": review, "executor_result": execution,
            "finalization_failure": failure_report if "finalization_failure" in receipt else None,
            "next_action": plan.get("recommended_next_action") or plan.get("next_action"),
            "receipt_path": receipt["receipt_path"]}
