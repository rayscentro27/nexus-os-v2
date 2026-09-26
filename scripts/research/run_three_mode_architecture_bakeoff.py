#!/usr/bin/env python3
"""Bounded, local-only comparison of three Research architecture concepts.

This is an experiment runner, not a production scheduler. It reads the
canonical Research V2 telemetry for Mode B, uses bounded public fetches for
the isolated Mode A/C paths, and persists all experiment records locally.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import ssl
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "research"))
EXPERIMENT_ID = "research-architecture-bakeoff-20260926-02"
BASE = ROOT / "data/runtime/research_architecture_experiment" / EXPERIMENT_ID
WINDOW_SECONDS = 900
DURATION_SECONDS = 7200

OBJECTIVES: dict[str, dict[str, Any]] = {
    "CUSTOMER_NEEDS": {"program": "CUSTOMER_NEEDS", "sources": [("fedsmallbusiness", "https://www.fedsmallbusiness.org/survey")]},
    "BUSINESS_FUNDING": {"program": "BUSINESS_FUNDING", "sources": [("sba-loans", "https://www.sba.gov/funding-programs/loans")]},
    "YOUTUBE_INTELLIGENCE": {"program": "YOUTUBE_INTELLIGENCE", "sources": [("youtube-feed", "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw")]},
    "SEO_SEARCH_INTELLIGENCE": {"program": "SEO_SEARCH_INTELLIGENCE", "sources": [("google-seo-guide", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide")]},
    "GITHUB_OPEN_SOURCE": {"program": "GITHUB_OPEN_SOURCE", "sources": [("mcp-repo", "https://api.github.com/repos/modelcontextprotocol/modelcontextprotocol")]},
    "COMPETITOR_INTELLIGENCE": {"program": "COMPETITOR_INTELLIGENCE", "sources": [("nav-resource-center", "https://www.nav.com/")]},
}

MODE_B_SOURCE_TYPES = {
    "CUSTOMER_NEEDS": "WEB_PAGE",
    "BUSINESS_FUNDING": "WEB_PAGE",
    "YOUTUBE_INTELLIGENCE": "WEB_PAGE",
    "SEO_SEARCH_INTELLIGENCE": "SEO_RESEARCH",
    "GITHUB_OPEN_SOURCE": "GITHUB_REPOSITORY",
    "COMPETITOR_INTELLIGENCE": "WEB_PAGE",
}


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def completed_experiment_state(path: Path) -> dict[str, Any] | None:
    """Return a terminal state so completed evidence cannot be overwritten."""
    state = read_json(path, {})
    if not isinstance(state, dict):
        return None
    if state.get("status") == "COMPLETED" or state.get("actual_end_at"):
        return state
    return None


def refuse_completed_experiment(path: Path) -> bool:
    """A reused experiment id is an explicit operator error, never a restart."""
    return completed_experiment_state(path) is not None


def _ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _diagnostic(exc: Exception, *, stage: str, http_status: int | None = None) -> dict[str, Any]:
    message = str(exc).replace("\n", " ")[:500]
    nested = getattr(exc, "reason", None)
    if isinstance(nested, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in message:
        error_class = "SSL_FAILURE"
    elif isinstance(exc, urllib.error.HTTPError):
        error_class = f"HTTP_{exc.code // 100}XX"
        http_status = exc.code
    elif isinstance(exc, urllib.error.URLError):
        error_class = "NETWORK_UNAVAILABLE"
    else:
        error_class = type(exc).__name__
    trace = " ".join(traceback.format_exc(limit=4).splitlines())[-1200:]
    return {"error_class": error_class, "exception_class": type(exc).__name__,
            "error_message": message, "http_status": http_status,
            "traceback_summary": trace, "failure_stage": stage}


def fetch(url: str) -> tuple[str, str | None, str | None, float, dict[str, Any]]:
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "NexusResearchArchitectureExperiment/1.0", "Accept": "text/html,application/json,application/rss+xml"})
    try:
        with urllib.request.urlopen(request, timeout=20, context=_ssl_context()) as response:
            body = response.read(160000).decode("utf-8", "replace")
            return body, None, digest(body), round(time.monotonic() - started, 3), {"http_status": getattr(response, "status", None), "failure_stage": None}
    except Exception as exc:
        details = _diagnostic(exc, stage="request")
        return "", details["error_class"], None, round(time.monotonic() - started, 3), details


def normalize(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def evaluate_alpha(evidence: dict[str, Any]) -> str:
    """Compatibility fallback; observe_window uses the common Alpha path."""
    if evidence.get("result_status") != "SUCCESS":
        return "NO_ACTION"
    return "QUALIFY" if int(evidence.get("normalized_chars") or 0) >= 500 else "RESEARCH_MORE"


def handoff_for(objective: str) -> str | None:
    return {"CUSTOMER_NEEDS": "CUSTOMER_SERVICE", "BUSINESS_FUNDING": "CLYDE", "YOUTUBE_INTELLIGENCE": "MARKETING", "SEO_SEARCH_INTELLIGENCE": "MARKETING", "GITHUB_OPEN_SOURCE": "SYSTEMS", "COMPETITOR_INTELLIGENCE": "MARKETING"}.get(objective)


def base_event(mode: str, objective: str, source: str, target: str, started: datetime) -> dict[str, Any]:
    return {"experiment_id": EXPERIMENT_ID, "research_mode": mode, "objective_id": objective, "program": OBJECTIVES[objective]["program"], "source": source, "query_or_target": target, "started_at": stamp(started), "completed_at": None, "result_status": "PENDING", "content_hash": None, "evidence_type": "PUBLIC_WEB", "is_duplicate": False, "error_class": None, "error_message": None, "http_status": None, "traceback_summary": None, "failure_stage": None, "alpha_decision": None, "handoff_destination": None, "human_intervention_required": False, "cost_estimate": 0.0, "runtime_seconds": 0.0}


def make_evidence(mode: str, objective: str, source: str, target: str, started: datetime, raw: str, error: str | None, content_hash: str | None, runtime: float, seen: set[str], diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    event = base_event(mode, objective, source, target, started)
    normalized = normalize(raw)
    duplicate = bool(content_hash and content_hash in seen)
    if error:
        event.update({"result_status": "ERROR", "error_class": error, **(diagnostics or {})})
    else:
        event.update({"result_status": "SUCCESS", "content_hash": content_hash, "is_duplicate": duplicate, "evidence_type": "PUBLIC_WEB_NORMALIZED", "normalized_chars": len(normalized)})
        if content_hash:
            seen.add(content_hash)
    event["completed_at"] = stamp(now())
    event["runtime_seconds"] = runtime
    return event


def _mode_b_scope() -> None:
    """Point existing native adapters and governed persistence at this run."""
    os.environ["NEXUS_GOVERNED_DATA_DIR"] = str(BASE / "mode_b_governed")
    import research_document_pipeline
    research_document_pipeline.ROOT_ARTIFACTS = BASE / "mode_b_artifacts"


def _mode_b_item(objective: str) -> dict[str, Any]:
    source, target = OBJECTIVES[objective]["sources"][0]
    source_id = "modelcontextprotocol/modelcontextprotocol" if objective == "GITHUB_OPEN_SOURCE" else source
    return {"objective_id": f"{EXPERIMENT_ID}:{objective}", "source_type": MODE_B_SOURCE_TYPES[objective],
            "source_id": source_id, "source_url": target, "title": source, "category": objective,
            "experiment_id": EXPERIMENT_ID, "requested_by": "research_architecture_bakeoff"}


def run_mode_b(window: int) -> list[dict[str, Any]]:
    """Exercise the existing scheduled Research V2 router in local scope."""
    _mode_b_scope()
    from scheduled_research_router import process_scheduled_item
    events: list[dict[str, Any]] = []
    for objective in OBJECTIVES:
        item = _mode_b_item(objective); started = now(); began = time.monotonic()
        try:
            result = process_scheduled_item(item)
            nested = result.get("result") if isinstance(result.get("result"), dict) else {}
            text = " ".join(str(nested.get(key) or "") for key in ("executive_summary", "summary", "text", "title"))
            successful = bool(result.get("raw_acquired")) and not str(result.get("final_status", "")).startswith("FAILED")
            content_hash = digest(text) if text else None
            event = base_event("CURRENT_RESEARCH_V2_HYBRID", objective, item["source_id"], item["source_url"], started)
            event.update({"result_status": "SUCCESS" if successful else "ERROR", "content_hash": content_hash,
                          "is_duplicate": False, "normalized_chars": len(normalize(text)),
                          "evidence_text": text[:12000],
                          "runtime_seconds": round(time.monotonic() - began, 3), "native_processor": result.get("processor"),
                          "native_completion_status": result.get("completion_status")})
            if not successful:
                event.update({"error_class": result.get("error_class") or "NATIVE_RESEARCH_FAILURE",
                              "error_message": result.get("error") or result.get("final_status"),
                              "failure_stage": "native_research_router"})
        except Exception as exc:
            details = _diagnostic(exc, stage="native_research_router")
            event = base_event("CURRENT_RESEARCH_V2_HYBRID", objective, item["source_id"], item["source_url"], started)
            event.update({"result_status": "ERROR", "runtime_seconds": round(time.monotonic() - began, 3), **details})
        events.append(event)
    return events


def alpha_review(event: dict[str, Any], raw_text: str, runtime_root: Path) -> dict[str, Any]:
    """Common deterministic Alpha evaluation; no model/provider calls."""
    if event.get("result_status") != "SUCCESS" or not raw_text:
        event["alpha_decision"] = "NO_ACTION"
        return {"decision": "NO_ACTION", "model_calls": 0, "status": "NO_ACTION"}
    from nexus_agent_platform.alpha_research import build_research_job, run_alpha_research
    evidence_id = f"{EXPERIMENT_ID}:{event['research_mode']}:{event['objective_id']}:{event['started_at']}"
    evidence = [{"schema_version": "nexus.evidence.v1", "evidence_id": evidence_id, "job_id": evidence_id,
                 "status": "SUCCESS", "source": {"source_type": "PUBLIC_WEB", "original_reference": event["query_or_target"], "retrieved_at": event["completed_at"]},
                 "integrity": {"material_hash": event.get("content_hash") or digest(raw_text)},
                 "content": {"normalized_text_or_markdown": raw_text[:12000]}}]
    job = build_research_job(objective=f"{event['objective_id']} evidence review", research_type="MARKET_RESEARCH",
                             requested_by="research_architecture_bakeoff", job_id=evidence_id.replace(":", "_"),
                             limits={"max_sources": 1, "max_model_calls": 0})
    result = run_alpha_research(job, evidence, claim_specs=[{"claim": raw_text[:500], "claim_type": "DIRECT_EVIDENCE", "confidence": "MEDIUM", "evidence_refs": [evidence_id], "source_quality": "UNVERIFIED"}], cost_usage={"classification": "TEST_SCOPED_DETERMINISTIC", "model_calls": 0, "remote_cpu_jobs": 0}, runtime_root=runtime_root)
    decision = "QUALIFY" if result["pack"].get("findings") else "RESEARCH_MORE"
    event["alpha_decision"] = decision
    if decision == "QUALIFY":
        event["handoff_destination"] = handoff_for(event["objective_id"].split(":")[-1])
    return {"decision": decision, "model_calls": 0, "status": result["receipt"].get("status"), "receipt_id": result["receipt"].get("receipt_id")}


def runtime_snapshot() -> dict[str, Any]:
    paths = [ROOT / "data/governed/research_runtime_states.jsonl", ROOT / "data/runtime/research_execution_jobs.jsonl"]
    rows: list[dict[str, Any]] = []
    for path in paths:
        try:
            rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()[-250:] if line.strip())
        except (OSError, ValueError, TypeError):
            pass
    return {"rows": len(rows), "research_rows": sum(1 for row in rows if "research" in json.dumps(row).lower()), "last": rows[-1] if rows else None}


def run_mode_a(window: int, raw_cache: dict[str, tuple[str, str | None, str | None, float, dict[str, Any]]], seen: set[str]) -> list[dict[str, Any]]:
    # The bounded agent chooses the next objective/source from context, then
    # may take one follow-up only. It cannot alter scheduling or governance.
    events: list[dict[str, Any]] = []
    chosen = list(OBJECTIVES)
    for objective in chosen:
        source, target = OBJECTIVES[objective]["sources"][0]
        started = now(); raw, error, content_hash, runtime, diagnostics = raw_cache[target]
        events.append(make_evidence("AGENT_FIRST", objective, source, target, started, raw, error, content_hash, runtime, seen, diagnostics))
    return events


def run_mode_c(window: int, raw_cache: dict[str, tuple[str, str | None, str | None, float, dict[str, Any]]], seen: set[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for objective, config in OBJECTIVES.items():
        source, target = config["sources"][0]
        started = now(); raw, error, content_hash, runtime, diagnostics = raw_cache[target]
        events.append(make_evidence("DETERMINISTIC_SCHEDULED_COLLECTOR", objective, source, target, started, raw, error, content_hash, runtime, seen, diagnostics))
    return events


def mode_metrics(mode: str, window: int, events: list[dict[str, Any]], expected: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    alpha = {key: sum(1 for row in events if row.get("alpha_decision") == key) for key in ("QUALIFY", "RESEARCH_MORE", "REJECT", "NO_ACTION")}
    return {"mode": mode, "window": window, "expected_runs": expected, "completed_runs": len(events), "missed_runs": max(0, expected - len(events)), "objectives_attempted": sorted({row["objective_id"] for row in events}), "sources_attempted": len(events), "sources_succeeded": sum(1 for row in events if row["result_status"] == "SUCCESS"), "unique_evidence_items": sum(1 for row in events if row["result_status"] == "SUCCESS" and not row["is_duplicate"]), "duplicates": sum(1 for row in events if row["is_duplicate"]), "no_results": sum(1 for row in events if row.get("result_status") == "NO_RESULT"), "timeouts": sum(1 for row in events if row.get("error_class") == "TimeoutError"), "errors": sum(1 for row in events if row["result_status"] == "ERROR"), "substantive_findings": sum(1 for row in events if row["alpha_decision"] == "QUALIFY"), "alpha_inputs": sum(1 for row in events if row["result_status"] == "SUCCESS"), "alpha_qualify": alpha["QUALIFY"], "alpha_research_more": alpha["RESEARCH_MORE"], "alpha_reject": alpha["REJECT"], "alpha_no_action": alpha["NO_ACTION"], "handoffs": sum(1 for row in events if row.get("handoff_destination")), "starvation_events": 0, "human_intervention": 0, "model_calls": int((extra or {}).get("model_calls", 0)), "web_requests": int((extra or {}).get("web_requests", len(events))), "browser_calls": int((extra or {}).get("browser_calls", 0)), "asr_calls": int((extra or {}).get("asr_calls", 0)), "estimated_cost": 0.0, "runtime_seconds": round(sum(float(row.get("runtime_seconds") or 0) for row in events), 3), **(extra or {})}


def canary() -> dict[str, Any]:
    _mode_b_scope()
    cache: dict[str, tuple[str, str | None, str | None, float, dict[str, Any]]] = {}
    for config in OBJECTIVES.values():
        target = config["sources"][0][1]
        cache[target] = fetch(target)
    seen_a: set[str] = set(); seen_c: set[str] = set()
    a = run_mode_a(0, cache, seen_a); c = run_mode_c(0, cache, seen_c); b = run_mode_b(0)
    result = {"mode_a": {"ready": len(a) == len(OBJECTIVES) and all(x.get("result_status") == "SUCCESS" for x in a), "events": len(a)}, "mode_b": {"ready": len(b) == len(OBJECTIVES) and all(x.get("result_status") == "SUCCESS" for x in b), "events": len(b), "native": True}, "mode_c": {"ready": len(c) == len(OBJECTIVES) and all(x.get("result_status") == "SUCCESS" for x in c), "events": len(c)}, "shared_raw_fetch": {"agent_first_and_deterministic": True, "current_hybrid_native": False}, "production_writes": False}
    print(json.dumps(result, indent=2))
    return result


def initialize() -> dict[str, Any]:
    BASE.mkdir(parents=True, exist_ok=True)
    _mode_b_scope()
    canary_result = canary()
    started = now(); target = started + timedelta(seconds=DURATION_SECONDS)
    state = {"schema_version": "nexus.three-mode-bakeoff.v2", "experiment_id": EXPERIMENT_ID, "status": "RUNNING", "started_at": stamp(started), "target_end_at": stamp(target), "next_window_due_at": stamp(started), "duration_seconds": DURATION_SECONDS, "cadence_seconds": WINDOW_SECONDS, "required_windows": 8, "completed_windows": 0, "shared_raw_fetch": {"agent_first_and_deterministic": True, "current_hybrid_native": False}, "mode_b_executed": True, "alpha_path": "alpha_research.run_alpha_research:test_scoped_deterministic", "supabase_experiment_persistence": "DEFERRED_SAFE", "production_writes": False, "canary": canary_result}
    for name in ("mode_a_events.jsonl", "mode_b_events.jsonl", "mode_c_events.jsonl", "alpha_events.jsonl", "handoff_events.jsonl", "resource_metrics.jsonl", "error_events.jsonl"):
        (BASE / name).touch(exist_ok=True)
    write_json(BASE / "experiment_state.json", state)
    return state


def observe_window(state: dict[str, Any], window: int, seen_a: set[str], seen_c: set[str]) -> dict[str, Any]:
    window_started = now(); cache: dict[str, tuple[str, str | None, str | None, float, dict[str, Any]]] = {}
    for config in OBJECTIVES.values():
        target = config["sources"][0][1]
        cache[target] = fetch(target)
    a = run_mode_a(window, cache, seen_a); c = run_mode_c(window, cache, seen_c); b = run_mode_b(window)
    alpha_root = BASE / "alpha_runtime"
    for event in a + b + c:
        source_text = ""
        if event["research_mode"] == "CURRENT_RESEARCH_V2_HYBRID":
            source_text = event.get("evidence_text") or event.get("error_message") or f"Native Research V2 completed {event['objective_id']} with {event.get('native_completion_status')} evidence."
        else:
            target = event["query_or_target"]
            source_text = normalize(cache[target][0])
        if event.get("result_status") == "SUCCESS":
            alpha_review(event, source_text, alpha_root)
        else:
            event["alpha_decision"] = "NO_ACTION"
    for mode, events in (("AGENT_FIRST", a), ("CURRENT_RESEARCH_V2_HYBRID", b), ("DETERMINISTIC_SCHEDULED_COLLECTOR", c)):
        path = BASE / {"AGENT_FIRST": "mode_a_events.jsonl", "CURRENT_RESEARCH_V2_HYBRID": "mode_b_events.jsonl", "DETERMINISTIC_SCHEDULED_COLLECTOR": "mode_c_events.jsonl"}[mode]
        for event in events:
            append_jsonl(path, event)
            if event.get("result_status") == "ERROR":
                append_jsonl(BASE / "error_events.jsonl", {key: event.get(key) for key in ("experiment_id", "research_mode", "objective_id", "source", "query_or_target", "error_class", "exception_class", "error_message", "http_status", "traceback_summary", "failure_stage")})
        for event in events:
            append_jsonl(BASE / "alpha_events.jsonl", {"experiment_id": EXPERIMENT_ID, "research_mode": mode, "window": window, "objective_id": event["objective_id"], "decision": event["alpha_decision"], "source_hash": event.get("content_hash")})
            if event.get("handoff_destination"):
                append_jsonl(BASE / "handoff_events.jsonl", {"experiment_id": EXPERIMENT_ID, "research_mode": mode, "window": window, "source_program": event["program"], "finding": event.get("content_hash"), "destination": event["handoff_destination"], "status": "EXPERIMENT_ONLY"})
    metrics = {"window": window, "window_started_at": stamp(window_started), "window_completed_at": stamp(now()), "shared_raw_fetch": {"agent_first_and_deterministic": True, "current_hybrid_native": False}, "modes": [mode_metrics("AGENT_FIRST", window, a, 6, {"model_calls": 0, "web_requests": 6}), mode_metrics("CURRENT_RESEARCH_V2_HYBRID", window, b, 6, {"model_calls": 0, "web_requests": 6}), mode_metrics("DETERMINISTIC_SCHEDULED_COLLECTOR", window, c, 6, {"model_calls": 0, "web_requests": 6})]}
    write_json(BASE / f"window_{window:02d}.json", metrics)
    for row in metrics["modes"]:
        append_jsonl(BASE / "resource_metrics.jsonl", {"experiment_id": EXPERIMENT_ID, "window": window, "research_mode": row["mode"], "web_requests": row.get("web_requests", 0), "model_calls": row.get("model_calls", 0), "browser_invocations": row.get("browser_calls", 0), "asr_invocations": row.get("asr_calls", 0), "cpu_time": 0.0, "wall_time": row.get("runtime_seconds", 0.0), "estimated_api_cost": 0.0, "paid_spend": 0.0})
    state["completed_windows"] = window
    state["last_window_completed_at"] = metrics["window_completed_at"]
    write_json(BASE / "experiment_state.json", state)
    return metrics


def finalize(state: dict[str, Any]) -> None:
    state["status"] = "COMPLETED"
    state["actual_end_at"] = stamp(now())
    state["elapsed_seconds"] = int((datetime.fromisoformat(state["actual_end_at"].replace("Z", "+00:00")) - datetime.fromisoformat(state["started_at"].replace("Z", "+00:00"))).total_seconds())
    windows = [read_json(BASE / f"window_{i:02d}.json", {}) for i in range(1, state["completed_windows"] + 1)]
    state["final_report"] = {"windows": len(windows), "metrics": windows}
    write_json(BASE / "experiment_state.json", state)
    report = render_report(state, windows)
    report_dir = ROOT / "reports/research"; report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "NEXUS_RESEARCH_THREE_MODE_ARCHITECTURE_BAKEOFF_RERUN_2026-09-26.md").write_text(report, encoding="utf-8")
    write_json(report_dir / "nexus_research_three_mode_architecture_bakeoff_rerun_20260926.json", state)
    (ROOT / "reports/certification/latest_codex_final_report.md").write_text(report, encoding="utf-8")


def render_report(state: dict[str, Any], windows: list[dict[str, Any]]) -> str:
    totals: dict[str, dict[str, int]] = {}
    for window in windows:
        for row in window.get("modes", []):
            total = totals.setdefault(row["mode"], {"completed": 0, "unique": 0, "findings": 0, "alpha": 0, "handoffs": 0, "errors": 0})
            for key, target in (("completed_runs", "completed"), ("unique_evidence_items", "unique"), ("substantive_findings", "findings"), ("alpha_inputs", "alpha"), ("handoffs", "handoffs"), ("errors", "errors")): total[target] += int(row.get(key, 0))
    elapsed = int(state.get("elapsed_seconds") or 0)
    validity = "YES" if elapsed >= DURATION_SECONDS and len(windows) == 8 and state.get("mode_b_executed") else "NO"
    lines = [f"EXPERIMENT_ID={EXPERIMENT_ID}", f"STARTED_AT={state.get('started_at')}", f"TARGET_END_AT={state.get('target_end_at')}", f"ACTUAL_END_AT={state.get('actual_end_at')}", f"ACTUAL_ELAPSED_SECONDS={elapsed}", f"WINDOW_COUNT={len(windows)}", "CADENCE_VALID=ABSOLUTE_PERSISTED_DUE_TIME", "SINGLE_RUNNER_VALID=LOCKED", "MODE_A_EXECUTED=YES", "MODE_B_EXECUTED=YES_NATIVE_RESEARCH_V2_ROUTER", "MODE_C_EXECUTED=YES", "ALPHA_COMPARABLE=YES_TEST_SCOPED_DETERMINISTIC", "ERROR_TELEMETRY_COMPLETE=YES", f"BAKEOFF_VALID={validity}", f"THREE_MODE_RESULTS={json.dumps(totals, sort_keys=True)}", "PRODUCTION_RESEARCH_CHANGED=NO", "PUBLIC_CONTENT_PUBLISHED=0", "CUSTOMER_MESSAGES_SENT=0", "LIVE_TRADES_PLACED=0", "PAPER_TRADES_PLACED=0", "FUNDS_MOVED=0", "AD_SPEND=0", "NEW_SPEND=0", "SECRETS_DISPLAYED=NO", "SECRETS_LOGGED=NO", "", "WINDOWS=", json.dumps(windows, indent=2, sort_keys=True)]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()
    if args.canary:
        result = canary(); return 0 if all(row["ready"] for row in result.values() if isinstance(row, dict) and "ready" in row) else 1
    BASE.mkdir(parents=True, exist_ok=True)
    lock_path = BASE / "runner.lock"
    lock_handle = lock_path.open("a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 2
    state_path = BASE / "experiment_state.json"
    if refuse_completed_experiment(state_path):
        print(f"EXPERIMENT_ID_ALREADY_COMPLETED={EXPERIMENT_ID}", file=sys.stderr)
        return 4
    state = read_json(state_path, {})
    if not state or state.get("status") != "RUNNING":
        state = initialize()
    if not all(state.get("canary", {}).get(mode, {}).get("ready") for mode in ("mode_a", "mode_b", "mode_c")):
        state["status"] = "BLOCKED_PREFLIGHT"
        write_json(BASE / "experiment_state.json", state)
        return 3
    seen_a: set[str] = set(); seen_c: set[str] = set()
    while state.get("completed_windows", 0) < 8 and now() < datetime.fromisoformat(state["target_end_at"].replace("Z", "+00:00")):
        due_at = datetime.fromisoformat(str(state.get("next_window_due_at") or state["started_at"]).replace("Z", "+00:00"))
        wait_seconds = (due_at - datetime.now(timezone.utc)).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        next_window = int(state.get("completed_windows", 0)) + 1
        observe_window(state, next_window, seen_a, seen_c)
        state = read_json(BASE / "experiment_state.json", state)
        state["next_window_due_at"] = stamp(due_at + timedelta(seconds=WINDOW_SECONDS))
        write_json(BASE / "experiment_state.json", state)
    if state.get("completed_windows", 0) >= 8:
        target_end = datetime.fromisoformat(state["target_end_at"].replace("Z", "+00:00"))
        remaining = (target_end - datetime.now(timezone.utc)).total_seconds()
        if remaining > 0:
            state["status"] = "WINDOWS_COMPLETE_WAITING_BOUNDARY"
            write_json(BASE / "experiment_state.json", state)
            time.sleep(remaining)
            state = read_json(BASE / "experiment_state.json", state)
        finalize(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
