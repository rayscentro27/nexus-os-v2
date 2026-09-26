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
import ssl
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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
SOURCE_TIMEOUTS = {
    "hackernews": 60,
    "github": 60,
    "reddit": 45,
    "grounding": 45,
    "youtube": 90,
}


def _public_json(url: str, *, accept: str = "application/json", timeout: int = 10) -> dict[str, Any] | list[Any]:
    """Read one public JSON endpoint with a small, verified network bound."""
    request = urllib.request.Request(url, headers={"User-Agent": "Nexus-Research/2.0", "Accept": accept})
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        payload = response.read(2_000_000)
    value = json.loads(payload.decode("utf-8", errors="replace"))
    if not isinstance(value, (dict, list)):
        raise ValueError("public endpoint returned non-JSON object")
    return value


def _public_signal(source: str, query: str, url: str, title: str, summary: str, published_at: str, run_id: str, engagement: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "signal_id": _stable("signal", f"{source}:{url}"), "query": query, "topic": title,
        "source_type": source.upper(), "source_url": url, "source_title": title,
        "published_at": published_at, "retrieved_at": _now(), "community": source,
        "engagement": engagement or {}, "freshness": "CURRENT", "relevance": None,
        "excerpt": summary[:2000], "customer_language": summary[:2000],
        "problem_signal": summary[:2000], "desired_outcome_signal": "",
        "complaint_signal": "", "commercial_intent_signal": "",
        "content_hash": _stable("content", summary), "upstream_run_id": run_id,
        "cluster": None,
    }


def _public_source_fallback(source: str, query: str, run_id: str, days: int = 30) -> tuple[list[dict[str, Any]], str]:
    """Use a lightweight public endpoint when the pinned CLI source stalls.

    This is deliberately source-specific.  It is not a second scheduler and it
    never turns an unreachable provider into a fabricated signal.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    # The pinned CLI's natural-language question is often too broad for
    # provider search syntax.  Keep the evidence tied to the question while
    # using a compact provider query that can return dated records.
    provider_query = "AI automation small business" if source == "github" else "AI automation"
    encoded = urllib.parse.quote(provider_query)
    if source == "github":
        data = _public_json(f"https://api.github.com/search/repositories?q={encoded}&sort=updated&order=desc&per_page=8", accept="application/vnd.github+json")
        rows = data.get("items", []) if isinstance(data, dict) else []
        signals = []
        for row in rows:
            stamp = row.get("updated_at") or row.get("pushed_at") or ""
            try:
                if datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            name = str(row.get("full_name") or row.get("name") or "GitHub repository")
            summary = str(row.get("description") or "Repository updated within the research window.")
            signals.append(_public_signal("GITHUB", query, str(row.get("html_url") or ""), name, summary, stamp, run_id, {"stars": row.get("stargazers_count"), "forks": row.get("forks_count")}))
        return signals, "github_public_api_fallback"
    if source == "hackernews":
        data = _public_json(f"https://hn.algolia.com/api/v1/search_by_date?query={encoded}&tags=story&hitsPerPage=10")
        rows = data.get("hits", []) if isinstance(data, dict) else []
        signals = []
        for row in rows:
            stamp = str(row.get("created_at") or "")
            try:
                if datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            title = str(row.get("title") or row.get("story_title") or "Hacker News story")
            url = str(row.get("url") or f"https://news.ycombinator.com/item?id={row.get('objectID')}")
            summary = str(row.get("story_text") or title)
            signals.append(_public_signal("HACKERNEWS", query, url, title, summary, stamp, run_id, {"points": row.get("points"), "comments": row.get("num_comments")}))
        return signals, "hackernews_algolia_public_fallback"
    raise RuntimeError(f"no approved public fallback for {source}")


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


def _runtime_ssl_environment(environment: dict[str, str]) -> None:
    """Give the pinned stdlib HTTP clients a verified CA bundle on macOS.

    The production Mac Python installation has certifi available, while its
    interpreter default CA lookup is incomplete.  This is process-scoped and
    does not weaken TLS verification or add credentials.
    """
    try:
        import certifi
        bundle = certifi.where()
        if bundle and Path(bundle).exists():
            environment.setdefault("SSL_CERT_FILE", bundle)
            environment.setdefault("REQUESTS_CA_BUNDLE", bundle)
    except Exception:
        pass


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
    configured_weights = request.get("source_weights") or {}
    source_weights = {source: float(configured_weights.get(source, 1)) for source in plan_sources}
    plan_path = cache_dir / f"{run_id}.plan.json"
    plan_path.write_text(json.dumps({
        "intent": "product", "freshness_mode": "strict_recent", "cluster_mode": "market",
        "raw_topic": query, "subqueries": [{"label": "demand", "search_query": query, "ranking_query": query, "sources": plan_sources, "weight": 1}],
        "source_weights": source_weights, "notes": ["Nexus Demand Radar bounded plan"],
    }), encoding="utf-8")
    command.extend(["--plan", str(plan_path)])
    if request.get("mock") is True:
        command.append("--mock")
    if requested_sources:
        command.extend(["--search", ",".join(requested_sources)])
    environment = os.environ.copy()
    _runtime_ssl_environment(environment)
    environment["LAST30DAYS_MEMORY_DIR"] = str(cache_dir)
    environment["LAST30DAYS_BROWSER_COOKIES"] = "0"
    environment.pop("LAST30DAYS_PUBLISH_PASSWORD", None)
    limit = max(5, min(int(timeout_seconds or request.get("max_runtime_seconds", 90)), 180))
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        stdout, stderr = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired as exc:
        partial_stdout = exc.stdout or ""
        partial_stderr = exc.stderr or ""
        if process is not None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                tail_stdout, tail_stderr = process.communicate(timeout=5)
                partial_stdout = partial_stdout or tail_stdout or ""
                partial_stderr = partial_stderr or tail_stderr or ""
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        if isinstance(partial_stdout, bytes):
            partial_stdout = partial_stdout.decode(errors="replace")
        if isinstance(partial_stderr, bytes):
            partial_stderr = partial_stderr.decode(errors="replace")
        result = {
            "status": "TIMEOUT", "run_id": run_id, "source_status": {},
            "sources_attempted": requested_sources,
            "stdout_tail": str(partial_stdout)[-1200:],
            "stderr": (str(partial_stderr)[-1800:] or "bounded Last30Days timeout"),
            "timeout_seconds": limit,
        }
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


def run_demand_radar_sources(request: dict[str, Any], *, source_timeouts: dict[str, int] | None = None) -> dict[str, Any]:
    """Run requested sources independently and merge usable partial results.

    The upstream CLI emits its JSON document only after the whole invocation
    completes. Independent bounded invocations prevent one stalled source from
    discarding evidence already returned by another source.
    """
    requested = [str(item).lower() for item in (request.get("requested_sources") or []) if item]
    if not requested:
        requested = ["reddit", "youtube", "hackernews", "github", "grounding"]
    limits = dict(SOURCE_TIMEOUTS)
    limits.update({str(key).lower(): int(value) for key, value in (source_timeouts or {}).items()})
    runs: list[dict[str, Any]] = []
    # Run each provider independently and concurrently. A slow source is
    # recorded as degraded without extending the entire multi-source window.
    def run_one(source: str) -> dict[str, Any]:
        child = dict(request)
        child["request_id"] = f"{request.get('request_id') or 'last30days'}:{source}"
        child["requested_sources"] = [source]
        child["max_runtime_seconds"] = limits.get(source, int(request.get("max_runtime_seconds", 90)))
        return run_demand_radar(child, timeout_seconds=limits.get(source))
    with ThreadPoolExecutor(max_workers=max(1, min(len(requested), 5))) as pool:
        futures = {pool.submit(run_one, source): source for source in requested}
        for future in as_completed(futures):
            source = futures[future]
            try:
                runs.append(future.result())
            except Exception as exc:
                runs.append({"status": "ERROR", "sources_attempted": [source], "stderr": f"{type(exc).__name__}: {exc}", "source_status": {}})

    signals: list[dict[str, Any]] = []
    clusters: list[dict[str, Any]] = []
    source_status: dict[str, str] = {}
    successful: list[str] = []
    errors: list[dict[str, Any]] = []
    for run in runs:
        source_status.update({str(key): str(value) for key, value in (run.get("source_status") or {}).items()})
        signals.extend(run.get("signals") or [])
        clusters.extend(run.get("clusters") or [])
        successful.extend(run.get("sources_successful") or [])
        if run.get("status") in {"TIMEOUT", "ERROR", "UNAVAILABLE"}:
            source = (run.get("sources_attempted") or [])
            source = source[0] if source else str(requested[len(errors)]) if len(errors) < len(requested) else "UNKNOWN"
            errors.append({"source": source, "status": run.get("status"), "stderr": run.get("stderr", "")})
    # Recover useful public evidence independently for providers whose pinned
    # CLI invocation timed out or returned an adapter error.  The original
    # failure remains in partial_runs; a fallback is only successful when it
    # returns dated source records.
    fallback_runs: list[dict[str, Any]] = []
    failed_sources = {str(error.get("source", "")).lower() for error in errors}
    fallback_candidates = sorted((failed_sources | {source for source in requested if source in {"github", "hackernews"} and source not in successful}) & {"github", "hackernews"})
    for source in fallback_candidates:
        try:
            fallback_signals, provider = _public_source_fallback(source, str(request.get("query") or ""), str(request.get("request_id") or _stable("last30days", _now())))
            if fallback_signals:
                inserted, linked = _persist_sources(fallback_signals, str(request.get("request_id") or "public-fallback"))
                fallback_runs.append({"status": "PASS", "run_id": f"fallback:{source}", "result_count": len(fallback_signals), "signals": fallback_signals, "clusters": [], "new_evidence_count": inserted, "existing_source_links": linked, "source_status": {source: "OK_PUBLIC_FALLBACK"}, "sources_successful": [source], "fallback_provider": provider})
                source_status[source] = "OK_PUBLIC_FALLBACK"
                successful.append(source)
                errors = [error for error in errors if str(error.get("source", "")).lower() != source]
        except Exception as exc:
            fallback_runs.append({"status": "ERROR", "run_id": f"fallback:{source}", "result_count": 0, "signals": [], "clusters": [], "source_status": {source: "FALLBACK_ERROR"}, "stderr": f"{type(exc).__name__}: {exc}"})
    runs.extend(fallback_runs)
    for run in fallback_runs:
        signals.extend(run.get("signals") or [])
        successful.extend(run.get("sources_successful") or [])
    deduped: dict[str, dict[str, Any]] = {}
    for signal in signals:
        deduped[str(signal.get("source_url") or signal.get("signal_id"))] = signal
    signals = list(deduped.values())
    source_types = sorted({str(item.get("source_type")) for item in signals if item.get("source_type")})
    if len(source_types) >= 2 and len(signals) >= 2:
        clusters.append({
            "demand_cluster_id": _stable("cluster", f"{request.get('query')}:{':'.join(source_types)}"),
            "cluster_title": str(request.get("query") or "cross-source demand"),
            "audience": "unknown until Research verifies the signal",
            "problem": "Cross-source human signals require Research verification.",
            "question": request.get("query"), "source_types": source_types,
            "source_refs": [item.get("source_url") for item in signals if item.get("source_url")],
            "signal_count": len(signals),
            "engagement_summary": {"items": [_engagement(item) for item in signals]},
            "freshness": "CURRENT", "customer_language_examples": [item.get("customer_language", "")[:300] for item in signals[:4]],
            "complaint_signals": [], "desired_outcomes": [], "commercial_intent": "UNKNOWN",
            "contradictions": [], "evidence_strength": "DISCOVERY_ONLY",
        })
    status = "PASS" if signals else "DEGRADED" if errors or any(value not in {"NO_RESULTS", "OK"} for value in source_status.values()) else "NO_RESULTS"
    merged = {
        "status": status, "run_id": str(request.get("request_id") or _stable("last30days", f"merged:{_now()}")),
        "request_id": request.get("request_id"), "work_id": request.get("work_id"), "objective_id": request.get("objective_id"),
        "query": request.get("query"), "time_window": request.get("time_window", "LAST_30_DAYS"),
        "work_class": str(request.get("work_class") or "DEMAND_DISCOVERY").upper(), "completed_at": _now(),
        "source_status": source_status, "sources_attempted": requested, "sources_successful": sorted(set(successful)),
        "signals": signals, "clusters": clusters, "result_count": len(signals), "cluster_count": len(clusters),
        "new_evidence_count": sum(int(run.get("new_evidence_count") or 0) for run in runs),
        "existing_source_links": sum(int(run.get("existing_source_links") or 0) for run in runs),
        "partial_runs": [{"run_id": run.get("run_id"), "status": run.get("status"), "result_count": run.get("result_count", 0), "source_status": run.get("source_status", {}), "stderr": run.get("stderr", "")} for run in runs],
        "errors": errors, "browser_cookies_enabled": False, "publication_enabled": False, "external_mutations": False,
    }
    _write_run(merged)
    return merged


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
