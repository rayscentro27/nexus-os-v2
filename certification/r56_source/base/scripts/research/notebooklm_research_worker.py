#!/usr/bin/env python3
"""NotebookLM-backed YouTube Research worker on the existing Research queue.

This module adds no new queue.  It claims from
``nexus_agent_platform.research_work_queue.ResearchWorkQueue`` - the same
priority/lease/settle machinery that already runs the supervised Research wake
- sends the claimed source through the NotebookLM adapter, persists structured
findings and provenance to Supabase, creates canonical department handoffs, and
settles the claim with a deterministic status.

Backlog items and proactive discoveries are the same objects in that queue, so
both travel this one path.  Continuation decisions (claim, retry, wait,
complete, fail, handoff) are made here in ordinary Python; the NotebookLM
answer is data until the deterministic quality gate accepts it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "scripts", ROOT / "scripts" / "research"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import research_profiles as rp  # noqa: E402
from notebooklm_research_adapter import (  # noqa: E402
    FAILURE_TAXONOMY,
    NotebookLMResearchAdapter,
    NotebookLMError,
    get_adapter,
    is_terminal,
    retry_delay_seconds,
)
from nexus_agent_platform.research_work_queue import (  # noqa: E402
    ResearchWorkQueue,
    default_queue,
    parse_time,
    utcnow,
)
from nexus_agent_platform.governed import persistence  # noqa: E402

try:
    from social import _supabase as supabase
except Exception:  # pragma: no cover
    supabase = None

try:
    from operations import nexus_handoff as handoff_store
except Exception:  # pragma: no cover
    handoff_store = None

RESULT_LOG = ROOT / "data/runtime/notebooklm_research_results.jsonl"
CHANNEL_REGISTRY_PATH = ROOT / "data/runtime/alpha_source_registry.json"
PROACTIVE_STATE_PATH = ROOT / "data/runtime/notebooklm_proactive_research.json"
TREND_SIGNAL_LOG = ROOT / "data/governed/research_trend_signals.jsonl"
GAP_OBJECTIVE_LOG = ROOT / "data/governed/notebooklm_research_gaps.jsonl"
RESEARCH_DEPARTMENT = "RESEARCH"
PROFILE_MISMATCH_RECHECK_SECONDS = 15 * 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_hash(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:32]


def _write(table: str, row: dict[str, Any], *, on_conflict: str | None = None) -> tuple[int, Any]:
    """Insert, or merge on an existing unique key so a retry is idempotent."""
    if supabase is None or not supabase.configured():
        return 0, "supabase_not_configured"
    path = f"{table}?on_conflict={on_conflict}" if on_conflict else table
    return supabase.rest("POST", path, body=[row], prefer="return=representation,resolution=merge-duplicates")


def log_result(record: dict[str, Any]) -> dict[str, Any]:
    RESULT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return record


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------


def ensure_research_notebook(notebook_title: str, *, external_notebook_id: str, pool_id: str) -> str | None:
    """Mirror one NotebookLM pool notebook into research_notebooks (additive row)."""
    if supabase is None or not supabase.configured():
        return None
    row = {
        "title": notebook_title,
        "description": f"NotebookLM pool {pool_id} mirrored for Research provenance.",
        "owner_department": RESEARCH_DEPARTMENT,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
    }
    status, body = supabase.rest("GET", f"research_notebooks?title=eq.{notebook_title}&select=id&limit=1")
    if status == 200 and isinstance(body, list) and body:
        return body[0]["id"]
    write_status, write_body = _write("research_notebooks", row)
    if write_status in {200, 201} and isinstance(write_body, list) and write_body:
        return write_body[0].get("id")
    return None


def persist_source(*, work_item: dict[str, Any], outcome: dict[str, Any],
                   research_notebook_id: str | None) -> dict[str, Any]:
    provenance = outcome.get("provenance", {})
    record = outcome.get("record", {})
    metadata = {
        "source_type": work_item.get("source_type") or "YOUTUBE_VIDEO",
        "source_id": work_item.get("source_id"),
        "video_id": provenance.get("video_id"),
        "channel": work_item.get("channel_name") or provenance.get("channel"),
        "research_profile_id": outcome.get("research_profile_id"),
        "top_level_profile": outcome.get("top_level_profile", outcome.get("research_profile_id")),
        "trading_subtype": outcome.get("trading_subtype"),
        "content_mode": outcome.get("content_mode"),
        "question_contract_id": outcome.get("question_contract_id"),
        "secondary_signals": outcome.get("secondary_signals", []),
        "claim_provenance": "VIDEO_SAYS" if str(work_item.get("source_type", "")).upper().startswith("YOUTUBE") else "SOURCE_SAYS",
        "external_verification": [],
        "channel_qualification": outcome.get("channel_qualification"),
        "notebooklm_notebook_id": provenance.get("notebook_id"),
        "notebooklm_notebook_title": provenance.get("notebook_title"),
        "notebooklm_notebook_pool": provenance.get("notebook_pool"),
        "notebooklm_source_id": provenance.get("source_id"),
        "notebooklm_source_title": provenance.get("source_title"),
        "notebooklm_conversation_id": provenance.get("conversation_id"),
        "notebooklm_profile": provenance.get("notebooklm_profile"),
        "profile_digest": provenance.get("profile_digest"),
        "prompt_sha256": provenance.get("prompt_sha256"),
        "source_scope_method": provenance.get("source_scope_method"),
        "source_added": provenance.get("source_added"),
        "source_dedupe": provenance.get("source_dedupe"),
        "source_indexed_at": provenance.get("source_indexed_at"),
        "grounding_quotes": (outcome.get("quality") or {}).get("checks", {}).get("grounding_quotes", []),
        "extraction_record": record,
        "adapter": provenance.get("adapter"),
        "adapter_version": provenance.get("adapter_version"),
        "observed_at": provenance.get("observed_at"),
    }
    row = {
        "source_type": work_item.get("source_type") or "YOUTUBE_VIDEO",
        "title": work_item.get("title") or provenance.get("source_title"),
        "url": work_item.get("source_url") or provenance.get("video_url"),
        "author": work_item.get("channel_name"),
        "published_at": work_item.get("published_at"),
        "accessed_at": _now(),
        "snippet": outcome.get("summary"),
        "why_it_matters": "; ".join(outcome.get("key_findings", [])[:3]) or None,
        "metadata": metadata,
        "created_at": _now(),
    }
    if research_notebook_id:
        row["notebook_id"] = research_notebook_id
    url = str(row.get("url") or "")
    if url:
        found_status, found_body = supabase.rest("GET", f"research_sources?url=eq.{urllib.parse.quote(url, safe='')}"
                                                                "&select=id&limit=1")
        if found_status == 200 and isinstance(found_body, list) and found_body:
            existing_id = found_body[0]["id"]
            patch_status, patch_body = supabase.rest(
                "PATCH", f"research_sources?id=eq.{existing_id}",
                body={k: v for k, v in row.items() if k != "created_at"}, prefer="return=representation",
            )
            if patch_status in {200, 204}:
                return {"status": "PERSISTED", "table": "research_sources", "supabase_source_id": existing_id,
                        "write_mode": "updated_existing", "research_notebook_id": research_notebook_id}
            return {"status": "SUPABASE_WRITE_FAILED", "table": "research_sources", "http_status": patch_status,
                    "error": str(patch_body)[:300]}
    status, body = _write("research_sources", row)
    if status not in {200, 201}:
        return {"status": "SUPABASE_WRITE_FAILED", "table": "research_sources", "http_status": status,
                "error": str(body)[:300]}
    source_id = body[0].get("id") if isinstance(body, list) and body else None
    return {"status": "PERSISTED", "table": "research_sources", "supabase_source_id": source_id,
            "write_mode": "inserted", "research_notebook_id": research_notebook_id}


def persist_finding(*, work_item: dict[str, Any], outcome: dict[str, Any],
                    research_source_id: str | None) -> dict[str, Any]:
    provenance = outcome.get("provenance", {})
    finding_id = f"nbf_{_content_hash(work_item.get('work_id'), provenance.get('source_id'))}"
    row = {
        "finding_id": finding_id,
        "research_job_id": work_item.get("work_id"),
        "created_at": _now(),
        "updated_at": _now(),
        "source_type": work_item.get("source_type") or "YOUTUBE_VIDEO",
        "source_name": work_item.get("title"),
        "source_url": work_item.get("source_url"),
        "source_channel": work_item.get("channel_name"),
        "source_date": work_item.get("published_at"),
        "raw_artifact_reference": provenance.get("notebooklm_source_id"),
        "transcript_reference": provenance.get("notebooklm_conversation_id"),
        "content_hash": _content_hash(outcome.get("record")),
        "research_mode": "NOTEBOOKLM_SOURCE_SCOPED",
        "requested_by": work_item.get("requested_by") or RESEARCH_DEPARTMENT,
        "summary": outcome.get("summary"),
        "claims": outcome.get("key_findings", []),
        "evidence": outcome.get("evidence", []),
        "unknowns": [],
        "contradictions": [],
        "followup_questions": [],
        "primary_subject": outcome.get("top_level_profile", outcome.get("research_profile_id")),
        "secondary_subjects": ([outcome.get("trading_subtype")] if outcome.get("trading_subtype") else []),
        "tags": [work_item.get("source_type") or "YOUTUBE_VIDEO", work_item.get("lane_id"), outcome.get("research_profile_id"),
                 outcome.get("trading_subtype")],
        "entities": [provenance.get("video_id"), work_item.get("source_url")],
        "classification_status": "PROFILE_ASSIGNED",
        "classification_confidence": "DETERMINISTIC",
        "relevant_departments": outcome.get("target_departments", []),
        "alpha_opinion": "NOT_REVIEWED",
        "scam_status": "UNKNOWN",
        "finding": outcome.get("summary"),
    }
    if research_source_id:
        row["raw_artifact_reference"] = research_source_id
    found_status, found_body = supabase.rest("GET", f"research_findings?finding_id=eq.{finding_id}&select=id&limit=1")
    if found_status == 200 and isinstance(found_body, list) and found_body:
        patch_status, patch_body = supabase.rest(
            "PATCH", f"research_findings?id=eq.{found_body[0]['id']}",
            body={k: v for k, v in row.items() if k != "created_at"}, prefer="return=representation",
        )
        if patch_status in {200, 204}:
            return {"status": "PERSISTED", "table": "research_findings", "finding_id": finding_id,
                    "finding_uuid": found_body[0]["id"], "write_mode": "updated_existing"}
        return {"status": "SUPABASE_WRITE_FAILED", "table": "research_findings", "http_status": patch_status,
                "error": str(patch_body)[:300], "finding_id": finding_id}
    status, body = _write("research_findings", row)
    if status not in {200, 201}:
        return {"status": "SUPABASE_WRITE_FAILED", "table": "research_findings", "http_status": status,
                "error": str(body)[:300], "finding_id": finding_id}
    finding_uuid = body[0].get("id") if isinstance(body, list) and body else None
    return {"status": "PERSISTED", "table": "research_findings", "finding_id": finding_id,
            "finding_uuid": finding_uuid, "write_mode": "inserted"}


def create_handoffs(*, work_item: dict[str, Any], outcome: dict[str, Any], finding_id: str | None,
                    finding_uuid: str | None = None) -> list[dict[str, Any]]:
    if handoff_store is None or not handoff_store.configured():
        return [{"status": "UNAVAILABLE", "reason": "HANDOFF_STORE_NOT_CONFIGURED"}]
    provenance = outcome.get("provenance", {})
    created: list[dict[str, Any]] = []
    for department in outcome.get("target_departments", []):
        payload = {
            "finding_id": finding_id,
            "research_case_id": work_item.get("research_case_id"),
            "research_profile_id": outcome.get("research_profile_id"),
            "top_level_profile": outcome.get("top_level_profile", outcome.get("research_profile_id")),
            "trading_subtype": outcome.get("trading_subtype"),
            "content_mode": outcome.get("content_mode"),
            "question_contract_id": outcome.get("question_contract_id"),
            "secondary_signals": outcome.get("secondary_signals", []),
            "claim_provenance": "VIDEO_SAYS",
            "video_url": work_item.get("source_url"),
            "video_title": work_item.get("title"),
            "channel": work_item.get("channel_name"),
            "summary": outcome.get("summary"),
            "extraction": outcome.get("record"),
            "grounding_quotes": (outcome.get("quality") or {}).get("checks", {}).get("grounding_quotes", []),
            "notebooklm_notebook_id": provenance.get("notebook_id"),
            "notebooklm_source_id": provenance.get("source_id"),
            "source_scope_method": provenance.get("source_scope_method"),
            "work_id": work_item.get("work_id"),
        }
        result = handoff_store.create_handoff(
            source_department=RESEARCH_DEPARTMENT,
            target_department=department,
            handoff_type="RESEARCH_OBSERVATION",
            topic=(work_item.get("title") or "Untitled research source")[:180],
            payload=payload,
            source_ids=[str(provenance.get("video_id") or work_item.get("source_id"))],
            artifact_refs=[str(provenance.get("notebooklm_source_id") or "")],
            logical_key=f"notebooklm:{work_item.get('work_id')}:{department}",
        )
        if result.get("created") and finding_uuid:
            handoff_store.rest("PATCH", f"nexus_department_handoffs?handoff_id=eq.{result.get('handoff_id')}",
                               body={"finding_id": finding_uuid})
        created.append({"target_department": department, **result})
    return created


# ---------------------------------------------------------------------------
# Deterministic outcome mapping
# ---------------------------------------------------------------------------


def settle_status_for(failure_code: str, attempt: int) -> tuple[str, str | None]:
    """Map one stage failure to a queue status.  Deterministic, never AI."""
    plan = FAILURE_TAXONOMY[failure_code]
    if plan["retry"] == "none" or is_terminal(failure_code, attempt):
        return "FAILED_FINAL", failure_code
    return "FAILED_RETRYABLE", failure_code


def apply_next_eligible(work_id: str, failure_code: str, attempt: int) -> str | None:
    from datetime import timedelta

    delay = retry_delay_seconds(failure_code, attempt)
    if delay <= 0:
        return None
    return (utcnow() + timedelta(seconds=delay)).isoformat()


def process_claim(*, work_item: dict[str, Any], adapter: NotebookLMResearchAdapter,
                  queue: ResearchWorkQueue | None = None) -> dict[str, Any]:
    """Run one claimed queue item end to end and settle it."""
    queue = queue or default_queue()
    work_id = str(work_item.get("work_id"))
    attempt = int(work_item.get("attempt_count") or 1)
    url = str(work_item.get("source_url") or "")
    if not url:
        result = {"status": "FAILED", "failure_code": "NOTEBOOK_SOURCE_ADD_FAILED",
                  "failure_stage": "source_add", "retry_policy": "bounded", "max_attempts": 3,
                  "error": "queue item has no source_url", "provenance": {"video_url": url}}
        return _settle_failure(queue=queue, work_item=work_item, result=result, attempt=attempt)

    description = str(work_item.get("description") or work_item.get("question") or "")
    channel = str(work_item.get("channel_name") or "")
    title = str(work_item.get("title") or "")

    # A NotebookLM request must be attached to a durable, novel Research case
    # before any notebook lookup/create call. Explicit Ray/department requests
    # can reopen an existing source for a distinct question; routine duplicates
    # are suppressed without creating a workspace.
    from research.proactive_research_memory import (canonical_result_id, known_research_identities,
        persist_state, process_discovery_result)
    candidate = {"url": url, "youtube_video_id": adapter.video_id_of(url), "title": title,
                 "source_id": work_item.get("source_id"), "content_hash": work_item.get("content_hash"),
                 "workspace_useful": True}
    case_id = str(work_item.get("research_case_id") or "")
    opportunity_context = None
    intake_new_source = False
    business_opportunity = (str(work_item.get("entry_type") or "").upper() in {"SOURCE_LED", "VENDOR_LED", "OBJECTIVE_LED", "TREND_SIGNAL_LED"}
        and (str(work_item.get("objective_family") or work_item.get("objective_type") or "").upper() in {"BUSINESS_OPPORTUNITIES", "BUSINESS_OPPORTUNITY"}
             or "BUSINESS_OPPORTUNIT" in " ".join(str(x) for x in (work_item.get("target_departments") or [] )).upper()
             or "BUSINESS_OPPORTUNIT" in str(work_item.get("request_type") or "").upper()))
    case_objective = None
    if business_opportunity:
        intake_result = _business_opportunity_source_intake(work_item=work_item,adapter=adapter,
            url=url,title=title,description=description)
        if not intake_result.get("ok"):
            failure={"status":"FAILED","failure_code":"BUSINESS_OPPORTUNITY_INTAKE_FAILED",
                "failure_stage":"feeder_intake_or_alpha_classification","retry_policy":"bounded",
                "max_attempts":2,"error":str(intake_result.get("reason") or "intake failed")[:400],
                "detail":intake_result.get("detail")}
            return _settle_failure(queue=queue,work_item=work_item,result=failure,attempt=attempt)
        if not intake_result.get("promoted"):
            settled=queue.settle(work_id,"COMPLETE",result={"disposition":"FEEDER_INTAKE_ONLY",
                "promotion_decision":intake_result.get("promotion_decision"),
                "source_role":intake_result.get("source_role"),"feeder_notebook_id":intake_result.get("feeder_notebook_id"),
                "feeder_source_id":intake_result.get("feeder_source_id"),"no_dedicated_notebook_created":True},blocker_type=None)
            return {"outcome":"FEEDER_INTAKE_ONLY","work_id":work_id,
                "queue_status":(settled or {}).get("status"),"promotion_decision":intake_result.get("promotion_decision")}
        opportunity_context=intake_result["context"]
        intake_new_source=bool(intake_result.get("source_added"))
        opportunity_id=str(intake_result.get("opportunity_id") or "")
        case_objective={"objective":str(opportunity_context.get("objective") or title or url),
            "objective_family":"BUSINESS_OPPORTUNITIES","business_or_nexus_goal":opportunity_id,
            "owner_department":"RESEARCH","primary_question":str(work_item.get("question") or
                "What actionable business opportunity intelligence does this source support?"),
            "originating_goal_id":str(work_item.get("objective_id") or work_item.get("lane_id") or work_id),
            "signal":{"entry_type":opportunity_context.get("entry_type"),"source_role":opportunity_context.get("source_role"),
                "opportunity_id":opportunity_id,"feeder_role":"INTAKE_ONLY"}}
        case_id=str(opportunity_context.get("research_case_id") or case_id or "")
    if not case_id:
        identity = canonical_result_id(candidate)
        known = known_research_identities()
        requested = str(work_item.get("requested_by") or "").upper()
        monitored_new_upload = (str(work_item.get("selection_reason") or "").startswith("monitored_channel_discovery")
                                and str(work_item.get("monitor_mode") or "NEW_CONTENT_ONLY") == "NEW_CONTENT_ONLY"
                                and bool(work_item.get("published_at")))
        monitored_new_upload = monitored_new_upload or intake_new_source
        if requested.startswith(("RAY", "DEPARTMENT")) or monitored_new_upload:
            known.discard(identity)
            known.discard("youtube:" + adapter.video_id_of(url))
        score = 0.85 if work_item.get("source_qualification") else 0.75
        decision = process_discovery_result(candidate, objective_id=str(work_item.get("objective_id") or work_item.get("lane_id") or work_id),
            objective_type=str(work_item.get("request_type") or "RESEARCH_WORK"), topic=title or description or url,
            known_ids=known, relevance=score, value=score,
            known_source=monitored_new_upload, new_information=monitored_new_upload,
            case_objective=case_objective, existing_case_id=case_id or None)
        case = decision.get("case")
        if not case or not decision.get("create_notebook_workspace"):
            settled = queue.settle(work_id, "SUPERSEDED", result={
                "disposition": "DUPLICATE_OR_LOW_VALUE_SUPPRESSED", "novelty": decision,
                "next_action": "RETURN_TO_PROACTIVE_DISCOVERY_OR_AWAIT_EXPLICIT_REQUEST",
                "notebook_created": False}, blocker_type=None)
            return {"outcome": "SUPPRESSED_BEFORE_NOTEBOOK", "work_id": work_id,
                    "queue_status": (settled or {}).get("status"), "novelty": decision}
        case_id = str(case["case_id"])
        work_item["research_case_id"] = case_id
        if opportunity_context:
            from nexus_agent_platform import business_opportunity_research_v2 as bo
            opportunity_context = bo.save_opportunity_context({**opportunity_context,
                "research_case_id":case_id,"status":"PROMOTED_TO_RESEARCH",
                "notebook_role":"DEDICATED_RESEARCH","research_director_mode":"RESEARCH_DIRECTOR"})
            from research.research_case_engine import _save as save_research_case
            case = save_research_case(case, "BUSINESS_OPPORTUNITY_CONTEXT_BOUND",
                opportunity_id=opportunity_context.get("opportunity_id"), entry_type=opportunity_context.get("entry_type"),
                source_role=opportunity_context.get("source_role"), feeder_role="INTAKE_ONLY",
                notebook_role="DEDICATED_RESEARCH", director_mode="RESEARCH_DIRECTOR")

    if business_opportunity and case_id:
        # Repair legacy/source-scoped case metadata in place so the normal
        # contract runner selects the business opportunity mission contract.
        if opportunity_context and str(opportunity_context.get("research_case_id") or "") != case_id:
            from nexus_agent_platform.business_opportunity_research_v2 import save_opportunity_context
            opportunity_context=save_opportunity_context({**opportunity_context,"research_case_id":case_id,
                "status":"PROMOTED_TO_RESEARCH","notebook_role":"DEDICATED_RESEARCH"})
        from research.research_case_engine import get_case as get_research_case, _save as save_research_case
        current_case = get_research_case(case_id)
        if current_case and opportunity_context:
            current_case = save_research_case(current_case, "BUSINESS_OPPORTUNITY_RESEARCH_CLASSIFIED",
                objective_family="BUSINESS_OPPORTUNITIES", research_purpose="MISSION_RESEARCH",
                research_domain="BUSINESS_OPPORTUNITY", opportunity_id=opportunity_context.get("opportunity_id"),
                entry_type=opportunity_context.get("entry_type"),source_role=opportunity_context.get("source_role"),
                notebook_role="DEDICATED_RESEARCH",feeder_deep_research=False)
            case_id = str(current_case.get("case_id") or case_id)

    if business_opportunity and not opportunity_context:
        from nexus_agent_platform import business_opportunity_research_v2 as bo
        opportunity_context = next((row for row in bo.load_opportunity_contexts()
            if str(row.get("research_case_id") or "") == case_id), None)
        if not opportunity_context:
            intake = bo.build_intake(title=title or description or url, objective=description or title,
                source_url=url, source_type=str(work_item.get("source_type") or "YOUTUBE_VIDEO"),
                source_id=str(work_item.get("source_id") or adapter.video_id_of(url) or ""),
                description=description,vendor_name=str(work_item.get("vendor_name") or ""),
                trend_signal=work_item.get("trend_signal") if isinstance(work_item.get("trend_signal"), dict) else None)
            prepared = bo.prepare_opportunity_intake(intake=intake, objective=title or description or url,
                original_source={"source_id":work_item.get("source_id") or adapter.video_id_of(url),
                    "title":title,"url":url,"source_class":"ORIGINAL_SOURCE_CLAIM"})
            opportunity_context = bo.save_opportunity_context({**prepared["context"],"research_case_id":case_id,
                "status":"PROMOTED_TO_RESEARCH","notebook_role":"DEDICATED_RESEARCH"})

    try:
        source_kind=str(work_item.get("source_type") or "YOUTUBE_VIDEO").upper()
        is_youtube=source_kind in {"YOUTUBE_VIDEO","YOUTUBE","VIDEO"} and bool(adapter.video_id_of(url))
        if business_opportunity and not is_youtube:
            with adapter._job_slot():
                outcome=_process_promoted_opportunity_url(work_item=work_item,adapter=adapter,case_id=case_id,
                    url=url,title=title,description=description)
        else:
            outcome = adapter.process_video(video_url=url, research_profile_id=work_item.get("research_profile_id") or "",
                                            video_title=title, video_description=description, channel=channel,
                                            research_case_id=case_id) \
                if work_item.get("research_profile_id") else _classify_then_process(adapter, url, title, description, channel,
                                                                                      research_case_id=case_id)
    except NotebookLMError as exc:
        result = {"status": "FAILED", "failure_code": exc.failure_code, "failure_stage": exc.stage,
                  "retry_policy": FAILURE_TAXONOMY[exc.failure_code]["retry"],
                  "max_attempts": FAILURE_TAXONOMY[exc.failure_code]["max_attempts"],
                  "error": str(exc)[:500], "provenance": {"video_url": url}}
        return _settle_failure(queue=queue, work_item=work_item, result=result, attempt=attempt)

    if outcome.get("status") == "PROFILE_MISMATCH":
        return _settle_profile_mismatch(queue=queue, work_item=work_item, result=outcome)
    if outcome.get("status") != "EXTRACTED":
        return _settle_failure(queue=queue, work_item=work_item, result=outcome, attempt=attempt)

    channel_qualification = _qualify_processed_channel(work_item, outcome)
    if channel_qualification:
        outcome["channel_qualification"] = channel_qualification
        outcome.setdefault("provenance", {})["channel_qualification"] = channel_qualification

    channel_qualification = _qualify_processed_channel(work_item, outcome)
    if channel_qualification:
        outcome["channel_qualification"] = channel_qualification
        outcome.setdefault("provenance", {})["channel_qualification"] = channel_qualification

    outcome.setdefault("classification", {}).setdefault("profile_id", outcome.get("research_profile_id"))
    provenance = outcome.get("provenance", {})
    if business_opportunity and opportunity_context:
        from nexus_agent_platform import business_opportunity_research_v2 as bo
        artifact_dir=ROOT/"data/runtime/business_opportunity_context/source_artifacts"
        artifact_dir.mkdir(parents=True,exist_ok=True)
        artifact_id=hashlib.sha256(f"{work_id}:{provenance.get('source_id')}".encode()).hexdigest()[:24]
        artifact_path=artifact_dir/f"{artifact_id}.json"
        artifact_path.write_text(json.dumps({"work_id":work_id,"opportunity_id":opportunity_context.get("opportunity_id"),
            "source_id":provenance.get("source_id"),"source_url":url,"notebook_id":provenance.get("notebook_id"),
            "source_claim_extraction":outcome.get("record"),"summary":outcome.get("summary"),
            "recorded_at":_now()},ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        promoted = bo.promote_to_dedicated_research({**opportunity_context,
            "research_case_id":case_id,"notebook_id":provenance.get("notebook_id"),
            "status":"RESEARCH_ACTIVE","source_role":opportunity_context.get("source_role"),
            "source_extraction_artifact":str(artifact_path.relative_to(ROOT))},
            objective=str(opportunity_context.get("objective") or title),
            original_source=opportunity_context.get("original_source"))
        outcome["business_opportunity_promotion"] = {"opportunity_id":promoted.get("opportunity_id"),
            "notebook_id":promoted.get("notebook_id"),"notebook_role":"DEDICATED_RESEARCH",
            "status":promoted.get("status")}
    research_notebook_id = ensure_research_notebook(str(provenance.get("notebook_title") or "Nexus Research"),
                                                    external_notebook_id=str(provenance.get("notebook_id")),
                                                    pool_id=str(provenance.get("notebook_pool")))

    if business_opportunity:
        # Source claims and extraction belong in the feeder/dedicated notebook
        # and local active context. Supabase receives only case control and
        # notebook/source references until Needle readiness.
        source_row={"status":"LOCAL_ONLY","table":"local_business_opportunity_context",
            "source_reference":provenance.get("source_id"),"research_notebook_id":research_notebook_id}
    else:
        source_row = persist_source(work_item=work_item, outcome=outcome, research_notebook_id=research_notebook_id)
    if source_row.get("status") != "PERSISTED":
        failure = {"status": "FAILED", "failure_code": "NOTEBOOK_PERSISTENCE_FAILED", "failure_stage": "persist",
                   "retry_policy": "bounded", "max_attempts": 3,
                   "error": f"research_sources write failed: {source_row.get('error')}",
                   "provenance": provenance}
        return _settle_failure(queue=queue, work_item=work_item, result=failure, attempt=attempt)

    finding_row = ({"status":"LOCAL_ONLY","finding_id":f"local_{_content_hash(work_id,provenance.get('source_id'))}",
        "finding_uuid":None} if business_opportunity else persist_finding(work_item=work_item,outcome=outcome,
            research_source_id=source_row.get("supabase_source_id")))
    if finding_row.get("status") != "PERSISTED":
        failure = {"status": "FAILED", "failure_code": "NOTEBOOK_PERSISTENCE_FAILED", "failure_stage": "persist",
                   "retry_policy": "bounded", "max_attempts": 3,
                   "error": f"research_findings write failed: {finding_row.get('error')}",
                   "provenance": provenance}
        return _settle_failure(queue=queue, work_item=work_item, result=failure, attempt=attempt)

    handoffs = ([] if business_opportunity else create_handoffs(work_item=work_item,outcome=outcome,
        finding_id=finding_row.get("finding_id"),finding_uuid=finding_row.get("finding_uuid")))
    handoff_failures = [row for row in handoffs if row.get("status") in {"CREATE_FAILED", "UNAVAILABLE"}]
    if handoff_failures:
        failure = {"status": "FAILED", "failure_code": "DEPARTMENT_HANDOFF_FAILED", "failure_stage": "handoff",
                   "retry_policy": "bounded", "max_attempts": 3,
                   "error": f"department handoff failed: {json.dumps(handoff_failures, default=str)[:400]}",
                   "provenance": provenance}
        return _settle_failure(queue=queue, work_item=work_item, result=failure, attempt=attempt)

    # When the queue item belongs to an objective-level case, append its source,
    # finding, and department requests to that same case. Keep the legacy
    # source-scoped receipt below for older consumers and audit history.
    if work_item.get("research_case_id"):
        try:
            from research.research_case_engine import add_source, record_finding, _save, get_case
            objective_case_id = str(work_item["research_case_id"])
            add_source(objective_case_id, {"source_id": source_row.get("supabase_source_id") or work_item.get("source_id") or url,
                "url": url, "title": title, "source_class": work_item.get("source_class") or work_item.get("source_type") or "YOUTUBE",
                "research_source_id": source_row.get("supabase_source_id"), "notebook_id": provenance.get("notebook_id"),
                "extraction_status": "EXTRACTED"})
            if not business_opportunity:
                record_finding(objective_case_id, {"finding_id": finding_row.get("finding_id"),
                    "summary": outcome.get("summary") or title, "source_id": source_row.get("supabase_source_id"),
                    "evidence_quality": (outcome.get("quality") or {}).get("evidence_quality"),
                    "notebook_id": provenance.get("notebook_id")})
            current_case = get_case(objective_case_id)
            if current_case:
                requests = list(current_case.get("department_requests") or [])
                for handoff in handoffs:
                    if handoff.get("handoff_id"):
                        requests.append({"handoff_id": handoff.get("handoff_id"),
                            "department": handoff.get("target_department"), "status": "DELIVERED",
                            "finding_id": finding_row.get("finding_id"), "recorded_at": _now()})
                _save(current_case, "SOURCE_WORKER_RESULT_ATTACHED", department_requests=requests,
                      status="DEPARTMENT_DEVELOPMENT" if handoffs else "UNDER_DEVELOPMENT",
                      next_department_action="RECEIVER_ACKNOWLEDGEMENT_REQUIRED" if handoffs else None,
                      continue_research=True)
                # Legacy cases can predate durable playbook binding. Select and
                # persist the domain playbook on the normal worker path before
                # attempting NotebookLM so an unbound case is still developed.
                if not current_case.get("notebook_playbook"):
                    try:
                        from research.notebook_playbooks import select_playbook
                        playbook = select_playbook(
                            objective_family=current_case.get("objective_family", ""),
                            owner_department=current_case.get("owner_department", ""),
                            current_goal=current_case.get("business_or_nexus_goal", ""),
                            case_context=current_case.get("objective", ""))
                        from research.research_case_engine import _save as save_case
                        save_case(current_case, "NOTEBOOK_PLAYBOOK_SELECTED_BY_NORMAL_WORKER",
                            notebook_playbook={"playbook_id": playbook["playbook_id"],
                                "case_type": playbook["case_type"], "version": playbook["version"],
                                "selection_reason": playbook.get("selection_reason", "NORMAL_WORKER_DOMAIN_MATCH"),
                                "selected_by": "NOTEBOOKLM_RESEARCH_WORKER", "selected_at": _now()},
                            status="UNDER_DEVELOPMENT", continue_research=True,
                            next_research_action="RUN_SELECTED_NOTEBOOK_PLAYBOOK")
                        current_case = get_case(objective_case_id)
                    except Exception as exc:
                        outcome["notebook_playbook_selection"] = {
                            "status": "DEFERRED", "error": type(exc).__name__}
                # Objective cases use NotebookLM as an accumulating workspace.
                # Run the governed domain playbook on the first attached source
                # and once again only when genuinely new case evidence arrives.
                # A playbook failure must not discard a successfully persisted
                # source/finding or fail the ordinary queue item.
                if current_case.get("notebook_playbook"):
                    try:
                        from research.notebook_playbook_runner import run_case_playbook
                        binding = current_case.get("notebook_playbook") or {}
                        attached_count = len(current_case.get("sources") or [])
                        previous_count = int(binding.get("last_source_count_at_run") or 0)
                        explicit_case_request = str(work_item.get("requested_by") or "").upper().startswith("RAY")
                        if explicit_case_request or not binding.get("last_run_at") or attached_count > previous_count:
                            playbook_result = run_case_playbook(objective_case_id, adapter=adapter,
                                                               source_work_id=work_id)
                            outcome["notebook_playbook"] = {
                                "status": "COMPLETED" if playbook_result.get("ok") else "DEFERRED",
                                "run_id": playbook_result.get("receipt_id"),
                                "reason": playbook_result.get("reason"),
                            }
                    except Exception as exc:
                        outcome["notebook_playbook"] = {
                            "status": "DEFERRED", "error": type(exc).__name__}
        except Exception as exc:
            # Do not lose a successful existing worker result because the
            # optional objective-case projection was unavailable.
            outcome["objective_case_projection"] = {"status": "FAILED", "error": type(exc).__name__}

    case_state = "FOLLOWUP_WINDOW" if handoffs else "CLOSE_CANDIDATE"
    persist_state({"memory_kind": "PROACTIVE_RESEARCH_CASE", "case_id": case_id,
        "objective_id": str(work_item.get("objective_id") or work_item.get("lane_id") or work_id),
        "objective_type": str(work_item.get("request_type") or "RESEARCH_WORK").upper(),
        "topic": title or description or url, "result_identity": canonical_result_id(candidate),
        "classification": "NEW_RELEVANT", "status": case_state,
        "source_id": work_item.get("source_id"), "canonical_url": url,
        "research_source_id": source_row.get("supabase_source_id"),
        "finding_id": finding_row.get("finding_id"), "handoff_ids": [row.get("handoff_id") for row in handoffs if row.get("handoff_id")],
        "notebook_id": provenance.get("notebook_id"), "notebook_scope": "RESEARCH_CASE",
        "followup_window_days": 7 if handoffs else 0,
        "close_candidate_after": None if handoffs else _now(),
        "next_action": "AWAIT_DEPARTMENT_FOLLOWUP_OR_CLOSE_CANDIDATE" if handoffs else "CLOSE_CASE_CANDIDATE"})

    persistence.append_record("research_notebooklm_findings", {
        "recorded_at": _now(), "work_id": work_id, "video_url": url,
        "research_profile_id": outcome.get("research_profile_id"),
        "notebook_id": provenance.get("notebook_id"), "source_id": provenance.get("source_id"),
        "conversation_id": provenance.get("conversation_id"), "finding_id": finding_row.get("finding_id"),
        "supabase_source_id": source_row.get("supabase_source_id"),
        "record": outcome.get("record"), "grounding_quotes":
            (outcome.get("quality") or {}).get("checks", {}).get("grounding_quotes", []),
    })

    settled = queue.settle(work_id, "COMPLETE", result={
        "processor": "notebooklm_research_adapter",
        "research_profile_id": outcome.get("research_profile_id"),
        "notebook_id": provenance.get("notebook_id"),
        "notebooklm_source_id": provenance.get("source_id"),
        "conversation_id": provenance.get("conversation_id"),
        "source_scope_method": provenance.get("source_scope_method"),
        "finding_id": finding_row.get("finding_id"),
        "supabase_source_id": source_row.get("supabase_source_id"),
        "handoff_count": len(handoffs),
        "final_status": "FULLY_PROCESSED",
        "elapsed_seconds": provenance.get("elapsed_seconds"),
        "notebook_playbook": outcome.get("notebook_playbook"),
    }, blocker_type=None)

    record = {
        "recorded_at": _now(), "work_id": work_id, "video_id": provenance.get("video_id"), "video_url": url,
        "outcome": "EXTRACTED", "research_profile_id": outcome.get("research_profile_id"),
        "record": outcome.get("record"), "summary": outcome.get("summary"),
        "grounding_quotes": (outcome.get("quality") or {}).get("checks", {}).get("grounding_quotes", []),
        "provenance": provenance, "persistence": {"source": source_row, "finding": finding_row, "handoffs": handoffs},
        "queue_status": "COMPLETE", "elapsed_seconds": provenance.get("elapsed_seconds"),
        "notebook_playbook": outcome.get("notebook_playbook"),
    }
    log_result(record)
    return record


def _classify_then_process(adapter: NotebookLMResearchAdapter, url: str, title: str,
                           description: str, channel: str, *, research_case_id: str | None = None) -> dict[str, Any]:
    from notebooklm_research_adapter import process_youtube_for_research

    return process_youtube_for_research(video_url=url, title=title, description=description, channel=channel,
                                        adapter=adapter, research_case_id=research_case_id)


def _business_opportunity_source_intake(*, work_item: dict[str, Any], adapter: NotebookLMResearchAdapter,
                                        url: str, title: str, description: str) -> dict[str, Any]:
    """Source-scope one intake turn in the configured BO feeder, then let Alpha decide promotion."""
    from nexus_agent_platform import business_opportunity_research_v2 as bo
    selection_path=ROOT/"configs/notebooklm_selected_notebooks.json"
    selected=json.loads(selection_path.read_text(encoding="utf-8"))
    feeder=next((row for row in selected.get("notebooks",[])
        if row.get("research_lane")=="business_opportunities"),None)
    if not feeder or not feeder.get("notebook_id"):
        return {"ok":False,"reason":"BUSINESS_OPPORTUNITY_FEEDER_NOT_CONFIGURED"}
    feeder_id=str(feeder["notebook_id"])
    video_id=adapter.video_id_of(url)
    with adapter._job_slot():
        sources=adapter.sources(feeder_id)
        existing=adapter.find_existing_source(sources,video_id=video_id,video_title=title)
        added=existing is None
        source=existing or adapter.add_source(feeder_id,url,video_title=title)
        source_id=str(source.get("id") or "")
        if not source_id:
            return {"ok":False,"reason":"FEEDER_SOURCE_ID_MISSING"}
        indexed=adapter.wait_for_source(feeder_id,source_id)
        prompt=("FEEDER INTAKE ONLY. Inspect only the selected YouTube source below; do not conduct deep research, "
            "do not summarize unrelated feeder sources, and do not mark creator claims as verified. Return compact JSON: "
            "source_claims, candidate_opportunity, target_customer, claimed_problem, offer_or_model, notable_price_claims, "
            "source_role, material_unknowns, extraction_confidence. Preserve uncertainty.\n"
            f"SOURCE_ID={source_id}\nSOURCE_TITLE={title[:300]}\nSOURCE_URL={url}\nDESCRIPTION={description[:1200]}")
        turn=adapter.ask_source_scoped(feeder_id,source_id,prompt)
        foreign=[str(row.get("source_id")) for row in turn.get("references",[])
            if row.get("source_id") and str(row.get("source_id"))!=source_id]
        if foreign:
            return {"ok":False,"reason":"FEEDER_INTAKE_SOURCE_CONTAMINATION","foreign_refs":foreign}
    source_claim=str(turn.get("answer") or "")[:4000]
    intake=bo.build_intake(title=title or url,objective=title or description,source_url=url,
        source_type=str(work_item.get("source_type") or "YOUTUBE_VIDEO"),
        source_id=str(work_item.get("source_id") or video_id or source_id),description=description,
        vendor_name=str(work_item.get("vendor_name") or ""),
        trend_signal=work_item.get("trend_signal") if isinstance(work_item.get("trend_signal"),dict) else None)
    contexts=bo.load_opportunity_contexts()
    candidates=[{"opportunity_id":row.get("opportunity_id"),"objective":row.get("objective"),
        "original_idea":row.get("original_idea"),"status":row.get("status")}
        for row in contexts[:12] if row.get("opportunity_id")]
    plan=bo.execute_research_director(objective=title or description or url,
        context={"entry_type":intake["entry_type"],"source_role":intake["source_role"],
            "incoming_source":{"title":title,"url":url,"source_claims":source_claim,
                "feeder_notebook_id":feeder_id,"feeder_source_id":source_id},
            "candidate_existing_opportunities":candidates,"opportunity_relationship":intake.get("opportunity_relationship")},
        findings=[{"claim":source_claim,"evidence_status":"UNVERIFIED","source_id":source_id}],
        event="SOURCE_INTAKE")
    if plan.get("status")!="PLANNED":
        return {"ok":False,"reason":"ALPHA_SOURCE_INTAKE_CLASSIFICATION_UNAVAILABLE",
            "detail":plan.get("status"),"feeder_notebook_id":feeder_id,"feeder_source_id":source_id}
    decision=dict(plan.get("intake_classification") or {})
    matched_id=decision.get("matched_opportunity_id")
    if decision.get("promotion_decision")=="PROMOTE_EXISTING" and matched_id:
        intake["matched_opportunity_id"]=matched_id
        intake["opportunity_relationship"]="MATCH_EXISTING_OPPORTUNITY"
    elif decision.get("promotion_decision")=="PROMOTE_RELATED":
        intake["opportunity_relationship"]="RELATED_BUT_DISTINCT"
        intake["related_opportunity_id"]=matched_id
        intake["matched_opportunity_id"]=None
    promotion=str(decision.get("promotion_decision") or "INTAKE_ONLY")
    if promotion not in {"PROMOTE_NEW","PROMOTE_EXISTING","PROMOTE_RELATED"}:
        return {"ok":True,"promoted":False,"promotion_decision":promotion,
            "feeder_notebook_id":feeder_id,"feeder_source_id":source_id,"source_added":added,
            "source_role":decision.get("source_role"),"relationship":decision.get("relationship"),
            "source_claims":source_claim,"research_director_plan":plan,"notebook_role":"FEEDER_INTAKE_ONLY"}
    prepared=bo.prepare_opportunity_intake(intake=intake,objective=title or description or url,
        original_source={"source_id":work_item.get("source_id") or video_id or source_id,
            "title":title,"url":url,"source_class":"ORIGINAL_SOURCE_CLAIM",
            "feeder_notebook_id":feeder_id,"feeder_source_id":source_id})
    context={**prepared["context"],"source_claims":source_claim,
        "source_role":decision.get("source_role") or intake.get("source_role"),
        "opportunity_relationship":intake.get("opportunity_relationship"),
        "related_opportunity_id":intake.get("related_opportunity_id"),
        "alpha_initial_direction":{"candidate_questions":plan.get("candidate_questions",[])[:12],
            "alternatives":plan.get("alternatives",[])[:8],
            "promotion_decision":promotion,"hypotheses_only":True},
        "status":"PROMOTED_TO_RESEARCH","notebook_role":"PENDING_DEDICATED_RESEARCH",
        "feeder_notebook_id":feeder_id,"feeder_source_id":source_id}
    context=bo.save_opportunity_context(context)
    return {"ok":True,"promoted":True,"promotion_decision":promotion,"intake":intake,
        "context":context,"opportunity_id":prepared["opportunity_id"],"feeder_notebook_id":feeder_id,
        "feeder_source_id":source_id,"source_added":added,"source_claims":source_claim,
        "research_director_plan":plan,"notebook_role":"FEEDER_INTAKE_ONLY"}


def _process_promoted_opportunity_url(*, work_item: dict[str, Any], adapter: NotebookLMResearchAdapter,
                                      case_id: str, url: str, title: str, description: str) -> dict[str, Any]:
    """Attach a promoted non-YouTube source to its case notebook and extract only that source."""
    notebook=adapter.resolve_case_notebook(case_id,title=title or f"Nexus Research Case {case_id}",max_sources=30)
    sources=adapter.sources(str(notebook["notebook_id"]))
    existing=adapter.find_existing_source(sources,video_id=None,video_title=title)
    source=existing or adapter.add_source(str(notebook["notebook_id"]),url,video_title=title or url)
    source_id=str(source.get("id") or "")
    if not source_id: raise NotebookLMError("NOTEBOOK_SOURCE_ADD_FAILED","dedicated source returned no id",stage="source_add")
    indexed=adapter.wait_for_source(str(notebook["notebook_id"]),source_id)
    prompt=("PROMOTED BUSINESS OPPORTUNITY SOURCE INTAKE. Use only this source. Extract its claims and factual content; "
        "do not treat vendor claims as verified, and do not perform the full research contract in this turn. Return compact JSON "
        "with source_claims, offer, target_customer, pricing_claims, terms, evidence_gaps, and source_role. Preserve unknowns.\n"
        f"SOURCE_ID={source_id}\nTITLE={title[:280]}\nURL={url}\nDESCRIPTION={description[:1600]}")
    turn=adapter.ask_source_scoped(str(notebook["notebook_id"]),source_id,prompt)
    refs=[str(row.get("source_id")) for row in turn.get("references",[]) if row.get("source_id")]
    if any(ref!=source_id for ref in refs):
        raise NotebookLMError("NOTEBOOK_SOURCE_CONTAMINATION","promoted source extraction cited another source",stage="ask")
    answer=str(turn.get("answer") or "")
    return {"status":"EXTRACTED","summary":answer[:1800],"record":{"source_claims":answer[:4000],
        "evidence_status":"UNVERIFIED","source_refs":[source_id]},"key_findings":[],"quality":{"evidence_quality":"UNVERIFIED"},
        "target_departments":[],"research_profile_id":"BUSINESS_OPPORTUNITY_SOURCE_INTAKE",
        "provenance":{"adapter":"notebooklm_research_adapter","adapter_version":"1.0.0",
            "research_case_id":case_id,"video_url":url,"video_id":None,"video_title":title,
            "notebook_id":notebook["notebook_id"],"notebook_title":notebook.get("title"),
            "notebook_scope":"RESEARCH_CASE","notebook_created":notebook.get("created"),
            "source_id":source_id,"source_title":indexed.get("title") or title,
            "source_added":not bool(existing),"source_dedupe":"existing_source_reused" if existing else "added_new",
            "source_indexed_at":_now(),"conversation_id":turn.get("conversation_id"),
            "source_scope_method":"NOTEBOOKLM_SOURCE_SCOPED"}}


def _settle_failure(*, queue: ResearchWorkQueue, work_item: dict[str, Any], result: dict[str, Any],
                    attempt: int) -> dict[str, Any]:
    work_id = str(work_item.get("work_id"))
    failure_code = str(result.get("failure_code") or "NOTEBOOK_ASK_FAILED")
    status, blocker = settle_status_for(failure_code, attempt)
    next_eligible = apply_next_eligible(work_id, failure_code, attempt)
    queue.settle(work_id, status, result={
        "processor": "notebooklm_research_adapter",
        "failure_code": failure_code,
        "failure_stage": result.get("failure_stage"),
        "error": result.get("error"),
        "attempt": attempt,
    }, blocker_type=blocker, next_eligible_at=next_eligible)
    record = {
        "recorded_at": _now(), "work_id": work_id, "video_url": work_item.get("source_url"),
        "outcome": "FAILED", "failure_code": failure_code, "failure_stage": result.get("failure_stage"),
        "error": result.get("error"), "attempt": attempt, "queue_status": status, "blocker_type": blocker,
        "next_eligible_at": next_eligible, "provenance": result.get("provenance", {}),
    }
    log_result(record)
    return record


def _settle_profile_mismatch(*, queue: ResearchWorkQueue, work_item: dict[str, Any],
                             result: dict[str, Any]) -> dict[str, Any]:
    """Keep an unresolved routing mismatch recoverable, never a source failure."""
    from datetime import timedelta

    work_id = str(work_item.get("work_id"))
    next_eligible = (utcnow() + timedelta(seconds=PROFILE_MISMATCH_RECHECK_SECONDS)).isoformat()
    queue.settle(work_id, "BLOCKED_EXTERNAL", result={
        "processor": "notebooklm_research_adapter",
        "routing_status": "PROFILE_MISMATCH",
        "profile_fit_history": result.get("profile_fit_history", []),
    }, blocker_type="PROFILE_MISMATCH", next_eligible_at=next_eligible)
    record = {
        "recorded_at": _now(), "work_id": work_id, "video_url": work_item.get("source_url"),
        "outcome": "PROFILE_MISMATCH", "queue_status": "BLOCKED_EXTERNAL",
        "profile_fit_history": result.get("profile_fit_history", []),
        "next_eligible_at": next_eligible, "provenance": result.get("provenance", {}),
    }
    log_result(record)
    return record


# ---------------------------------------------------------------------------
# Claim loop
# ---------------------------------------------------------------------------


def eligible_youtube_items(queue: ResearchWorkQueue, *, limit: int | None = None) -> list[dict[str, Any]]:
    from nexus_agent_platform.research_work_queue import is_claimable

    rows = [item for item in queue.load().get("items", [])
            if str(item.get("source_type", "")).upper().startswith("YOUTUBE")
            and is_claimable(item)
            and item.get("source_url")]
    rows.sort(key=lambda row: (int(row.get("priority", 50)), str(row.get("created_at", ""))))
    return rows[:limit] if limit else rows


# ---------------------------------------------------------------------------
# Proactive monitored-channel discovery (same queue, same processor)
# ---------------------------------------------------------------------------


def known_video_ids(queue: ResearchWorkQueue) -> set[str]:
    """Dedupe set covering every video identifier already in the queue."""
    seen: set[str] = set()
    for item in queue.load().get("items", []):
        url = str(item.get("source_url") or "")
        for part in re.split(r"[/?=&.\s]+", url):
            if len(part) == 11 and re.fullmatch(r"[A-Za-z0-9_-]{11}", part):
                seen.add(part)
        source_id = str(item.get("source_id") or "")
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", source_id):
            seen.add(source_id)
    # Include NotebookLM Research persistence as well as queue state so old
    # completed work cannot be re-enqueued after queue compaction.
    try:
        if supabase is not None and supabase.configured():
            status, rows = supabase.rest("GET", "research_sources?metadata->>video_id=not.is.null&select=metadata&limit=2000")
            if status == 200 and isinstance(rows, list):
                seen.update(str((row.get("metadata") or {}).get("video_id")) for row in rows
                            if (row.get("metadata") or {}).get("video_id"))
    except Exception:
        pass  # queue dedupe remains authoritative when Supabase is unavailable
    return seen


def monitored_channels(config_path: Path | None = None) -> list[dict[str, Any]]:
    """Return the authoritative enabled YouTube monitors in worker shape.

    The optional argument is retained for callers from the earlier worker
    interface.  Permanent monitoring is governed by the designated source
    registry; legacy channel configs are not allowed to widen that set.
    """
    from research.youtube_channel_registry import enabled_channels

    rows = enabled_channels()
    normalized: list[dict[str, Any]] = []
    for source in rows:
        channel_id = source.get("external_channel_id") or source.get("channel_id")
        canonical_url = source.get("canonical_url") or source.get("url")
        if not channel_id or not canonical_url:
            continue
        normalized.append({
            **source,
            "id": source.get("source_id"),
            "source_id": source.get("source_id"),
            "channel_id": channel_id,
            "url": canonical_url,
            "triage_mode": str(source.get("triage_mode") or "TRIAGE_ONLY").upper(),
        })
    return normalized


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, default=str) + "\n")


def qualify_source(*, title: str, description: str = "", attention_score: float | None = None,
                   fills_gap: bool = False, authoritative: bool = False) -> dict[str, Any]:
    """Pre-enrichment gate; category fit is intentionally not required for attention."""
    classification = rp.classify_profile(title=title, description=description)
    if attention_score is not None and attention_score >= 0.8:
        tier, reason = "QUALIFIED_RESOURCE", "HIGH_ATTENTION_SIGNAL"
    elif fills_gap or authoritative:
        tier, reason = "QUALIFIED_RESOURCE", "GAP_OR_AUTHORITATIVE_VALUE"
    elif classification["profile_id"] != rp.FALLBACK_PROFILE_ID:
        tier, reason = "QUALIFIED_RESOURCE", "STRUCTURED_PROFILE_MATCH"
    elif len((title + " " + description).strip()) >= 60:
        tier, reason = "PARTIAL_RESOURCE", "SUBSTANTIVE_UNCLASSIFIED_METADATA"
    elif len((title or "").strip()) >= 20:
        tier, reason = "WEAK_LEAD", "INSUFFICIENT_STRUCTURED_OR_ATTENTION_EVIDENCE"
    else:
        tier, reason = "REJECTED_SOURCE", "INSUFFICIENT_SOURCE_METADATA"
    return {"qualification": tier, "reason": reason,
            "classification_profile_hint": classification["profile_id"],
            "high_attention_signal": bool(attention_score is not None and attention_score >= 0.8)}


def qualify_channel(metrics: dict[str, Any]) -> dict[str, Any]:
    """Conservative channel contract; one popular upload cannot earn MONITOR."""
    recent = int(metrics.get("recent_video_count", 0) or 0)
    relevant = float(metrics.get("relevant_fraction", 0) or 0)
    original = float(metrics.get("original_fraction", 0) or 0)
    promo = float(metrics.get("promotional_density", 1) or 0)
    active_days = metrics.get("days_since_last_upload")
    repeated_value = bool(metrics.get("repeated_structured_value"))
    engagement = float(metrics.get("engagement_signal", 0) or 0)
    fit = bool(metrics.get("profile_fit"))
    if metrics.get("spam_or_deceptive"):
        decision = "REJECT"
    elif recent == 1:
        decision = "ONE_SOURCE_ONLY"
    elif recent >= 5 and active_days is not None and active_days <= 45 and relevant >= .6 and original >= .6 and promo <= .25 and repeated_value and fit:
        decision = "MONITOR"
    elif recent >= 3 and relevant >= .4 and promo <= .5 and fit:
        decision = "WATCHLIST"
    elif recent >= 2 and (relevant < .25 or original < .25 or promo > .6):
        decision = "LOW_VALUE"
    else:
        decision = "WATCHLIST"
    return {"decision": decision, "metrics": {
        "topic_consistency": relevant, "recent_activity_days": active_days,
        "publishing_frequency_recent_count": recent, "relevant_recent_fraction": relevant,
        "original_content_fraction": original, "engagement_attention_signal": engagement,
        "profile_fit": fit, "repeated_structured_research_value": repeated_value,
        "promotional_density": promo, "recent_activity_pass": active_days is not None and active_days <= 45,
    }, "requires_multiple_recent_sources": decision != "ONE_SOURCE_ONLY"}


def _registry_rows() -> list[dict[str, Any]]:
    try:
        from research.youtube_channel_registry import enabled_channels
        return enabled_channels()
    except Exception:
        return []


def _save_registry(rows: list[dict[str, Any]]) -> None:
    _atomic_json(CHANNEL_REGISTRY_PATH, rows)


def _update_channel_scan(channel_id: str, *, videos: list[dict[str, Any]], error: str | None = None,
                         persist_remote: bool = True,
                         source_snapshot: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    from research.youtube_channel_registry import enabled_channels, update_monitor_state
    registry = source_snapshot if source_snapshot is not None else enabled_channels()
    source = next((row for row in registry
                   if row.get("external_channel_id") == channel_id or row.get("source_id") == channel_id), None)
    if source is None:
        return None
    return update_monitor_state(source["source_id"], last_checked_at=_now(), last_error=error,
                               persist_remote=persist_remote)


def _qualify_processed_channel(work_item: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any] | None:
    channel_id = work_item.get("channel_id")
    if not channel_id:
        if str(work_item.get("source_url") or "").startswith(("https://youtube.com/", "https://www.youtube.com/", "https://youtu.be/")):
            return discover_new_youtube_channel(work_item, outcome)
        return None
    row = next((item for item in _registry_rows() if item.get("channel_id") == channel_id), None)
    scan_items = (row or {}).get("recent_scan_items", [])
    titles = [str(item.get("title") or "") for item in scan_items]
    if work_item.get("title") and work_item["title"] not in titles:
        titles.append(str(work_item["title"]))
    relevant = sum(1 for title in titles if rp.classify_profile(title=title)["profile_id"] != rp.FALLBACK_PROFILE_ID)
    decision = qualify_channel({
        "recent_video_count": len(titles), "relevant_fraction": relevant / max(1, len(titles)),
        "original_fraction": 0.0 if len(titles) < 5 else float((row or {}).get("original_content_fraction", 0)),
        "promotional_density": (row or {}).get("promotional_density", 1.0),
        "days_since_last_upload": (row or {}).get("days_since_last_upload"),
        "repeated_structured_value": bool(outcome.get("record")),
        "engagement_signal": (row or {}).get("engagement_signal", 0),
        "profile_fit": outcome.get("status") == "EXTRACTED",
        "spam_or_deceptive": bool((row or {}).get("spam_or_deceptive")),
    })
    if decision["decision"] == "MONITOR" and row is None:
        registry = _registry_rows()
        registry.append({"source_id": "src_" + hashlib.sha256(str(work_item.get("channel_url")).encode()).hexdigest()[:20],
                         "source_type": "YOUTUBE_CHANNEL", "channel_id": channel_id,
                         "channel_name": work_item.get("channel_name"), "channel_url": work_item.get("channel_url"),
                         "name": work_item.get("channel_name"), "monitoring_enabled": True,
                         "qualification": decision, "priority": 50,
                         "last_checked_at": _now(), "failure_count": 0})
        _save_registry(registry)
    elif row is None:
        registry = _registry_rows()
        registry.append({"source_id": "src_" + hashlib.sha256(str(work_item.get("channel_url")).encode()).hexdigest()[:20],
                         "source_type": "YOUTUBE_CHANNEL", "channel_id": channel_id,
                         "channel_name": work_item.get("channel_name"), "channel_url": work_item.get("channel_url"),
                         "name": work_item.get("channel_name"), "monitoring_enabled": False,
                         "qualification": decision, "priority": 50, "last_checked_at": _now(),
                         "failure_count": 0})
        _save_registry(registry)
    return decision


def discover_new_youtube_channel(work_item: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    """After a useful video is processed, qualify its channel using bounded public metadata only."""
    from youtube_full_pipeline import _run_ytdlp, select_channel_videos
    url = str(work_item.get("source_url") or "")
    result = _run_ytdlp(["yt-dlp", "--no-warnings", "--no-update", "--skip-download", "--no-playlist",
                         "--dump-single-json", url])
    if result.returncode != 0:
        return {"decision": "ONE_SOURCE_ONLY", "metadata_status": "UNAVAILABLE",
                "capability_gap": "public_channel_metadata_unavailable"}
    try:
        metadata = json.loads(result.stdout)
    except (TypeError, ValueError):
        return {"decision": "ONE_SOURCE_ONLY", "metadata_status": "INVALID",
                "capability_gap": "public_channel_metadata_invalid"}
    channel_id = str(metadata.get("channel_id") or metadata.get("uploader_id") or "")
    if not channel_id:
        return {"decision": "ONE_SOURCE_ONLY", "metadata_status": "MISSING_CHANNEL_ID",
                "capability_gap": "youtube_channel_id_not_exposed"}
    channel_url = str(metadata.get("channel_url") or f"https://www.youtube.com/channel/{channel_id}")
    try:
        recent = select_channel_videos(channel_url, 8)
    except Exception:
        recent = []
    titles = [str(item.get("title") or "") for item in recent]
    if work_item.get("title") and work_item["title"] not in titles:
        titles.insert(0, str(work_item["title"]))
    relevant = sum(rp.classify_profile(title=title)["profile_id"] != rp.FALLBACK_PROFILE_ID for title in titles)
    normalized = [re.sub(r"[^a-z0-9]+", " ", title.lower()).strip() for title in titles]
    original_fraction = len(set(normalized)) / max(1, len(normalized))
    promo_terms = re.compile(r"(sponsor|affiliate|discount code|use code|referral)", re.I)
    promo_fraction = sum(bool(promo_terms.search(title)) for title in titles) / max(1, len(titles))
    publish_values = [str(item.get("published_at") or "") for item in recent]
    days_since = None
    if publish_values and publish_values[0]:
        try:
            days_since = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(publish_values[0].replace("Z", "+00:00"))).days)
        except ValueError:
            pass
    queue_rows = (default_queue().load().get("items", []))
    repeat_value = sum(row.get("channel_id") == channel_id and row.get("status") == "COMPLETE"
                       for row in queue_rows) >= 2
    metrics = {"recent_video_count": len(titles), "relevant_fraction": relevant / max(1, len(titles)),
               "original_fraction": original_fraction, "promotional_density": promo_fraction,
               "days_since_last_upload": days_since,
               "engagement_signal": min(1.0, (float(metadata.get("view_count") or 0) / 1_000_000)),
               "repeated_structured_value": repeat_value, "profile_fit": outcome.get("status") == "EXTRACTED",
               "spam_or_deceptive": False}
    decision = qualify_channel(metrics)
    registry = _registry_rows()
    existing = next((row for row in registry if row.get("channel_id") == channel_id), None)
    channel_record = {"source_id": "src_" + hashlib.sha256(channel_url.encode()).hexdigest()[:20],
                      "source_type": "YOUTUBE_CHANNEL", "channel_id": channel_id,
                      "channel_name": metadata.get("channel") or metadata.get("uploader") or work_item.get("channel_name"),
                      "channel_url": channel_url, "name": metadata.get("channel") or metadata.get("uploader"),
                      "monitoring_enabled": decision["decision"] == "MONITOR",
                      "default_profile": outcome.get("research_profile_id"),
                      "default_notebook": outcome.get("provenance", {}).get("notebook_id"),
                      "target_departments": outcome.get("target_departments", []),
                      "priority": 50, "last_checked_at": _now(), "failure_count": 0,
                      "qualification": decision, "recent_scan_items": recent[:8], **metrics}
    if existing:
        existing.update(channel_record)
    else:
        registry.append(channel_record)
    _save_registry(registry)
    return decision


def discover_open_trends(*, limit: int = 12, queue: ResearchWorkQueue | None = None) -> dict[str, Any]:
    """Retired legacy trend scan; retained as an explicit non-running shim."""
    return {"status": "LEGACY_SOURCE_NOT_ELIGIBLE_FOR_NORMAL_SELECTION",
            "queries_run": 0, "results_found": 0, "qualified_sources_enqueued": [],
            "reason": "Legacy generic trend scans are not eligible for normal proactive selection."}


def discover_and_enqueue(*, queue: ResearchWorkQueue | None = None, per_channel: int = 5,
                         config_path: Path | None = None, start_index: int = 0,
                         max_channels: int | None = None,
                         channels_snapshot: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Enumerate monitored channels and append genuinely new videos to the queue.

    Reuses the existing bounded RSS/yt-dlp channel selector and the existing
    queue's ``enqueue``.  No new discovery engine and no second queue: a
    discovered video is an ordinary ``YOUTUBE_VIDEO`` work item that the same
    processor picks up.
    """
    from youtube_full_pipeline import select_channel_videos
    from research.youtube_channel_registry import upsert_supabase

    queue = queue or default_queue()
    seen = known_video_ids(queue)
    queue_by_video = {str(item.get("source_id")): item for item in queue.load().get("items", [])
                      if item.get("source_id")}
    all_channels = channels_snapshot if channels_snapshot is not None else monitored_channels(config_path)
    if all_channels and max_channels is not None and len(all_channels) > max(0, int(max_channels)):
        start_index = int(start_index) % len(all_channels)
        ordered = all_channels[start_index:] + all_channels[:start_index]
        channels = ordered[:max(0, int(max_channels))]
    else:
        start_index = 0
        channels = all_channels
    enumerated = 0
    new_videos: list[dict[str, Any]] = []
    post_baseline_detected = 0
    metadata_triaged = 0
    duplicates = 0
    errors: list[dict[str, str]] = []
    baselines_established = 0
    monitor_updates: list[dict[str, Any]] = []
    for channel in channels:
        try:
            channel_url = (f"https://www.youtube.com/channel/{channel['channel_id']}/videos"
                           if channel.get("channel_id") else str(channel.get("url", "")))
            rows = select_channel_videos(channel_url,
                                         max(1, min(per_channel, 8)))
        except Exception as exc:
            updated = _update_channel_scan(str(channel.get("channel_id") or channel["id"]), videos=[], error=str(exc)[:200], persist_remote=False,
                                           source_snapshot=channels)
            if updated: monitor_updates.append(updated)
            errors.append({"channel_id": str(channel.get("channel_id") or channel["id"]), "error": str(exc)[:200]})
            continue
        enumerated += len(rows)
        from research.youtube_channel_registry import _parse_published_at, split_by_baseline, update_monitor_state
        post_baseline, baseline_only = split_by_baseline(channel, rows)
        post_baseline_detected += len(post_baseline)
        head = rows[0] if rows else {}
        if baseline_only:
            if head.get("video_id"):
                updated = update_monitor_state(channel["source_id"], baseline_video_id=str(head["video_id"]),
                                     baseline_published_at=head.get("published_at"), last_checked_at=_now(), persist_remote=False)
                if updated: monitor_updates.append(updated)
                baselines_established += 1
            else:
                updated = _update_channel_scan(str(channel.get("channel_id") or channel["id"]),
                                     videos=[], error="empty_initial_snapshot", persist_remote=False,
                                     source_snapshot=channels)
                if updated: monitor_updates.append(updated)
            continue
        _update_channel_scan(str(channel.get("channel_id") or channel["id"]), videos=rows)
        # A baseline may advance only when every observed newer video has a
        # durable triage/processing disposition AND this bounded enumeration
        # reaches the previous baseline.  A queued or unenumerated upload must
        # remain discoverable on the next pass.
        baseline_id = str(channel.get("baseline_video_id") or channel.get("last_seen_video_id") or
                          channel.get("last_item_seen") or "")
        baseline_at = _parse_published_at(channel.get("baseline_published_at") or channel.get("last_item_seen_at"))
        reaches_baseline = any(str(row.get("video_id") or "") == baseline_id for row in rows)
        if baseline_at and rows:
            oldest_stamp = min((_parse_published_at(row.get("published_at")) for row in rows
                                if _parse_published_at(row.get("published_at"))), default=None)
            reaches_baseline = reaches_baseline or bool(oldest_stamp and oldest_stamp <= baseline_at)
        channel_dispositions_complete = True
        for row in post_baseline:
            video_id = str(row.get("video_id") or "")
            if not video_id:
                channel_dispositions_complete = False
                continue
            if video_id in seen:
                duplicates += 1
                queued_item = queue_by_video.get(video_id)
                if not queued_item or str(queued_item.get("status") or "").upper() not in {
                    "COMPLETE", "COMPLETED", "SUPERSEDED", "FAILED_FINAL"}:
                    channel_dispositions_complete = False
                continue
            qualification = qualify_source(title=str(row.get("title") or ""),
                                           description=str(row.get("description") or ""))
            seen.add(video_id)
            from research.youtube_channel_registry import persist_video_metadata, persist_youtube_case
            mode = str(channel.get("triage_mode", "TRIAGE_ONLY")).upper()
            low = qualification["qualification"] not in {"QUALIFIED_RESOURCE", "PARTIAL_RESOURCE"}
            disposition = "IGNORE_LOW_RELEVANCE" if mode == "IGNORE_LOW_RELEVANCE" and low else "TRIAGE_ONLY"
            if mode == "AUTO_RESEARCH" and not low:
                business_opportunity_channel = any("BUSINESS_OPPORTUNIT" in str(value).upper()
                    for value in (channel.get("target_departments") or []))
                case = None
                if business_opportunity_channel:
                    # Queue the qualified source without opening a Research
                    # case or notebook. The normal durable worker first
                    # source-scopes feeder intake, then Alpha decides whether
                    # to promote/reuse a coherent opportunity case.
                    disposition = "AUTO_RESEARCH"
                    receipt = persist_video_metadata(channel,row,disposition=disposition,
                        qualification=qualification,case_id=None)
                else:
                    from research.proactive_research_memory import process_discovery_result
                    relevance = 1.0 if qualification["qualification"] == "QUALIFIED_RESOURCE" else 0.55
                    decision = process_discovery_result(
                        {"url": row.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                         "youtube_video_id": video_id, "title": row.get("title", ""),
                         "workspace_useful": True},
                        objective_id=str(channel["source_id"]), objective_type="YOUTUBE_INTELLIGENCE",
                        topic=str(channel.get("category") or "YouTube channel intelligence"),
                        known_ids=seen - {video_id}, relevance=relevance, value=relevance)
                    case = decision.get("case")
                    case_receipt = persist_youtube_case(channel,row,case) if case else {"ok":False}
                    disposition = "AUTO_RESEARCH" if case and case_receipt.get("ok") and decision.get("create_notebook_workspace") else "TRIAGE_ONLY"
                    receipt = persist_video_metadata(channel,row,disposition=disposition,qualification=qualification,
                        case_id=(case or {}).get("case_id"))
                if disposition == "AUTO_RESEARCH" and receipt.get("ok"):
                    new_videos.append({"video_id": video_id, "title": row.get("title") or video_id,
                                       "url": row.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                                       "published_at": row.get("published_at"), "channel": channel,
                                       "qualification": qualification, "research_case_id": (case or {}).get("case_id")})
                    channel_dispositions_complete = False
                elif not receipt.get("ok"):
                    channel_dispositions_complete = False
                else:
                    metadata_triaged += 1
            else:
                receipt = persist_video_metadata(channel, row, disposition=disposition, qualification=qualification)
                if not receipt.get("ok"):
                    channel_dispositions_complete = False
                else:
                    metadata_triaged += 1
        if head.get("video_id") and reaches_baseline and channel_dispositions_complete:
            updated = update_monitor_state(channel["source_id"], baseline_video_id=str(head["video_id"]),
                                 baseline_published_at=head.get("published_at"), last_checked_at=_now(), persist_remote=False)
            if updated: monitor_updates.append(updated)
        else:
            updated = _update_channel_scan(str(channel.get("channel_id") or channel["id"]), videos=rows,
                                           persist_remote=False, source_snapshot=channels)
            if updated: monitor_updates.append(updated)
    registry_flush = upsert_supabase(monitor_updates) if monitor_updates else {"ok": True, "written": 0}
    appended: list[str] = []
    for video in new_videos:
        channel_key = video["channel"].get("channel_id") or video["channel"].get("source_id")
        work_id = f"yt-channel:{channel_key}:{video['video_id']}"
        # YouTube queue intake performs only classification/matching here.
        # Alpha's Research Director decides promotion later; feeder intake is
        # not the dedicated deep-research notebook.
        from nexus_agent_platform.business_opportunity_research_v2 import build_intake
        intake = build_intake(title=str(video.get("title") or video["video_id"]),
            objective=str(video["channel"].get("purpose") or ""),
            source_url=str(video.get("url") or f"https://www.youtube.com/watch?v={video['video_id']}"),
            source_type="YOUTUBE_VIDEO", source_id=str(video["video_id"]),
            description=str(video.get("description") or ""))
        queue.enqueue(work_id=work_id, work_class="ASSIGNED", source_type="YOUTUBE_VIDEO",
                      source_id=video["video_id"], source_url=video["url"], title=video["title"],
                      lane_id="YOUTUBE_CONTENT", program_id="YOUTUBE_INTELLIGENCE",
                      priority=max(1, min(50, int(video["channel"].get("priority", 20)))),
                      lifecycle="ONE_TIME", work_role="RESEARCHER",
                      requested_by="proactive_channel_discovery",
                      channel_name=video["channel"].get("name"), channel_id=video["channel"].get("channel_id"),
                      channel_url=video["channel"].get("url"), published_at=video.get("published_at"),
                      monitor_mode="NEW_CONTENT_ONLY", research_case_id=video.get("research_case_id"),
                      default_profile_hint=video["channel"].get("default_profile"),
                      default_notebook_hint=video["channel"].get("default_notebook"),
                      target_departments=video["channel"].get("target_departments", []),
                      source_qualification=video["qualification"],
                      research_processor="notebooklm_research_worker",
                      selection_reason=f"monitored_channel_discovery:{video['channel']['id']}",
                      research_objective=video["channel"].get("purpose") or "channel_watch_research",
                      entry_type=intake["entry_type"], source_role=intake["source_role"],
                      opportunity_relationship=intake["opportunity_relationship"],
                      opportunity_id=(opportunity_context or {}).get("opportunity_id") or intake.get("matched_opportunity_id"),
                      promotion_status=intake["promotion_status"], director_mode="RESEARCH_DIRECTOR",
                      notebook_role="FEEDER_INTAKE_ONLY",
                      opportunity_intake_id=intake["intake_id"],
                      objective_family="BUSINESS_OPPORTUNITIES" if business_opportunity_channel else None,
                      research_purpose="MISSION_RESEARCH" if business_opportunity_channel else None,
                      research_domain="BUSINESS_OPPORTUNITY" if business_opportunity_channel else None)
        appended.append(work_id)
    next_index = ((start_index + len(channels)) % len(all_channels)) if all_channels else 0
    return {"channels_checked": len(channels), "channels_total": len(all_channels),
            "channel_start_index": start_index, "next_channel_index": next_index,
            "channel_rotation_complete": not all_channels or next_index == 0,
            "videos_enumerated": enumerated,
            "new_videos_found": post_baseline_detected, "new_videos_triaged": metadata_triaged,
            "research_items_queued": len(appended), "baselines_established": baselines_established,
            "duplicates_suppressed": duplicates,
            "queue_appended": appended, "errors": errors, "monitor_state_batch_write": registry_flush,
            "qualified_new_sources": len(appended),
            "work_class": "ASSIGNED", "lane_id": "YOUTUBE_CONTENT",
            "same_processor": "notebooklm_research_worker.process_claim"}


def run_proactive_discovery_cycle(*, queue: ResearchWorkQueue | None = None,
                                  force: bool = False) -> dict[str, Any]:
    """One bounded discovery heartbeat, scheduled by the existing Research kernel."""
    cycle_started = time.monotonic()
    stage_timings: dict[str, float] = {}
    state_read_started = time.monotonic()
    queue = queue or default_queue()
    try:
        state = json.loads(PROACTIVE_STATE_PATH.read_text(encoding="utf-8")) if PROACTIVE_STATE_PATH.exists() else {}
    except (OSError, ValueError):
        state = {}
    stage_timings["state_read_and_queue_init_seconds"] = round(time.monotonic() - state_read_started, 3)
    now_dt = datetime.now(timezone.utc)
    def due(key: str, hours: int) -> bool:
        if force or not state.get(key): return True
        try:
            stamp = datetime.fromisoformat(str(state[key]).replace("Z", "+00:00"))
            return (now_dt - stamp).total_seconds() >= hours * 3600
        except ValueError:
            return True
    monitored: dict[str, Any] = {"channels_checked": 0, "new_videos_found": 0,
                                 "duplicates_suppressed": 0, "queue_appended": []}
    trends: dict[str, Any] = {"status": "NOT_SELECTED", "queries_run": 0, "results_found": 0,
                              "qualified_sources_enqueued": []}
    proactive_search: dict[str, Any] = {"status": "NOT_DUE", "provider": "EXISTING_WEB_SEARCH_ABSTRACTION"}
    gaps: dict[str, Any] = {"gap_objectives_created": 0, "objectives": []}
    selection_started = time.monotonic()
    channel_refresh_due = force or not state.get("last_channel_refresh") or due("last_channel_refresh", 6)
    due_tasks = []
    if channel_refresh_due: due_tasks.append("MONITORED_SOURCES")
    if due("last_proactive_search", 6): due_tasks.append("PROACTIVE_SEARCH")
    if due("last_gap_scan", 24): due_tasks.append("GAP_RESEARCH")
    case_continuation = None
    try:
        from research.research_case_engine import next_schedulable_case
        case_continuation = next_schedulable_case()
    except Exception:
        case_continuation = None
    task_order = ["MONITORED_SOURCES", "PROACTIVE_SEARCH", "GAP_RESEARCH"]
    cursor = int(state.get("proactive_task_cursor") or 0) % len(task_order)
    selected_task = ("CASE_CONTINUATION" if case_continuation else
                     next((task_order[(cursor + offset) % len(task_order)] for offset in range(len(task_order))
                           if task_order[(cursor + offset) % len(task_order)] in due_tasks), None))
    stage_timings["objective_task_selection_seconds"] = round(time.monotonic() - selection_started, 3)
    task_started = time.monotonic()
    if selected_task:
        if selected_task in task_order:
            state["proactive_task_cursor"] = (task_order.index(selected_task) + 1) % len(task_order)
        state["last_proactive_task_started"] = {"task": selected_task, "at": _now()}
        _atomic_json(PROACTIVE_STATE_PATH, state)
    if selected_task == "MONITORED_SOURCES":
        start = int(state.get("channel_rotation_cursor") or 0)
        # Persist rotation before network I/O so a timed-out feed cannot pin
        # every future heartbeat to the same source pair.
        channels_now = monitored_channels()
        state["channel_rotation_cursor"] = (start + min(2, len(channels_now))) % len(channels_now) if channels_now else 0
        _atomic_json(PROACTIVE_STATE_PATH, state)
        monitored = discover_and_enqueue(queue=queue, per_channel=3, start_index=start, max_channels=2,
                                         channels_snapshot=channels_now)
        if monitored.get("channel_rotation_complete"):
            state["last_channel_refresh"] = _now()
    elif selected_task == "PROACTIVE_SEARCH":
        try:
            from nexus_agent_platform.proactive_objectives import run_selected_proactive_objective
            proactive_search = run_selected_proactive_objective()
            proactive_search["provider_truth"] = "Customer-first scored objective selection; approved web search or bounded affiliate directory search. Domains found in results are evidence only."
            state["last_discovery_lane"] = proactive_search.get("objective", {}).get("lane")
            state["last_proactive_search"] = _now()
            state["last_proactive_objective_family"] = proactive_search.get("objective", {}).get("objective_family")
        except Exception as exc:
            proactive_search = {"status": "CAPABILITY_DEGRADED",
                                "error": f"{type(exc).__name__}: {exc}"[:250]}
    elif selected_task == "CASE_CONTINUATION":
        from research.research_case_engine import continue_case_once
        proactive_search = continue_case_once(str(case_continuation.get("case_id")))
        proactive_search["objective"] = {"research_question": proactive_search.get("question"),
                                          "objective_family": case_continuation.get("objective_family"),
                                          "case_id": case_continuation.get("case_id")}
        state["last_case_continuation"] = {"case_id": case_continuation.get("case_id"),
                                            "at": _now(), "status": proactive_search.get("status"),
                                            "run_id": proactive_search.get("run_id")}
        state["last_proactive_search"] = _now()
    elif selected_task == "GAP_RESEARCH":
        gaps = close_research_gaps(max_items=1)
        state["last_gap_scan"] = _now()
    state["last_proactive_cycle"] = _now()
    full_queue_summary = queue.summary()
    state["discovery_mode"] = "ACTIVE" if full_queue_summary["queue_depth"] == 0 else "QUEUED_WORK_AVAILABLE"
    persist_started = time.monotonic()
    _atomic_json(PROACTIVE_STATE_PATH, state)
    stage_timings["selected_task_execution_seconds"] = round(time.monotonic() - task_started, 3)
    stage_timings["state_persistence_seconds"] = round(time.monotonic() - persist_started, 3)
    stage_timings["total_cycle_seconds"] = round(time.monotonic() - cycle_started, 3)
    degraded = (selected_task == "PROACTIVE_SEARCH" and proactive_search.get("status") == "CAPABILITY_DEGRADED")
    result = {"status": "DEGRADED" if degraded else "PASS",
            "monitored_source_refresh": monitored, "open_trend_discovery": trends,
            "rotating_proactive_search": proactive_search,
            "proactive_selection": proactive_search.get("objective"),
            "research_gap_closure": gaps, "queue_empty_enters_discovery_mode": True,
            "continuation_durable": True, "queue_summary": {key: full_queue_summary.get(key) for key in
                ("queue_depth", "by_class", "by_status")},
            "processor": "notebooklm_research_worker.process_claim", "selected_task": selected_task,
            "stage_timings": stage_timings}
    receipt_path = ROOT / "reports/runtime/proactive_discovery_wake_latest.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"schema_version": "nexus.proactive-wake-timing.v1", "recorded_at": _now(),
               "selected_task": selected_task, "stage_timings": stage_timings,
               "query_stage_timings": (proactive_search or {}).get("stage_timings", {}),
               "status": result["status"], "discovery_run_id": (proactive_search or {}).get("discovery_run_id"),
               "provider_truth": (proactive_search or {}).get("provider_truth"),
               "current_proactive_objective": (proactive_search.get("objective") or {}).get("research_question"),
               "why_this_objective_was_selected": proactive_search.get("why_this_objective_was_selected"),
               "objective_family": (proactive_search.get("objective") or {}).get("objective_family"),
               "research_question": (proactive_search.get("objective") or {}).get("research_question"),
               "evidence_needed": (proactive_search.get("objective") or {}).get("evidence_needed"),
               "best_source_classes": (proactive_search.get("objective") or {}).get("best_source_classes", []),
               "why_these_sources": (proactive_search.get("objective") or {}).get("why_these_sources"),
               "quality_assessment": proactive_search.get("quality_assessment"),
               "raw_signal_ids": proactive_search.get("raw_signal_ids", []),
               "query": (proactive_search.get("objective_run") or {}).get("query"),
               "source_classes": proactive_search.get("source_classes_used", []),
               "raw_signals": int(proactive_search.get("results_found", 0) or 0),
               "qualified_findings": int(proactive_search.get("qualified_findings_created", 0) or 0),
               "handoffs": int(proactive_search.get("handoffs_created", 0) or 0),
               "saturation_state": proactive_search.get("saturation_state"),
               "next_research_direction": proactive_search.get("next_research_direction"),
               "result_counts": {"youtube_checked": monitored.get("channels_checked", 0),
                   "new_videos": monitored.get("new_videos_found", 0), "trend_results": 0,
                   "trend_findings_created": 0,
                   "proactive_query": (proactive_search.get("objective_run") or {}).get("query"),
                   "proactive_results": proactive_search.get("results_found", 0),
                   "sources_appended": len(monitored.get("queue_appended", [])) + int(proactive_search.get("sources_appended_to_fifo", 0) or 0)}}
    _atomic_json(receipt_path, receipt)
    result["wake_receipt_path"] = str(receipt_path)
    result["wake_receipt_created"] = True
    return result


def run_batch(*, limit: int = 10, work_ids: Iterable[str] | None = None,
              adapter: NotebookLMResearchAdapter | None = None,
              queue: ResearchWorkQueue | None = None) -> dict[str, Any]:
    """Process a bounded batch through the existing queue.  One job at a time."""
    queue = queue or default_queue()
    adapter = adapter or get_adapter()
    queue.recover_expired_leases()
    if work_ids:
        candidates = [row for row in queue.load().get("items", []) if row.get("work_id") in set(work_ids)]
    else:
        candidates = eligible_youtube_items(queue, limit=limit)
    started = utcnow()
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        work_id = str(candidate.get("work_id"))
        claimed = queue.claim_work(work_id, worker_id="notebooklm_research_worker", lease_seconds=1800)
        if claimed is None:
            records.append({"recorded_at": _now(), "work_id": work_id, "outcome": "SKIPPED",
                            "reason": "not_claimable", "queue_status": candidate.get("status")})
            continue
        try:
            records.append(process_claim(work_item=claimed, adapter=adapter, queue=queue))
        except Exception as exc:  # pragma: no cover - defensive
            records.append(_settle_failure(queue=queue, work_item=claimed,
                                           result={"status": "FAILED",
                                                   "failure_code": "NOTEBOOK_PERSISTENCE_FAILED",
                                                   "failure_stage": "worker",
                                                   "error": f"{type(exc).__name__}: {exc}"[:500],
                                                   "provenance": {}},
                                           attempt=int(claimed.get("attempt_count") or 1)))
    summary = summarize(records)
    summary.update({"adapter_subprocesses": adapter.stats.get("subprocesses", 0),
                    "adapter_failures": adapter.stats.get("failures", []),
                    "started_at": started.isoformat(), "finished_at": _now(),
                    "max_concurrency": int(os.environ.get("NEXUS_NOTEBOOK_MAX_CONCURRENCY", "1"))})
    return {"summary": summary, "records": records}


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    extracted = [row for row in records if row.get("outcome") == "EXTRACTED"]
    failed = [row for row in records if row.get("outcome") == "FAILED"]
    skipped = [row for row in records if row.get("outcome") == "SKIPPED"]
    handoffs = sum(len((row.get("persistence") or {}).get("handoffs") or []) for row in extracted)
    handoffs_created = sum(
        1 for row in extracted
        for entry in ((row.get("persistence") or {}).get("handoffs") or [])
        if entry.get("created")
    )
    return {
        "attempted": len([row for row in records if row.get("outcome") in {"EXTRACTED", "FAILED", "PROFILE_MISMATCH"}]),
        "extracted": len(extracted),
        "structured_results_saved": len([row for row in extracted if row.get("record")]),
        "findings_persisted": len([row for row in extracted if (row.get("persistence") or {}).get("finding")]),
        "sources_persisted": len([row for row in extracted if (row.get("persistence") or {}).get("source")]),
        "handoffs_total": handoffs,
        "handoffs_created": handoffs_created,
        "completed": len([row for row in extracted if row.get("queue_status") == "COMPLETE"]),
        "failed_retryable": len([row for row in failed if row.get("queue_status") == "FAILED_RETRYABLE"]),
        "failed_final": len([row for row in failed if row.get("queue_status") == "FAILED_FINAL"]),
        "profile_mismatches": len([row for row in records if row.get("outcome") == "PROFILE_MISMATCH"]),
        "skipped": len(skipped),
        "failure_codes": {code: sum(1 for row in failed if row.get("failure_code") == code)
                          for code in sorted({row.get("failure_code") for row in failed if row.get("failure_code")})},
        "elapsed_seconds_total": round(sum(float(row.get("elapsed_seconds") or 0) for row in extracted), 3),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NotebookLM YouTube Research worker on the existing queue")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--work-id", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--discover", action="store_true", help="enumerate monitored channels and append new videos")
    parser.add_argument("--proactive-heartbeat", action="store_true",
                        help="run one bounded monitored/trend/gap discovery pass")
    args = parser.parse_args()

    if args.dry_run:
        rows = eligible_youtube_items(default_queue(), limit=args.limit)
        print(json.dumps({"eligible": len(rows),
                          "sample": [{"work_id": row.get("work_id"), "title": row.get("title"),
                                      "url": row.get("source_url"), "priority": row.get("priority")}
                                     for row in rows[:args.limit]]}, indent=2, default=str))
        raise SystemExit(0)

    if args.discover:
        print(json.dumps(discover_and_enqueue(per_channel=args.limit), indent=2, default=str))
        raise SystemExit(0)

    if args.proactive_heartbeat:
        print(json.dumps(run_proactive_discovery_cycle(force=True), indent=2, default=str))
        raise SystemExit(0)

    output = run_batch(limit=args.limit, work_ids=args.work_id or None)
    print(json.dumps(output, indent=2, default=str))
