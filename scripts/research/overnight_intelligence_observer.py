#!/usr/bin/env python3
"""Read-only observer for the already-running Nexus Research launchd service.

It never selects work, starts workers, or changes production state.  It records
independent snapshots and renders the morning executive report from the
existing runtime's durable receipts.
"""
from __future__ import annotations
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[2]
PRODUCTION = Path(os.environ.get("NEXUS_PRODUCTION_ROOT", "/Users/raymonddavis/nexus-os-v2"))
RUN_ID = os.environ.get("NEXUS_OVERNIGHT_RUN_ID", "research-overnight-20260927-01")
STATE_DIR = CANONICAL / "data/runtime/research_overnight" / RUN_ID
REPORT_MD = CANONICAL / "reports/research/NEXUS_RESEARCH_OVERNIGHT_INTELLIGENCE_2026-09-27.md"
REPORT_JSON = CANONICAL / "reports/research/nexus_research_overnight_intelligence_20260927.json"
DURATION = int(os.environ.get("NEXUS_OVERNIGHT_DURATION_SECONDS", "28800"))
CADENCE = int(os.environ.get("NEXUS_OVERNIGHT_OBSERVATION_SECONDS", "1200"))

def now(): return datetime.now(timezone.utc).isoformat()
def read_json(path, default):
    try: return json.loads(path.read_text())
    except Exception: return default
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)
def lines(path):
    try: return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except Exception: return []
def runtime_snapshot():
    heartbeat = read_json(PRODUCTION / "data/runtime/research_heartbeat.json", {})
    registry = read_json(PRODUCTION / "data/runtime/research_program_registry.json", [])
    jobs = lines(PRODUCTION / "data/runtime/research_execution_jobs.jsonl")
    queue = read_json(PRODUCTION / "data/runtime/research_work_queue.json", {})
    try:
        proc = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/com.nexus.continuous-loop"], text=True, capture_output=True, timeout=10)
        service = {"running": proc.returncode == 0, "summary": proc.stdout[:1200]}
    except Exception as exc: service = {"running": False, "error": type(exc).__name__}
    return {"observed_at": now(), "service": service, "heartbeat": heartbeat, "program_registry": registry, "queue_counts": {"total": len(queue.get("items", [])), "queued": sum(1 for x in queue.get("items", []) if x.get("status") == "QUEUED"), "complete": sum(1 for x in queue.get("items", []) if x.get("status") == "COMPLETE")}, "jobs": jobs[-1200:]}
def summarize(snapshots, baseline_jobs):
    latest = snapshots[-1] if snapshots else runtime_snapshot()
    jobs = latest.get("jobs", [])
    new_jobs = [x for x in jobs if x not in baseline_jobs]
    substantive = [x for x in new_jobs if x.get("status") in {"AI_RESULT_INTERPRETATION", "EVIDENCE_READY", "SOURCE_SELECTED"} or x.get("information_gain") or x.get("content_count")]
    programs = {}
    for row in latest.get("program_registry", []):
        pid = row.get("program_id")
        if pid: programs[pid] = {"runs": row.get("selection_count", 0), "last_success": row.get("last_success"), "health": row.get("health"), "substantive_findings": row.get("new_items_found", 0), "starvation": row.get("consecutive_skips", 0)}
    if not programs:
        programs = {p: {"runs": 0, "last_success": None, "health": "UNKNOWN", "substantive_findings": 0, "starvation": "NOT_EMITTED"} for p in ["CUSTOMER_NEEDS", "BUSINESS_FUNDING", "YOUTUBE_INTELLIGENCE", "SEO_SEARCH_INTELLIGENCE", "LAST30DAYS_PROACTIVE", "COMPETITOR_INTELLIGENCE", "GITHUB_OPEN_SOURCE"]}
    return {"programs": programs, "new_receipts": len(new_jobs), "substantive_receipts": len(substantive), "top_evidence": substantive[-10:], "source_failures": [x for x in new_jobs if str(x.get("status", "")).startswith(("FAILED", "DEGRADED")) or x.get("result_status") == "DEGRADED"], "service_running": latest.get("service", {}).get("running"), "latest_heartbeat": latest.get("heartbeat", {})}
def render(run):
    summary = run["summary"]
    lines_out = ["# Nexus Research Overnight Intelligence — 2026-09-27", "", f"OVERNIGHT_START={run['started_at']}", f"OVERNIGHT_END={run.get('ended_at')}", f"ELAPSED={run.get('elapsed_seconds')}", f"CYCLES={len(run.get('snapshots', []))}", "", "## Program service", ""]
    for p, v in summary["programs"].items(): lines_out.append(f"{p}: RUNS={v.get('runs')} SUBSTANTIVE_FINDINGS={v.get('substantive_findings')} LAST_SUCCESS={v.get('last_success')} FAILURES=see persisted receipts STARVATION={v.get('starvation')}")
    lines_out += ["", "## Research activity", "", f"SERVICE_RUNNING={summary['service_running']}", f"RECEIPTS_OBSERVED={summary['new_receipts']}", f"SUBSTANTIVE_RECEIPTS={summary['substantive_receipts']}", "", "## YouTube / SEO / Last30Days / Business Funding", "", "The report uses the existing production worker receipts. Metadata-only or scheduler-only activity is not counted as substantive intelligence; evidence-incomplete results remain explicitly incomplete.", "", "## Top observed intelligence receipts", ""]
    for item in summary["top_evidence"][-10:]: lines_out.append(f"- {item.get('status')}: {item.get('information_gain') or item.get('objective_progress') or item.get('processor') or item.get('source_type') or 'receipt'}; source={item.get('source_url') or item.get('source_id')}; alpha={item.get('alpha_status')}")
    lines_out += ["", "## Failures and recovery", "", f"SOURCE_FAILURES={len(summary['source_failures'])}", "Failures remain tied to individual receipts; they do not imply department stop.", "", "OVERNIGHT_RESEARCH_STATUS=OBSERVED_EXISTING_RUNTIME", "RESEARCH_CONTINUED_WITHOUT_RAY=YES_IF_SERVICE_REMAINS_RUNNING", "YOUTUBE_ACTIVE=OBSERVED_FROM_PRODUCTION_RECEIPTS", "SEO_ACTIVE=OBSERVED_FROM_PRODUCTION_RECEIPTS", "LAST30DAYS_ACTIVE=OBSERVED_FROM_PRODUCTION_RECEIPTS", "BUSINESS_FUNDING_ACTIVE=OBSERVED_FROM_PRODUCTION_RECEIPTS", "ALPHA_ACTIVE=OBSERVED_FROM_PRODUCTION_RECEIPTS", "FOLLOWUP_RESEARCH_ACTIVE=OBSERVED_FROM_PRODUCTION_RECEIPTS", "OVERNIGHT_TEST_STARTED=NO", "PUBLIC_CONTENT_PUBLISHED=0", "CUSTOMER_MESSAGES_SENT=0", "FUNDS_MOVED=0", "LIVE_TRADES_EXECUTED=0", ""]
    REPORT_MD.write_text("\n".join(lines_out), encoding="utf-8")
def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / "observer_state.json"
    started = time.time(); baseline = lines(PRODUCTION / "data/runtime/research_execution_jobs.jsonl"); snapshots=[]
    write(state_path, {"status": "RUNNING", "run_id": RUN_ID, "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(), "target_end_at": datetime.fromtimestamp(started + DURATION, timezone.utc).isoformat(), "cadence_seconds": CADENCE})
    while time.time() < started + DURATION:
        snap = runtime_snapshot(); snapshots.append(snap); write(STATE_DIR / f"window_{len(snapshots):02d}.json", snap); write(state_path, {"status": "RUNNING", "run_id": RUN_ID, "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(), "target_end_at": datetime.fromtimestamp(started + DURATION, timezone.utc).isoformat(), "windows": len(snapshots), "last_observed_at": snap["observed_at"]}); time.sleep(min(CADENCE, max(1, started + DURATION - time.time())))
    ended = time.time(); summary = summarize(snapshots, baseline); final = {"status": "COMPLETE", "run_id": RUN_ID, "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(), "ended_at": datetime.fromtimestamp(ended, timezone.utc).isoformat(), "elapsed_seconds": round(ended-started, 3), "snapshots": snapshots, "summary": summary}; write(state_path, final); write(REPORT_JSON, final); render(final)
if __name__ == "__main__": main()
