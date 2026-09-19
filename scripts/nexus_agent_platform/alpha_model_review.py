"""Model-backed Alpha review over an existing bounded Research package.

This is an adapter around the existing Alpha governed stores and receipt
contract.  It does not create a second queue, provider, or decision system.
The deterministic Alpha evaluator remains a pre-check; this module adds the
model judgment required for decision-grade demand findings.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_work_queue import default_queue


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model_name() -> str:
    return (
        os.environ.get("ALPHA_OPENROUTER_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or os.environ.get("HERMES_ALPHA_MODEL")
        or "openai/gpt-4o-mini"
    )


def _json_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start : end + 1])
            return value if isinstance(value, dict) else None
        except Exception:
            return None


def _source_rows(package: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for source in (package.get("sources") or package.get("source_rows") or [])[:10]:
        if not isinstance(source, dict):
            continue
        rows.append({
            "title": source.get("title") or source.get("source_title") or source.get("name") or "Untitled source",
            "url": source.get("url") or source.get("source_url") or source.get("canonical_url") or source.get("source_ref"),
            "source_type": source.get("provider") or source.get("source_type") or source.get("source_name"),
            "snippet": (source.get("snippet") or source.get("excerpt") or source.get("summary") or source.get("description") or "")[:700],
            "retrieved_at": source.get("retrieved_at") or package.get("retrieved_at"),
        })
    return rows


def _normalize_need(judgment: dict[str, Any], package: dict[str, Any], source_refs: list[str]) -> dict[str, Any]:
    """Require a structured need even when a model returns a short string."""
    raw = judgment.get("need")
    analysis = package.get("analysis") if isinstance(package.get("analysis"), dict) else {}
    query = str(package.get("query") or package.get("title") or "").strip()
    if isinstance(raw, dict):
        need = dict(raw)
    else:
        need = {"problem": str(raw or judgment.get("reasoning_summary") or query)}
    need.setdefault("audience", "new LLC owners seeking business funding")
    need.setdefault("problem", query)
    need.setdefault("question", query)
    need.setdefault("desired_outcome", analysis.get("recommended_next_action") or judgment.get("recommended_next_stage") or "clear evidence-backed funding-readiness next step")
    need.setdefault("pain_points", judgment.get("deficiencies") or [judgment.get("reasoning_summary") or "funding requirements and denial reasons remain difficult to interpret"])
    need.setdefault("terminology_used_by_customers", [word for word in ("new LLC", "funding", "denial", "credit", "documentation") if word.lower() in query.lower()])
    need.setdefault("demand_signals", [analysis.get("summary") or judgment.get("reasoning_summary") or "Multiple current public sources address the same funding problem."])
    need.setdefault("commercial_intent", judgment.get("commercial_intent_assessment") or package.get("commercial_intent") or "UNKNOWN")
    need.setdefault("where_customers_congregate", sorted({row.get("source_type") for row in _source_rows(package) if row.get("source_type")}))
    need.setdefault("current_solutions", [judgment.get("existing_solution_assessment") or "Existing lender documentation and funding-readiness guidance"])
    need.setdefault("competitor_promises", [])
    need.setdefault("complaint_signals", judgment.get("contradictions") or [])
    need.setdefault("source_refs", source_refs)
    need.setdefault("evidence_gaps", judgment.get("deficiencies") or ["Independent conversion and outcome evidence is not yet available."])
    need.setdefault("confidence", judgment.get("confidence") or "UNKNOWN")
    need.setdefault("status", "MODEL_REVIEWED")
    need.setdefault("alpha_review_required", False)
    return need


def review_demand_package(package: dict[str, Any], *, runtime_root: Path | None = None) -> dict[str, Any]:
    """Review one fresh demand package through the configured real provider."""
    from alpha.alpha_live_research import http_json, load_runtime_env, ssl_context  # noqa: F401

    load_runtime_env()
    request_id = persistence.new_id("alpha_model_req")
    started_at = _now()
    model = _model_name()
    provider = "openrouter"
    sources = _source_rows(package)
    query = str(package.get("query") or package.get("title") or "").strip()[:1000]
    source_refs = [row.get("url") for row in sources if row.get("url")]
    prompt = {
        "request_id": request_id,
        "customer_need_question": query,
        "fresh_research_summary": package.get("summary") or package.get("analysis", {}).get("summary"),
        "research_analysis": package.get("analysis") or {},
        "sources": sources,
        "source_refs": source_refs,
        "evaluate_solution_paths": [
            "GoClear service", "affiliate", "referral", "partner", "resell",
            "white-label", "consulting", "education", "lead generation",
            "existing third-party software", "new Nexus software", "no attractive opportunity",
        ],
        "allowed_decisions": ["QUALIFY", "RESEARCH_MORE", "REJECT", "PARK"],
        "required_json_keys": [
            "need", "decision", "confidence", "reasoning_summary", "evidence_strength",
            "contradictions", "deficiencies", "commercial_intent_assessment",
            "existing_solution_assessment", "monetization_paths_considered",
            "required_followup", "recommended_next_stage",
        ],
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "You are Nexus Alpha. Review only the supplied fresh public evidence. "
                "Do not invent demand, customers, revenue, or capabilities. Separate "
                "observed evidence from inference. Return one compact JSON object only."
            )},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
        "temperature": 0.2,
        "max_tokens": 1400,
    }
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {"status": "BLOCKED", "request_id": request_id, "provider": provider, "model": model, "error": "missing_credential", "model_calls": 0}
    ok, status, data, error, latency_ms = http_json(
        "POST", "https://openrouter.ai/api/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Alpha Governed Review"},
        payload, timeout=60,
    )
    text = ""
    try:
        text = str(data["choices"][0]["message"]["content"] or "")
    except Exception:
        text = ""
    judgment = _json_object(text) if ok else None
    if not judgment or str(judgment.get("decision") or "").upper() not in {"QUALIFY", "RESEARCH_MORE", "REJECT", "PARK"}:
        return {
            "status": "FAILED", "request_id": request_id, "provider": provider, "model": model,
            "model_calls": 1 if ok else 0, "http_status": status, "error": error or "invalid_structured_review",
            "latency_ms": latency_ms,
        }

    decision = str(judgment["decision"]).upper()
    need = _normalize_need(judgment, package, source_refs)
    need_id = str(need.get("need_id") or persistence.new_id("need"))
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    # A semantic Research cluster may already map to a governed need.  Preserve
    # that identity and enrich through the existing record path rather than
    # creating a duplicate need merely because Alpha is reviewing it.
    if package.get("need_id"):
        need_record = {"need_id": str(package["need_id"]), "status": "ALPHA_REVIEWED", "updated_at": _now()}
    else:
        need_record = ResearchWorkQueue().create_need(
            audience=str(need.get("audience") or "unknown"), problem=str(need.get("problem") or query),
            question=str(need.get("question") or query), desired_outcome=str(need.get("desired_outcome") or "unknown"),
            pain_points=list(need.get("pain_points") or []), terminology=list(need.get("terminology_used_by_customers") or []),
            demand_signals=list(need.get("demand_signals") or []), commercial_intent=str(need.get("commercial_intent") or "UNKNOWN"),
            source_refs=source_refs, where_customers_congregate=list(need.get("where_customers_congregate") or []),
            existing_solutions=list(need.get("current_solutions") or []), competitor_promises=list(need.get("competitor_promises") or []),
            competitor_complaints=list(need.get("complaint_signals") or []), evidence_gaps=list(need.get("evidence_gaps") or []),
            confidence=str(need.get("confidence") or "PRELIMINARY"),
        )
    need.update(need_record)
    need_id = str(need_record.get("need_id") or need_id)
    finding_id = str(package.get("finding_id") or package.get("research_id") or persistence.new_id("finding"))
    investigation_id = str(package.get("investigation_id") or package.get("research_id") or "")
    job = {
        "schema_version": "nexus.alpha-model-review.v1",
        "research_job_id": str(package.get("research_id") or persistence.new_id("alpha_job")),
        "objective": query,
        "request_id": request_id,
        "created_at": started_at,
    }
    # Keep the existing Alpha receipt/artifact format as the canonical receipt
    # store; this call records the real model usage in its model_usage field.
    receipt_id = persistence.new_id("alpha_receipt")
    completed_at = _now()
    receipt = {
        "schema_version": "nexus.alpha-model-review-receipt.v1",
        "receipt_id": receipt_id, "request_id": request_id,
        "research_job_id": job["research_job_id"], "finding_id": finding_id,
        "need_id": need_id, "investigation_id": investigation_id or None,
        "provider": provider, "model": model, "model_calls": 1,
        "started_at": started_at, "completed_at": completed_at,
        "decision": decision, "status": "COMPLETE", "latency_ms": latency_ms,
        "source_refs": source_refs, "evidence_refs": source_refs,
        "model_review": judgment,
        "execution_performed": True, "consequential_action_performed": False,
    }
    evaluation = {
        "schema_version": "nexus.alpha-evaluation.v2",
        "evaluation_id": persistence.new_id("alpha_eval"),
        "request_id": request_id, "receipt_id": receipt_id,
        "research_item_id": finding_id, "research_id": package.get("research_id"),
        "finding_id": finding_id, "need_id": need_id,
        "investigation_id": investigation_id or None,
        "provider": provider, "model": model, "model_calls": 1,
        "decision": decision, "confidence": judgment.get("confidence"),
        "reasoning_summary": judgment.get("reasoning_summary"),
        "evidence_strength": judgment.get("evidence_strength"),
        "contradictions": judgment.get("contradictions") or [],
        "deficiencies": judgment.get("deficiencies") or [],
        "commercial_intent_assessment": judgment.get("commercial_intent_assessment"),
        "existing_solution_assessment": judgment.get("existing_solution_assessment"),
        "monetization_paths_considered": judgment.get("monetization_paths_considered") or [],
        "required_followup": judgment.get("required_followup"),
        "recommended_next_stage": judgment.get("recommended_next_stage"),
        "evidence_refs": source_refs, "source_refs": source_refs,
        "evaluated_at": completed_at, "no_external_action": True,
    }
    persistence.append_record("alpha_evaluations", evaluation)
    if decision == "RESEARCH_MORE":
        followup = default_queue().enqueue(
            work_id=f"alpha-model-followup:{evaluation['evaluation_id']}",
            work_class="ASSIGNED", priority=2, source_type="PUBLIC_WEB",
            source_id=finding_id, requested_by="alpha", parent_request_id=request_id,
            objective_id=investigation_id or finding_id, alpha_followup_required=True,
            selection_reason="alpha_followup", evidence_refs=source_refs,
            # Queue fields are scalar transport fields.  The prior code put
            # the entire source_refs list into source_url, which serialized
            # as unusable/empty input and caused a retryable URL failure.
            source_url=source_refs[0] if source_refs else None,
        )
        receipt["followup_work_id"] = followup.get("work_id")
        receipt["followup_priority"] = 2
    if decision == "QUALIFY":
        handoff_id = persistence.new_id("research_handoff")
        handoff = {
            "schema_version": "nexus.research-v2.1",
            "handoff_id": handoff_id, "finding_id": finding_id, "need_id": need_id,
            "alpha_receipt_id": receipt_id, "target_department": "CLYDE_CREDIT",
            "reason": "Model-backed Alpha qualified a funding-readiness customer need for internal review.",
            "department_handoff_status": "DRAFT_REVIEW_REQUIRED",
            "expected_department_output": "bounded funding-readiness validation brief",
            "external_action_allowed": False, "source_refs": source_refs,
            "recorded_at": completed_at,
        }
        persistence.append_record("research_v2_handoffs", handoff)
        receipt["handoff_id"] = handoff_id
        receipt["handoff_status"] = "DRAFT_REVIEW_REQUIRED"
        receipt["target_department"] = "CLYDE_CREDIT"
    root = runtime_root or Path(__file__).resolve().parents[2] / "data/runtime/alpha_research"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{receipt_id}.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "COMPLETE", "request_id": request_id, "receipt": receipt, "evaluation": evaluation, "need": need, "provider": provider, "model": model, "model_calls": 1}
