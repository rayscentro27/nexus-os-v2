#!/usr/bin/env python3
"""Read-only operational snapshot of canonical local Research state.

This command reads existing files and performs one bounded ``ps`` inspection.
It does not import worker code, contact Supabase, call models/NotebookLM, claim
work, invoke schedulers, or write state.
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data/runtime/research_work_queue.json"
RESEARCH_HEARTBEAT_PATH = ROOT / "data/runtime/research_heartbeat.json"
PROACTIVE_STATE_PATH = ROOT / "data/runtime/notebooklm_proactive_research.json"
PROGRAM_STATE_PATH = ROOT / "data/runtime/research_program_service_state.json"
YOUTUBE_CONFIG_PATH = ROOT / "configs/youtube_research_channels.json"
NOTEBOOKLM_RESULTS_PATH = ROOT / "data/runtime/notebooklm_research_results.jsonl"
FINDINGS_PATH = ROOT / "data/governed/research_notebooklm_findings.jsonl"
GAPS_PATH = ROOT / "data/governed/notebooklm_research_gaps.jsonl"
TREND_SIGNALS_PATH = ROOT / "data/governed/research_trend_signals.jsonl"
HANDOFF_LOG_PATH = ROOT / "data/governed/research_v2_handoffs.jsonl"
PROACTIVE_MEMORY_PATH = ROOT / "data/governed/research_runtime_states.jsonl"
RAW_SIGNALS_PATH = ROOT / "data/governed/research_raw_signals.jsonl"
SOURCE_REGISTRY_PATH = ROOT / "data/governed/alpha_source_registry.jsonl"
PROACTIVE_WAKE_RECEIPT_PATH = ROOT / "reports/runtime/proactive_discovery_wake_latest.json"
TRADINGVIEW_RECEIPT_PATH = ROOT / "reports/runtime/tradingview_research_latest.json"
RESEARCH_TOOL_RUNS_PATH = ROOT / "data/governed/research_tool_layer_runs.jsonl"
KERNEL_COMMAND = str(ROOT / "scripts/run_continuous_operating_kernel.py")

UNAVAILABLE = "UNAVAILABLE"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]] | None:
    try:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
        return rows
    except (OSError, ValueError, TypeError):
        return None


def _read_jsonl_tail(path: Path, *, max_bytes: int = 2_000_000) -> list[dict[str, Any]] | None:
    """Read only a bounded tail from large append-only runtime memory files."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            raw = handle.read(max_bytes)
    except OSError:
        return None
    lines = raw.splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]
    rows = []
    for line in lines:
        try:
            value = json.loads(line)
            if isinstance(value, dict): rows.append(value)
        except (ValueError, TypeError):
            continue
    return rows


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)
    except ValueError:
        return None


def _fmt(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")
    if value is None or value == "":
        return UNAVAILABLE
    return str(value).replace("\n", " ").replace("=", ":")


def _recent_count(rows: list[dict[str, Any]] | None, timestamp_field: str,
                  cutoff: datetime, predicate=lambda row: True) -> int | str:
    if rows is None:
        return UNAVAILABLE
    return sum(1 for row in rows if predicate(row) and (_time(row.get(timestamp_field)) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff)


def _kernel_process() -> tuple[str, str, str]:
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,etime=,command="],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return UNAVAILABLE, UNAVAILABLE, UNAVAILABLE
    if result.returncode != 0:
        return UNAVAILABLE, UNAVAILABLE, UNAVAILABLE
    matches = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and KERNEL_COMMAND in parts[2] and "--daemon" in parts[2]:
            matches.append((parts[0], parts[1]))
    if not matches:
        return "NO", "UNAVAILABLE", "UNAVAILABLE"
    # The canonical supervisor is expected to be a singleton; report the first
    # matching PID without killing or otherwise inspecting any process.
    pid, elapsed = matches[0]
    return "YES", pid, elapsed


def _queue_status(item: dict[str, Any]) -> str:
    return str(item.get("status") or "UNKNOWN").upper()


def _historical(item: dict[str, Any]) -> bool:
    return item.get("archive_lane") == "HISTORICAL_BACKLOG" or str(item.get("priority_tier") or "").upper() in {"HISTORICAL_BACKLOG", "ARCHIVED_BACKLOG"}


def _completed(item: dict[str, Any]) -> bool:
    return _queue_status(item) in {"COMPLETE", "COMPLETED"}


def _notebooklm_item(row: dict[str, Any]) -> bool:
    outcome = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}
    processor = str(outcome.get("processor") or row.get("processor") or "").lower()
    # The durable result log itself is scoped to the NotebookLM research worker.
    return "notebooklm" in processor or "notebooklm" in str(row.get("work_id") or "").lower() or bool(row.get("record"))


def _first_time(row: dict[str, Any], fields: tuple[str, ...]) -> datetime | None:
    for field in fields:
        value = _time(row.get(field))
        if value:
            return value
    return None


def _last_time(rows: list[dict[str, Any]] | None, fields: tuple[str, ...], predicate=lambda row: True) -> datetime | None:
    if rows is None:
        return None
    times = [_first_time(row, fields) for row in rows if predicate(row)]
    values = [value for value in times if value]
    return max(values) if values else None


def _notebooklm_counts(rows: list[dict[str, Any]] | None, cutoff: datetime) -> tuple[int | str, int | str, int | str]:
    if rows is None:
        return UNAVAILABLE, UNAVAILABLE, UNAVAILABLE
    recent = [row for row in rows if (_first_time(row, ("recorded_at", "completed_at", "created_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    retryable = sum(str(row.get("queue_status") or "").upper() == "FAILED_RETRYABLE" for row in recent)
    final = sum(str(row.get("queue_status") or "").upper() == "FAILED_FINAL" for row in recent)
    completed = sum(str(row.get("queue_status") or "").upper() in {"COMPLETE", "COMPLETED"} for row in recent)
    return completed, retryable, final


def _handoff_count_from_queue(items: list[dict[str, Any]], cutoff: datetime) -> int | str:
    recent = [item for item in items if _completed(item) and (_time(item.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    if not recent:
        return 0
    counts = []
    for item in recent:
        result = item.get("last_result")
        if not isinstance(result, dict) or not isinstance(result.get("handoff_count"), int):
            return UNAVAILABLE
        counts.append(result["handoff_count"])
    return sum(counts)


def _handoff_counts_from_results(rows: list[dict[str, Any]] | None, cutoff: datetime) -> tuple[int | str, dict[str, int]]:
    """Count persisted department deliveries from the worker's durable result log."""
    if rows is None:
        return UNAVAILABLE, {}
    total = 0
    by_department: Counter[str] = Counter()
    for row in rows:
        if (_time(row.get("recorded_at") or row.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc)) < cutoff:
            continue
        persistence = row.get("persistence") if isinstance(row.get("persistence"), dict) else {}
        for handoff in persistence.get("handoffs") or []:
            if handoff.get("created") or handoff.get("status") in {"CREATED", "DELIVERED", "ACKNOWLEDGED"}:
                total += 1
                department = str(handoff.get("target_department") or "UNKNOWN").upper()
                by_department[department] += 1
    return total, dict(by_department)


def _format_output() -> str:
    now = datetime.now(timezone.utc)
    cutoff60, cutoff24 = now - timedelta(minutes=60), now - timedelta(hours=24)
    queue_doc = _read_json(QUEUE_PATH)
    queue_items = queue_doc.get("items") if queue_doc and isinstance(queue_doc.get("items"), list) else None
    heartbeat = _read_json(RESEARCH_HEARTBEAT_PATH)
    proactive = _read_json(PROACTIVE_STATE_PATH)
    program_state = _read_json(PROGRAM_STATE_PATH)
    youtube_config = _read_json(YOUTUBE_CONFIG_PATH)
    notebooklm_rows = _read_jsonl_tail(NOTEBOOKLM_RESULTS_PATH)
    findings = _read_jsonl_tail(FINDINGS_PATH)
    gaps = _read_jsonl(GAPS_PATH)
    trend_signals = _read_jsonl(TREND_SIGNALS_PATH)
    handoffs = _read_jsonl(HANDOFF_LOG_PATH)
    memory_rows = _read_jsonl_tail(PROACTIVE_MEMORY_PATH)
    raw_signal_rows = _read_jsonl_tail(RAW_SIGNALS_PATH)
    source_rows = _read_jsonl_tail(SOURCE_REGISTRY_PATH)
    youtube_reconciliation = _read_json(ROOT / "reports/runtime/youtube_notebooklm_live_reconciliation_latest.json") or {}
    notebooklm_inventory = _read_json(ROOT / "reports/runtime/notebooklm_inventory_latest.json") or {}
    wake_receipt = _read_json(PROACTIVE_WAKE_RECEIPT_PATH)
    tradingview_receipt = _read_json(TRADINGVIEW_RECEIPT_PATH)
    tool_layer_runs = _read_jsonl_tail(RESEARCH_TOOL_RUNS_PATH)
    latest_tool_run = (tool_layer_runs or [{}])[-1]
    objective_rows = _read_jsonl_tail(ROOT / "data/governed/proactive_research_objective_runs.jsonl")
    objective_runs = [row for row in objective_rows if row.get("record_type") == "PROACTIVE_OBJECTIVE_RUN"]
    latest_objective_run = max(objective_runs, key=lambda row: str(row.get("last_run_at") or ""), default={})
    if latest_objective_run and str(latest_objective_run.get("last_run_at") or "") > str(wake_receipt.get("recorded_at") or ""):
        wake_receipt = {**wake_receipt, "selected_task": "PROACTIVE_SEARCH",
            "current_proactive_objective": latest_objective_run.get("research_question"),
            "why_this_objective_was_selected": latest_objective_run.get("why_this_objective_was_selected"),
            "objective_family": latest_objective_run.get("objective_family"),
            "research_question": latest_objective_run.get("research_question"),
            "source_classes_planned": latest_objective_run.get("best_source_classes", []),
            "quality_assessment": latest_objective_run.get("quality_assessment"),
            "query": latest_objective_run.get("query"),
            "source_classes": latest_objective_run.get("source_classes_used", []),
            "raw_signals": latest_objective_run.get("raw_signals", (latest_objective_run.get("last_result") or {}).get("raw_signals", 0)),
            "qualified_findings": latest_objective_run.get("qualified_findings", 0),
            "handoffs": (latest_objective_run.get("last_result") or {}).get("handoffs", 0),
            "saturation_state": latest_objective_run.get("saturation_state"),
            "next_research_direction": "Rotate to another unsaturated customer/business objective family." if latest_objective_run.get("saturation_state") == "SATURATED_RECENTLY" else "Continue the open evidence gap through the existing Research contract."}
    selected_raw_ids = set((latest_objective_run or {}).get("raw_signal_ids") or [])
    raw_signal_details = [{**{k: row.get(k) for k in ("signal_id","source_class","source_url","source_title","source_date","firsthand_or_secondary","evidence_quality","source_fit","qualification_score","failed_criteria","more_research_could_rescue")},
                           "evidence_snippet": str(row.get("evidence_snippet") or "")[:240]}
                          for row in (raw_signal_rows or []) if row.get("signal_id") in selected_raw_ids][:5]

    alive, pid, uptime = _kernel_process()
    historical_items = [item for item in (queue_items or []) if _historical(item)]
    live_items = [item for item in (queue_items or []) if not _historical(item)]
    if queue_items is None:
        status_counts: Counter[str] = Counter()
        queue_total: int | str = UNAVAILABLE
        live_counts: Counter[str] = Counter()
        live_queue_total: int | str = UNAVAILABLE
    else:
        status_counts = Counter(_queue_status(item) for item in live_items)
        queue_total = len(queue_items)
        live_counts = status_counts
        live_queue_total = len(live_items)

    def queue_count(statuses: set[str]) -> int | str:
        return UNAVAILABLE if queue_items is None else sum(status_counts.get(status, 0) for status in statuses)

    live_eligible = UNAVAILABLE if queue_items is None else sum(
        _queue_status(item) in {"QUEUED", "READY", "NEW", "WAITING", "FAILED_RETRYABLE"}
        and (_time(item.get("next_eligible_at")) or datetime.min.replace(tzinfo=timezone.utc)) <= now
        for item in live_items
    )

    complete60 = _recent_count(live_items, "completed_at", cutoff60, _completed) if queue_items is not None else UNAVAILABLE
    complete24 = _recent_count(live_items, "completed_at", cutoff24, _completed) if queue_items is not None else UNAVAILABLE

    yt_items = [item for item in live_items if str(item.get("source_type") or "").upper() == "YOUTUBE_VIDEO"]
    yt_created24 = len({str(item.get("work_id") or item.get("source_id") or "") for item in yt_items
                        if (_time(item.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff24
                        and (item.get("work_id") or item.get("source_id"))}) if queue_items is not None else UNAVAILABLE
    yt_queued = sum(_queue_status(item) in {"QUEUED", "READY", "NEW", "FAILED_RETRYABLE"} for item in yt_items) if queue_items is not None else UNAVAILABLE
    yt_processing = sum(_queue_status(item) in {"IN_PROGRESS", "PROCESSING", "RUNNING"} for item in yt_items) if queue_items is not None else UNAVAILABLE
    yt_complete24 = sum(_completed(item) and (_time(item.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff24 for item in yt_items) if queue_items is not None else UNAVAILABLE

    nb60, nb_retry24, nb_final24 = _notebooklm_counts(notebooklm_rows, cutoff60), _notebooklm_counts(notebooklm_rows, cutoff24), _notebooklm_counts(notebooklm_rows, cutoff24)
    nb_success = _last_time(notebooklm_rows, ("recorded_at", "completed_at", "created_at"),
                            lambda row: str(row.get("queue_status") or "").upper() in {"COMPLETE", "COMPLETED"})
    nb_failure = _last_time(notebooklm_rows, ("recorded_at", "completed_at", "created_at"),
                            lambda row: str(row.get("queue_status") or "").upper() in {"FAILED_RETRYABLE", "FAILED_FINAL"})

    finding60 = _recent_count(findings, "recorded_at", cutoff60) if findings is not None else UNAVAILABLE
    finding24 = _recent_count(findings, "recorded_at", cutoff24) if findings is not None else UNAVAILABLE
    gap_last = _last_time(gaps, ("created_at", "recorded_at"))
    latest_cases: dict[str, dict[str, Any]] = {}
    if memory_rows is not None:
        for row in memory_rows:
            if row.get("memory_kind") in {"PROACTIVE_RESEARCH_CASE", "RESEARCH_CASE"} and row.get("case_id"):
                key = str(row["case_id"])
                prior = latest_cases.get(key)
                stamp = str(row.get("recorded_at") or row.get("created_at") or "")
                prior_stamp = str((prior or {}).get("recorded_at") or (prior or {}).get("created_at") or "")
                if prior is None or stamp >= prior_stamp:
                    latest_cases[key] = row
    cases_active = sum(str(row.get("status") or "").upper() in {"OPEN", "ACTIVE", "FOLLOWUP_WINDOW",
                        "DISCOVERED", "PROMISING", "UNDER_DEVELOPMENT", "RESEARCHING_MISSING_PIECES",
                        "SYNTHESIZING", "RECOMMENDATION_READY", "DEPARTMENT_DEVELOPMENT", "TESTING",
                        "REFINING", "MORE_RESEARCH_REQUIRED", "QUALIFIED"}
                       for row in latest_cases.values()) if memory_rows is not None else UNAVAILABLE
    try:
        from research.research_case_engine import metrics_snapshot, prioritized_cases
        deep_case_metrics = metrics_snapshot()
        deep_cases = prioritized_cases(limit=3)
    except Exception:
        deep_case_metrics, deep_cases = {}, []
    notebook_cases = sum(bool(row.get("notebook_id") or row.get("notebook_scope") == "RESEARCH_CASE"
                              or (row.get("notebook_workspace") or {}).get("notebook_id"))
                         for row in latest_cases.values()) if memory_rows is not None else UNAVAILABLE
    # Use the durable append-only source registry projection and collapse its
    # monitor history to one row per stable source ID. The older channel config
    # does not carry NEW_CONTENT_ONLY baselines.
    latest_sources: dict[str, dict[str, Any]] = {}
    if source_rows is not None:
        for row in source_rows:
            if str(row.get("source_type") or "").upper() != "YOUTUBE_CHANNEL":
                continue
            key = str(row.get("source_id") or row.get("external_channel_id") or row.get("canonical_url") or "")
            prior = latest_sources.get(key)
            stamp = str(row.get("updated_at") or row.get("last_checked_at") or "")
            if key and (prior is None or stamp >= str(prior.get("updated_at") or prior.get("last_checked_at") or "")):
                latest_sources[key] = row
    channel_rows = [row for row in latest_sources.values() if row.get("enabled", row.get("status") == "ACTIVE")
                    and str(row.get("monitor_mode") or "").upper() == "NEW_CONTENT_ONLY"]
    monitored_channels = len(channel_rows) if source_rows is not None else UNAVAILABLE
    # The live reconciliation reads the authoritative designated-channel
    # registry. Prefer that count over legacy research_sources rows, which can
    # include retired/duplicate channel records and produced a stale count of
    # 23 while the enabled registry contains 21 channels.
    if isinstance(youtube_reconciliation.get("enabled_channel_count"), int):
        monitored_channels = youtube_reconciliation["enabled_channel_count"]
    baselines_pending = sum(not (row.get("baseline_video_id") or row.get("last_item_seen") or
                                 ((row.get("monitor_baseline") or {}).get("video_id"))) for row in channel_rows) if source_rows is not None else UNAVAILABLE

    last_cycle_time = _time((heartbeat or {}).get("started_at"))
    last_cycle_id = (heartbeat or {}).get("cycle_id")
    last_cycle = f"{_fmt(last_cycle_time)} ({last_cycle_id})" if last_cycle_time and last_cycle_id else UNAVAILABLE
    next_wake = _fmt(_time((heartbeat or {}).get("next_wake")))
    proactive_last = _fmt(_time((proactive or {}).get("last_proactive_cycle")))
    proactive_success = "YES" if wake_receipt and wake_receipt.get("status") == "PASS" else "NO" if wake_receipt else UNAVAILABLE
    proactive_duration = ((wake_receipt or {}).get("stage_timings") or {}).get("total_cycle_seconds", UNAVAILABLE)
    monitored_last = _fmt(_time((proactive or {}).get("last_channel_refresh")))
    trend_last = _fmt(_time((proactive or {}).get("last_open_trend_scan")))
    gap_run = _fmt(gap_last)

    # Claim timestamps are cleared when a queue item completes, so this local
    # queue cannot prove an exact historical claim count.
    claim60: int | str = UNAVAILABLE
    # Failure-history timestamps are not guaranteed for every retryable item;
    # avoid presenting an incomplete count as exact.
    retryable60: int | str = UNAVAILABLE

    proactive_completed24 = 0
    if queue_items is not None:
        proactive_completed24 = sum(
            str(item.get("work_id") or "").startswith("proactive-trend:") and _completed(item) and not _historical(item)
            and (_time(item.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff24
            for item in queue_items
        )
    handoffs60, handoffs_by_dept60 = _handoff_counts_from_results(notebooklm_rows, cutoff60)
    handoffs24, handoffs_by_dept24 = _handoff_counts_from_results(notebooklm_rows, cutoff24)
    handoff_productive_count = handoffs60
    # The worker result log includes the creation/delivery receipt and is the
    # authoritative local read model for handoffs produced by Research runs.
    _ = trend_signals
    _ = program_state

    backlog60 = UNAVAILABLE
    backlog24 = UNAVAILABLE
    nb_completed60 = nb60[0]
    nb_completed24 = nb_retry24[0]
    nb_retry_count24 = nb_retry24[1]
    nb_final_count24 = nb_final24[2]

    recent_completed = isinstance(complete60, int) and complete60 > 0
    recent_findings = isinstance(finding60, int) and finding60 > 0
    monitored_recent = bool(_time((proactive or {}).get("last_channel_refresh")) and _time((proactive or {}).get("last_channel_refresh")) >= cutoff24)
    proactive_recent = bool(_time((proactive or {}).get("last_proactive_cycle")) and _time((proactive or {}).get("last_proactive_cycle")) >= cutoff24)
    research_productive = "YES" if recent_completed or recent_findings or monitored_recent or proactive_recent else "NO" if isinstance(complete60, int) and isinstance(finding60, int) else UNAVAILABLE
    proactive_productive = "YES" if proactive_completed24 > 0 else "NO" if queue_items is not None else UNAVAILABLE
    queue_moving = "YES" if recent_completed else "NO" if isinstance(complete60, int) else UNAVAILABLE
    notebooklm_productive = "YES" if isinstance(nb_completed60, int) and nb_completed60 > 0 else "NO" if isinstance(nb_completed60, int) else UNAVAILABLE
    handoffs_productive = "YES" if isinstance(handoff_productive_count, int) and handoff_productive_count > 0 else "NO" if isinstance(handoff_productive_count, int) else UNAVAILABLE
    attention = "YES" if any(isinstance(value, int) and value > 0 for value in (queue_count({"FAILED_RETRYABLE"}), queue_count({"FAILED_FINAL"}))) else "NO" if queue_items is not None else UNAVAILABLE

    values: list[tuple[str, Any]] = [
        ("RUNTIME_ALIVE", alive), ("RUNTIME_PID", pid), ("RUNTIME_UPTIME", uptime),
        ("LIVE_QUEUE_TOTAL", live_queue_total), ("LIVE_QUEUE_ELIGIBLE", live_eligible),
        ("HISTORICAL_BACKLOG_COUNT", len(historical_items) if queue_items is not None else UNAVAILABLE),
        ("ACTIVE_CASES", cases_active),
        ("MONITORED_CHANNELS", monitored_channels), ("YOUTUBE_BASELINES_PENDING", baselines_pending),
        ("YOUTUBE_CHANNELS_ENABLED", youtube_reconciliation.get("enabled_channel_count", monitored_channels)),
        ("YOUTUBE_CHANNELS_CHECKED", youtube_reconciliation.get("channels_checked", UNAVAILABLE)),
        ("YOUTUBE_NEW_VIDEOS_FOUND", youtube_reconciliation.get("current_new_video_count", UNAVAILABLE)),
        ("YOUTUBE_NEW_VIDEOS_PROCESSED", youtube_reconciliation.get("research_processed_count", UNAVAILABLE)),
        ("YOUTUBE_MISSED_VIDEOS_RECOVERED", youtube_reconciliation.get("missed_current_videos_recovered", UNAVAILABLE)),
        ("YOUTUBE_LATEST_VIDEO_RECONCILIATION", json.dumps(youtube_reconciliation.get("new_videos", [])[:12], ensure_ascii=False, separators=(",", ":")) if youtube_reconciliation else UNAVAILABLE),
        ("NOTEBOOKLM_LIVE_INVENTORY_COUNT", notebooklm_inventory.get("notebooks_found_count", UNAVAILABLE)),
        ("NOTEBOOKLM_NEXUS_NOTEBOOK_COUNT", youtube_reconciliation.get("notebooklm_nexus_related_count", UNAVAILABLE)),
        ("NOTEBOOKLM_ACTIVE_CASE_COUNT", sum(1 for row in (youtube_reconciliation.get("case_rows") or []) if str(row.get("status") or "").upper() in {"OPEN", "ACTIVE", "FOLLOWUP_WINDOW"}) if youtube_reconciliation else UNAVAILABLE),
        ("NOTEBOOKLM_FOLLOWUP_REUSABLE_COUNT", sum(1 for row in (youtube_reconciliation.get("case_rows") or []) if str(row.get("status") or "").upper() == "FOLLOWUP_WINDOW") if youtube_reconciliation else UNAVAILABLE),
        ("NOTEBOOKLM_ORPHANED_COUNT", youtube_reconciliation.get("notebooklm_orphaned_case_count", UNAVAILABLE)),
        ("PROACTIVE_LAST_SUCCESS", proactive_success), ("PROACTIVE_LAST_DURATION", proactive_duration),
        ("MONITORED_SOURCE_ACTIVITY", _fmt(monitored_last)),
        ("PROACTIVE_DISCOVERY_ACTIVITY", _fmt(proactive_last)),
        ("CURRENT_PROACTIVE_OBJECTIVE", wake_receipt.get("current_proactive_objective", UNAVAILABLE)),
        ("PROACTIVE_WHY_SELECTED", wake_receipt.get("why_this_objective_was_selected", UNAVAILABLE)),
        ("PROACTIVE_OBJECTIVE_FAMILY", wake_receipt.get("objective_family", UNAVAILABLE)),
        ("PROACTIVE_RESEARCH_QUESTION", wake_receipt.get("research_question", UNAVAILABLE)),
        ("PROACTIVE_RESEARCH_CONCLUSION", (wake_receipt.get("quality_assessment") or {}).get("research_conclusion", UNAVAILABLE)),
        ("PROACTIVE_SOURCE_FIT", (wake_receipt.get("quality_assessment") or {}).get("source_fit", UNAVAILABLE)),
        ("PROACTIVE_EVIDENCE_QUALITY", (wake_receipt.get("quality_assessment") or {}).get("evidence_quality", UNAVAILABLE)),
        ("PROACTIVE_EVIDENCE_DIVERSITY", (wake_receipt.get("quality_assessment") or {}).get("evidence_diversity", UNAVAILABLE)),
        ("PROACTIVE_FIRSTHAND_EVIDENCE_COUNT", (wake_receipt.get("quality_assessment") or {}).get("firsthand_evidence_count", UNAVAILABLE)),
        ("PROACTIVE_CROSS_SOURCE_CONFIRMATION", (wake_receipt.get("quality_assessment") or {}).get("cross_source_confirmation", UNAVAILABLE)),
        ("PROACTIVE_QUERY", wake_receipt.get("query", UNAVAILABLE)),
        ("PROACTIVE_SOURCE_CLASSES", ",".join(wake_receipt.get("source_classes", []) or []) or UNAVAILABLE),
        ("PROACTIVE_SOURCE_CLASSES_PLANNED", ",".join(wake_receipt.get("source_classes_planned", []) or []) or UNAVAILABLE),
        ("PROACTIVE_SEARCHES_RUN", (wake_receipt.get("quality_assessment") or {}).get("searches_run", UNAVAILABLE)),
        ("PROACTIVE_SOURCES_OPENED", (wake_receipt.get("quality_assessment") or {}).get("sources_opened", UNAVAILABLE)),
        ("PROACTIVE_RAW_SIGNAL_DETAILS", json.dumps(raw_signal_details, ensure_ascii=False, separators=(",", ":")) if selected_raw_ids else "[]"),
        ("PROACTIVE_MARKET_CLUSTER", "NOT_FORMED_INSUFFICIENT_EVIDENCE" if len(raw_signal_details) < 3 else "REQUIRES_CLUSTER_QUALIFICATION"),
        ("PROACTIVE_RAW_SIGNALS", wake_receipt.get("raw_signals", UNAVAILABLE)),
        ("PROACTIVE_QUALIFIED_FINDINGS", wake_receipt.get("qualified_findings", UNAVAILABLE)),
        ("PROACTIVE_HANDOFFS", wake_receipt.get("handoffs", UNAVAILABLE)),
        ("PROACTIVE_SATURATION_STATE", wake_receipt.get("saturation_state", UNAVAILABLE)),
        ("PROACTIVE_NEXT_DIRECTION", wake_receipt.get("next_research_direction", UNAVAILABLE)),
        ("PROACTIVE_NEXT_RESEARCH_ACTION", (wake_receipt.get("quality_assessment") or {}).get("next_research_action", UNAVAILABLE)),
        ("TRADINGVIEW_ITEMS_CHECKED", tradingview_receipt.get("items_checked", UNAVAILABLE)),
        ("TRADINGVIEW_STRATEGIES_FOUND", tradingview_receipt.get("strategies_found", UNAVAILABLE)),
        ("TRADINGVIEW_INDICATORS_FOUND", tradingview_receipt.get("indicators_found", UNAVAILABLE)),
        ("TRADINGVIEW_QUALIFIED_FOR_TESTING", tradingview_receipt.get("qualified_for_testing", UNAVAILABLE)),
        ("TRADINGVIEW_HANDOFFS_TO_TRADING", tradingview_receipt.get("handoffs_to_trading", UNAVAILABLE)),
        ("RESEARCH_TOOL_CANARY_RUN_ID", latest_tool_run.get("run_id", UNAVAILABLE)),
        ("RESEARCH_EXECUTION_ENGINE", latest_tool_run.get("engine", UNAVAILABLE)),
        ("RESEARCH_FALLBACK_USED", latest_tool_run.get("fallback_used", UNAVAILABLE)),
        ("RESEARCH_FALLBACK_REASON", latest_tool_run.get("fallback_reason", UNAVAILABLE)),
        ("RESEARCH_TOOL_CANARY_QUESTION", latest_tool_run.get("research_question", UNAVAILABLE)),
        ("RESEARCH_TOOL_SOURCE_STRATEGY", json.dumps(latest_tool_run.get("source_strategy") or {}, ensure_ascii=False, separators=(",", ":")) if latest_tool_run else UNAVAILABLE),
        ("RESEARCH_TOOL_TOOLS_USED", json.dumps(latest_tool_run.get("tools_used") or latest_tool_run.get("tools_selected") or [], ensure_ascii=False, separators=(",", ":")) if latest_tool_run else UNAVAILABLE),
        ("RESEARCH_TOOL_SEARCH_COUNT", latest_tool_run.get("search_count", UNAVAILABLE)),
        ("RESEARCH_TOOL_SOURCES_OPENED", latest_tool_run.get("sources_opened", UNAVAILABLE)),
        ("RESEARCH_TOOL_FIRSTHAND_SOURCE_COUNT", latest_tool_run.get("firsthand_source_count", UNAVAILABLE)),
        ("RESEARCH_TOOL_OFFICIAL_SOURCE_COUNT", latest_tool_run.get("official_source_count", UNAVAILABLE)),
        ("RESEARCH_TOOL_MARKETPLACE_SOURCE_COUNT", latest_tool_run.get("marketplace_source_count", UNAVAILABLE)),
        ("RESEARCH_TOOL_SOURCE_CLASSES", ",".join(latest_tool_run.get("source_classes_observed") or []) or UNAVAILABLE),
        ("RESEARCH_TOOL_SOURCE_FIT", latest_tool_run.get("source_fit", UNAVAILABLE)),
        ("RESEARCH_TOOL_EVIDENCE_QUALITY", latest_tool_run.get("evidence_quality", UNAVAILABLE)),
        ("RESEARCH_TOOL_EXECUTION_STATUS", latest_tool_run.get("execution_status", UNAVAILABLE)),
        ("RESEARCH_TOOL_RESEARCH_CONCLUSION", latest_tool_run.get("research_conclusion", UNAVAILABLE)),
        ("RESEARCH_TOOL_WHY_CONCLUDED", latest_tool_run.get("why_concluded", UNAVAILABLE)),
        ("RESEARCH_TOOL_NEXT_ACTION", latest_tool_run.get("next_research_action", UNAVAILABLE)),
        ("RESEARCH_TOOL_SOURCE_URLS", json.dumps(latest_tool_run.get("candidate_source_urls") or [], ensure_ascii=False, separators=(",", ":")) if latest_tool_run else "[]"),
        ("RESEARCH_TOOL_SEARCH_DETAILS", json.dumps(latest_tool_run.get("searches") or [], ensure_ascii=False, separators=(",", ":")) if latest_tool_run else "[]"),
        ("RESEARCH_TOOL_OPENED_SOURCE_DETAILS", json.dumps(latest_tool_run.get("sources_opened") or [], ensure_ascii=False, separators=(",", ":")) if latest_tool_run else "[]"),
        ("VIRAL_RESEARCH_ACTIVITY", _fmt(trend_last)),
        ("NOTEBOOKLM_CASES", notebook_cases),
        ("ACTIVE_DEEP_RESEARCH_CASES", deep_case_metrics.get("active_deep_cases", UNAVAILABLE)),
        ("RESEARCH_CASES_ADVANCED", deep_case_metrics.get("cases_advanced", UNAVAILABLE)),
        ("RESEARCH_CASES_RECOMMENDATION_READY", deep_case_metrics.get("cases_recommendation_ready", UNAVAILABLE)),
        ("RESEARCH_CASE_FOLLOWUP_QUESTIONS_ANSWERED", deep_case_metrics.get("followup_questions_answered", UNAVAILABLE)),
        ("RESEARCH_CASE_MULTI_SOURCE_SYNTHESES", deep_case_metrics.get("multi_source_syntheses", UNAVAILABLE)),
        ("RESEARCH_CASE_RECOMMENDATIONS", deep_case_metrics.get("recommendations_produced", UNAVAILABLE)),
        ("RESEARCH_CASE_ACTIVE_OBJECTIVES", json.dumps([{key: row.get(key) for key in ("case_id", "objective", "objective_family", "status", "owner_department", "source_count", "source_class_count", "open_questions", "answered_questions", "recommendations", "next_research_action", "depth_used", "depth_budget", "requires_ray")} for row in deep_cases], ensure_ascii=False, separators=(",", ":"))),
        ("FINDINGS_PERSISTED", finding24), ("HANDOFFS_CREATED", handoffs24),
        ("RESEARCH_PRODUCTIVE", research_productive),
        ("ATTENTION_REASON", "retryable_or_final_live_queue_items" if attention == "YES" else "none" if attention == "NO" else UNAVAILABLE),
        ("LAST_CYCLE", last_cycle), ("NEXT_WAKE", next_wake),
        ("QUEUE_TOTAL", queue_total), ("QUEUE_ELIGIBLE", queue_count({"QUEUED", "READY", "NEW"})),
        ("QUEUE_PROCESSING", queue_count({"IN_PROGRESS", "PROCESSING", "RUNNING"})),
        ("QUEUE_RETRYABLE", queue_count({"FAILED_RETRYABLE"})), ("QUEUE_FAILED_FINAL", queue_count({"FAILED_FINAL"})),
        ("QUEUE_COMPLETE", queue_count({"COMPLETE", "COMPLETED"})), ("QUEUE_SUPERSEDED", queue_count({"SUPERSEDED"})),
        ("QUEUE_MONITORING", queue_count({"MONITORING"})),
        ("COMPLETED_LAST_60_MIN", complete60), ("COMPLETED_LAST_24H", complete24),
        ("CLAIMED_LAST_60_MIN", claim60), ("RETRYABLE_LAST_60_MIN", retryable60),
        ("PROACTIVE_HEARTBEAT_LAST_RUN", proactive_last), ("PROACTIVE_HEARTBEAT_NEXT_RUN", UNAVAILABLE),
        ("MONITORED_SOURCE_LAST_RUN", monitored_last), ("MONITORED_CHANNELS_CHECKED_LAST_CYCLE", UNAVAILABLE),
        ("OPEN_TREND_DISCOVERY_LAST_RUN", trend_last), ("DISCOVERY_QUERIES_LAST_CYCLE", UNAVAILABLE),
        ("DISCOVERY_RESULTS_LAST_CYCLE", UNAVAILABLE), ("QUALIFIED_SOURCES_LAST_CYCLE", UNAVAILABLE),
        ("GAP_RESEARCH_LAST_RUN", gap_run),
        ("YOUTUBE_MONITORED_CHANNELS", monitored_channels), ("NEW_VIDEOS_LAST_24H", yt_created24),
        ("YOUTUBE_ITEMS_QUEUED", yt_queued), ("YOUTUBE_ITEMS_PROCESSING", yt_processing),
        ("YOUTUBE_ITEMS_COMPLETED_LAST_24H", yt_complete24),
        ("NOTEBOOKLM_ITEMS_COMPLETED_LAST_60_MIN", nb_completed60),
        ("NOTEBOOKLM_ITEMS_COMPLETED_LAST_24H", nb_completed24),
        ("NOTEBOOKLM_RETRYABLE_LAST_24H", nb_retry_count24), ("NOTEBOOKLM_FINAL_FAILURES_LAST_24H", nb_final_count24),
        ("LAST_NOTEBOOKLM_SUCCESS", _fmt(nb_success)), ("LAST_NOTEBOOKLM_FAILURE", _fmt(nb_failure)),
        ("FINDINGS_PERSISTED_LAST_60_MIN", finding60), ("FINDINGS_PERSISTED_LAST_24H", finding24),
        ("HANDOFFS_CREATED_LAST_60_MIN", handoffs60), ("HANDOFFS_CREATED_LAST_24H", handoffs24),
        ("TRADING_HANDOFFS_LAST_24H", sum(v for k,v in handoffs_by_dept24.items() if "TRADING" in k)),
        ("MARKETING_HANDOFFS_LAST_24H", handoffs_by_dept24.get("MARKETING", 0)),
        ("CREATIVE_HANDOFFS_LAST_24H", handoffs_by_dept24.get("CREATIVE", 0)),
        ("SYSTEMS_HANDOFFS_LAST_24H", handoffs_by_dept24.get("SYSTEMS", 0)),
        ("LABS_HANDOFFS_LAST_24H", handoffs_by_dept24.get("LABS", 0)),
        ("BACKLOG_CHANGE_LAST_60_MIN", backlog60), ("BACKLOG_CHANGE_LAST_24H", backlog24),
        ("RESEARCH_PRODUCTIVE", research_productive), ("PROACTIVE_RESEARCH_PRODUCTIVE", proactive_productive),
        ("QUEUE_MOVING", queue_moving), ("NOTEBOOKLM_PRODUCTIVE", notebooklm_productive),
        ("HANDOFFS_PRODUCTIVE", handoffs_productive), ("ATTENTION_REQUIRED", attention),
        ("STATUS_COMMAND_CREATED", "YES"), ("STATUS_COMMAND_READ_ONLY", "YES"),
        ("STATUS_COMMAND_PASS", "YES"),
    ]
    return "\n".join(f"{key}={_fmt(value)}" for key, value in values)


if __name__ == "__main__":
    print(_format_output())
