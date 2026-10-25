"""Semantic research-readiness review behind the deterministic notebook gate.

Needle checks whether the evidence package is usable by its next department.
It does not score project desirability, make Alpha decisions, or execute work.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / "data/runtime/needle_research_readiness"
RECEIPTS = ROOT / "data/governed/needle_research_readiness.jsonl"

RUBRICS = {
    "BUSINESS_CREATION_NOTEBOOK_V1": "Distinguish REQUIRED, OPTIONAL, lender/product-specific, UNVERIFIED, AVOID, DO_NOW, and CAN_WAIT. Reject unsupported universal fundability folklore. Verify truthful activity-based NAICS reasoning and qualify website/address/phone/DUNS/tradeline claims.",
    "FUNDING_TECHNIQUE_INTELLIGENCE_NOTEBOOK_V1": "Separate SOURCE CLAIM from NEXUS VERIFIED VERSION. Check product and official source identification, amount/guarantee distinction, score evidence, PG/revenue/tenure/membership/banking dependencies, fixable-gap remediation, and Clyde-facing action rule. A major unsupported claim labeled verified requires RESEARCH_MORE.",
    "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1": "Check every candidate against comparable dimensions: evidenced customer problem and demand, complaints, alternatives/competitors, pricing and revenue labels, acquisition, implementation, costs/complexity, risks and contradictions. Require a credible fast-validation path with incremental cash, launch timing, first-revenue mechanism, success/pivot signals, and what not to build before validation. Affiliate, merchandise, and content routes must be considered when relevant and must not be stated as available without evidence. Verify the package gives Business Opportunities evidence for its own decision; Needle must not rank or select the best business.",
    "FOREX_STRATEGY_MISSION_NOTEBOOK_V1": "Check instrument, timeframe, hypothesis, deterministic entry/exit/stop rules, risk, spread/slippage/news handling or explicit unknowns, data/backtest requirements, and invalidation assumptions. Never call a strategy profitable before Trading backtests it. Vague rules that cannot be implemented require RESEARCH_MORE.",
}

COMMON_RUBRIC = """Assess: objective alignment and drift; whether answers substantively answer their questions; fact/inference/unknown distinctions; evidence support for VERIFIED claims; preservation of PARTIALLY_VERIFIED, UNVERIFIED, and CONTRADICTED states; synthesis accuracy and contradiction handling; material gap visibility and supplementation relevance; whether the Action Statement follows from the evidence and exposes material dependencies; downstream usability and provenance. Do not treat absence of a published requirement as proof it is not required. Do not make the downstream business, funding, trading, or launch decision. Needle checks research readiness only; it is not Alpha and must not invoke Alpha, Trading, Business Plans, or project approval."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_input(state: dict[str, Any]) -> dict[str, Any]:
    handoff = state.get("handoff_package") or {}
    handoff_payload = handoff.get("handoff_payload") or {}
    rows = []
    for row in state.get("required_questions", []):
        if not row.get("required"):
            continue
        rows.append({key: row.get(key) for key in ("question_id", "question_text", "asked", "evidence_status", "answer_status", "source_refs", "supplementation_attempted")})
    return {key: state.get(key) for key in ("research_job_id", "research_purpose", "research_domain", "contract_id", "objective", "notebook_id") } | {
        "required_questions": rows,
        "evidence_gaps": [{key: gap.get(key) for key in ("question_id", "question_text", "evidence_status", "reviewed", "supplementation_attempted", "unresolved_note", "source_refs")} for gap in state.get("evidence_gaps", [])],
        "synthesis": str(handoff_payload.get("synthesis") or state.get("synthesis") or "")[:2500],
        "action_statement": handoff_payload.get("action_statement") or {},
        "structured_extraction": handoff_payload.get("structured_extraction") or {},
        "handoff_payload": handoff_payload,
        "provenance": handoff.get("provenance") or {
            "notebook_id": state.get("notebook_id"), "source_inventory": state.get("source_inventory", [])},
    }


def _build_prompt(state: dict[str, Any], *, deterministic_result: dict[str, Any], repair_attempt: int) -> str:
    contract_id = str(state.get("contract_id") or "")
    rubric = RUBRICS.get(contract_id)
    if not rubric:
        raise ValueError("NEEDLE_UNSUPPORTED_CONTRACT")
    next_department = {
        "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1": "BUSINESS_OPPORTUNITIES",
        "FOREX_STRATEGY_MISSION_NOTEBOOK_V1": "TRADING",
        "BUSINESS_CREATION_NOTEBOOK_V1": "BUSINESS_CREATION",
        "FUNDING_TECHNIQUE_INTELLIGENCE_NOTEBOOK_V1": "CLYDE_CREDIT",
    }[contract_id]
    payload = _compact_input(state)
    return ("You are Needle, Nexus's Research Notebook Readiness Verifier. Evaluate only semantic readiness for the declared downstream department. "
        "Mechanical completeness has already been checked; do not repeat it or alter the recorded question statuses. " + COMMON_RUBRIC + "\nDOMAIN RUBRIC: " + rubric +
        "\nReturn one JSON object only with keys: outcome (READY_FOR_DEPARTMENT or RESEARCH_MORE), reason_code, summary, "
        "affected_question_ids (array), specific_gap, requested_research_action, evidence_needed, unresolved_items_safe (boolean), "
        f"next_department. Set next_department to exactly {next_department!r}; it is a fixed workflow route, not a judgment. "
        "For READY_FOR_DEPARTMENT, reason_code may be READY; explain any important unknowns in summary and unresolved_items_safe. "
        "For RESEARCH_MORE provide a concrete repair, at least one affected existing question ID when applicable, and evidence needed. "
        "After repair_attempt=1, do not loop on an unresolvable unknown: permit readiness if it is explicitly preserved and the next department can act safely. "
        "Do not claim source verification that is absent from the package. Do not include the full notebook or invent facts.\n"
        f"DETERMINISTIC_GATE={json.dumps(deterministic_result, ensure_ascii=False)}\nREPAIR_ATTEMPT={repair_attempt}\nPACKAGE={json.dumps(payload, ensure_ascii=False)}")


def _openrouter_operation(payload: dict[str, Any], token: str) -> dict[str, Any]:
    request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
            "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Needle Research Readiness"})
    with urllib.request.urlopen(request, timeout=75) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("NEEDLE_MODEL_INVALID_RESPONSE")
    return value


def _extract_json(result: Any) -> dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("choices"), list):
        message = ((result.get("choices") or [{}])[0].get("message") or {})
        text = str(message.get("content") or "")
    else:
        text = str(result or "")
    try:
        obj = json.loads(text)
    except (TypeError, ValueError):
        match = re.search(r"\{.*\}", text, re.S)
        try:
            obj = json.loads(match.group(0)) if match else None
        except ValueError:
            obj = None
    if not isinstance(obj, dict):
        raise ValueError("NEEDLE_INVALID_STRUCTURED_RESULT")
    return obj


def _persist_artifact(receipt_id: str, prompt: str, raw_response: str, result: dict[str, Any]) -> str:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_ROOT / f"{receipt_id}.json"
    path.write_text(json.dumps({"receipt_id": receipt_id, "prompt": prompt, "response": raw_response,
        "response_sha256": hashlib.sha256(raw_response.encode()).hexdigest(), "recorded_at": _now()},
        ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def verify_readiness(state: dict[str, Any], *, deterministic_result: dict[str, Any],
                     router: Any | None = None, operation: Callable | None = None,
                     repair_attempt: int = 0) -> dict[str, Any]:
    """Run deterministic gate first, then one governed LIGHT_REASONING review."""
    if not deterministic_result.get("complete"):
        return {"status": "MECHANICAL_INCOMPLETE", "ok": False,
            "reason_code": "NOTEBOOK_COMPLETION_CONTRACT_FAILED", "verification": deterministic_result}
    prompt = _build_prompt(state, deterministic_result=deterministic_result, repair_attempt=repair_attempt)
    if router is None:
        scripts = str(ROOT / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import model_router as router  # canonical Nexus router
    payload = {"messages": [{"role": "user", "content": prompt}], "temperature": 0,
        "max_tokens": 1200, "response_format": {"type": "json_object"}}
    call = operation or _openrouter_operation
    try:
        routed = router.execute_reasoning(agent_key="nexus_needle", task_type="research_readiness",
            sensitivity="internal_strategy", reasoning_class="LIGHT_REASONING", payload=payload,
            operation=call, max_tokens=1200, timeout_seconds=90,
            purpose=f"needle-research-readiness:{state.get('research_job_id') or state.get('contract_id')}")
    except Exception as exc:
        return {"ok":False,"status":"BLOCKED","reason_code":"CANONICAL_MODEL_ROUTE_UNAVAILABLE",
            "error_type":type(exc).__name__,"error":str(exc)[:240],
            "execution_class":"LIGHT_REASONING","next_department":None,
            "notebook_id":state.get("notebook_id"),"recorded_at":_now()}
    response = routed.get("result")
    answer = _extract_json(response)
    outcome = str(answer.get("outcome") or "").upper()
    if outcome not in {"READY_FOR_DEPARTMENT", "RESEARCH_MORE"}:
        raise ValueError("NEEDLE_INVALID_OUTCOME")
    valid_ids = {str(row.get("question_id")) for row in state.get("required_questions", [])}
    affected = [str(qid) for qid in answer.get("affected_question_ids", []) if str(qid) in valid_ids]
    if outcome == "RESEARCH_MORE" and (len(str(answer.get("reason_code") or "").strip()) < 4
            or len(str(answer.get("specific_gap") or "").strip()) < 25
            or len(str(answer.get("requested_research_action") or "").strip()) < 35
            or len(str(answer.get("evidence_needed") or "").strip()) < 12):
        raise ValueError("NEEDLE_RESEARCH_MORE_REQUIRES_SPECIFIC_REPAIR")
    if outcome == "RESEARCH_MORE" and answer.get("affected_question_ids") and not affected:
        raise ValueError("NEEDLE_RESEARCH_MORE_UNKNOWN_QUESTION_ID")
    contract_next = {"BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1": "BUSINESS_OPPORTUNITIES",
        "FOREX_STRATEGY_MISSION_NOTEBOOK_V1": "TRADING", "BUSINESS_CREATION_NOTEBOOK_V1": "BUSINESS_CREATION",
        "FUNDING_TECHNIQUE_INTELLIGENCE_NOTEBOOK_V1": "CLYDE_CREDIT"}[state["contract_id"]]
    if str(answer.get("next_department") or "").upper() != contract_next:
        raise ValueError("NEEDLE_DOWNSTREAM_DEPARTMENT_MISMATCH")
    raw = str(((response.get("choices") or [{}])[0].get("message") or {}).get("content") or "") if isinstance(response, dict) else json.dumps(answer)
    receipt_id = "needle_" + uuid.uuid4().hex[:18]
    artifact_ref = _persist_artifact(receipt_id, prompt, raw, answer)
    compact = {"receipt_id": receipt_id, "status": outcome, "reason_code": str(answer.get("reason_code") or "READY")[:100],
        "summary": str(answer.get("summary") or "")[:1200], "affected_question_ids": affected,
        "specific_gap": str(answer.get("specific_gap") or "")[:800] or None,
        "requested_research_action": str(answer.get("requested_research_action") or "")[:1200] or None,
        "evidence_needed": str(answer.get("evidence_needed") or "")[:800] or None,
        "unresolved_items_safe": bool(answer.get("unresolved_items_safe")),
        "next_department": contract_next, "notebook_id": state.get("notebook_id"),
        "execution_class": "LIGHT_REASONING", "provider": routed.get("provider"), "model": routed.get("model"),
        "cost_class": routed.get("cost_class"), "latency_ms": routed.get("latency_ms"),
        "model_execution_metadata": routed.get("execution_metadata"), "artifact_ref": artifact_ref,
        "recorded_at": _now()}
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(compact, ensure_ascii=False, sort_keys=True) + "\n")
    return {"ok": outcome == "READY_FOR_DEPARTMENT", **compact, "raw_answer": answer}

