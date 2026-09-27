#!/usr/bin/env python3
"""Generate a read-only two-hour Research intelligence status report.

This observer reads existing durable receipts and runtime state. It never
selects work, claims a queue item, starts/stops Research, or mutates scheduling.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
# Make the canonical script package importable when this supported on-demand
# command is run directly, without requiring callers to set PYTHONPATH.
sys.path.insert(0, str(ROOT / "scripts"))
HISTORY = ROOT / "reports/research/two_hour"
HEARTBEAT = ROOT / "data/runtime/research_heartbeat.json"
JOBS = ROOT / "data/runtime/research_execution_jobs.jsonl"
PROGRAMS = ROOT / "data/runtime/research_program_registry.json"
PROGRAM_STATE = ROOT / "data/runtime/research_program_service_state.json"
QUEUE = ROOT / "data/runtime/research_work_queue.json"

SUBSTANTIVE = {"AI_RESULT_INTERPRETATION", "EVIDENCE_READY"}
FAILURE_PREFIXES = ("FAILED", "DEGRADED", "ERROR", "BLOCKED")
CANONICAL_SCOPE = [
    "CUSTOMER_NEEDS", "BUSINESS_FUNDING", "FINANCIAL_INSTITUTION_INTELLIGENCE",
    "YOUTUBE_INTELLIGENCE", "SEO_SEARCH_INTELLIGENCE", "GITHUB_OPEN_SOURCE",
    "LAST30DAYS_PROACTIVE", "AFFILIATE_SOLUTION_DISCOVERY", "COMPETITOR_INTELLIGENCE",
    "PROJECT_SUPPORT", "RESEARCH_FOLLOWUPS", "DEPARTMENT_PROJECT_REQUESTS",
]


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except ValueError:
                continue
    except OSError:
        pass
    return rows


def stamp(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def in_window(row: dict, start: datetime, end: datetime) -> bool:
    at = stamp(row.get("at") or row.get("evaluated_at") or row.get("recorded_at") or row.get("created_at") or row.get("updated_at"))
    return bool(at and start <= at.astimezone(timezone.utc) <= end)


def launchd_state() -> dict:
    try:
        result = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/com.nexus.continuous-loop"], capture_output=True, text=True, timeout=5)
        text = result.stdout
        pid = re.search(r"\n\tpid = (\d+)", text)
        return {"running": result.returncode == 0, "pid": int(pid.group(1)) if pid else None, "label": "com.nexus.continuous-loop"}
    except (OSError, subprocess.TimeoutExpired):
        return {"running": False, "pid": None, "label": "com.nexus.continuous-loop"}


def rows_for(path: Path, start: datetime, end: datetime) -> tuple[list[dict], list[dict]]:
    all_rows = read_jsonl(path)
    return all_rows, [row for row in all_rows if in_window(row, start, end)]


def latest_by(rows: list[dict], key: str) -> list[dict]:
    latest = {}
    for row in rows:
        if row.get(key):
            latest[str(row[key])] = row
    return list(latest.values())


def report(window_hours: int = 2, today: bool = False) -> dict:
    end = datetime.now(timezone.utc)
    local_end = end.astimezone(ZoneInfo("America/Phoenix"))
    start = local_end.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc) if today else end - timedelta(hours=window_hours)
    heartbeat = read_json(HEARTBEAT, {})
    programs = read_json(PROGRAMS, [])
    if isinstance(programs, dict):
        programs = programs.get("programs", [])
    program_state = read_json(PROGRAM_STATE, {})
    queue = read_json(QUEUE, {})
    all_jobs, window_jobs = rows_for(JOBS, start, end)
    governed = {
        "alpha": read_jsonl(ROOT / "data/governed/alpha_evaluations.jsonl"),
        "handoffs": read_jsonl(ROOT / "data/governed/research_v2_handoffs.jsonl"),
        "returns": read_jsonl(ROOT / "data/governed/research_requests.jsonl"),
        "questions": read_jsonl(ROOT / "data/governed/research_questions.jsonl"),
    }
    window_alpha = [row for row in governed["alpha"] if in_window(row, start, end)]
    today_start = end.astimezone(ZoneInfo("America/Phoenix")).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    today_jobs = [row for row in all_jobs if in_window(row, today_start, end)]
    today_alpha = [row for row in governed["alpha"] if in_window(row, today_start, end)]
    source_selected = [row for row in window_jobs if row.get("status") == "SOURCE_SELECTED"]
    analyses = [row for row in window_jobs if row.get("status") == "AI_RESULT_INTERPRETATION"]
    evidence = [row for row in window_jobs if row.get("status") == "EVIDENCE_READY" and int(row.get("content_count") or 0) > 0]
    failures = [row for row in window_jobs if str(row.get("status") or "").startswith(FAILURE_PREFIXES) or row.get("result_status") == "DEGRADED"]
    handoffs = [row for row in governed["handoffs"] if in_window(row, start, end)]
    returns = [row for row in governed["returns"] if in_window(row, start, end)]
    questions = [row for row in governed["questions"] if in_window(row, start, end)]
    proactive_questions = [row for row in questions if row.get("research_mode") in {"GOCLEAR_PROACTIVE", "NEXUS_DEPARTMENTAL_PROACTIVE"}]
    proactive_execs = [row for row in window_jobs if row.get("research_mode") in {"GOCLEAR_PROACTIVE", "NEXUS_DEPARTMENTAL_PROACTIVE"} or row.get("alpha_eligible")]
    department_research = Counter(str(row.get("DEPARTMENT") or row.get("department_target") or "UNOWNED") for row in proactive_questions + proactive_execs)
    explicit_items = [row for row in queue.get("items", []) if row.get("research_mode") in {"GOCLEAR_PROACTIVE", "NEXUS_DEPARTMENTAL_PROACTIVE"} or row.get("alpha_eligible")]
    unowned = sum(1 for row in explicit_items if not row.get("department_target"))
    unconsumed = sum(1 for row in explicit_items if row.get("department_target") and row.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"})
    followup_rows = [row for row in governed["returns"] if row.get("schema_version") == "nexus.research-more-followup.v1"]
    followup_window = [row for row in followup_rows if in_window(row, start, end)]
    followup_ids = {str(row.get("work_id") or "") for row in queue.get("items", []) if row.get("alpha_followup_required")}
    alpha_by_finding = Counter(str(row.get("research_item_id") or row.get("finding_id") or "") for row in governed["alpha"])
    # Count only the second and later review for a logical finding.  Counting
    # every row for a finding with multiple receipts would inflate follow-up
    # productivity and could mistake the original review for a re-review.
    seen_alpha = set()
    second_reviews = []
    for row in sorted(governed["alpha"], key=lambda value: str(value.get("evaluated_at") or value.get("completed_at") or "")):
        finding_key = str(row.get("research_item_id") or row.get("finding_id") or "")
        if finding_key in seen_alpha and in_window(row, start, end):
            second_reviews.append(row)
        seen_alpha.add(finding_key)
    source_failures = [row for row in window_jobs if str(row.get("status") or "").startswith(("FAILED", "DEGRADED"))]
    source_fallbacks = [row for row in window_jobs if row.get("status") == "STRATEGY_CHANGED"]
    department_work_orders = [row for row in read_jsonl(ROOT / "data/governed/work_orders.jsonl") if in_window(row, start, end) and row.get("owner_specialist")]
    try:
        from nexus_agent_platform.project_advancement import advancement_metrics
        company_advancement = advancement_metrics(since=start.isoformat())
    except Exception as exc:
        company_advancement = {"status": "UNAVAILABLE", "error": str(exc)[:200]}
    decisions = Counter(str(row.get("decision") or "UNKNOWN").upper() for row in window_alpha)
    sources = Counter(str(row.get("source_type") or row.get("source_id") or "UNKNOWN") for row in source_selected)
    return {
        "schema_version": "nexus.research.two-hour-report.v1",
        "generated_at": end.isoformat(),
        "window": {"start": start.isoformat(), "end": end.isoformat(), "hours": window_hours},
        "system": {
            "research_service": launchd_state(),
            "heartbeat": heartbeat,
            "next_wake": heartbeat.get("next_wake"),
            "active_programs": [row.get("program_id") for row in programs if row.get("enabled", True)],
            "failed_or_retrying_programs": [key for key, value in program_state.items() if value.get("blocker") or value.get("starvation_status") in {"BLOCKED", "STARVED"}],
            "provider_model_health": {"alpha": "observed from persisted Alpha receipts", "provider": sorted({str(row.get("provider")) for row in window_alpha if row.get("provider")})},
            "continuous_scope": {"programs": CANONICAL_SCOPE, "single_scheduler": "com.nexus.continuous-loop", "source": "existing scheduler/lane registry"},
        },
        "what_research_did": {
            "channel_checks": len([row for row in window_jobs if row.get("status") == "SOURCE_SELECTED"]),
            "source_selected": len(source_selected),
            "transcripts_acquired": len([row for row in window_jobs if row.get("status") == "TRANSCRIPT_ACQUIRED"]),
            "transcripts_analyzed": len([row for row in analyses if "youtube" in json.dumps(row).lower()]),
            "ai_analyses": len(analyses),
            "substantive_findings": len(evidence),
            "source_types": dict(sources),
            "follow_up_searches": len([row for row in window_jobs if row.get("alpha_followup_required") or row.get("parent_request_id")]),
        },
        "domains": {
            "youtube": {"videos_selected": len([row for row in source_selected if row.get("source_type") == "YOUTUBE_VIDEO"]), "ai_analyses": len([row for row in analyses if "youtube" in json.dumps(row).lower()])},
            "financial_institution_intelligence": {"source_count": len([row for row in window_jobs if any(x in json.dumps(row).lower() for x in ("bank", "lender", "credit"))]), "substantive_findings": len([row for row in evidence if any(x in json.dumps(row).lower() for x in ("bank", "lender", "credit"))])},
            "customer_needs": {"substantive_findings": 0, "status": "NO_DOMAIN_TAG_IN_WINDOW"},
            "business_funding": {"substantive_findings": len([row for row in evidence if any(x in json.dumps(row).lower() for x in ("funding", "loan", "lender"))])},
            "seo_search": {"substantive_findings": len([row for row in evidence if "seo" in json.dumps(row).lower()])},
            "github_technology": {"substantive_findings": len([row for row in evidence if "github" in json.dumps(row).lower()])},
            "last30days": {"substantive_findings": len([row for row in evidence if "last30" in json.dumps(row).lower()])},
        },
        "alpha": {"reviews_completed": len(window_alpha), "decisions": dict(decisions), "provider_models": sorted({f"{row.get('provider','unknown')}:{row.get('model','unknown')}" for row in window_alpha})},
        "handoffs": {"count": len(handoffs), "departments": sorted({str(row.get("department_target") or row.get("target_department") or "UNKNOWN") for row in handoffs})},
        "returns": {"count": len(returns), "alpha_to_research": len([row for row in returns if "alpha" in json.dumps(row).lower()]), "clyde_to_research": len([row for row in returns if "clyde" in json.dumps(row).lower()])},
        "project_impact": {"projects_advanced": len([row for row in evidence if row.get("objective_progress") or row.get("information_gain")]), "projects_unchanged": 0, "projects_stalled": len(failures), "exact_bottleneck": sorted({str(row.get("failure_class") or row.get("result_status")) for row in failures})},
        "productivity": {"sources_acquired": len(evidence), "substantive_findings": len(evidence), "ai_analyses": len(analyses), "alpha_reviews": len(window_alpha), "department_handoffs": len(handoffs), "duplicates": len([row for row in window_jobs if row.get("status") == "DUPLICATE"]), "no_ops": len([row for row in window_jobs if row.get("result_status") == "NO_ACTION_REQUIRED"]), "failed_acquisitions": len(failures)},
        "proactive": {"proactive_questions_generated": len(proactive_questions), "proactive_investigations_started": len([row for row in proactive_execs if row.get("status") in {"CLAIMED", "RUNNING", "SOURCE_SELECTED", "AI_INVESTIGATION_PLAN"}]), "proactive_investigations_completed": len([row for row in proactive_execs if row.get("status") == "COMPLETED"]), "proactive_findings_created": len([row for row in evidence if row in proactive_execs]), "proactive_alpha_reviews": len([row for row in window_alpha if row.get("research_mode") in {"GOCLEAR_PROACTIVE", "NEXUS_DEPARTMENTAL_PROACTIVE"}]), "proactive_handoffs": len([row for row in handoffs if row.get("research_mode") in {"GOCLEAR_PROACTIVE", "NEXUS_DEPARTMENTAL_PROACTIVE"}]), "requested_research_completed": len([row for row in returns if row.get("status") in {"RETURNED", "READY_TO_RESUME", "RESUMED"}]), "projects_advanced": len([row for row in evidence if row.get("objective_progress") and row.get("objective_id")]), "revenue_relevant_findings": len([row for row in proactive_questions if "revenue" in json.dumps(row).lower() or "opportunity" in json.dumps(row).lower()]), "department_research_by_department": dict(department_research), "unowned_findings": unowned, "unconsumed_handoffs": unconsumed},
        "follow_up": {"research_more_created": len(followup_window), "research_more_owned": len([row for row in followup_window if row.get("owner")]), "research_more_in_progress": sum(1 for row in queue.get("items", []) if row.get("alpha_followup_required") and row.get("status") == "IN_PROGRESS"), "research_more_completed": sum(1 for row in queue.get("items", []) if row.get("alpha_followup_required") and row.get("status") == "COMPLETE"), "research_more_returned_to_alpha": len(second_reviews), "research_more_still_unowned": sum(1 for row in queue.get("items", []) if row.get("alpha_followup_required") and not row.get("owner")), "source_failures": len(source_failures), "source_fallbacks_attempted": len(source_fallbacks), "source_recoveries": len([row for row in window_jobs if row.get("status") == "COMPLETED" and row.get("alpha_followup_required")]), "alpha_second_reviews": len(second_reviews), "qualified_after_followup": len([row for row in second_reviews if row.get("decision") == "QUALIFY"]), "test_after_followup": len([row for row in second_reviews if row.get("decision") == "TEST"]), "monitor_after_followup": len([row for row in second_reviews if row.get("decision") == "MONITOR"]), "reject_after_followup": len([row for row in second_reviews if row.get("decision") == "REJECT"]), "department_work_orders_created": len(department_work_orders), "projects_advanced": len([row for row in second_reviews if row.get("decision") in {"QUALIFY", "TEST"}]), "revenue_work_advanced": len([row for row in second_reviews if row.get("decision") in {"QUALIFY", "TEST"} and "REVENUE" in json.dumps(row).upper()]), "named_followups": [{"research_request_id": row.get("research_request_id") or row.get("request_id"), "question": row.get("question"), "owner": row.get("owner"), "department": row.get("department")} for row in followup_window]},
        "company_advancement": company_advancement,
        "cumulative_today": {"sources_acquired": len([row for row in today_jobs if row.get("status") == "EVIDENCE_READY" and int(row.get("content_count") or 0) > 0]), "substantive_findings": len([row for row in today_jobs if row.get("status") == "EVIDENCE_READY" and int(row.get("content_count") or 0) > 0]), "ai_analyses": len([row for row in today_jobs if row.get("status") == "AI_RESULT_INTERPRETATION"]), "alpha_reviews": len(today_alpha), "decisions": dict(Counter(str(row.get("decision") or "UNKNOWN").upper() for row in today_alpha))},
        "next_two_hours": {"priorities": [row.get("program_id") for row in programs if row.get("enabled", True)][:8], "queued_followups": sum(1 for row in queue.get("items", []) if row.get("status") == "QUEUED" and row.get("alpha_followup_required")), "project_driven_research": sum(1 for row in queue.get("items", []) if row.get("status") == "QUEUED" and row.get("objective_id"))},
        "blockers": {"human_action_required": [], "source_provider_failures": len(failures), "technical_blockers": sorted({str(row.get("failure_class")) for row in failures if row.get("failure_class")}), "stale_data": [], "worker_issues": []},
        "governance": {"observer_only": True, "selects_work": False, "consumes_jobs": False, "stops_research": False, "external_actions": 0},
    }


def render(payload: dict) -> str:
    window = payload["window"]
    work = payload["what_research_did"]
    prod = payload["productivity"]
    alpha = payload["alpha"]
    proactive = payload.get("proactive", {})
    follow_up = payload.get("follow_up", {})
    company = payload.get("company_advancement", {})
    lines = ["# Nexus Continuous Research — Two-Hour Intelligence Report", "", f"WINDOW_START={window['start']}", f"WINDOW_END={window['end']}", "", "## SYSTEM", f"RESEARCH_SERVICE_RUNNING={payload['system']['research_service']['running']}", f"RESEARCH_SERVICE_PID={payload['system']['research_service']['pid']}", f"RESEARCH_HEARTBEAT={payload['system']['heartbeat'].get('heartbeat')}", f"RESEARCH_NEXT_WAKE={payload['system']['next_wake']}", f"ACTIVE_PROGRAMS={', '.join(payload['system']['active_programs'])}", f"FAILED_OR_RETRYING_PROGRAMS={', '.join(payload['system']['failed_or_retrying_programs']) or 'NONE'}", "", "## TWO_HOUR_DELTA", f"SOURCES_ACQUIRED={prod['sources_acquired']}", f"SUBSTANTIVE_FINDINGS={prod['substantive_findings']}", f"AI_ANALYSES={prod['ai_analyses']}", f"ALPHA_REVIEWS={prod['alpha_reviews']}", f"HANDOFFS={prod['department_handoffs']}", f"FAILURES={prod['failed_acquisitions']}", "", "## FOLLOW-UP RESEARCH", *[f"{key.upper()}={json.dumps(value, sort_keys=True)}" for key, value in follow_up.items()], "", "## COMPANY ADVANCEMENT", *[f"{key.upper()}={json.dumps(value, sort_keys=True)}" for key, value in company.items()], "", "## PROACTIVE PRODUCTIVITY", *[f"{key.upper()}={json.dumps(value, sort_keys=True)}" for key, value in proactive.items()], "", "## WHAT RESEARCH ACTUALLY DID", f"SOURCE_SELECTED={work['source_selected']}", f"TRANSCRIPTS_ACQUIRED={work['transcripts_acquired']}", f"TRANSCRIPTS_ANALYZED={work['transcripts_analyzed']}", f"AI_ANALYSES={work['ai_analyses']}", f"SUBSTANTIVE_FINDINGS={work['substantive_findings']}", f"FOLLOW_UP_SEARCHES={work['follow_up_searches']}", f"SOURCE_TYPES={json.dumps(work['source_types'], sort_keys=True)}", "", "## DOMAIN OUTPUT", *[f"{name.upper()}={json.dumps(value, sort_keys=True)}" for name, value in payload["domains"].items()], "", "## ALPHA", f"REVIEWS_COMPLETED={alpha['reviews_completed']}", f"DECISIONS={json.dumps(alpha['decisions'], sort_keys=True)}", f"PROVIDER_MODELS={', '.join(alpha['provider_models']) or 'NONE'}", "", "## HANDOFFS / RETURNS", f"HANDOFFS={json.dumps(payload['handoffs'], sort_keys=True)}", f"RETURNS={json.dumps(payload['returns'], sort_keys=True)}", "", "## CUMULATIVE_TODAY", *[f"{key.upper()}={json.dumps(value, sort_keys=True)}" for key, value in payload["cumulative_today"].items()], "", "## NEXT TWO HOURS", f"PRIORITIES={', '.join(payload['next_two_hours']['priorities'])}", f"QUEUED_FOLLOWUPS={payload['next_two_hours']['queued_followups']}", f"PROJECT_DRIVEN_RESEARCH={payload['next_two_hours']['project_driven_research']}", "", "## BLOCKERS", f"BLOCKERS={json.dumps(payload['blockers'], sort_keys=True)}", "", "REPORTER_SELECTS_WORK=NO", "REPORTER_STOPS_RESEARCH=NO", "REPORTER_CONSUMES_JOBS=NO", "EXTERNAL_ACTIONS=0", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=2)
    parser.add_argument("--today", action="store_true")
    parser.add_argument("--output", choices=("latest", "history"), default="latest")
    args = parser.parse_args()
    payload = report(max(1, args.window_hours), today=args.today)
    HISTORY.mkdir(parents=True, exist_ok=True)
    local_stamp = datetime.now(ZoneInfo("America/Phoenix")).strftime("%Y-%m-%d_%H%M")
    md = render(payload)
    history_stamp = local_stamp
    suffix = 1
    while (HISTORY / f"{history_stamp}.md").exists() or (HISTORY / f"{history_stamp}.json").exists():
        history_stamp = f"{local_stamp}_{suffix:02d}"
        suffix += 1
    (HISTORY / f"{history_stamp}.md").write_text(md, encoding="utf-8")
    (HISTORY / f"{history_stamp}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output == "latest":
        (HISTORY / "latest.md").write_text(md, encoding="utf-8")
        (HISTORY / "latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(HISTORY / "latest.md" if args.output == "latest" else HISTORY / f"{history_stamp}.md"), "history_report": str(HISTORY / f"{history_stamp}.md"), "window": payload["window"], "substantive_findings": payload["productivity"]["substantive_findings"], "ai_analyses": payload["productivity"]["ai_analyses"], "alpha_reviews": payload["productivity"]["alpha_reviews"], "handoffs": payload["productivity"]["department_handoffs"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
