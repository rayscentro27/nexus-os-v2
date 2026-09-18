"""Bounded, read-only Nexus adapter for the pinned ``iannuttall/seo`` CLI."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence

ROOT = Path(__file__).resolve().parents[3]
PINNED_COMMIT = "52f10012021131c2405cddfb976d583a6af3b490"
PINNED_VERSION = "0.2.40"
DEFAULT_INSTALL = ROOT / ".runtime" / "third_party" / "iannuttall-seo" / "npm-runtime-0.2.40"
SEO_TIMEOUT_SECONDS = 120
SEO_MAX_PAGES = 25
SEO_MAX_DEPTH = 3
SEO_CONCURRENCY = 1
RUN_STATE = ROOT / "data" / "runtime" / "seo_operational_state_latest.json"

ALLOWED_REPORT_TYPES = {"SITE_TECHNICAL", "AUDIT_PAGE", "SITEMAP_HEALTH", "REPORT_CATALOG"}
WORK_CLASSES = {"TECHNICAL_FIX", "SEARCH_OPPORTUNITY", "CONTENT_OPPORTUNITY", "BUSINESS_RELEVANT_FINDING"}
MUTATION_COMMANDS_BLOCKED = {"indexnow", "auth", "login", "logout", "mutate", "delete", "publish", "provider", "credential", "gsc", "ga4", "dataforseo", "semrush", "ahrefs", "oauth", "openid"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"


def _install_path() -> Path:
    configured = os.environ.get("NEXUS_SEO_INSTALL_PATH", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_INSTALL


def _cli_path() -> Path:
    """Return the already-installed published CLI; never install implicitly."""
    install = _install_path()
    for candidate in (install / "node_modules/.bin/seo", install / "node_modules/seo/dist/cli.js"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"pinned seo@{PINNED_VERSION} runtime is missing at {install}")


def _run_cmd(args: list[str], timeout: int | None = None) -> tuple[str, str, int, float]:
    """Run fixed argv in its own process group and clean it up on timeout."""
    cli = _cli_path()
    env = dict(os.environ)
    env.update({"DO_NOT_TRACK": "1", "NEXUS": "1"})
    started = time.monotonic()
    proc = subprocess.Popen([str(cli), *args], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout or SEO_TIMEOUT_SECONDS)
        return stdout, stderr, proc.returncode, round(time.monotonic() - started, 3)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            stdout, stderr = proc.communicate(timeout=3)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        return stdout or "", (stderr or "") + f"\nTIMEOUT after {exc.timeout}s", -1, round(time.monotonic() - started, 3)


def _parse_json_output(text: str) -> dict[str, Any] | None:
    """Parse complete structured JSON only; logs/stderr are never evidence."""
    if not text or not text.strip():
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _validate_url(url: str) -> bool:
    return url.startswith(("https://", "http://")) and "\n" not in url and "\r" not in url


def _build_args(report_type: str, url: str, max_pages: int, max_depth: int) -> list[str]:
    if report_type == "SITE_TECHNICAL":
        # The published CLI takes the crawl target positionally.  ``--url`` is
        # valid for report/audit-page but causes crawl to wait on an invalid
        # empty target in 0.2.40.
        return ["crawl", url, "--max-pages", str(max_pages), "--max-depth", str(max_depth), "--json"]
    if report_type == "AUDIT_PAGE":
        return ["audit-page", "--url", url, "--json"]
    if report_type == "SITEMAP_HEALTH":
        return ["crawl", "--sitemap-url", url, "--health", "--json"]
    if report_type == "REPORT_CATALOG":
        return ["reports", "list", "--json"]
    raise ValueError(f"unsupported read-only operation: {report_type}")


def _allowlist_check(args: list[str]) -> bool:
    if not args or args[0] not in {"crawl", "audit-page", "reports"}:
        return False
    if args[0] == "reports" and args[1:2] != ["list"]:
        return False
    lowered = " ".join(args).lower()
    return not any(token in lowered for token in MUTATION_COMMANDS_BLOCKED)


def _classify_finding(finding: dict[str, Any]) -> str:
    category = str(finding.get("category") or "").lower()
    severity = str(finding.get("severity") or "").lower()
    rule_id = str(finding.get("ruleId") or finding.get("id") or "")
    if severity == "high":
        return "TECHNICAL_FIX"
    if severity == "medium" and (category in {"metadata", "content"} or rule_id in {"missing_meta_description", "near_empty_content"}):
        return "SEARCH_OPPORTUNITY"
    if severity == "low" and category == "content":
        return "CONTENT_OPPORTUNITY"
    return "TECHNICAL_FIX"


def _normalize_finding(page: dict[str, Any], finding: dict[str, Any], report_type: str, site_url: str, **ids: str | None) -> dict[str, Any]:
    rule_id = str(finding.get("ruleId") or finding.get("id") or "unknown")
    page_url = str(page.get("url") or site_url)
    raw = json.dumps(finding, sort_keys=True, separators=(",", ":"))
    return {
        "seo_evidence_id": _stable("seo", f"{site_url}|{page_url}|{rule_id}|{report_type}"),
        "source_tool": "iannuttall/seo", "tool_version": PINNED_VERSION, "report_type": report_type,
        "site_url": site_url, "page_url": page_url, "finding_id": rule_id,
        "finding_type": finding.get("category") or "unknown", "severity": finding.get("severity") or "unknown",
        "observed_evidence": raw, "derived_finding": _classify_finding(finding),
        "recommended_action": finding.get("recommendation") or finding.get("howToFix") or "",
        "verification_method": finding.get("howToVerify") or "",
        "coverage_state": finding.get("coverageState") or finding.get("coverage") or "COMPLETE",
        "skipped_checks": finding.get("warnings") or [], "partial_coverage": finding.get("caveats") or [],
        "provider": "iannuttall/seo", "retrieved_at": _now_iso(), "content_hash": _stable("content", raw),
        "request_id": ids.get("request_id"), "work_id": ids.get("work_id"), "objective_id": ids.get("objective_id"),
        "investigation_id": ids.get("investigation_id"),
    }


def _iter_findings(result: dict[str, Any], report_type: str, site_url: str, **ids: str | None) -> list[dict[str, Any]]:
    pages = [p for p in result.get("pages", []) if isinstance(p, dict)]
    issues = [i for i in result.get("issues", []) if isinstance(i, dict)]
    findings: list[dict[str, Any]] = []
    for issue in issues:
        urls = set(issue.get("sampleUrls") or [])
        for page in pages:
            if not urls or page.get("url") in urls or issue.get("url") == page.get("url"):
                findings.append(_normalize_finding(page, issue, report_type, site_url, **ids))
    for group in result.get("issueGroups", []) or result.get("topFixes", []) or []:
        if isinstance(group, dict):
            for url in group.get("sampleUrls") or [site_url]:
                page = next((p for p in pages if p.get("url") == url), {"url": url})
                findings.append(_normalize_finding(page, group, report_type, site_url, **ids))
    unique: dict[str, dict[str, Any]] = {}
    for finding in findings:
        unique[finding["seo_evidence_id"]] = finding
    return list(unique.values())


def _persist_findings(findings: list[dict[str, Any]], run_id: str) -> tuple[int, int]:
    existing = persistence.read_records("research_v2_sources")
    known_ids = {str(row.get("source_id") or row.get("seo_evidence_id")) for row in existing}
    known_hashes = {str(row.get("content_hash")) for row in existing if row.get("content_hash")}
    inserted = linked = 0
    for finding in findings:
        sid, content_hash = finding["seo_evidence_id"], finding["content_hash"]
        if sid in known_ids or content_hash in known_hashes:
            linked += 1
            continue
        persistence.append_record("research_v2_sources", {
            "schema_version": "nexus.research-v2.1", "source_id": sid, "source_type": "SEO_TECHNICAL_AUDIT",
            "source_url": finding["page_url"], "source_title": finding["finding_id"], "text": finding["derived_finding"],
            "source_observation": True, "research_intents": [finding["derived_finding"]], "processing_status": "FULLY_PROCESSED",
            "recorded_at": finding["retrieved_at"], "upstream_run_id": run_id, "content_hash": content_hash, "seo_evidence": finding,
        })
        known_ids.add(sid); known_hashes.add(content_hash); inserted += 1
    return inserted, linked


def _write_runtime_state(state: dict[str, Any]) -> None:
    RUN_STATE.parent.mkdir(parents=True, exist_ok=True)
    RUN_STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def adapter(*, request_id: str, work_id: str, objective_id: str | None = None, investigation_id: str | None = None,
            url: str = "", report_type: str = "SITE_TECHNICAL", max_pages: int = SEO_MAX_PAGES,
            max_depth: int = SEO_MAX_DEPTH, timeout_seconds: int = SEO_TIMEOUT_SECONDS,
            requested_by: str = "nexus", work_class: str = "TECHNICAL_FIX") -> dict[str, Any]:
    started = time.monotonic()
    if report_type not in ALLOWED_REPORT_TYPES or work_class not in WORK_CLASSES:
        return {"status": "REJECTED", "error": "report_type or work_class is not allowed"}
    if report_type != "REPORT_CATALOG" and not _validate_url(url):
        return {"status": "REJECTED", "error": "url must be an http(s) URL"}
    max_pages, max_depth = min(max(int(max_pages), 1), SEO_MAX_PAGES), min(max(int(max_depth), 0), SEO_MAX_DEPTH)
    args = _build_args(report_type, url, max_pages, max_depth)
    if not _allowlist_check(args):
        return {"status": "BLOCKED", "error": "read-only allowlist rejected operation"}
    try:
        stdout, stderr, returncode, runtime = _run_cmd(args, timeout_seconds)
    except FileNotFoundError as exc:
        state = {"status": "UNAVAILABLE", "last_error": str(exc), "retrieved_at": _now_iso()}
        _write_runtime_state(state)
        return {**state, "request_id": request_id, "work_id": work_id}
    result = _parse_json_output(stdout)
    if result is None:
        state = {"status": "TIMEOUT" if returncode == -1 else "PARSE_ERROR", "last_error": stderr[-1000:], "retrieved_at": _now_iso()}
        _write_runtime_state(state)
        return {**state, "request_id": request_id, "work_id": work_id, "execution_time_seconds": runtime}
    site_url = str(result.get("definition", {}).get("config", {}).get("url") or url)
    findings = _iter_findings(result, report_type, site_url, request_id=request_id, work_id=work_id, objective_id=objective_id, investigation_id=investigation_id)
    counts = {level: sum(1 for f in findings if str(f.get("severity")).lower() == level) for level in ("high", "medium", "low")}
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    coverage = result.get("coverageState") or result.get("coverage") or ("PARTIAL" if result.get("caveats") or result.get("warnings") else "COMPLETE")
    inserted, linked = _persist_findings(findings, request_id)
    state = {"status": "SUCCESS" if returncode == 0 else "FAILED", "last_run": _now_iso(), "site_url": site_url,
             "pages_crawled": summary.get("crawledUrls", summary.get("pagesCrawled", 0)), "finding_count": len(findings),
             "severity_counts": counts, "coverage_state": coverage, "last_error": stderr[-1000:] if returncode else None,
             "source": "seo_adapter.py", "request_id": request_id}
    _write_runtime_state(state)
    return {"status": state["status"], "seo_tool": "iannuttall/seo", "seo_version": PINNED_VERSION, "seo_commit": PINNED_COMMIT,
            "site_url": site_url, "pages_crawled": state["pages_crawled"], "findings": findings, "total_findings": len(findings),
            "severity_counts": counts, "coverage_state": coverage, "persisted_findings": inserted, "linked_existing": linked,
            "request_id": request_id, "work_id": work_id, "objective_id": objective_id, "investigation_id": investigation_id,
            "requested_by": requested_by, "execution_time_seconds": round(time.monotonic() - started, 3),
            "status_details": {"structured_json": True, "read_only": True, "do_not_track": True, "returncode": returncode, "stderr": stderr[-1000:] if returncode else ""}}


__all__ = ["adapter", "_allowlist_check", "_parse_json_output", "_normalize_finding", "_run_cmd"]
