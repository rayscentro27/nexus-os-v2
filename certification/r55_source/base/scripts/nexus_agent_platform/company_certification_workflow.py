"""Provider-free durable Research → Atlas → Funding certification stages.

The campaign uses an already acquired official SBA source artifact. It does not
claim customer demand or borrower eligibility from that source. Each transition
is a child durable job with a shared correlation id and an immutable local
artifact/handoff reference.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "reports/certification/whole_company/artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(ref: str) -> dict[str, Any]:
    path = (ROOT / ref).resolve() if not Path(ref).is_absolute() else Path(ref).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError("ARTIFACT_REFERENCE_OUTSIDE_CANONICAL_REPO")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ARTIFACT_CONTRACT_INVALID")
    return value


def _write(kind: str, job: Any, payload: dict[str, Any]) -> str:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(f"{job.job_id}:{kind}".encode()).hexdigest()[:24]
    path = ARTIFACT_DIR / f"{kind}_{digest}.json"
    record = {**payload, "artifact_id": f"{kind}_{digest}", "job_id": job.job_id,
              "correlation_id": job.correlation_id,
              "project_id": job.governance_context.get("project_id") or "goclear-readiness",
              "campaign_id": job.governance_context.get("campaign_id"),
              "department": job.department, "created_at": _now(),
              "receipt_id": f"receipt-pending:{job.job_id}"}
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def _handoff(kind: str, job: Any, source_ref: str, target: str,
             completed: list[str], remaining: list[str], recommendation: str,
             *, from_department: str | None = None) -> str:
    handoff_id = "handoff_" + hashlib.sha256(f"{job.job_id}:{kind}:{target}".encode()).hexdigest()[:24]
    path = ARTIFACT_DIR / f"{handoff_id}.json"
    path.write_text(json.dumps({
        "handoff_id": handoff_id,
        "project_id": job.governance_context.get("project_id") or "goclear-readiness",
        "campaign_id": job.governance_context.get("campaign_id"), "job_id": job.job_id,
        "correlation_id": job.correlation_id, "from_department": from_department or job.department,
        "to_department": target, "workflow_stage": kind, "input_artifact_ref": source_ref,
        "what_was_completed": completed, "what_remains": remaining,
        "recommendation": recommendation, "approval_state": "NOT_AUTHORIZED",
        "created_at": _now(), "receipt_id": f"receipt-pending:{job.job_id}",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def handle_job(job: Any, store: Any) -> dict[str, Any]:
    if job.governance_context.get("providers_allowed") != [] or job.governance_context.get("spend_allowed") is not False:
        raise PermissionError("CERTIFICATION_JOB_MUST_BE_PROVIDER_FREE")
    payload = _read(job.payload_ref or "")
    campaign_id = str(job.governance_context.get("campaign_id") or payload.get("campaign_id") or "")
    if not campaign_id:
        raise ValueError("CERTIFICATION_CAMPAIGN_ID_REQUIRED")
    from nexus_agent_platform.durable_jobs import create_next_job

    if job.job_type == "CERTIFICATION_RESEARCH_SYNTHESIS":
        summary = _read(payload["source_summary_ref"])
        provenance = _read(payload["source_provenance_ref"])
        source_url = provenance["references"][0]["source_url"]
        source_hash = provenance["references"][0]["content_hash"]
        if summary.get("executive_summary") is None or not source_hash:
            raise ValueError("RESEARCH_SOURCE_EVIDENCE_INCOMPLETE")
        artifact = {
            "schema_version": "nexus.company-certification-research.v1",
            "source_refs": [payload["source_summary_ref"], payload["source_provenance_ref"]],
            "source_url": source_url, "source_content_hash": source_hash,
            "source_retrieved_at": provenance["references"][0].get("retrieved_at"),
            "customer_need": "A simpler way to understand small-business funding routes is a hypothesis only; the source describes programs, not customer demand.",
            "complaint_or_pain_point": "Not established by this government source; customer interviews or behavioral evidence remain required.",
            "target_audience": "Small-business operators researching financing options (candidate audience; unvalidated).",
            "market_opportunity": "Educational navigation of official SBA funding information; opportunity is unvalidated.",
            "source_evidence_refs": [source_url], "confidence": "LOW_SOURCE_ONLY",
            "evidence_limitations": ["official program overview, not independent demand evidence", "retrieval is dated", "no borrower facts or eligibility evidence"],
            "recommended_marketing_angle": "Explain how to compare official funding paths and what information to verify.",
            "next_evidence_needed": ["customer interviews", "current program requirements", "geography and borrower profile"],
        }
        artifact_ref = _write("research", job, artifact)
        handoff_ref = _handoff("RESEARCH_TO_ATLAS", job, artifact_ref, "ATLAS",
                               ["bounded official-source synthesis", "source provenance and limits recorded"],
                               artifact["next_evidence_needed"], "Assess as an unvalidated educational opportunity; do not promote or imply demand.")
        child_payload = {"campaign_id": campaign_id, "research_artifact_ref": artifact_ref,
                         "research_handoff_ref": handoff_ref}
        child_ref = str((ARTIFACT_DIR / f"payload_atlas_{job.job_id}.json").relative_to(ROOT))
        (ROOT / child_ref).write_text(json.dumps(child_payload, sort_keys=True) + "\n", encoding="utf-8")
        child = create_next_job(store, job, department="ATLAS", job_type="CERTIFICATION_ATLAS_ANALYSIS",
                                payload_ref=child_ref, event_id=f"{campaign_id}:research-to-atlas")
        return {"status": "COMPLETED", "artifact_ref": artifact_ref, "handoff_ref": handoff_ref,
                "next_job_id": child.job_id, "source_hash": source_hash, "provider_calls": 0}

    if job.job_type == "CERTIFICATION_ATLAS_ANALYSIS":
        research = _read(payload["research_artifact_ref"])
        if research.get("confidence") != "LOW_SOURCE_ONLY":
            raise ValueError("RESEARCH_EVIDENCE_CLASSIFICATION_MISMATCH")
        atlas = {"schema_version": "nexus.company-certification-atlas.v1",
                 "research_artifact_ref": payload["research_artifact_ref"],
                 "opportunity_status": "NOT_PROMOTED_EVIDENCE_GAPS",
                 "customer_problem": "Unvalidated hypothesis; no customer complaint evidence in supplied source.",
                 "demand_evidence": "MISSING", "revenue_model": "NOT_ESTABLISHED",
                 "promotion_gates_passed": 0, "promotion_gates_required": 8,
                 "decision": "RESEARCH_REQUIRED", "next_owner": "CLYDE",
                 "no_financing_or_business_approval": True}
        artifact_ref = _write("atlas", job, atlas)
        handoff_ref = _handoff("ATLAS_TO_CLYDE", job, artifact_ref, "CLYDE",
                               ["opportunity gates evaluated", "no promotion without demand evidence"],
                               ["customer validation", "business model", "cost structure", "risk review"],
                               "Provide funding-path information only; borrower readiness and eligibility remain unknown.")
        child_ref = str((ARTIFACT_DIR / f"payload_funding_{job.job_id}.json").relative_to(ROOT))
        (ROOT / child_ref).write_text(json.dumps({"campaign_id": campaign_id, "research_artifact_ref": payload["research_artifact_ref"],
                                                  "atlas_artifact_ref": artifact_ref, "atlas_handoff_ref": handoff_ref}, sort_keys=True) + "\n", encoding="utf-8")
        child = create_next_job(store, job, department="CLYDE", job_type="CERTIFICATION_FUNDING_REVIEW",
                                payload_ref=child_ref, event_id=f"{campaign_id}:atlas-to-funding")
        return {"status": "COMPLETED", "artifact_ref": artifact_ref, "handoff_ref": handoff_ref,
                "next_job_id": child.job_id, "provider_calls": 0}

    if job.job_type == "CERTIFICATION_FUNDING_REVIEW":
        research = _read(payload["research_artifact_ref"])
        funding = {"schema_version": "nexus.company-certification-funding.v1",
                   "research_artifact_ref": payload["research_artifact_ref"],
                   "atlas_artifact_ref": payload["atlas_artifact_ref"],
                   "funding_path": "SBA_PROGRAMS_FOR_FUTURE_VERIFICATION",
                   "current_requirements_verified": False, "borrower_readiness": "UNKNOWN",
                   "eligibility_or_approval": "NOT_ASSESSED", "application_submitted": False,
                   "recommendation": "No product match until borrower profile, geography, and current requirements are verified.",
                   "evidence_refs": research["source_evidence_refs"]}
        artifact_ref = _write("funding", job, funding)
        handoff_ref = _handoff("FUNDING_TO_MARKETING", job, artifact_ref, "MARKETING",
                               ["official source summarized", "readiness and eligibility explicitly left unknown"],
                               ["validate audience need", "obtain current program terms", "obtain Ray approval before any publication"],
                               "Prepare an internal educational draft only; no application, financing claim, or spend.")
        from nexus_agent_platform.marketing_creative_workflow import _save_campaign, store_payload
        campaign = {"campaign_id": campaign_id, "project_id": "goclear-readiness", "business_id": "goclear",
                    "state": "REQUEST_RECEIVED", "source": "WHOLE_COMPANY_CERTIFICATION",
                    "workflow_stage": "RESEARCH_READY",
                    "research_ref": payload["research_artifact_ref"], "funding_ref": artifact_ref,
                    "asset_ids": [], "revision_count": 0, "approval_state": "PENDING",
                    "test_campaign": True, "correlation_id": job.correlation_id,
                    "handoff_ids": [payload["atlas_handoff_ref"], handoff_ref], "created_at": _now()}
        _save_campaign(campaign)
        strategy_payload = {"campaign_id": campaign_id, "project_id": "goclear-readiness", "business_id": "goclear",
            "target_audience": "Small-business operators researching financing options; unvalidated candidate audience",
            "problem": "Official SBA program navigation may be complex; customer demand has not been validated.",
            "offer": "An educational funding-readiness checklist with official-source links",
            "objective": "Help operators identify what to verify before exploring a funding path",
            "cta": "Review the information to gather before comparing options",
            "channels": ["INTERNAL_REVIEW"], "required_assets": ["LANDING_PAGE_COPY"],
            "brand_constraints": ["No funding guarantees", "No eligibility claims", "Internal review only"],
            "evidence_refs": [payload["research_artifact_ref"], payload["atlas_artifact_ref"], artifact_ref],
            "budget_class": "ZERO_SPEND_INTERNAL", "test_campaign": True}
        strategy_ref = store_payload(strategy_payload, payload_id="company-cert-strategy-" + campaign_id)
        child = create_next_job(store, job, department="MARKETING", job_type="MARKETING_STRATEGY",
                                payload_ref=strategy_ref, event_id=f"{campaign_id}:funding-to-marketing")
        return {"status": "COMPLETED", "artifact_ref": artifact_ref, "handoff_ref": handoff_ref,
                "next_job_id": child.job_id, "provider_calls": 0, "application_submitted": False}

    if job.job_type == "CERTIFICATION_NOVA_SUMMARY":
        from nexus_agent_platform.marketing_creative_workflow import campaign as get_campaign
        from nexus_agent_platform.marketing_creative_workflow import load_payload
        state = get_campaign(campaign_id)
        # An executive summary is read-only and must be available while a
        # campaign awaits Ray review. It cannot grant approval or publication
        # authority. Continue to reject campaigns in unrelated/closed states.
        allowed_review_states = {
            ("PENDING_RAY_APPROVAL", "PENDING_RAY_APPROVAL"),
            ("RAY_REVIEW_REQUIRED", "READY_FOR_RAY_REVIEW"),
        }
        if not state or (state.get("state"), state.get("approval_state")) not in allowed_review_states:
            raise ValueError("NOVA_SUMMARY_REQUIRES_RAY_REVIEW_STATE")
        evidence_records = []
        for ref in payload.get("source_artifacts", [])[:8]:
            try:
                record = _read(ref) if str(ref).startswith("reports/") else load_payload(str(ref))
            except (OSError, ValueError, TypeError):
                record = {}
            evidence_records.append({"artifact_ref": ref,
                                     "artifact_id": record.get("artifact_id") or record.get("strategy_id") or record.get("creative_brief_id"),
                                     "department": record.get("department"),
                                     "workflow_stage": record.get("workflow_stage"),
                                     "decision": record.get("decision") or record.get("recommendation"),
                                     "approval_state": record.get("approval_state")})
        if not evidence_records or any(not row.get("artifact_ref") for row in evidence_records):
            raise ValueError("NOVA_DURABLE_EVIDENCE_READ_REQUIRED")
        executive_summary = payload.get("executive_summary")
        if not isinstance(executive_summary, dict) or not executive_summary.get("category_decisions"):
            raise ValueError("NOVA_EXECUTIVE_SUMMARY_CONTEXT_REQUIRED")
        summary = {
            "schema_version": "nexus.company-certification-nova-summary.v1",
            "source_artifacts": evidence_records,
            "marketing_campaign_state": state.get("state"),
            "marketing_stage": state.get("workflow_stage"),
            "approval_state": state.get("approval_state"),
            "executive_summary": executive_summary,
            "recommendation": "Hold for Ray review; audience demand is unvalidated and financing eligibility is unknown.",
            "evidence_summary": "Official SBA source describes funding paths; it does not demonstrate customer demand or establish a specific borrower's eligibility.",
            "external_actions": {"publication": "BLOCKED_BY_APPROVAL", "email": "NOT_AUTHORIZED", "social": "NOT_AUTHORIZED", "spend": "NOT_AUTHORIZED", "trading": "NOT_AUTHORIZED"},
            "scheduler_authority": False,
        }
        artifact_ref = _write("nova_summary", job, summary)
        handoff_ref = _handoff("MARKETING_TO_NOVA_EXECUTIVE_SUMMARY", job, artifact_ref, "NOVA",
                               ["campaign evidence summarized", "approval boundary preserved"],
                               ["Ray review", "customer validation before public positioning"],
                               summary["recommendation"],
                               from_department="MULTI_DEPARTMENT" if payload.get("integrated_company_run") else "MARKETING")
        return {"status": "COMPLETED", "artifact_ref": artifact_ref,
                "handoff_ref": handoff_ref, "provider_calls": 0,
                "external_message_sent": False, "scheduler_authority": False}

    if job.job_type == "CERTIFICATION_TRADING_BACKTEST":
        spec_ref = "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1.json"
        data_ref = "data/runtime/wick_sequence_oanda_eurusd_h1_2026-10-06.json"
        handoff_file = ROOT / "data/governed/research_to_mercury_handoffs.jsonl"
        research_id = "wick-case-handoff-48fe6315085c"
        matching = []
        for line in handoff_file.open(encoding="utf-8"):
            try:
                candidate = json.loads(line)
            except ValueError:
                continue
            if candidate.get("research_to_mercury_handoff_id") == research_id or candidate.get("research_to_mercury_handoff_id") == "wick-case-handoff-48fe6315085c":
                matching.append(candidate)
        if not matching:
            raise ValueError("CERTIFIED_RESEARCH_TO_MERCURY_HANDOFF_MISSING")
        spec = _read(spec_ref)
        snapshot = _read(data_ref)
        if spec.get("live_trading") is not False or not snapshot.get("candles"):
            raise PermissionError("OFFLINE_TRADING_INPUT_GUARD_FAILED")
        output = ARTIFACT_DIR / f"wick_certification_backtest_{job.job_id}.json"
        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "NEXUS_WICK_EXPERIMENT_CLASS": "PRACTICE_EXPERIMENT",
               "NEXUS_WICK_LIVE_TRADING_ENABLED": "NO", "NEXUS_WICK_BROKER_ACCESS": "NO",
               "NEXUS_WICK_REPLAY_SPEC": str((ROOT / spec_ref).resolve()),
               "NEXUS_WICK_REPLAY_DATA": str((ROOT / data_ref).resolve()),
               "NEXUS_WICK_REPLAY_OUT": str(output.resolve())}
        completed = subprocess.run([sys.executable, str(ROOT / "artifacts/trading/wick_sequence_baseline_v1_replay.py")],
                                   cwd=ROOT, env=env, capture_output=True, text=True, timeout=90, check=False)
        if completed.returncode:
            raise RuntimeError(f"OFFLINE_BACKTEST_FAILED_{completed.returncode}")
        metrics = _read(str(output))
        if metrics.get("live_trading_enabled") is not False or metrics.get("broker_order_api_called") is not False:
            raise PermissionError("LIVE_OR_BROKER_PATH_DETECTED")
        artifact_ref = _write("trading", job, {
            "schema_version": "nexus.company-certification-trading.v1",
            "research_handoff_id": research_id, "research_handoff_source": "data/governed/research_to_mercury_handoffs.jsonl",
            "strategy_spec_ref": spec_ref, "backtest_data_ref": data_ref,
            "backtest_output_ref": str(output.relative_to(ROOT)),
            "instrument": metrics.get("instrument"), "timeframe": metrics.get("timeframe"),
            "trade_count": metrics.get("trade_count"), "win_rate": metrics.get("win_rate"),
            "profit_factor": metrics.get("profit_factor"), "expectancy": metrics.get("expectancy"),
            "max_drawdown_fraction": metrics.get("max_drawdown_fraction"),
            "data_limitations": metrics.get("limitations", []),
            "recommendation": "RESEARCH_ONLY; historical replay is not live or paper execution proof. Preserve LIVE_TRADING=OFF.",
            "live_trading_enabled": False, "broker_order_api_called": False,
        })
        handoff_ref = _handoff("TRADING_RESEARCH_TO_EXECUTIVE_REVIEW", job, artifact_ref, "NOVA",
                               ["existing research-to-Mercury handoff reviewed", "one deterministic offline historical replay completed"],
                               ["independent data-quality and out-of-sample validation"],
                               "Retain as research evidence only; no order authority or live-trading approval.")
        return {"status": "COMPLETED", "artifact_ref": artifact_ref, "handoff_ref": handoff_ref,
                "provider_calls": 0, "live_trading_enabled": False,
                "broker_order_api_called": False, "trade_count": metrics.get("trade_count")}

    raise ValueError("UNSUPPORTED_COMPANY_CERTIFICATION_JOB")


def record_receipt(job: Any, receipt: str, result: dict[str, Any]) -> None:
    for key in ("artifact_ref", "handoff_ref"):
        ref = result.get(key)
        if not ref:
            continue
        path = (ROOT / ref).resolve()
        if ROOT.resolve() not in path.parents or not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        record["receipt_id"] = receipt
        record["updated_at"] = _now()
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
