"""Narrow Nexus-owned Alpha evidence acquisition bridge.

Alpha may request public evidence through this module, but never receives
provider credentials or chooses a remote capability. Persistence and result
validation remain in the certified evidence-ingestion module.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from nexus_agent_platform.evidence_ingestion import (
    DEFAULT_HANDOFF,
    DEFAULT_RECEIPTS,
    DEFAULT_RUNTIME,
    accept_remote_evidence_result,
)
from nexus_agent_platform.remote_worker import build_remote_job
from nexus_agent_platform.providers.modal_provider import provider_from_environment


def _public_url(url: str) -> str:
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("public-http-url-required")
    return parsed.geturl()


def request_research_evidence(*, url: str, job_id: str, tenant_context: dict,
                              limits: Optional[dict] = None, provider: Any = None,
                              root: Path = DEFAULT_RUNTIME,
                              receipt_dir: Path = DEFAULT_RECEIPTS,
                              handoff: Path = DEFAULT_HANDOFF) -> dict:
    """Acquire exactly one public URL through the existing Nexus capability.

    The provider is injectable for deterministic tests. Production callers do
    not select a function or provider; the factory selects the certified
    Modal transport and fixed ``evidence_ingestion.crawl4ai`` capability.
    """
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("research-job-id-required")
    if not isinstance(tenant_context, dict) or set(tenant_context) - {"scope", "tenant_id"}:
        raise ValueError("bounded-tenant-context-required")
    public_url = _public_url(url)
    bounded_limits = {"max_pages": 1, "max_depth": 0, "timeout_seconds": min(max(int((limits or {}).get("timeout_seconds", 30)), 1), 30)}
    job = build_remote_job(
        capability="evidence_ingestion", adapter="crawl4ai",
        source={"source_type": "public_url", "original_reference": public_url},
        job_id=job_id, tenant_context=tenant_context,
        policy={"public_only": True, "no_external_processing": True},
        limits=bounded_limits, correlation={"consumer": "alpha_research_intelligence"},
    )
    selected_provider = provider or provider_from_environment()
    remote_result = selected_provider.submit(job)
    if remote_result.get("status") not in {"SUCCESS", "DUPLICATE", "NO_CHANGE"}:
        return {"status": remote_result.get("status", "DEPENDENCY_UNAVAILABLE"), "job": job, "remote_result": remote_result}
    accepted = accept_remote_evidence_result(remote_result, job=job, root=root, receipt_dir=receipt_dir, handoff=handoff)
    return {
        "status": accepted.get("status"), "job": job, "remote_result": remote_result,
        "evidence": {
            "evidence_id": accepted["evidence_id"],
            "artifact_ref": accepted["artifact_ref"],
            "original_source": (accepted.get("source") or {}).get("original_reference") or public_url,
            "source_type": (accepted.get("source") or {}).get("source_type", "public_url"),
            "retrieved_at": (accepted.get("source") or {}).get("retrieved_at"),
            "source_hash": (accepted.get("integrity") or {}).get("source_hash"),
            "material_hash": (accepted.get("integrity") or {}).get("material_hash"),
            "text": (accepted.get("content") or {}).get("normalized_text_or_markdown", ""),
            "status": accepted.get("status"),
        },
    }
