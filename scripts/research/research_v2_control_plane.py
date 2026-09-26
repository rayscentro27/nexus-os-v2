"""Small, durable Research V2 control-plane contracts.

This module is intentionally a library, not a daemon.  It adds planning,
fair selection, completion semantics, and receipts around the existing source
adapters and supervised runtime.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "runtime" / "research_v2_program_registry.json"
ALPHA_REGISTRY = ROOT / "data" / "runtime" / "alpha_source_registry.json"
RUNTIME_TICKS = ROOT / "data" / "runtime" / "research_v2_runtime_ticks.jsonl"
PROGRAM_IDS = (
    "CUSTOMER_NEEDS", "BUSINESS_FUNDING", "GOCLEAR_PRODUCT", "CUSTOMER_ACQUISITION",
    "YOUTUBE_INTELLIGENCE", "SEO_SEARCH_INTELLIGENCE", "GITHUB_OPEN_SOURCE",
    "LAST30DAYS_PROACTIVE", "AFFILIATE_SOLUTIONS", "COMPETITOR_INTELLIGENCE",
    "TRADING_RESEARCH", "PROJECT_SUPPORT", "RESEARCH_MORE",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def recover_youtube_channels(registry_path: Path | None = None) -> list[dict[str, Any]]:
    source = registry_path or ALPHA_REGISTRY
    data = json.loads(source.read_text()) if source.exists() else []
    rows = data.get("sources", data) if isinstance(data, dict) else data
    out, seen = [], set()
    for row in rows if isinstance(rows, list) else []:
        if str(row.get("source_type", "")).upper() != "YOUTUBE_CHANNEL":
            continue
        url = str(row.get("source_url") or row.get("url") or "").rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        name = row.get("source_name") or row.get("name") or ""
        if str(name).lower() in {"videos", "channel", "youtube channel"} or not name:
            name = url.rstrip("/").split("/@")[-1].split("/")[0]
        identity_url = url.removesuffix("/videos")
        channel_id = identity_url.rsplit("/", 1)[-1]
        out.append({"channel_id": channel_id, "channel_name": name, "channel_url": url,
                    "added_by": row.get("added_by", "UNKNOWN"), "status": row.get("status", "ACTIVE")})
    return out


def program_registry() -> dict[str, Any]:
    objectives = {
        "CUSTOMER_NEEDS": "Find recurring customer problems, complaints, desired outcomes, and buying signals.",
        "BUSINESS_FUNDING": "Produce evidence-backed funding, readiness, and bankability intelligence for Clyde.",
        "GOCLEAR_PRODUCT": "Answer product, beta, onboarding, and customer-experience questions for GoClear.",
        "CUSTOMER_ACQUISITION": "Find validated acquisition questions, channels, and content opportunities.",
        "YOUTUBE_INTELLIGENCE": "Analyze relevant historical and new video content for evidence and findings.",
        "SEO_SEARCH_INTELLIGENCE": "Investigate search intent, content gaps, and customer acquisition queries.",
        "GITHUB_OPEN_SOURCE": "Assess relevant repositories, releases, and tools for capability and integration value.",
        "LAST30DAYS_PROACTIVE": "Discover recent developments and demand signals across standing objectives.",
        "AFFILIATE_SOLUTIONS": "Match validated needs to reputable existing products or referral paths.",
        "COMPETITOR_INTELLIGENCE": "Compare relevant competitors and alternatives using evidence.",
        "TRADING_RESEARCH": "Conduct bounded, non-live research and paper-only validation.",
        "PROJECT_SUPPORT": "Answer explicit unanswered questions from active projects.",
        "RESEARCH_MORE": "Bounded follow-up on Alpha requests, never an indefinite queue source.",
    }
    return {"schema_version": "nexus.research-programs.v2", "generated_at": now(), "programs": [
        {"program_id": pid, "objective": objectives[pid], "owner": "RESEARCH", "source_types": [],
         "cadence": "FAIR_SCHEDULER", "backlog": 0, "active_questions": [],
         "definition_of_useful_output": "validated finding, useful negative, Alpha package, handoff, or documented blocker",
         "handoff_destinations": ["ALPHA"], "last_meaningful_result": None, "starvation_status": "ELIGIBLE"}
        for pid in PROGRAM_IDS
    ], "youtube_channels": recover_youtube_channels(), "scheduler": {
        "algorithm": "deficit_round_robin", "research_more_max_consecutive": 2,
        "starvation_threshold": 3, "monitor_checks_are_substantive": False}}


def persist_registry() -> dict[str, Any]:
    payload = program_registry()
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def derive_project_needs() -> list[dict[str, Any]]:
    """Derive only explicit research requests from active operator work orders."""
    path = ROOT / "data" / "runtime" / "active_operator_work_orders.json"
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    rows = value.get("work_orders", value) if isinstance(value, dict) else value
    needs = []
    for row in rows if isinstance(rows, list) else []:
        status = str(row.get("status", "")).upper()
        text = " ".join(str(row.get(k, "")) for k in ("title", "description", "category"))
        if status not in {"READY", "WAITING_APPROVAL", "ACTIVE"} or not any(term in text.lower() for term in ("needs research", "research queue", "funding readiness")):
            continue
        project = "Clyde / business funding" if "funding" in text.lower() else "Marketing / customer acquisition"
        needs.append({"project_id": str(row.get("goal_id") or row.get("program_id") or project),
                      "project": project, "question": str(row.get("title") or row.get("description")),
                      "source_work_order": row.get("title"), "source_status": status,
                      "evidence_refs": row.get("evidence_refs", [])})
    unique = {}
    for need in needs: unique.setdefault((need["project_id"], need["question"]), need)
    return list(unique.values())


def planner_tick(*, worker_id: str = "research_v2_runtime") -> dict[str, Any]:
    """Run V2 planning once inside an existing Research wake.

    This is deliberately not a scheduler: it only reconciles durable registry
    state and projects explicit needs into the existing leased queue.
    """
    registry = persist_registry()
    project_needs = derive_project_needs()
    created = 0
    try:
        from nexus_agent_platform.research_work_queue import default_queue
        queue = default_queue()
        existing = {str(item.get("work_id")) for item in queue.load().get("items", [])}
        for need in project_needs:
            digest = hashlib.sha256(f"{need['project_id']}:{need['question']}".encode()).hexdigest()[:20]
            work_id = f"project-research:{digest}"
            if work_id in existing:
                continue
            queue.enqueue(work_id=work_id, work_class="ASSIGNED", priority=2,
                          lane_id="FUNDING_LENDER" if "funding" in need["project"].lower() else "BUSINESS_MARKET",
                          source_type="RESEARCH_OBJECTIVE", source_id=work_id, title=need["question"],
                          question=need["question"], objective_id=need["project_id"], project_id=need["project_id"],
                          source_candidates=[
                              {"source_type": "WEB_PAGE", "source_id": "sba-loans", "source_url": "https://www.sba.gov/funding-programs/loans", "title": "SBA loan programs"},
                              {"source_type": "WEB_PAGE", "source_id": "fed-sbcs", "source_url": "https://www.fedsmallbusiness.org/survey", "title": "Federal Reserve Small Business Credit Survey"},
                          ], requested_by="research_v2_planner", department_target="CLYDE" if "funding" in need["project"].lower() else "MARKETING",
                          lifecycle="ONE_TIME", selection_reason="project_research_need", evidence_refs=need.get("evidence_refs", []))
            existing.add(work_id); created += 1
    except Exception as exc:
        return {"status": "DEGRADED", "error": str(exc)[:300], "registry_channels": len(registry["youtube_channels"]), "project_needs": len(project_needs), "tasks_created": created}
    result = {"status": "PASS", "worker_id": worker_id, "registry_channels": len(registry["youtube_channels"]), "programs": len(registry["programs"]), "project_needs": len(project_needs), "tasks_created": created, "backfill_target": len(registry["youtube_channels"]) * 10, "recorded_at": now()}
    try:
        from nexus_agent_platform.governed.persistence import append_record
        from nexus_agent_platform.research_work_queue import default_queue
        summary = default_queue().summary()
        try:
            from nexus_agent_platform.research_lane_scheduler import program_service_snapshot
            service = program_service_snapshot()
        except Exception:
            service = {}
        starved = sorted(program_id for program_id, state in service.items()
                         if str(state.get("starvation_status") or "").upper() == "RESEARCH_PROGRAM_STARVATION")
        project_starved = "PROJECT_SUPPORT" in starved
        append_record("research_runtime_states", {"schema_version": "nexus.research-runtime-v2.2", "recorded_at": result["recorded_at"], "process_health": "RUNNING", "research_productivity": "EVIDENCE_REQUIRED", "queue_summary": summary, "programs_starved": starved, "project_research_starvation": project_starved, "program_service_state": service, "last_planner_result": result})
    except Exception:
        pass
    RUNTIME_TICKS.parent.mkdir(parents=True, exist_ok=True)
    with RUNTIME_TICKS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")
    return result


def build_youtube_backfill(limit_per_channel: int = 10) -> list[dict[str, Any]]:
    return [{"task_id": f"yt_backfill_{channel['channel_id']}_{i}", "program_id": "YOUTUBE_INTELLIGENCE",
             "mode": "BACKFILL", "channel_id": channel["channel_id"], "channel_name": channel["channel_name"],
             "channel_url": channel["channel_url"], "video_ordinal": i, "analysis_status": "QUEUED",
             "transcript_status": "PENDING", "finding_status": "PENDING", "alpha_status": "PENDING",
             "handoff_status": "PENDING", "selection_reason": "registered-channel historical backfill"}
            for channel in recover_youtube_channels() for i in range(1, limit_per_channel + 1)]


def fair_select(tasks: list[dict[str, Any]], state: dict[str, Any] | None = None, limit: int = 1) -> list[dict[str, Any]]:
    state = state or {}; debt = dict(state.get("deficit", {})); last = state.get("last_program")
    for pid in PROGRAM_IDS: debt[pid] = float(debt.get(pid, 0)) + (1 if any(t.get("program_id") == pid for t in tasks) else 0)
    candidates = sorted((t for t in tasks if t.get("status", "QUEUED") in {"QUEUED", "READY"}), key=lambda t: debt.get(t.get("program_id"), 0), reverse=True)
    selected, used = [], set()
    for task in candidates:
        pid = task.get("program_id")
        if pid in used or (pid == "RESEARCH_MORE" and state.get("consecutive_research_more", 0) >= 2): continue
        selected.append(task); used.add(pid); debt[pid] = max(0, debt.get(pid, 0) - 1)
        if len(selected) >= limit: break
    return selected


def classify_completion(result: dict[str, Any], task_kind: str = "") -> str:
    status = str(result.get("processing_status", "")).upper()
    if status == "DUPLICATE_UNCHANGED": return "MONITOR_CHECK_COMPLETE"
    if result.get("finding_created") or result.get("claims_created") or result.get("structured_extraction") or result.get("research_disposition") in {"DEEP_RESEARCH", "HIGH_VALUE_REVIEW"}:
        return "SUBSTANTIVE_COMPLETE"
    if status in {"FULLY_PROCESSED", "DISCOVERY_CAPTURED"} and (result.get("summary") or result.get("text") or result.get("artifact_paths")):
        return "SUBSTANTIVE_COMPLETE"
    if status.startswith("FAILED") or result.get("error"): return "FAILED_RETRYABLE"
    return "EVIDENCE_INCOMPLETE"


STAGES = ("TASK_CREATED", "SOURCE_SELECTED", "SOURCE_ACCESSED", "CONTENT_CAPTURED", "ANALYSIS_COMPLETED", "FINDING_CREATED", "CROSS_CHECK_COMPLETED", "ALPHA_REVIEWED", "HANDOFF_COMPLETED")


def stage_receipts(item: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    completion = classify_completion(result, str(item.get("source_type", "")))
    evidence = bool(result.get("summary") or result.get("text") or result.get("artifact_paths") or result.get("claims_created"))
    reached = {"TASK_CREATED", "SOURCE_SELECTED"}
    if result.get("raw_acquired", True): reached.add("SOURCE_ACCESSED")
    if evidence: reached.update({"CONTENT_CAPTURED", "ANALYSIS_COMPLETED"})
    if completion == "SUBSTANTIVE_COMPLETE": reached.add("FINDING_CREATED")
    return [{"receipt_id": f"{item.get('task_id') or item.get('source_id','task')}_{stage.lower()}", "task_id": item.get("task_id") or item.get("source_id"), "stage": stage, "status": "COMPLETED" if stage in reached else "UNAVAILABLE", "completion_status": completion, "recorded_at": now()} for stage in STAGES]


def project_questions(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    for project in projects:
        for question in project.get("research_questions", []) + project.get("intelligence_needed", []) + project.get("research_blockers", []):
            if str(question).strip(): tasks.append({"program_id": "PROJECT_SUPPORT", "project": project.get("project") or project.get("name"), "question": str(question), "status": "QUEUED"})
    return tasks


def registry_snapshot() -> dict[str, Any]:
    data = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else persist_registry()
    return {"program_count": len(data.get("programs", [])), "youtube_channel_count": len(data.get("youtube_channels", [])), "youtube_channels": data.get("youtube_channels", []), "programs": data.get("programs", [])}
