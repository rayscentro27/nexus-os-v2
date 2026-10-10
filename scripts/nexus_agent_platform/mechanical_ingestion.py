"""Mechanical public-research ingestion into the canonical Supabase source ledger.

Acquisition and deterministic normalization own this path.  AI, Alpha,
classification, relevance, scoring, and department opinions are downstream
metadata and cannot prevent this write.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence

try:
    from social import _supabase as supabase
except Exception:  # pragma: no cover - exercised only in unconfigured installs
    supabase = None


INGESTION_STATES = {"QUEUED", "PROCESSING", "INGESTED", "FAILED_RETRYABLE", "FAILED_FINAL"}
VERSION = "mechanical-public-ingestion-v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def _inner(result: dict[str, Any]) -> dict[str, Any]:
    value = result.get("result")
    return value if isinstance(value, dict) else result


def _read_reference(reference: Any, root: Path) -> str:
    if not reference:
        return ""
    path = Path(str(reference))
    if not path.is_absolute():
        path = root / path
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _artifact_reference(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _content_text(result: dict[str, Any], root: Path, source_url: str = "") -> str:
    inner = _inner(result)
    candidates = [inner.get("transcript_path"), inner.get("normalized_content_path"),
                  inner.get("raw_content_path"), inner.get("content_reference")]
    for candidate in candidates:
        text = _read_reference(candidate, root)
        if text.strip():
            return text
    # Duplicate processor results intentionally omit artifact paths.  Recover
    # the already-acquired transcript by concrete YouTube video identity so an
    # exact local processor duplicate can still be promoted to the canonical
    # Supabase source record.
    url = str(inner.get("url") or source_url or "")
    video_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("v", [""])[0]
    if video_id:
        text = _read_reference(root / "reports" / "runtime" / "youtube_artifacts" / f"{video_id}.transcript.txt", root)
        if text.strip():
            return text
    # The web/document processor may return a summary even when the artifact
    # path was not surfaced by an adapter.  This is still real acquired text,
    # but it is not enough for a YouTube transcript proof.
    return str(inner.get("executive_summary") or inner.get("summary") or "")


def _claims(result: dict[str, Any]) -> list[Any]:
    inner = _inner(result)
    value = inner.get("claims") or inner.get("key_findings") or inner.get("findings") or []
    return value if isinstance(value, list) else [value]


def _evidence(result: dict[str, Any]) -> list[Any]:
    inner = _inner(result)
    value = inner.get("evidence") or inner.get("provenance") or inner.get("evidence_references") or []
    return value if isinstance(value, list) else [value]


def build_canonical_package(*, item: dict[str, Any], result: dict[str, Any],
                            queue_sequence: int | None = None, root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2]
    inner = _inner(result)
    source_id = str(item.get("source_id") or inner.get("video_id") or item.get("source_url") or "")
    source_type = str(item.get("source_type") or "PUBLIC_WEB").upper()
    source_url = str(item.get("source_url") or inner.get("url") or "")
    content = _content_text(result, root, source_url)
    content_hash = str(inner.get("content_hash") or inner.get("normalized_content_hash") or _digest(content))
    retrieved = str(inner.get("retrieved_at") or inner.get("last_processed_at") or _now())
    processed = str(inner.get("processed_at") or inner.get("last_processed_at") or _now())
    transcript_ref = inner.get("transcript_path")
    if not transcript_ref and source_type.startswith("YOUTUBE"):
        video_id = urllib.parse.parse_qs(urllib.parse.urlparse(source_url).query).get("v", [""])[0]
        if video_id:
            candidate = root / "reports" / "runtime" / "youtube_artifacts" / f"{video_id}.transcript.txt"
            if candidate.exists():
                transcript_ref = _artifact_reference(candidate, root)
    normalized_ref = inner.get("normalized_content_path") or inner.get("transcript_path")
    raw_ref = inner.get("raw_content_path") or inner.get("artifact_root")
    package = {
        "schema_version": "nexus.canonical-public-research.v1",
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "source_name": item.get("title") or inner.get("title") or source_id,
        "title": inner.get("title") or item.get("title") or source_id,
        "author_or_channel": item.get("author") or item.get("channel_name") or inner.get("channel") or "",
        "published_at": item.get("published_at") or inner.get("published_at"),
        "retrieved_at": retrieved,
        "processed_at": processed,
        "raw_content_reference": raw_ref,
        "normalized_content_reference": normalized_ref,
        "transcript_reference": transcript_ref,
        "content_hash": content_hash,
        "content_text_or_transcript": content,
        "summary": inner.get("executive_summary") or inner.get("summary") or "",
        "claims": _claims(result),
        "evidence": _evidence(result),
        "unknowns": inner.get("unknowns") or inner.get("unanswered_questions") or inner.get("follow_up_questions") or [],
        "processor_name": result.get("processor") or inner.get("processor") or "unknown_processor",
        "processor_version": inner.get("processing_version") or inner.get("processor_version") or VERSION,
        "research_job_id": item.get("work_id"),
        "queue_sequence": queue_sequence,
        "processing_status": "PROCESSING",
        "metadata": {
            "research_mode": item.get("research_mode"),
            "lane_id": item.get("lane_id"),
            "discovery_method": item.get("discovery_method") or inner.get("discovery_method"),
            "source_processing_status": inner.get("processing_status"),
            "duplicate_status": inner.get("duplicate_status"),
            "optional_ai_metadata": {},
        },
    }
    package["package_hash"] = _digest(json.dumps(package, sort_keys=True, default=str))
    return package


def _write_receipt(package: dict[str, Any], **values: Any) -> None:
    persistence.append_record("research_stage_receipts", {
        "schema_version": "nexus.research-stage-receipt.v2",
        "receipt_id": persistence.new_id("stage"),
        "created_at": _now(),
        "source_id": package.get("source_id"),
        "source_type": package.get("source_type"),
        "source_url": package.get("source_url"),
        "queue_sequence": package.get("queue_sequence"),
        "research_job_id": package.get("research_job_id"),
        **values,
    })


def ingest_public_source(*, item: dict[str, Any], result: dict[str, Any],
                         queue_sequence: int | None = None, root: Path | None = None) -> dict[str, Any]:
    """Write and read back one acquired public source package.

    A YouTube item requires actual transcript text.  Other public source types
    require normalized acquired content.  No business judgment is consulted.
    """
    package = build_canonical_package(item=item, result=result, queue_sequence=queue_sequence, root=root)
    source_type = package["source_type"]
    content = package["content_text_or_transcript"]
    if not package["source_id"] or not package["source_url"]:
        package["processing_status"] = "FAILED_RETRYABLE"
        package["error"] = "missing source identity"
        return package
    if not content.strip():
        package["processing_status"] = "FAILED_RETRYABLE"
        package["error"] = "processor returned no acquired content"
        _write_receipt(package, stage="SUPABASE_WRITE_NOT_ATTEMPTED", ingestion_status=package["processing_status"], error=package["error"])
        return package
    if source_type.startswith("YOUTUBE") and not package.get("transcript_reference"):
        package["processing_status"] = "FAILED_RETRYABLE"
        package["error"] = "YouTube transcript processing was not captured"
        _write_receipt(package, stage="SUPABASE_WRITE_NOT_ATTEMPTED", ingestion_status=package["processing_status"], error=package["error"])
        return package
    if supabase is None or not supabase.configured():
        package["processing_status"] = "FAILED_RETRYABLE"
        package["error"] = "supabase_not_configured"
        _write_receipt(package, stage="SUPABASE_WRITE_NOT_ATTEMPTED", ingestion_status=package["processing_status"], error=package["error"])
        return package

    package["processing_status"] = "PROCESSING"
    _write_receipt(package, stage="SUPABASE_WRITE_STARTED", ingestion_status="PROCESSING",
                   metadata_captured=True, content_captured=True,
                   transcript_captured=bool(package.get("transcript_reference")),
                   normalized_content_created=True, content_hash=package["content_hash"],
                   supabase_write_attempted=True)
    # Concrete identity is source_id + content_hash.  A new video, release, or
    # changed page content therefore creates a new canonical source row.
    query = f"url=eq.{supabase.q(package['source_url'])}&limit=100"
    status, rows = supabase.rest("GET", f"research_sources?{query}")
    if status == 200:
        for row in rows or []:
            prior = row.get("metadata") or {}
            if prior.get("source_id") == package["source_id"] and prior.get("content_hash") == package["content_hash"]:
                package["processing_status"] = "INGESTED_EXISTING"
                package["supabase_source_id"] = row.get("id")
                package["supabase_write_attempted"] = False
                package["supabase_write_confirmed"] = True
                package["readback_confirmed"] = True
                _write_receipt(package, stage="SUPABASE_WRITE_CONFIRMED", ingestion_status=package["processing_status"],
                               supabase_source_id=row.get("id"), supabase_write_attempted=False,
                               supabase_write_confirmed=True, readback_confirmed=True)
                return package
    row = {
        "source_type": source_type,
        "title": package["title"],
        "url": package["source_url"],
        "author": package.get("author_or_channel"),
        "published_at": package.get("published_at"),
        "accessed_at": package["retrieved_at"],
        "snippet": package["summary"][:4000],
        "why_it_matters": "Mechanical public research ingestion; downstream interpretation is separate.",
        "metadata": package,
    }
    write_status, written = supabase.rest("POST", "research_sources", body=[row], prefer="return=representation")
    if write_status not in {200, 201} or not written:
        package["processing_status"] = "FAILED_RETRYABLE"
        package["error"] = written
        _write_receipt(package, stage="SUPABASE_WRITE_FAILED", ingestion_status=package["processing_status"],
                       supabase_write_attempted=True, supabase_write_confirmed=False, error=written)
        return package
    source_row = written[0]
    source_id = source_row.get("id")
    read_status, readback = supabase.rest("GET", f"research_sources?id=eq.{supabase.q(str(source_id))}&limit=1")
    verified = read_status == 200 and bool(readback) and (readback[0].get("metadata") or {}).get("package_hash") == package["package_hash"]
    if verified:
        stored_metadata = dict(readback[0].get("metadata") or {})
        stored_metadata["processing_status"] = "INGESTED"
        status_write, _ = supabase.rest("PATCH", f"research_sources?id=eq.{supabase.q(str(source_id))}", body={"metadata": stored_metadata}, prefer="return=minimal")
        if status_write not in {200, 204}:
            verified = False
        else:
            read_status, readback = supabase.rest("GET", f"research_sources?id=eq.{supabase.q(str(source_id))}&limit=1")
            verified = (read_status == 200 and bool(readback)
                        and (readback[0].get("metadata") or {}).get("package_hash") == package["package_hash"]
                        and (readback[0].get("metadata") or {}).get("processing_status") == "INGESTED")
    package["supabase_source_id"] = source_id
    package["supabase_write_attempted"] = True
    package["supabase_write_confirmed"] = verified
    package["readback_confirmed"] = verified
    package["processing_status"] = "INGESTED" if verified else "FAILED_RETRYABLE"
    if not verified:
        package["error"] = "Supabase source row readback did not match package hash"
    _write_receipt(package, stage="SUPABASE_WRITE_CONFIRMED" if verified else "SUPABASE_READBACK_FAILED",
                   ingestion_status=package["processing_status"], supabase_source_id=source_id,
                   supabase_write_attempted=True, supabase_write_confirmed=verified,
                   readback_confirmed=verified, content_hash=package["content_hash"], error=package.get("error"))
    return package
