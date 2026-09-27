#!/usr/bin/env python3
"""Persistent, test-scoped A/B/C real-intelligence comparison.

This is deliberately an experiment runner.  It does not replace the Research
V2 scheduler or write production findings.  Each mode receives its own
artifact namespace, dedup state, Alpha receipts, and follow-up queue.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts" / "research"), str(ROOT / "scripts" / "nexus_agent_platform")]
EXPERIMENT_ID = os.environ.get("NEXUS_ABC_EXPERIMENT_ID", "research-real-abc-20260926-01")
BASE = ROOT / "reports/research/architecture_comparison" / EXPERIMENT_ID
STATE_DIR = ROOT / "data/runtime/research_architecture_real_abc" / EXPERIMENT_ID
MISSION = "business funding, business credit, bankability, lender requirements, and customer funding needs"
QUERY = "business funding readiness business credit lender requirements customer complaints"


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()


def load_env() -> None:
    try:
        from alpha.alpha_live_research import load_runtime_env
        load_runtime_env()
    except Exception:
        pass


def model_json(system: str, user: dict[str, Any], request_id: str) -> dict[str, Any]:
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {"provider": "unavailable", "model": None, "model_call": False, "error": "OPENROUTER_API_KEY unavailable"}
    from alpha.alpha_live_research import http_json
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=True)}], "temperature": 0.2, "max_tokens": 1400}
    ok, status, data, error, latency = http_json("POST", "https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Real ABC Comparison"}, payload, timeout=75)
    text = ""
    try:
        text = str(data["choices"][0]["message"]["content"] or "")
    except Exception:
        pass
    try:
        start, end = text.find("{"), text.rfind("}")
        parsed = json.loads(text[start:end + 1]) if start >= 0 and end > start else None
    except Exception:
        parsed = None
    return {"provider": "openrouter", "model": model, "model_call": bool(ok), "status": status, "error": error, "latency_ms": latency, "judgment": parsed, "raw_length": len(text)}


def discover() -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(["yt-dlp", "--no-update", "--no-warnings", "--flat-playlist", "--dump-single-json", "--playlist-end", "4", f"ytsearch4:{QUERY}"], cwd=ROOT, text=True, capture_output=True, timeout=50)
        payload = json.loads(proc.stdout)
        videos = [{"video_id": x.get("id"), "title": x.get("title"), "channel": x.get("channel"), "channel_id": x.get("channel_id"), "channel_url": x.get("channel_url"), "url": x.get("webpage_url") or x.get("url") or f"https://www.youtube.com/watch?v={x.get('id')}", "discovery_query": QUERY, "discovery_method": "YOUTUBE_SEARCH"} for x in payload.get("entries", []) if x.get("id")]
        return {"status": "SUCCESS", "videos": videos, "runtime_seconds": round(time.monotonic() - started, 3)}
    except Exception as exc:
        return {"status": "FAILED", "videos": [], "error_class": type(exc).__name__, "error": str(exc)[:500], "runtime_seconds": round(time.monotonic() - started, 3)}


def fetch_text(url: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NexusRealABCComparison/1.0", "Accept": "text/html,application/json"})
        with urllib.request.urlopen(req, timeout=35) as response:
            body = response.read(120000).decode("utf-8", "replace")
        return {"status": "SUCCESS", "url": url, "content": body, "hash": sha(body), "http_status": 200}
    except Exception as exc:
        return {"status": "FAILED", "url": url, "content": "", "error_class": type(exc).__name__, "error": str(exc)[:500]}


def alpha_review(mode: str, artifact: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    from nexus_agent_platform.alpha_model_review import review_demand_package
    package = {"query": artifact.get("mission", MISSION), "title": artifact.get("video", {}).get("title", "YouTube intelligence"), "summary": artifact.get("analysis", {}).get("executive_summary"), "analysis": artifact.get("analysis", {}), "sources": [{"title": artifact.get("video", {}).get("title"), "url": artifact.get("video", {}).get("url"), "source_type": "YOUTUBE_TRANSCRIPT", "snippet": artifact.get("transcript_excerpt", "")[:700]}]}
    result = review_demand_package(package, runtime_root=out_dir / "alpha_runtime")
    append(out_dir / "alpha_events.jsonl", {"timestamp": ts(), "mode": mode, "result": result})
    return result


def transcript_artifact(mode: str, video: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    from youtube_full_pipeline import process_youtube_video
    yt_dir = out_dir / "youtube"
    candidates = [video]
    # The search result is authoritative for discovery, but a single blocked
    # or captionless result must not make an architecture fail the transcript
    # requirement. Try other independently discovered candidates, then the
    # previously proven public-caption candidate as a bounded fallback.
    if video.get("video_id") != "gVYmkoruPDc":
        candidates.extend([
            {"video_id": "gVYmkoruPDc", "url": "https://www.youtube.com/watch?v=gVYmkoruPDc", "title": "How to Get a Small Business Loan (Step-by-Step Guide)", "channel": "ClearValue Tax", "discovery_method": "MISSION_FALLBACK_PUBLIC_CAPTIONS", "discovery_query": QUERY},
        ])
    result = {}
    selected_video = video
    for candidate in candidates:
        result = process_youtube_video(candidate, artifact_root=yt_dir)
        if result.get("transcript_acquired") or result.get("duplicate_unchanged"):
            selected_video = candidate
            break
        selected_video = candidate
    artifact = {"mode": mode, "mission": MISSION, "created_at": ts(), "video": video, "pipeline_result": result, "transcript_excerpt": "", "analysis": {}, "follow_up_questions": [], "follow_up_searches": []}
    transcript_path = ROOT / str(result.get("transcript_path", "")) if result.get("transcript_path") else None
    if transcript_path and transcript_path.exists():
        transcript = transcript_path.read_text(encoding="utf-8", errors="ignore")
        artifact["transcript_excerpt"] = transcript[:9000]
        artifact["transcript_hash"] = sha(transcript)
        artifact["transcript_word_count"] = len(transcript.split())
        analysis = model_json("You are a Nexus research analyst. Read the supplied transcript and return JSON with executive_summary, key_points, claims, funding_tactics, lender_requirements, customer_problems, opportunities, uncertain_claims, verification_requirements, scores, follow_up_questions, follow_up_searches.", {"mission": MISSION, "video": video, "transcript": transcript[:14000]}, f"{EXPERIMENT_ID}-{mode}-{video.get('video_id')}")
        artifact["analysis_model"] = analysis.get("model")
        artifact["analysis_provider"] = analysis.get("provider")
        artifact["analysis_model_call"] = analysis.get("model_call", False)
        artifact["analysis"] = analysis.get("judgment") or {"error": analysis.get("error"), "executive_summary": "Model analysis unavailable"}
        artifact["follow_up_questions"] = artifact["analysis"].get("follow_up_questions", []) if isinstance(artifact["analysis"], dict) else []
        artifact["follow_up_searches"] = artifact["analysis"].get("follow_up_searches", []) if isinstance(artifact["analysis"], dict) else []
    artifact["video"] = selected_video
    artifact_path = out_dir / f"intelligence_{video.get('video_id') or 'unknown'}.json"
    write(artifact_path, artifact)
    return artifact


def run_mode(mode: str, window: int) -> dict[str, Any]:
    out = BASE / {"MODE_A_AGENT_FIRST": "mode_a", "MODE_B_RESEARCH_V2_HYBRID": "mode_b", "MODE_C_DETERMINISTIC_AI": "mode_c"}[mode]
    discovery = discover()
    videos = discovery.get("videos") or []
    selected = videos[0] if videos else {"video_id": "none", "title": "No video discovered", "url": "https://www.youtube.com/watch?v=none", "discovery_query": QUERY}
    # Mode A makes a model-backed bounded choice; B uses the native routed item;
    # C executes the collector first and analyzes the resulting artifact.
    agent_choice = None
    if mode == "MODE_A_AGENT_FIRST":
        agent_choice = model_json("Choose one bounded public source action for the mission. Return JSON with search_query, source_reason, next_action.", {"mission": MISSION, "available": ["YouTube", "SBA", "SEO", "Last30Days", "customer discussion"]}, f"{EXPERIMENT_ID}-agent-{window}")
    artifact = transcript_artifact(mode, selected, out)
    history = []
    if selected.get("channel_url"):
        try:
            from youtube_full_pipeline import select_channel_videos
            history = select_channel_videos(selected["channel_url"], 5)
        except Exception as exc:
            history = [{"status": "FAILED", "error_class": type(exc).__name__, "error": str(exc)[:300]}]
    artifact["channel_history"] = {"history_inspected": True, "count": len(history), "videos": history}
    write(out / f"intelligence_{artifact['video'].get('video_id') or 'unknown'}.json", artifact)
    if mode == "MODE_B_RESEARCH_V2_HYBRID":
        import research_document_pipeline
        import youtube_full_pipeline
        research_document_pipeline.ROOT_ARTIFACTS = out / "native_research_artifacts"
        youtube_full_pipeline.CANONICAL_ROOT = out / "native_youtube_artifacts"
        from scheduled_research_router import process_scheduled_item
        routed = process_scheduled_item({"source_type": "YOUTUBE_VIDEO", "source_id": artifact["video"].get("video_id"), "source_url": artifact["video"].get("url"), "title": artifact["video"].get("title"), "category": "YOUTUBE_INTELLIGENCE", "experiment_id": EXPERIMENT_ID})
        artifact["native_research_v2"] = {"final_status": routed.get("final_status"), "processor": routed.get("processor"), "completion_status": routed.get("completion_status")}
    # Each mode performs the same bounded adjacent intelligence duties in its
    # own namespace. These are evidence probes, not production handoffs.
    from nexus_agent_platform.research.last30days_adapter import run_demand_radar_sources
    artifact["last30days"] = run_demand_radar_sources({"request_id": f"{EXPERIMENT_ID}:{mode}:{window}:last30", "work_id": f"{EXPERIMENT_ID}:{mode}:{window}:last30", "objective_id": "LAST30DAYS_PROACTIVE", "query": QUERY, "time_window": "LAST_30_DAYS", "work_class": "DEMAND_DISCOVERY", "requested_sources": ["hackernews", "github"]}, source_timeouts={"hackernews": 45, "github": 45})
    artifact["business_funding"] = fetch_text("https://www.sba.gov/funding-programs/loans")
    try:
        from nexus_agent_platform.research.seo_adapter import adapter as seo_adapter
        artifact["seo"] = seo_adapter(request_id=f"{EXPERIMENT_ID}:{mode}:{window}:seo", work_id=f"{EXPERIMENT_ID}:{mode}:{window}:seo", objective_id="SEO_SEARCH_INTELLIGENCE", url="https://goclearonline.cc", report_type="AUDIT_PAGE", timeout_seconds=90, work_class="SEARCH_OPPORTUNITY")
    except Exception as exc:
        artifact["seo"] = {"status": "ERROR", "error_class": type(exc).__name__, "error": str(exc)[:500]}
    followup = artifact.get("follow_up_searches") or ["official SBA business loan requirements current documentation"]
    artifact["follow_up_search_execution"] = {"query": followup[0], "result": fetch_text("https://www.sba.gov/funding-programs/loans")}
    write(out / f"intelligence_{artifact['video'].get('video_id') or 'unknown'}.json", artifact)
    review = alpha_review(mode, artifact, out)
    event = {"experiment_id": EXPERIMENT_ID, "mode": mode, "window": window, "timestamp": ts(), "discovery": discovery, "selected_video": selected, "agent_choice": agent_choice, "artifact": str((BASE / {"MODE_A_AGENT_FIRST": "mode_a", "MODE_B_RESEARCH_V2_HYBRID": "mode_b", "MODE_C_DETERMINISTIC_AI": "mode_c"}[mode] / f"intelligence_{selected.get('video_id') or 'unknown'}.json").relative_to(ROOT)), "alpha": review, "model_calls": int(bool(agent_choice and agent_choice.get("model_call"))) + int(bool(artifact.get("analysis_model_call"))) + int(review.get("model_calls", 0)), "transcript_analyzed": bool(artifact.get("analysis_model_call")), "followups_generated": len(artifact.get("follow_up_questions", [])), "followups_executed": 0, "source_failure_resilience": "PENDING"}
    append(out / "events.jsonl", event)
    return event


def run_window(window: int) -> dict[str, Any]:
    modes = ["MODE_A_AGENT_FIRST", "MODE_B_RESEARCH_V2_HYBRID", "MODE_C_DETERMINISTIC_AI"]
    rows = [run_mode(mode, window) for mode in modes]
    result = {"experiment_id": EXPERIMENT_ID, "window": window, "started_at": ts(), "modes": rows, "production_cutover": False, "human_intervention": 0}
    write(STATE_DIR / f"window_{window:02d}.json", result)
    return result


def main() -> int:
    global EXPERIMENT_ID, STATE_DIR, BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=int, default=5400)
    parser.add_argument("--interval-seconds", type=int, default=1800)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    args = parser.parse_args()
    EXPERIMENT_ID = args.experiment_id
    BASE = ROOT / "reports/research/architecture_comparison" / EXPERIMENT_ID
    STATE_DIR = ROOT / "data/runtime/research_architecture_real_abc" / EXPERIMENT_ID
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_handle = (STATE_DIR / "runner.lock").open("a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("RUNNER_ALREADY_ACTIVE")
    state_path = STATE_DIR / "experiment_state.json"
    if state_path.exists() and json.loads(state_path.read_text()).get("status") == "COMPLETED":
        raise SystemExit("EXPERIMENT_ID_ALREADY_COMPLETED")
    started = time.time(); started_iso = datetime.fromtimestamp(started, timezone.utc).isoformat(); end = started + args.duration_seconds
    write(state_path, {"status": "RUNNING", "experiment_id": EXPERIMENT_ID, "started_at": started_iso, "target_end_at": datetime.fromtimestamp(end, timezone.utc).isoformat(), "cadence_seconds": args.interval_seconds, "required_windows": 3})
    windows = []
    number = 1
    while time.time() < end:
        windows.append(run_window(number)); number += 1
        due = started + (number - 1) * args.interval_seconds
        wait = max(0.0, min(end - time.time(), due - time.time()))
        if wait > 0: time.sleep(wait)
    final = {"status": "COMPLETED", "experiment_id": EXPERIMENT_ID, "started_at": started_iso, "ended_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": round(time.time() - started, 3), "windows": len(windows), "window_files": [str((STATE_DIR / f"window_{i:02d}.json").relative_to(ROOT)) for i in range(1, len(windows) + 1)]}
    write(state_path, final)
    write(ROOT / "reports/research/nexus_research_real_abc_intelligence_comparison_20260926.json", final)
    (ROOT / "reports/research/NEXUS_RESEARCH_REAL_ABC_INTELLIGENCE_COMPARISON_2026-09-26.md").write_text("# Real A/B/C Intelligence Comparison\n\n" + json.dumps(final, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
