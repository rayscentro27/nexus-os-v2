"""Bounded real runtime handlers for the canonical Workflow Fabric.

This first activation binds only Nova objective intake and deterministic Research
planning. The controller remains the sole owner of workflow state transitions.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
RESOLVER = ROOT / "scripts/nexus_oracle_connection.py"


def _receipt_id(kind: str, packet: dict[str, Any], result: dict[str, Any]) -> str:
    encoded = json.dumps([kind, packet.get("workflow_id"), packet.get("current_step"), result],
                         sort_keys=True, default=str, separators=(",", ":")).encode()
    return kind.lower() + "-" + hashlib.sha256(encoded).hexdigest()[:20]


def nova_objective_intake(packet: dict[str, Any], *, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Execute the exact GoClear intake request on the authorized Oracle Hermes path."""
    proof = packet.get("authorization") if isinstance(packet.get("authorization"), dict) else {}
    if any(proof.get(key) != value for key, value in {
        "authorization": "AUTHORIZED", "agent_id": "NOVA", "bot_id": "NOVA_COORDINATOR",
        "skill_id": "nova.workflow_coordination", "environment_id": "ORACLE_NOVA_HERMES",
        "model_profile": "ROUTING_LIGHT", "model_profile_status": "AVAILABLE"}.items()):
        return {"status": "VALIDATION_FAILED", "error_code": "WORKFLOW_AUTHORIZATION_PROOF_MISSING"}
    result = runner([sys.executable, str(RESOLVER), "--nova-goclear-intake"],
        capture_output=True, text=True, timeout=150, check=False, cwd=ROOT)
    output = str(result.stdout or "")
    marker = "NOVA_GOCLEAR_INTAKE_RESULT="
    text = output.rsplit(marker, 1)[-1].strip() if marker in output else ""
    # Resolver diagnostics and request framing are not worker output.
    text = "\n".join(line for line in text.splitlines()
        if line and not line.startswith(("ORACLE_", "SAFE_COMMAND=", "CONNECTION_USED=", "HISTORICAL_CONNECTORS_")))[:4000]
    if result.returncode or "NOVA_GOCLEAR_INTAKE=PASS" not in output or not text:
        return {"status": "RETRY", "error_code": "NOVA_ORACLE_INTAKE_FAILED",
                "partial_output": text or None, "authorization": proof["authorization"]}
    value = {"status": "COMPLETE", "summary": text,
        "environment_id": "ORACLE_NOVA_HERMES", "model_profile": "ROUTING_LIGHT",
        "model_profile_status": proof["model_profile_status"],
        "authorization": proof["authorization"], "model_route": proof["model_profile_status"],
        "external_side_effects": False}
    value["generation_receipt_id"] = _receipt_id("nova-intake", packet, value)
    return value


def research_plan(packet: dict[str, Any]) -> dict[str, Any]:
    """Use the existing Research contract and live local Research health to plan."""
    from nexus_agent_platform.workflow_runtime_health import probe_mac_research
    observation = probe_mac_research(timeout_seconds=2)
    if observation.get("status") != "HEALTHY":
        return {"status": "WAITING_DEPENDENCY", "error_code": "MAC_RESEARCH_RUNTIME_UNHEALTHY",
                "partial_output": {"health": observation}}
    proof = packet.get("authorization") if isinstance(packet.get("authorization"), dict) else {}
    if any(proof.get(key) != value for key, value in {
        "authorization": "AUTHORIZED", "agent_id": "RESEARCH_LEAD", "bot_id": "RESEARCH_PLANNER",
        "skill_id": "research.plan", "environment_id": "MAC_MINI",
        "model_profile": "ROUTING_LIGHT", "model_profile_status": "AVAILABLE"}.items()):
        return {"status": "VALIDATION_FAILED", "error_code": "WORKFLOW_AUTHORIZATION_PROOF_MISSING"}
    from nexus_agent_platform.alpha_research import build_research_job, build_research_plan
    objective = str(packet.get("objective") or "")
    job = build_research_job(objective=objective, research_type="FUNDING_PROGRAM_RESEARCH",
        requested_by="workflow_fabric", limits={"max_sources": 5, "max_model_calls": 0,
        "max_evidence_jobs": 0, "max_runtime_seconds": 120, "max_output_chars": 4000})
    plan = build_research_plan(job)
    from nexus_agent_platform.research_read_status import read_research_status
    status = read_research_status()
    result = {"status": "COMPLETE", "plan": plan, "research_runtime_status": status.get("status"),
        "research_runtime_provenance": status.get("provenance"), "authorization": proof["authorization"],
        "environment_id": "MAC_MINI", "model_profile": "ROUTING_LIGHT",
        "model_profile_status": proof["model_profile_status"], "external_research_performed": False,
        "external_side_effects": False}
    result["generation_receipt_id"] = _receipt_id("research-plan", packet, result)
    return result


def minimum_runtime_handlers() -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    """Handlers genuinely implemented and bound today; absent handlers stay unavailable."""
    return {"NOVA_COORDINATOR": nova_objective_intake,
            "RESEARCH_PLANNER": research_plan}
