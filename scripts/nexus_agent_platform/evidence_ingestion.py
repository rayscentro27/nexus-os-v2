"""Bounded Nexus evidence-ingestion capability worker.

This is a capability adapter, not a scheduler, research brain, approval store,
or authority layer. It converts one explicitly supplied local file or one
public URL into a provenance-first artifact and a small receipt. Heavy or
networked work is intentionally kept outside the certified Nexus processes.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_RUNTIME = ROOT / "data/runtime/evidence_ingestion"
DEFAULT_ARTIFACTS = DEFAULT_RUNTIME / "artifacts"
DEFAULT_HANDOFF = DEFAULT_RUNTIME / "intake_events.jsonl"
DEFAULT_RECEIPTS = ROOT / "reports/runtime/evidence_ingestion_receipts"
DEFAULT_HEARTBEAT = ROOT / "reports/runtime/nexus_evidence_ingestion_heartbeat_latest.json"

SCHEMA_VERSION = "nexus.evidence.v1"
NORMALIZATION_VERSION = "nexus.evidence.normalization.v1"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_CHARS = 500_000
MAX_URL_CHARS = 2_048
MAX_TIMEOUT_SECONDS = 30
ALLOWED_SUFFIXES = {".txt", ".md", ".markdown", ".html", ".htm", ".pdf", ".docx", ".xlsx", ".pptx"}
BLOCKED_PARTS = {".env", ".env.local", ".env.production", "runtime.env", ".ssh", ".aws", ".config", "credentials", "secrets"}
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|pk)_(?:live|test)_[a-z0-9]{12,}\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)

ERRORS = {
    "SUCCESS", "NO_CHANGE", "DUPLICATE", "UNSUPPORTED_FORMAT", "SOURCE_TOO_LARGE",
    "INVALID_PATH", "BLOCKED_PATH", "INVALID_URL", "PRIVATE_NETWORK_BLOCKED",
    "REDIRECT_BLOCKED", "SOURCE_UNAVAILABLE", "ACCESS_DENIED", "ROBOTS_BLOCKED",
    "TIMEOUT", "PARSE_FAILED", "CONVERSION_FAILED", "CONTENT_EMPTY",
    "SAFETY_BLOCKED", "DEPENDENCY_UNAVAILABLE",
}

DEFAULT_TENANT_CONTEXT = {"scope": "founder_admin", "tenant_id": None}


def build_job_envelope(*, adapter: str, source: dict, job_id: Optional[str] = None,
                       tenant_context: Optional[dict] = None, limits: Optional[dict] = None) -> dict:
    """Build the transport-neutral request sent to a local or future worker."""
    return safe_json({
        "job_id": job_id or f"evidence-{uuid.uuid4().hex[:16]}",
        "capability": "evidence_ingestion",
        "adapter": adapter,
        "source": source,
        "policy": {"public_only": adapter == "crawl4ai", "no_external_processing": True},
        "limits": limits or {"max_pages": 1, "max_depth": 0, "timeout_seconds": MAX_TIMEOUT_SECONDS},
        "tenant_context": tenant_context or DEFAULT_TENANT_CONTEXT,
        "requested_at": utc_now(),
    })


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in value.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def material_hash(value: str) -> str:
    return sha256_bytes(normalize_text(value).encode("utf-8"))


def classify_text(value: str) -> tuple[str, bool, str]:
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            return "RESTRICTED", True, "restricted-pattern-detected"
    if re.search(r"(?i)\b(?:ssn|social security|credit report|account number|routing number)\b", value):
        return "SENSITIVE", True, "sensitive-term-detected"
    return "PUBLIC", False, "no-sensitive-pattern-detected"


def result_error(status: str, *, job_id: str, adapter: str, message: str, started: str, source: Optional[dict] = None) -> dict:
    if status not in ERRORS:
        status = "PARSE_FAILED"
    completed = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": f"ev-{uuid.uuid4().hex[:20]}",
        "receipt_id": f"evidence-receipt-{uuid.uuid4().hex[:16]}",
        "job_id": job_id,
        "status": status,
        "adapter": adapter,
        "worker_type": "MAC_MINI_ISOLATED_WORKER",
        "error": {"classification": status, "message": message[:500]},
        "source": {**(source or {}), "adapter": adapter},
        "integrity": {"source_hash": None, "material_hash": None, "normalization_version": NORMALIZATION_VERSION, "duplicate_status": "NOT_APPLICABLE"},
        "content": {"title": None, "normalized_text_or_markdown": "", "truncated": False, "metadata": {}},
        "safety": {"redaction_status": "NOT_RUN", "network_classification": "NOT_PROCESSED", "sensitive_data_detected": False, "external_processing": False},
        "execution": {"job_id": job_id, "worker_type": "MAC_MINI_ISOLATED_WORKER", "requested_at": started, "started_at": started, "completed_at": completed, "duration_ms": 0},
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_json(value: dict) -> dict:
    return json.loads(json.dumps(value, default=str))


def allowed_local_path(path_value: str, allowed_roots: list[Path], max_bytes: int) -> tuple[Optional[Path], Optional[str]]:
    try:
        path = Path(path_value).expanduser()
        if path.is_symlink():
            return None, "symlink-not-allowed"
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "path-not-found"
    if not resolved.is_file():
        return None, "not-a-regular-file"
    if any(part.lower() in BLOCKED_PARTS or part.lower().endswith(".env") for part in resolved.parts):
        return None, "blocked-sensitive-path"
    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        return None, "unsupported-extension"
    if not any(resolved == root or root in resolved.parents for root in (r.resolve() for r in allowed_roots)):
        return None, "outside-approved-intake-root"
    try:
        if resolved.stat().st_size > max_bytes:
            return None, "source-too-large"
    except OSError:
        return None, "stat-failed"
    return resolved, None


def _convert_markitdown(path: Path) -> str:
    try:
        from markitdown import MarkItDown
    except Exception as exc:  # pragma: no cover - exercised by environment check
        raise RuntimeError(f"markitdown unavailable: {exc}") from exc
    result = MarkItDown().convert(str(path))
    text = getattr(result, "text_content", None)
    if text is None:
        text = str(result)
    return str(text)


def _resolved_ip_addresses(host: str) -> list[ipaddress._BaseAddress]:
    addresses = []
    try:
        for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
            addresses.append(ipaddress.ip_address(item[4][0]))
    except (OSError, ValueError):
        return []
    return list(dict.fromkeys(addresses))


def validate_public_url(url: str, *, resolve_host: Callable[[str], list[ipaddress._BaseAddress]] = _resolved_ip_addresses) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(url, str) or len(url.strip()) > MAX_URL_CHARS:
        return None, "invalid-url"
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None, "unsupported-url-or-credentials"
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"} or host.endswith(".localhost"):
        return None, "private-network-host"
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        addresses = resolve_host(host)
        if not addresses:
            return None, "host-resolution-failed"
    if any(address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast or address.is_unspecified for address in addresses):
        return None, "private-network-address"
    return parsed.geturl(), None


def _crawl_with_crawl4ai(url: str, timeout_seconds: int) -> dict:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    except Exception as exc:  # pragma: no cover - environment check
        raise RuntimeError(f"crawl4ai unavailable: {exc}") from exc

    async def run() -> dict:
        browser = BrowserConfig(headless=True, verbose=False, java_script_enabled=True,
                               accept_downloads=False, max_pages_before_recycle=1,
                               user_agent="NexusEvidencePilot/1.0 (+https://github.com/rayscentro27/nexus-os-v2)")
        config = CrawlerRunConfig(page_timeout=timeout_seconds * 1000, wait_until="domcontentloaded",
                                  check_robots_txt=True, max_retries=0,
                                  remove_forms=True, process_iframes=False, screenshot=False,
                                  pdf=False, capture_mhtml=False, verbose=False)
        async with AsyncWebCrawler(config=browser, base_directory=str(DEFAULT_RUNTIME)) as crawler:
            result = await crawler.arun(url=url, config=config)
            return {
                "success": bool(getattr(result, "success", False)),
                "status_code": getattr(result, "status_code", None),
                "final_url": getattr(result, "url", None) or getattr(result, "redirected_url", None) or url,
                "title": getattr(result, "title", None),
                "markdown": getattr(result, "markdown", None) or "",
                "html": getattr(result, "html", None) or "",
                "error_message": getattr(result, "error_message", None),
            }
    return asyncio.run(asyncio.wait_for(run(), timeout=timeout_seconds + 5))


def _write_artifact(result: dict, root: Path, receipt_dir: Path, handoff: Path) -> dict:
    evidence_id = result["evidence_id"]
    artifact_path = root / "artifacts" / f"{evidence_id}.json"
    receipt_path = receipt_dir / f"{result['receipt_id']}.json"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    with handoff.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({
            "event_type": "evidence_ingestion_completed",
            "evidence_id": evidence_id,
            "job_id": result["job_id"],
            "status": result["status"],
            "source": result["source"],
            "integrity": result["integrity"],
            "artifact_ref": str(artifact_path),
            "created_at": result["execution"]["completed_at"],
        }, sort_keys=True) + "\n")
    public_result = dict(result)
    public_result["content"] = dict(public_result.get("content") or {})
    artifact_payload = dict(public_result)
    write_json(artifact_path, artifact_payload)
    receipt = {
        "receipt_id": result["receipt_id"], "job_id": result["job_id"], "evidence_id": evidence_id,
        "source_type": result["source"]["source_type"], "adapter": result["source"]["adapter"],
        "worker_type": result["execution"]["worker_type"], "requested_at": result["execution"]["requested_at"],
        "started_at": result["execution"]["started_at"], "completed_at": result["execution"]["completed_at"],
        "result": result["status"], "source_hash": result["integrity"].get("source_hash"),
        "material_hash": result["integrity"].get("material_hash"), "duplicate_status": result["integrity"].get("duplicate_status"),
        "redaction_status": result["safety"].get("redaction_status"), "error_classification": (result.get("error") or {}).get("classification"),
        "output_reference": str(artifact_path), "downstream_handoff_reference": str(handoff),
        "duration_ms": result["execution"].get("duration_ms"),
    }
    write_json(receipt_path, receipt)
    return {"artifact_ref": str(artifact_path), "receipt_ref": str(receipt_path), "receipt": receipt}


def _finish(result: dict, *, started_clock: float, root: Path, receipt_dir: Path, handoff: Path, existing_materials: set[str]) -> dict:
    result["execution"]["completed_at"] = utc_now()
    result["execution"]["duration_ms"] = int((time.monotonic() - started_clock) * 1000)
    if result.get("status") in {"SUCCESS", "NO_CHANGE"}:
        mh = result.get("integrity", {}).get("material_hash")
        if mh and mh in existing_materials:
            result["status"] = "DUPLICATE"
            result["integrity"]["duplicate_status"] = "DUPLICATE"
        else:
            result["integrity"]["duplicate_status"] = "NEW"
    refs = _write_artifact(result, root, receipt_dir, handoff)
    result["artifact_ref"] = refs["artifact_ref"]
    result["receipt_ref"] = refs["receipt_ref"]
    return result


def ingest_file(path_value: str, *, job_id: Optional[str] = None, allowed_roots: Optional[list[Path]] = None,
                root: Path = DEFAULT_RUNTIME, receipt_dir: Path = DEFAULT_RECEIPTS, handoff: Path = DEFAULT_HANDOFF,
                max_bytes: int = MAX_FILE_BYTES, timeout_seconds: int = MAX_TIMEOUT_SECONDS,
                converter: Callable[[Path], str] = _convert_markitdown,
                tenant_context: Optional[dict] = None) -> dict:
    job_id = job_id or f"evidence-{uuid.uuid4().hex[:16]}"
    started = utc_now(); clock = time.monotonic(); evidence_id = f"ev-{uuid.uuid4().hex[:20]}"
    roots = allowed_roots or [root / "fixtures", ROOT / "data/sources"]
    path, reason = allowed_local_path(path_value, roots, max_bytes)
    source = {"source_type": "local_file", "original_reference": path_value, "adapter": "markitdown", "adapter_version": "0.1.7", "retrieved_at": started}
    if not path:
        status = "SOURCE_TOO_LARGE" if reason == "source-too-large" else "UNSUPPORTED_FORMAT" if reason == "unsupported-extension" else "BLOCKED_PATH" if reason in {"blocked-sensitive-path", "outside-approved-intake-root", "symlink-not-allowed"} else "INVALID_PATH"
        return _finish(result_error(status, job_id=job_id, adapter="markitdown", message=reason or "invalid path", started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    source.update({"display_name": path.name, "content_type": path.suffix.lower()})
    try:
        source_bytes = path.read_bytes()
        source_hash = sha256_bytes(source_bytes)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(converter, path)
            text = future.result(timeout=timeout_seconds)
        normalized = normalize_text(text)
    except FutureTimeout:
        return _finish(result_error("TIMEOUT", job_id=job_id, adapter="markitdown", message="conversion exceeded bounded timeout", started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    except RuntimeError as exc:
        return _finish(result_error("DEPENDENCY_UNAVAILABLE", job_id=job_id, adapter="markitdown", message=str(exc), started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    except Exception as exc:
        return _finish(result_error("CONVERSION_FAILED", job_id=job_id, adapter="markitdown", message=str(exc), started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    if not normalized:
        return _finish(result_error("CONTENT_EMPTY", job_id=job_id, adapter="markitdown", message="conversion produced no normalized content", started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    sensitivity, detected, reason = classify_text(normalized)
    result = {
        "schema_version": SCHEMA_VERSION, "evidence_id": evidence_id, "job_id": job_id, "status": "SUCCESS",
        "source": {**source, "provenance": {"path_scope": "approved_local_intake", "approved_root_count": len(roots)}},
        "integrity": {"source_hash": source_hash, "material_hash": material_hash(normalized), "normalization_version": NORMALIZATION_VERSION, "duplicate_status": "UNKNOWN"},
        "content": {"title": path.stem, "normalized_text_or_markdown": normalized[:MAX_OUTPUT_CHARS], "truncated": len(normalized) > MAX_OUTPUT_CHARS, "metadata": {}},
        "safety": {"redaction_status": "REVIEW_REQUIRED" if detected else "NO_REDACTION_NEEDED", "network_classification": "LOCAL_ONLY", "sensitive_data_detected": detected, "classification": sensitivity, "classification_reason": reason, "external_processing": False},
        "execution": {"job_id": job_id, "worker_type": "MAC_MINI_ISOLATED_WORKER", "requested_at": started, "started_at": started, "completed_at": started, "duration_ms": 0, "tenant_context": tenant_context or DEFAULT_TENANT_CONTEXT},
        "receipt_id": f"evidence-receipt-{uuid.uuid4().hex[:16]}",
    }
    existing = set()
    for item in root.glob("artifacts/*.json") if (root / "artifacts").exists() else []:
        try:
            old = json.loads(item.read_text(encoding="utf-8")); old_hash = old.get("integrity", {}).get("material_hash")
            if old_hash: existing.add(old_hash)
        except (OSError, ValueError):
            continue
    return _finish(result, started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=existing)


def ingest_url(url: str, *, job_id: Optional[str] = None, root: Path = DEFAULT_RUNTIME, receipt_dir: Path = DEFAULT_RECEIPTS,
               handoff: Path = DEFAULT_HANDOFF, timeout_seconds: int = MAX_TIMEOUT_SECONDS,
               crawler: Callable[[str, int], dict] = _crawl_with_crawl4ai,
               tenant_context: Optional[dict] = None) -> dict:
    job_id = job_id or f"evidence-{uuid.uuid4().hex[:16]}"; started = utc_now(); clock = time.monotonic(); evidence_id = f"ev-{uuid.uuid4().hex[:20]}"
    requested, reason = validate_public_url(url)
    source = {"source_type": "public_url", "original_reference": url, "adapter": "crawl4ai", "adapter_version": "0.9.2", "retrieved_at": started}
    if not requested:
        status = "PRIVATE_NETWORK_BLOCKED" if reason and "private" in reason else "INVALID_URL"
        return _finish(result_error(status, job_id=job_id, adapter="crawl4ai", message=reason or "invalid URL", started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    try:
        crawled = crawler(requested, timeout_seconds)
    except (TimeoutError, asyncio.TimeoutError):
        return _finish(result_error("TIMEOUT", job_id=job_id, adapter="crawl4ai", message="crawl exceeded bounded timeout", started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    except RuntimeError as exc:
        return _finish(result_error("DEPENDENCY_UNAVAILABLE", job_id=job_id, adapter="crawl4ai", message=str(exc), started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        status = "DEPENDENCY_UNAVAILABLE" if "executable doesn't exist" in lowered or "does not support" in lowered or "playwright" in lowered else "SOURCE_UNAVAILABLE"
        return _finish(result_error(status, job_id=job_id, adapter="crawl4ai", message=message, started=started, source=source), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    final_url, redirect_reason = validate_public_url(str(crawled.get("final_url") or requested))
    if not final_url:
        return _finish(result_error("REDIRECT_BLOCKED", job_id=job_id, adapter="crawl4ai", message=redirect_reason or "redirect destination blocked", started=started, source={**source, "requested_url": requested, "final_url": crawled.get("final_url")}), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    if not crawled.get("success"):
        status = "ROBOTS_BLOCKED" if "robot" in str(crawled.get("error_message") or "").lower() else "SOURCE_UNAVAILABLE"
        return _finish(result_error(status, job_id=job_id, adapter="crawl4ai", message=str(crawled.get("error_message") or "crawl unsuccessful"), started=started, source={**source, "requested_url": requested, "final_url": final_url}), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    raw_text = str(crawled.get("html") or crawled.get("markdown") or "")
    if len(raw_text.encode("utf-8")) > MAX_FILE_BYTES:
        return _finish(result_error("SOURCE_TOO_LARGE", job_id=job_id, adapter="crawl4ai", message="web response exceeded bounded source size", started=started, source={**source, "requested_url": requested, "final_url": final_url}), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    normalized = normalize_text(str(crawled.get("markdown") or ""))
    if len(normalized) > MAX_OUTPUT_CHARS:
        normalized = normalized[:MAX_OUTPUT_CHARS]
    if not normalized:
        return _finish(result_error("CONTENT_EMPTY", job_id=job_id, adapter="crawl4ai", message="crawl produced no markdown", started=started, source={**source, "requested_url": requested, "final_url": final_url}), started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=set())
    sensitivity, detected, reason = classify_text(normalized)
    raw = raw_text.encode("utf-8") or normalized.encode("utf-8")
    result = {
        "schema_version": SCHEMA_VERSION, "evidence_id": evidence_id, "job_id": job_id, "status": "SUCCESS",
        "source": {**source, "requested_url": requested, "final_url": final_url, "content_type": "text/html", "http_status": crawled.get("status_code"), "provenance": {"crawl_depth": 0, "max_pages": 1, "public_only": True}},
        "integrity": {"source_hash": sha256_bytes(raw), "material_hash": material_hash(normalized), "normalization_version": NORMALIZATION_VERSION, "duplicate_status": "UNKNOWN"},
        "content": {"title": crawled.get("title") or final_url, "normalized_text_or_markdown": normalized, "truncated": False, "metadata": {"status_code": crawled.get("status_code")}},
        "safety": {"redaction_status": "REVIEW_REQUIRED" if detected else "NO_REDACTION_NEEDED", "network_classification": "PUBLIC_WEB_ONLY", "sensitive_data_detected": detected, "classification": sensitivity, "classification_reason": reason, "external_processing": False},
        "execution": {"job_id": job_id, "worker_type": "MAC_MINI_ISOLATED_WORKER", "requested_at": started, "started_at": started, "completed_at": started, "duration_ms": 0, "tenant_context": tenant_context or DEFAULT_TENANT_CONTEXT},
        "receipt_id": f"evidence-receipt-{uuid.uuid4().hex[:16]}",
    }
    existing = set()
    for item in root.glob("artifacts/*.json") if (root / "artifacts").exists() else []:
        try:
            old = json.loads(item.read_text(encoding="utf-8")); old_hash = old.get("integrity", {}).get("material_hash")
            if old_hash: existing.add(old_hash)
        except (OSError, ValueError):
            continue
    return _finish(result, started_clock=clock, root=root, receipt_dir=receipt_dir, handoff=handoff, existing_materials=existing)


def write_heartbeat(result: dict, *, path: Path = DEFAULT_HEARTBEAT) -> None:
    write_json(path, {"capability": "evidence_ingestion", "status": "HEALTHY" if result.get("status") in {"SUCCESS", "NO_CHANGE", "DUPLICATE"} else "DEGRADED", "last_run": result.get("execution", {}).get("completed_at"), "last_result": result.get("status"), "last_adapter": result.get("adapter") or result.get("source", {}).get("adapter"), "receipt_id": result.get("receipt_id"), "optional": True, "core_health_dependency": False, "external_action_performed": False, "updated_at": utc_now()})


def accept_remote_evidence_result(remote_result: dict, *, job: dict, root: Path = DEFAULT_RUNTIME,
                                  receipt_dir: Path = DEFAULT_RECEIPTS, handoff: Path = DEFAULT_HANDOFF) -> dict:
    """Validate and persist a worker result into Nexus's canonical evidence path.

    Remote artifacts are transport outputs, not canonical truth. This adapter
    performs the final envelope/tenant/job checks and writes the accepted
    evidence through the same artifact, receipt, and intake handoff primitives
    used by local ingestion.
    """
    if not isinstance(remote_result, dict) or remote_result.get("schema_version") != "nexus.remote-result.v1":
        raise ValueError("unsupported-remote-result-schema")
    if remote_result.get("job_id") != job.get("job_id"):
        raise ValueError("remote-result-job-mismatch")
    if remote_result.get("capability") != job.get("capability") or job.get("adapter") != "crawl4ai":
        raise ValueError("remote-result-capability-mismatch")
    if remote_result.get("tenant_context") != job.get("tenant_context"):
        raise ValueError("remote-result-tenant-mismatch")
    evidence = remote_result.get("evidence_result")
    if not isinstance(evidence, dict) or evidence.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("missing-canonical-evidence-result")
    if evidence.get("job_id") != job.get("job_id"):
        raise ValueError("evidence-job-mismatch")
    if evidence.get("status") not in {"SUCCESS", "DUPLICATE", "NO_CHANGE"}:
        raise ValueError("remote-evidence-not-successful")
    integrity = evidence.get("integrity") or {}
    if not integrity.get("source_hash") or not integrity.get("material_hash"):
        raise ValueError("remote-evidence-missing-hashes")

    accepted = json.loads(json.dumps(evidence))
    accepted["execution"] = dict(accepted.get("execution") or {})
    accepted["execution"]["worker_type"] = "REMOTE_CPU_WORKER"
    accepted["execution"]["remote_provider"] = remote_result.get("provider")
    accepted["execution"]["worker_id"] = remote_result.get("worker_id")
    accepted["execution"]["requested_at"] = accepted["execution"].get("requested_at") or remote_result.get("started_at") or utc_now()
    accepted["execution"]["started_at"] = accepted["execution"].get("started_at") or remote_result.get("started_at") or accepted["execution"]["requested_at"]
    accepted["execution"]["completed_at"] = accepted["execution"].get("completed_at") or utc_now()
    accepted["remote_receipt_ref"] = remote_result.get("receipt_ref")

    existing = set()
    artifact_dir = root / "artifacts"
    if artifact_dir.exists():
        for item in artifact_dir.glob("*.json"):
            try:
                old = json.loads(item.read_text(encoding="utf-8"))
                old_hash = old.get("integrity", {}).get("material_hash")
                if old_hash:
                    existing.add(old_hash)
            except (OSError, ValueError):
                continue
    if integrity["material_hash"] in existing:
        accepted["status"] = "DUPLICATE"
        accepted["integrity"]["duplicate_status"] = "DUPLICATE"
    accepted["receipt_id"] = f"evidence-receipt-{uuid.uuid4().hex[:16]}"
    refs = _write_artifact(accepted, root, receipt_dir, handoff)
    accepted.update(refs)
    write_heartbeat(accepted)
    return accepted


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run one bounded Nexus evidence-ingestion job")
    group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--file"); group.add_argument("--url")
    parser.add_argument("--job-id"); parser.add_argument("--root", type=Path, default=Path(os.environ.get("NEXUS_EVIDENCE_RUNTIME", DEFAULT_RUNTIME)))
    parser.add_argument("--allowed-root", action="append", type=Path); parser.add_argument("--timeout", type=int, default=MAX_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    root = args.root; receipt_dir = ROOT / "reports/runtime/evidence_ingestion_receipts" if root.is_relative_to(ROOT) else root / "receipts"; handoff = root / "intake_events.jsonl"
    result = ingest_file(args.file, job_id=args.job_id, allowed_roots=args.allowed_root or [root / "fixtures", ROOT / "data/sources"], root=root, receipt_dir=receipt_dir, handoff=handoff, timeout_seconds=min(max(args.timeout, 1), MAX_TIMEOUT_SECONDS)) if args.file else ingest_url(args.url, job_id=args.job_id, root=root, receipt_dir=receipt_dir, handoff=handoff, timeout_seconds=min(max(args.timeout, 1), MAX_TIMEOUT_SECONDS))
    write_heartbeat(result)
    print(json.dumps({k: result.get(k) for k in ("job_id", "evidence_id", "status", "receipt_id", "artifact_ref", "receipt_ref", "integrity", "source", "error") if result.get(k) is not None}, sort_keys=True))
    return 0 if result.get("status") in {"SUCCESS", "DUPLICATE", "NO_CHANGE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
