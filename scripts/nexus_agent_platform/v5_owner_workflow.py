"""Department-owned V5 research orchestration through the existing NotebookLM adapter."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def handle_job(job: Any) -> dict[str, Any]:
    if not job.payload_ref:
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_PAYLOAD_REQUIRED"}
    payload_path = (ROOT / job.payload_ref).resolve()
    if not payload_path.is_relative_to(ROOT.resolve()) or not payload_path.is_file():
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_PAYLOAD_INVALID"}
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if payload.get("campaign_id") != "NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9":
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_CAMPAIGN_MISMATCH"}
    if payload.get("owner_objective_id") != "ownerobj_nexus_full_owner_real_world_v5_6fb82fd9":
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_OBJECTIVE_MISMATCH"}
    # The execution belongs to Research. NotebookLM performs source-scoped
    # review/synthesis through the already governed provider adapter; this
    # module only validates the assignment and persists its returned evidence.
    from nexus_agent_platform.notebooklm_discovery import execute_import_and_synthesize
    result = execute_import_and_synthesize(job, payload)
    if result.get("status") != "COMPLETED":
        return {**result, "department": "RESEARCH", "workflow": "NOTEBOOKLM_SOURCE_REVIEW"}
    artifact_ref = result.get("artifact_ref")
    if not artifact_ref:
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_EVIDENCE_REF_MISSING"}
    artifact_path = (ROOT / artifact_ref).resolve()
    if not artifact_path.is_relative_to(ROOT.resolve()) or not artifact_path.is_file():
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_EVIDENCE_NOT_PERSISTED"}
    evidence = json.loads(artifact_path.read_text(encoding="utf-8"))
    answer = evidence.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return {"status": "BLOCKED", "reason": "V5_RESEARCH_SOURCE_SCOPED_ANSWER_MISSING",
                "artifact_ref": artifact_ref}
    return {**result, "department": "RESEARCH", "workflow": "NOTEBOOKLM_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
            "campaign_id": payload["campaign_id"], "owner_objective_id": payload["owner_objective_id"],
            "evidence_class": "NOTEBOOKLM_SOURCE_GROUNDED_RESEARCH", "opportunity_inventory_ref": artifact_ref}
