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
from nexus_agent_platform.alpha_decision_policy import apply_policy
from nexus_agent_platform.research_followups import build_followup, persist_followup


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


def _oracle_model_review(prompt: dict[str, Any], request_id: str) -> dict[str, Any]:
    """Use the existing zero-token-charge Oracle Gemma route under job governance."""
    from nexus_agent_platform.oracle_gemma_provider import generate_json

    compact_task = {
        "request_id": prompt.get("request_id"),
        "customer_need_question": prompt.get("customer_need_question"),
        "fresh_research_summary": str(prompt.get("fresh_research_summary") or "")[:800],
        "research_analysis": {
            "findings": (prompt.get("research_analysis") or {}).get("findings", [])[:2],
            "unknowns": (prompt.get("research_analysis") or {}).get("unknowns", [])[:2],
            "pricing_evidence": (prompt.get("research_analysis") or {}).get("pricing_evidence", [])[:2],
        },
        "sources": [{**row, "snippet": str(row.get("snippet") or "")[:160]}
                    for row in prompt.get("sources", [])[:3]],
        "source_refs": prompt.get("source_refs", [])[:3],
        "allowed_decisions": prompt.get("allowed_decisions", []),
        "required_json_keys": ["decision", "confidence", "reasoning_summary", "evidence_strength",
            "evidence_for", "evidence_against", "unknowns", "strengths", "weaknesses",
            "strongest_assumption", "weakest_assumption", "one_improvement", "why_interesting"],
        "review_scope": {"required": (prompt.get("review_scope") or {}).get("required", []),
                         "source_limitations": (prompt.get("review_scope") or {}).get("source_limitations", [])[:3]},
    }
    bounded_prompt = {
        "role": "Nexus Alpha evidence reviewer",
        "instructions": (
            "Review only supplied evidence. Do not invent demand, customers, revenue, or pricing. Return compact JSON "
            "with every listed key. Keep each finding brief. strengths and weaknesses must each have exactly 3 items. "
            "Include strongest_assumption, weakest_assumption, one_improvement, why_interesting, and an allowed decision."
        ),
        "task": compact_task,
    }
    result = generate_json(bounded_prompt, timeout=180)
    return {
        "provider": result["provider"],
        "model": result["model"],
        "model_calls": 1 if result.get("judgment") else 0,
        "http_status": None,
        "error": result.get("error"),
        "latency_ms": result.get("latency_ms"),
        "judgment": result.get("judgment"),
        "transport_status": result.get("status"),
    }


def review_demand_package(package: dict[str, Any], *, runtime_root: Path | None = None,
                         force_oracle: bool = False) -> dict[str, Any]:
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
        "allowed_decisions": ["QUALIFY", "TEST", "CERTIFICATION_TEST", "RESEARCH_MORE", "MONITOR", "REJECT", "NO_ACTION"],
        "required_json_keys": [
            "need", "decision", "confidence", "reasoning_summary", "evidence_strength", "evidence_for", "evidence_against", "unknowns", "hard_blockers", "soft_risks", "testable_unknowns",
            "contradictions", "deficiencies", "commercial_intent_assessment",
            "existing_solution_assessment", "monetization_paths_considered",
            "required_followup", "recommended_next_stage",
            "can_this_be_tested_safely", "can_this_be_tested_cheaply",
            "can_this_be_tested_reversibly", "can_this_teach_nexus_something",
            "hard_blocker_present", "why_certification_test_not_used",
            "strengths", "weaknesses", "strongest_assumption", "weakest_assumption",
            "one_improvement", "why_interesting",
        ],
        "review_scope": package.get("review_scope") or {},
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "You are Nexus Alpha. Review only the supplied fresh public evidence. "
                "Do not invent demand, customers, revenue, or capabilities. Separate "
                "observed evidence from inference. Do not reject merely because certainty "
                "is incomplete: identify whether a low-cost reversible internal TEST can "
                "resolve the uncertainty. Reserve rejection for hard safety/compliance, "
                "clear irrelevance, disproven claims, impossible dependencies, or no "
                "meaningful hypothesis. During BUILD_CERTIFICATION mode, include an explicit testability review; do not treat low confidence alone as a hard stop. "
                "When review_scope requests a business-model evaluation, provide exactly three evidence-grounded strengths and three weaknesses, "
                "the strongest and weakest assumptions, one improvement, and why the model is interesting. State evidence gaps plainly. "
                "Keep every string under 18 words, avoid repeating source summaries, and complete the required fields before adding detail. Return one compact JSON object only."
            )},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
        "temperature": 0.2,
        "max_tokens": 1400,
        # Use JSON mode rather than a large constrained schema. The latter
        # caused the currently available zero-cost production model to spend
        # its whole completion window on hidden reasoning and return no body.
        # Required fields remain validated below and by the receipt contract.
        "response_format": {"type": "json_object"},
    }
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model_calls = 0
    status = None
    error = None
    latency_ms = None
    judgment = None
    response_diagnostic: dict[str, Any] = {}
    if force_oracle and os.environ.get("NEXUS_REASONING_CLASS") != "OFFLINE_EXPERIMENT":
        return {"status": "FAILED", "request_id": request_id, "provider": "oracle_ollama_gemma",
            "model": "gemma3:4b", "model_calls": 0, "error": "ORACLE_GEMMA_OFFLINE_EXPERIMENT_ONLY"}
    if force_oracle:
        oracle = _oracle_model_review(prompt, request_id)
        provider = oracle["provider"]
        model = oracle["model"]
        model_calls = oracle["model_calls"]
        status = oracle["transport_status"]
        error = oracle["error"]
        latency_ms = oracle["latency_ms"]
        judgment = oracle["judgment"]
    else:
        # All Alpha judgment calls go through the existing policy-gated model
        # router. Free-tier models are selected from the existing model_routes
        # registry, checked against OpenRouter's live quota/catalog, and invoked
        # under the durable provider governor with paid fallback disabled.
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
            import model_router
            from alpha.alpha_live_research import _http_json_unchecked

            def invoke(routed_payload, token):
                ok, http_status, data, request_error, elapsed = _http_json_unchecked(
                    "POST", "https://openrouter.ai/api/v1/chat/completions",
                    {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Alpha Governed Review"},
                    routed_payload, timeout=75)
                if not ok:
                    raise RuntimeError(f"OPENROUTER_HTTP_{http_status or 'ERROR'}:{request_error or 'request_failed'}")
                return data

            route_result = model_router.execute_reasoning(agent_key="nexus_alpha", task_type="research",
                sensitivity="public_research", reasoning_class="STRONG_REASONING", payload=payload,
                operation=invoke, max_tokens=1600, purpose=f"alpha-review:{request_id}")
            data = route_result["result"]
            provider, model = route_result["provider"], route_result["model"]
            status, error, latency_ms, model_calls = 200, None, route_result["latency_ms"], 1
            try:
                message = data["choices"][0]["message"]
                text = str(message.get("content") or "")
                usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
                details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
                response_diagnostic = {"finish_reason": (data.get("choices") or [{}])[0].get("finish_reason"),
                    "refusal": str(message.get("refusal") or "")[:240],
                    "content_length": len(text), "message_keys": sorted(message.keys()),
                    "reasoning_chars": len(str(message.get("reasoning") or "")),
                    "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                    "reasoning_tokens": details.get("reasoning_tokens"), "content_excerpt": text[:1600]}
            except Exception:
                text = ""
            judgment = _json_object(text)
            if isinstance(judgment, dict) and isinstance(judgment.get("decision"), str):
                judgment["decision"] = judgment["decision"].strip().upper()
        except Exception as exc:
            provider = "openrouter"
            error = f"{type(exc).__name__}:{str(exc)[:180]}"
            status = None
            model_calls = 0
            judgment = None
    if not judgment or str(judgment.get("decision") or "").strip().upper() not in {"QUALIFY", "TEST", "CERTIFICATION_TEST", "RESEARCH_MORE", "MONITOR", "REJECT", "NO_ACTION"}:
        failure = {
            "status": "FAILED", "request_id": request_id, "provider": provider, "model": model,
            "model_calls": model_calls, "http_status": status, "error": error or "invalid_structured_review",
            "latency_ms": latency_ms,
        }
        if response_diagnostic:
            failure["response_diagnostic"] = response_diagnostic
            job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
            if job_id:
                failure_dir = Path(__file__).resolve().parents[2] / "data/runtime/alpha_model_failures"
                failure_dir.mkdir(parents=True, exist_ok=True)
                (failure_dir / f"{job_id}.json").write_text(json.dumps({
                    "job_id": job_id, "request_id": request_id, "provider": provider, "model": model,
                    "error": failure["error"], "diagnostic": response_diagnostic,
                }, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return failure

    policy = apply_policy(package, judgment)
    decision = policy["decision"]
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
        "decision": decision, "model_decision": policy["model_decision"], "status": "COMPLETE", "latency_ms": latency_ms,
        "source_refs": source_refs, "evidence_refs": source_refs,
        "model_review": {**judgment, "policy": policy},
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
        "decision": decision, "model_decision": policy["model_decision"], "confidence": judgment.get("confidence"),
        "reasoning_summary": judgment.get("reasoning_summary"),
        "evidence_strength": judgment.get("evidence_strength"),
        "contradictions": judgment.get("contradictions") or [],
        "deficiencies": judgment.get("deficiencies") or [],
        "commercial_intent_assessment": judgment.get("commercial_intent_assessment"),
        "existing_solution_assessment": judgment.get("existing_solution_assessment"),
        "monetization_paths_considered": judgment.get("monetization_paths_considered") or [],
        "required_followup": judgment.get("required_followup"),
        "recommended_next_stage": judgment.get("recommended_next_stage"),
        "why": policy["why"], "evidence_for": policy["evidence_for"], "evidence_against": policy["evidence_against"],
        "unknowns": policy["unknowns"], "hard_blockers": policy["hard_blockers"], "soft_risks": policy["soft_risks"],
        "testable_unknowns": policy["testable_unknowns"], "recommended_next_step": policy["recommended_next_step"],
        "can_this_be_tested_safely": policy["can_this_be_tested_safely"],
        "can_this_be_tested_cheaply": policy["can_this_be_tested_cheaply"],
        "can_this_be_tested_reversibly": policy["can_this_be_tested_reversibly"],
        "can_this_teach_nexus_something": policy["can_this_teach_nexus_something"],
        "hard_blocker_present": policy["hard_blocker_present"],
        "why_certification_test_not_used": policy["why_certification_test_not_used"],
        "next_owner": policy["next_owner"], "ray_policy_rules_applied": policy["ray_policy_rules_applied"],
        "evidence_refs": source_refs, "source_refs": source_refs,
        "strengths": judgment.get("strengths") or [],
        "weaknesses": judgment.get("weaknesses") or [],
        "strongest_assumption": judgment.get("strongest_assumption"),
        "weakest_assumption": judgment.get("weakest_assumption"),
        "one_improvement": judgment.get("one_improvement"),
        "why_interesting": judgment.get("why_interesting"),
        "evaluated_at": completed_at, "no_external_action": True,
    }
    persistence.append_record("alpha_evaluations", evaluation)
    if decision == "RESEARCH_MORE":
        queue = default_queue()
        # RESEARCH_MORE can be emitted again when a completed follow-up is
        # re-read or when two scheduler paths review the same package.  Keep
        # the append-only evaluations, but never create two active requests
        # for the same objective/evidence gap/source set.
        objective_key = investigation_id or finding_id
        gap_key = str(judgment.get("required_followup") or "Alpha evidence follow-up").strip().lower()
        source_key = tuple(sorted(str(value) for value in source_refs if value))
        existing = None
        for row in queue.load().get("items", []):
            if row.get("status") not in {"QUEUED", "WAITING", "IN_PROGRESS"}:
                continue
            if str(row.get("objective_id") or "") != str(objective_key):
                continue
            if not row.get("alpha_followup_required"):
                continue
            row_gap = str(row.get("title") or "").strip().lower()
            row_sources = tuple(sorted(str(value) for value in (row.get("evidence_refs") or []) if value))
            if row_gap == gap_key and row_sources == source_key:
                existing = row
                break
        if existing:
            followup = {**existing, "deduplicated": True, "duplicate_of": existing.get("work_id")}
        else:
            followup = queue.enqueue(
            work_id=f"alpha-model-followup:{evaluation['evaluation_id']}",
            work_class="ASSIGNED", priority=0, source_type="PUBLIC_WEB",
            source_id=finding_id, requested_by="alpha", parent_request_id=request_id,
            objective_id=investigation_id or finding_id, alpha_followup_required=True,
            required_capabilities=["WEB_ACQUISITION"],
            title=str(judgment.get("required_followup") or "Alpha evidence follow-up"),
            selection_reason="alpha_followup", evidence_refs=source_refs,
            # Queue fields are scalar transport fields.  The prior code put
            # the entire source_refs list into source_url, which serialized
            # as unusable/empty input and caused a retryable URL failure.
            source_url=source_refs[0] if source_refs else None,
            department_target=policy["next_owner"], research_mode=package.get("research_mode"),
            alpha_eligible=True, alpha_review_required=True, WHY_THIS_RESEARCH=policy["why"],
            TRIGGER="RESEARCH_GAP", DEPARTMENT=policy["next_owner"], PARENT_GOAL=package.get("parent_goal_id"),
            PROJECT=package.get("project_id") or package.get("objective_id"), EXPECTED_VALUE=policy["recommended_next_step"],
            )
            # The operational queue projection above is kept for backward
            # compatibility; the governed follow-up contract supplies the
            # durable owner, source classes, lineage, and return target.
            durable = build_followup(finding_id=finding_id, alpha_receipt_id=receipt_id, alpha_request_id=request_id,
                missing_evidence=policy["unknowns"], question=str(judgment.get("required_followup") or "Resolve the evidence deficiency identified by Alpha."),
                package=package, parent_goal=package.get("parent_goal_id"), project_id=package.get("project_id") or package.get("objective_id"),
                source_candidates=[{"source_type":"WEB_PAGE","source_url":ref,"source_id":f"alpha-source-{index}","title":"Existing Alpha evidence reference"} for index, ref in enumerate(source_refs)],
                work_id=followup.get("work_id"))
            persist_followup(durable)
            followup = {**followup, "research_request_id": durable["research_request_id"], "owner": durable["owner"], "fallback_sources": durable["fallback_sources"]}
        receipt["followup_work_id"] = followup.get("work_id")
        receipt["followup_priority"] = 2
        receipt["followup_deduplicated"] = bool(followup.get("deduplicated"))
    if decision in {"QUALIFY", "TEST", "CERTIFICATION_TEST"}:
        handoff_id = persistence.new_id("research_handoff")
        handoff = {
            "schema_version": "nexus.research-v2.1",
            "handoff_id": handoff_id, "finding_id": finding_id, "need_id": need_id,
            "alpha_receipt_id": receipt_id, "alpha_decision": decision,
            "target_department": str(package.get("handoff_target") or package.get("department_target") or "CLYDE_CREDIT").upper(),
            "department_target": str(package.get("handoff_target") or package.get("department_target") or "CLYDE_CREDIT").upper(),
            "reason": policy["why"],
            "department_handoff_status": "DRAFT_REVIEW_REQUIRED" if decision == "QUALIFY" else "CERTIFICATION_TEST_PROPOSED" if decision == "CERTIFICATION_TEST" else "TEST_PROPOSED",
            "expected_department_output": policy["recommended_next_step"],
            "testability_review": {key: policy[key] for key in ("can_this_be_tested_safely", "can_this_be_tested_cheaply", "can_this_be_tested_reversibly", "can_this_teach_nexus_something", "hard_blocker_present", "why_certification_test_not_used")},
            "research_package_id": package.get("research_package_id") or package.get("research_id"),
            "project_id": package.get("project_id") or package.get("objective_id") or investigation_id,
            "parent_goal_id": package.get("parent_goal_id"),
            "strategy_spec": package.get("strategy_spec"),
            "backtest_artifact": package.get("backtest_artifact"),
            "external_action_allowed": False, "source_refs": source_refs,
            "recorded_at": completed_at,
        }
        persistence.append_record("research_v2_handoffs", handoff)
        receipt["handoff_id"] = handoff_id
        receipt["handoff_status"] = handoff["department_handoff_status"]
        receipt["target_department"] = handoff["target_department"]
    root = runtime_root or Path(__file__).resolve().parents[2] / "data/runtime/alpha_research"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{receipt_id}.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "COMPLETE", "request_id": request_id, "receipt": receipt, "evaluation": evaluation, "need": need, "provider": provider, "model": model, "model_calls": 1}


def review_existing_research_artifact(*, artifact_path: Path, source_job_id: str,
                                      source_receipt_id: str, request: str,
                                      runtime_root: Path | None = None) -> dict[str, Any]:
    """Run the real Alpha model review over one completed Research receipt."""
    path = Path(artifact_path).resolve()
    root = Path(__file__).resolve().parents[2].resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return {"status": "FAILED", "error": "source_research_artifact_invalid"}
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "FAILED", "error": "source_research_artifact_unreadable"}
    output = artifact.get("output_artifact") if isinstance(artifact.get("output_artifact"), dict) else {}
    findings = output.get("findings") if isinstance(output.get("findings"), list) else []
    official = output.get("official_source_page") if isinstance(output.get("official_source_page"), dict) else {}
    sources = [{"title": row.get("title"), "url": row.get("url"), "snippet": row.get("snippet"),
                "source_type": row.get("engine"), "retrieved_at": artifact.get("completed_at")}
               for row in findings if isinstance(row, dict)]
    if official:
        sources.append({"title": official.get("title"), "url": official.get("url"),
                        "snippet": "; ".join(str(value) for value in (official.get("pricing_evidence") or []) if value),
                        "source_type": "NEXUS_RESEARCH_WEB_RETRIEVAL", "retrieved_at": official.get("retrieved_at")})
    if not sources:
        return {"status": "FAILED", "error": "source_research_artifact_has_no_evidence"}
    summary = str(output.get("executive_summary") or "")[:3000]
    package = {
        "research_id": source_job_id, "finding_id": source_job_id,
        "investigation_id": str(artifact.get("objective_id") or source_job_id),
        "query": "Microsoft Project project and resource management software business model",
        "title": "Microsoft Project business example", "summary": summary,
        "analysis": {"summary": summary, "findings": output.get("key_findings") or [],
                     "unknowns": output.get("uncertainties") or [],
                     "pricing_evidence": official.get("pricing_evidence") or []},
        "sources": sources,
        "review_scope": {"task": str(request)[:1600],
            "required": ["exactly 3 strengths", "exactly 3 weaknesses", "strongest assumption",
                         "weakest assumption", "one improvement", "one reason this model is interesting"],
            "source_research_job_id": source_job_id,
            "source_research_receipt_id": source_receipt_id,
            "source_limitations": output.get("uncertainties") or []},
    }
    result = review_demand_package(package, runtime_root=runtime_root)
    result["source_research_job_id"] = source_job_id
    result["source_research_receipt_id"] = source_receipt_id
    result["source_artifact_path"] = str(path.relative_to(root))
    return result
