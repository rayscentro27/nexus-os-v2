"""Bounded Last30Days Demand Radar adapter.

Last30Days is an acquisition tool, not a Nexus source of truth or business
decision-maker.  This adapter runs the pinned third-party CLI with cookies and
publication disabled, normalizes its versioned JSON export, and persists only
bounded source evidence and run metadata into the existing Research V2 store.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence

ROOT = Path(__file__).resolve().parents[3]
PINNED_COMMIT = "25a5cea5bfa5723991894385041ebb3b87049753"
DEFAULT_INSTALL = ROOT / ".runtime" / "third_party" / "last30days-skill" / PINNED_COMMIT
DEFAULT_CACHE = ROOT / ".runtime" / "last30days-cache"
RUN_SNAPSHOT = ROOT / "data" / "runtime" / "last30days_demand_radar_latest.json"
RUN_LOG = ROOT / "data" / "runtime" / "last30days_demand_radar_runs.jsonl"
WINDOW_DAYS = {"LAST_24_HOURS": 1, "LAST_7_DAYS": 7, "LAST_30_DAYS": 30, "LAST_90_DAYS": 90, "EVERGREEN": 3650}
WORK_CLASSES = {"DEMAND_DISCOVERY", "GENERAL_DISCOVERY", "MONITORED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:20]}"


def _install_path() -> Path:
    configured = os.environ.get("LAST30DAYS_INSTALL_PATH", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_INSTALL


def _script_path() -> Path:
    return _install_path() / "skills" / "last30days" / "scripts" / "last30days.py"


def _json_from_stdout(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start : end + 1])
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def _source_status(value: Any) -> str:
    return str(value or "ERROR").upper().replace("-", "_")


def _source_type(result: dict[str, Any]) -> str:
    return str(result.get("source") or "UNKNOWN").upper()


def _engagement(result: dict[str, Any]) -> dict[str, Any]:
    value = result.get("engagement")
    return value if isinstance(value, dict) else {}


def _normalized_signals(data: dict[str, Any], upstream_run_id: str) -> list[dict[str, Any]]:
    signals = []
    for row in data.get("results") or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "")
        source = _source_type(row)
        signal_id = _stable("signal", f"{source}:{url or row.get('title', '')}")
        engagement = _engagement(row)
        signals.append({
            "signal_id": signal_id, "query": data.get("query"), "topic": row.get("title"),
            "source_type": source, "source_url": url, "source_title": row.get("title"),
            "published_at": row.get("published_at"), "retrieved_at": data.get("generated_at") or _now(),
            "community": row.get("source"), "engagement": engagement,
            "freshness": "CURRENT", "relevance": row.get("relevance_score"),
            "excerpt": row.get("summary") or "", "customer_language": row.get("summary") or "",
            "problem_signal": row.get("summary") or "", "desired_outcome_signal": "",
            "complaint_signal": "", "commercial_intent_signal": "",
            "content_hash": _stable("content", json.dumps(row, sort_keys=True)),
            "upstream_run_id": upstream_run_id, "cluster": row.get("cluster"),
        })
    return signals


def _clusters(data: dict[str, Any], signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_cluster: dict[int, list[dict[str, Any]]] = {}
    for signal in signals:
        cluster = signal.get("cluster")
        if isinstance(cluster, int):
            by_cluster.setdefault(cluster, []).append(signal)
    output = []
    for index, row in enumerate(data.get("clusters") or []):
        if not isinstance(row, dict):
            continue
        members = by_cluster.get(index, [])
        output.append({
            "demand_cluster_id": _stable("cluster", f"{data.get('query')}:{index}:{row.get('title')}"),
            "cluster_title": row.get("title") or "Untitled demand cluster",
            "audience": "unknown until Research verifies the signal",
            "problem": row.get("summary") or row.get("title") or "unknown",
            "question": data.get("query"),
            "source_types": sorted({item["source_type"] for item in members}),
            "source_refs": [item["source_url"] for item in members if item.get("source_url")],
            "signal_count": len(members),
            "engagement_summary": {"total": row.get("engagement_total", 0), "items": [_engagement(item) for item in members]},
            "freshness": "CURRENT", "customer_language_examples": [item["customer_language"][:300] for item in members[:4]],
            "complaint_signals": [], "desired_outcomes": [], "commercial_intent": "UNKNOWN",
            "contradictions": [], "evidence_strength": "DISCOVERY_ONLY",
        })
    return output


def _persist_sources(signals: list[dict[str, Any]], run_id: str) -> tuple[int, int]:
    existing = persistence.read_records("research_v2_sources")
    known = {str(row.get("source_url")) for row in existing if row.get("source_url")}
    inserted = 0
    linked = 0
    for signal in signals:
        url = signal.get("source_url")
        if not url:
            continue
        if url in known:
            linked += 1
            continue
        persistence.append_record("research_v2_sources", {
            "schema_version": "nexus.research-v2.1", "source_id": signal["signal_id"],
            "source_type": signal["source_type"], "source_url": url,
            "source_title": signal.get("source_title"), "source_author_or_channel": signal.get("community"),
            "text": signal.get("excerpt") or "NOT_PRESENT", "source_observation": True,
            "research_intents": ["CUSTOMER_DEMAND_DISCOVERY"], "processing_status": "DISCOVERY_CAPTURED",
            "recorded_at": signal.get("retrieved_at") or _now(), "upstream_run_id": run_id,
            "content_hash": signal.get("content_hash"), "engagement": signal.get("engagement") or {},
        })
        known.add(url)
        inserted += 1
    return inserted, linked


def _write_run(record: dict[str, Any]) -> None:
    RUN_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    RUN_SNAPSHOT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with RUN_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def run_demand_radar(request: dict[str, Any], *, timeout_seconds: int | None = None) -> dict[str, Any]:
    """Run one bounded Last30Days acquisition under the existing discovery class."""
    ops_path = str(ROOT / "scripts" / "ops")
    if ops_path not in sys.path:
        sys.path.insert(0, ops_path)
    try:
        from nexus_runtime_env import load_runtime_env
        load_runtime_env()
    except Exception:
        # The daemon normally loads runtime credentials before invoking the
        # adapter; direct health/fixture runs remain safe without them.
        pass
    work_class = str(request.get("work_class") or "DEMAND_DISCOVERY").upper()
    if work_class not in WORK_CLASSES:
        raise ValueError(f"unsupported Last30Days work_class: {work_class}")
    query = str(request.get("query") or "").strip()
    if not query:
        raise ValueError("Last30Days demand radar requires query")
    window = str(request.get("time_window") or "LAST_30_DAYS").upper()
    days = WINDOW_DAYS.get(window, 30)
    run_id = str(request.get("request_id") or _stable("last30days", f"{query}:{window}:{_now()}"))
    cache_dir = Path(request.get("cache_dir") or DEFAULT_CACHE)
    cache_dir.mkdir(parents=True, exist_ok=True)
    script = _script_path()
    started = _now()
    if not script.exists():
        result = {"status": "UNAVAILABLE", "run_id": run_id, "error": "pinned Last30Days installation is missing", "source_status": {}}
        _write_run(result)
        return result
    command = [sys.executable, str(script), query, "--emit=json", "--json-profile=agent", "--no-browser-cookies", "--quick", "--days", str(days), "--max-results", str(min(int(request.get("max_results", 20)), 50)), "--max-per-source", str(min(int(request.get("max_per_source", 8)), 20)), "--save-dir", str(cache_dir)]
    requested_sources = [str(item) for item in (request.get("requested_sources") or []) if item]
    plan_sources = requested_sources or ["reddit", "youtube", "hackernews", "github", "grounding"]
    plan_path = cache_dir / f"{run_id}.plan.json"
    plan_path.write_text(json.dumps({
        "intent": "product", "freshness_mode": "strict_recent", "cluster_mode": "market",
        "raw_topic": query, "subqueries": [{"label": "demand", "search_query": query, "ranking_query": query, "sources": plan_sources, "weight": 1}],
        "source_weights": {source: 1 for source in plan_sources}, "notes": ["Nexus Demand Radar bounded plan"],
    }), encoding="utf-8")
    command.extend(["--plan", str(plan_path)])
    if request.get("mock") is True:
        command.append("--mock")
    if requested_sources:
        command.extend(["--search", ",".join(requested_sources)])
    environment = os.environ.copy()
    environment["LAST30DAYS_MEMORY_DIR"] = str(cache_dir)
    environment["LAST30DAYS_BROWSER_COOKIES"] = "0"
    environment.pop("LAST30DAYS_PUBLISH_PASSWORD", None)
    limit = max(5, min(int(timeout_seconds or request.get("max_runtime_seconds", 90)), 180))
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        stdout, stderr = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        if process is not None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        result = {"status": "TIMEOUT", "run_id": run_id, "source_status": {}, "stderr": "bounded Last30Days timeout"}
        _write_run(result)
        return result
    except OSError as exc:
        result = {"status": "ERROR", "run_id": run_id, "source_status": {}, "stderr": type(exc).__name__}
        _write_run(result)
        return result
    data = _json_from_stdout(stdout or "")
    if process.returncode != 0 or not data:
        result = {"status": "ERROR", "run_id": run_id, "source_status": {}, "stderr": (stderr or "invalid Last30Days JSON")[-1200:]}
        _write_run(result)
        return result
    signals = _normalized_signals(data, run_id)
    clusters = _clusters(data, signals)
    inserted, linked = _persist_sources(signals, run_id)
    source_values = [str(value).lower() for value in (data.get("source_status") or {}).values()]
    run_status = "PASS" if signals else "DEGRADED" if any(value not in {"no-results", "ok"} for value in source_values) else "NO_RESULTS"
    result = {
        "status": run_status, "run_id": run_id,
        "request_id": request.get("request_id"), "work_id": request.get("work_id"), "objective_id": request.get("objective_id"),
        "query": query, "time_window": window, "work_class": work_class,
        "started_at": started, "completed_at": _now(), "schema_version": data.get("schema_version"),
        "source_status": {str(key): _source_status(value) for key, value in (data.get("source_status") or {}).items()},
        "sources_attempted": sorted((data.get("source_status") or {}).keys()),
        "sources_successful": sorted(key for key, value in (data.get("source_status") or {}).items() if str(value).lower() in {"ok", "partial"}),
        "signals": signals, "clusters": clusters, "result_count": len(signals), "cluster_count": len(clusters),
        "new_evidence_count": inserted, "existing_source_links": linked,
        "browser_cookies_enabled": False, "publication_enabled": False, "external_mutations": False,
        "upstream_cache_dir": str(cache_dir), "stderr": (stderr or "")[-800:],
    }
    _write_run(result)
    return result


def health() -> dict[str, Any]:
    script = _script_path()
    return {"status": "HEALTHY" if script.exists() else "UNAVAILABLE", "version": "3.24.0", "pinned_commit": PINNED_COMMIT, "install_path": str(_install_path()), "browser_cookies_enabled": False, "publication_enabled": False}


def _need_match(cluster: dict[str, Any]) -> dict[str, Any] | None:
    needs_path = ROOT / "data" / "governed" / "research_needs.jsonl"
    if not needs_path.exists():
        return None
    query_words = {word for word in str(cluster.get("problem") or cluster.get("question") or "").lower().split() if len(word) > 3}
    best: tuple[float, dict[str, Any]] | None = None
    for line in needs_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        existing_words = {word for word in str(row.get("problem") or row.get("question") or "").lower().split() if len(word) > 3}
        score = len(query_words & existing_words) / max(1, len(query_words | existing_words))
        if best is None or score > best[0]:
            best = (score, row)
    return best[1] if best and best[0] >= 0.35 else None


def promote_clusters(run: dict[str, Any], *, minimum_source_types: int = 2, minimum_signals: int = 2) -> list[dict[str, Any]]:
    """Promote only strong clusters through the existing need/Alpha path."""
    from nexus_agent_platform.alpha_model_review import review_demand_package

    outcomes = []
    signal_by_url = {str(item.get("source_url")): item for item in run.get("signals") or [] if item.get("source_url")}
    for cluster in run.get("clusters") or []:
        if len(cluster.get("source_types") or []) < minimum_source_types or int(cluster.get("signal_count") or 0) < minimum_signals:
            outcomes.append({"cluster_id": cluster.get("demand_cluster_id"), "status": "HELD_BELOW_PROMOTION_THRESHOLD"})
            continue
        existing = _need_match(cluster)
        if existing:
            linked = dict(existing)
            linked["source_refs"] = sorted(set((existing.get("source_refs") or []) + (cluster.get("source_refs") or [])))
            linked["last30days_cluster_id"] = cluster.get("demand_cluster_id")
            linked["updated_at"] = _now()
            # Append-only need history: same need_id, enriched evidence.  The
            # existing reader's latest-record semantics preserve one need.
            needs_path = ROOT / "data" / "governed" / "research_needs.jsonl"
            with needs_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(linked, sort_keys=True) + "\n")
            outcomes.append({"cluster_id": cluster.get("demand_cluster_id"), "status": "EXISTING_NEED_ENRICHED", "need_id": existing.get("need_id")})
            continue
        package = {
            "research_id": cluster.get("demand_cluster_id"), "query": cluster.get("question") or run.get("query"),
            "summary": cluster.get("problem"), "sources": [signal_by_url[url] for url in cluster.get("source_refs") or [] if url in signal_by_url],
            "analysis": {"summary": cluster.get("problem"), "recommended_next_action": "Alpha review required before any external action."},
        }
        review = review_demand_package(package)
        outcomes.append({"cluster_id": cluster.get("demand_cluster_id"), "status": review.get("status"), "need_id": (review.get("need") or {}).get("need_id"), "alpha_receipt_id": (review.get("receipt") or {}).get("receipt_id"), "alpha_decision": (review.get("evaluation") or {}).get("decision")})
    return outcomes
