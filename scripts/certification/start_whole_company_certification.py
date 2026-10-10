#!/usr/bin/env python3
"""Enqueue the single bounded, provider-free whole-company certification run."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.durable_jobs import default_store  # noqa: E402

CAMPAIGN_ID = "NEXUS-WHOLE-COMPANY-20261009-GOCLEAR-READINESS"
CORRELATION_ID = "corr-nexus-company-cert-20261009-goclear"
ARTIFACT_DIR = ROOT / "reports/certification/whole_company/artifacts"


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "campaign_id": CAMPAIGN_ID,
        "source_summary_ref": "reports/runtime/research_artifacts/web/cert-sba-1.summary.json",
        "source_provenance_ref": "reports/runtime/research_artifacts/web/cert-sba-1.provenance.json",
    }
    payload_path = ARTIFACT_DIR / "payload_research.json"
    payload_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    store = default_store()
    governance = {"campaign_id": CAMPAIGN_ID, "providers_allowed": [], "spend_allowed": False,
                  "external_actions_allowed": False, "resource_class": "LIGHTWEIGHT_INTERNAL",
                  "test_campaign": True}
    job = store.enqueue(
        "RESEARCH", "CERTIFICATION_RESEARCH_SYNTHESIS", payload_ref=str(payload_path.relative_to(ROOT)),
        correlation_id=CORRELATION_ID, idempotency_key=f"whole-company-cert:{CAMPAIGN_ID}:research",
        max_attempts=1,
        budget_envelope={"max_requests": 12, "max_response_bytes": 100_000, "max_tokens": 0,
                         "max_gpu_seconds": 0, "max_runtime_seconds": 120,
                         "max_resource_creations": 0, "max_estimated_cost": 0.0, "max_retries": 1},
        governance_context=governance,
    )
    print(json.dumps({"campaign_id": CAMPAIGN_ID, "correlation_id": job.correlation_id,
                      "job_id": job.job_id, "state": job.state, "payload_ref": job.payload_ref,
                      "provider_calls_allowed": False, "spend_allowed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
