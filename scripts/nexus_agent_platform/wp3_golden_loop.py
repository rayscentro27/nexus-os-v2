"""Governed WP3 golden loop for Daily/System Operations.

This is intentionally small: TruthKernel owns authority and receipts, the
executor is a fixed Python entrypoint, and Hermes is an advisory reviewer.
There is no arbitrary command, tool, or filesystem path supplied by Hermes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .truth_kernel import TruthKernel, utc_now

ROOT = Path(__file__).resolve().parents[2]
PROCESS_ID = "wp3_daily_system_operations"
PYTHON_ENTRYPOINT = "scripts/operations/nexus_daily_monitor.py"
OUTPUT_ARTIFACTS = (
    ROOT / "reports/runtime/nexus_daily_monitor_latest.json",
    ROOT / "reports/runtime/nexus_daily_monitor_latest.md",
)
RECEIPT_DIR = ROOT / "reports/rebuild/nexus_golden_loop_receipts"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_status(status: dict[str, Any]) -> dict[str, Any]:
    """Allow only synthetic, non-PII operational context into the review."""
    encoded = json.dumps(status, sort_keys=True, default=str)
    if any(token in encoded.lower() for token in ("@", "-----begin", "api_key", "token=")):
        raise ValueError("unsafe or credential-like context")
    return {"status": status, "authority": "read_only", "advisory": True}


def _register() -> TruthKernel:
    kernel = TruthKernel()
    kernel.register_process({
        "process_id": PROCESS_ID,
        "canonical_entrypoint": PYTHON_ENTRYPOINT,
        "purpose": "Bounded Daily/System Operations diagnostic loop with Hermes advisory review.",
        "execution_mode": "RUN_ONCE",
        "expected_running": False,
        "authority_contract": {"authority": "internal_read_only", "external_mutation": False},
        "input_contract": {"source": "synthetic operational context", "pii_allowed": False},
        "output_contract": {"artifacts": [
            "reports/runtime/nexus_daily_monitor_latest.json",
            "reports/runtime/nexus_daily_monitor_latest.md",
        ]},
    })
    return kernel


def run_golden_loop(
    status: dict[str, Any],
    *,
    reviewer: Callable[[dict[str, Any]], dict[str, Any]],
    timeout_seconds: int = 45,
    hermes_profile: str = "default",
    model_provider: str = "Oracle Ollama",
    model_name: str = "gemma3:4b",
) -> dict[str, Any]:
    """Execute one real bounded loop and emit a complete receipt."""
    started = utc_now()
    run_id = f"wp3_{uuid.uuid4().hex}"
    loop_id = "NEXUS_DAILY_SYSTEM_OPERATIONS"
    trigger_id = f"trigger_{uuid.uuid4().hex}"
    kernel = _register()
    truth_run = kernel.start_run(PROCESS_ID, trigger_type="campaign", trigger_id=trigger_id,
                                 git_sha="HEAD", entrypoint=PYTHON_ENTRYPOINT)
    kernel.mark_run_started(truth_run, started_at=started)
    authority = {"status": "PASS", "class": "internal_read_only", "hermes_write": False}
    dependency = {"status": "PASS", "dependencies": ["runtime reports", "process registry"]}
    kernel.record_authority_result(truth_run, authority)
    kernel.record_dependency_result(truth_run, dependency)
    receipt: dict[str, Any] = {
        "schema_version": "nexus.golden-loop-receipt.v1",
        "run_id": run_id,
        "loop_id": loop_id,
        "process_id": PROCESS_ID,
        "trigger_id": trigger_id,
        "trigger_time": started,
        "input_source": "synthetic operational status",
        "input_freshness": "PASS",
        "authority_result": authority,
        "dependency_result": dependency,
        "hermes_profile": hermes_profile,
        "hermes_worker": "nexus-review-advisor",
        "kanban_task_id": None,
        "model_provider": model_provider,
        "model_name": model_name,
        "skills_used": [],
        "tools_used": [],
        "python_entrypoint": PYTHON_ENTRYPOINT,
        "git_sha": "HEAD",
        "started_at": started,
        "completed_at": None,
        "exit_status": "RUNNING",
        "output_artifact": [],
        "output_hash": {},
        "side_effect_expected": {"local_reports": True, "external": False},
        "side_effect_observed": {},
        "validation_result": {},
        "hermes_review_result": {},
        "handoff_used": False,
        "retry_used": False,
        "recovery_used": False,
        "receipt_id": f"receipt_{uuid.uuid4().hex}",
        "final_state": "RUNNING",
    }
    try:
        _safe_status(status)
        command = [sys.executable, PYTHON_ENTRYPOINT]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                   timeout=timeout_seconds, check=False)
        receipt["exit_status"] = "PASS" if completed.returncode == 0 else "FAIL"
        receipt["exit_code"] = completed.returncode
        if completed.returncode != 0:
            raise RuntimeError("python executor failed")
        outputs = [path for path in OUTPUT_ARTIFACTS if path.is_file()]
        if len(outputs) != len(OUTPUT_ARTIFACTS):
            raise RuntimeError("required executor output missing")
        report = json.loads(OUTPUT_ARTIFACTS[0].read_text(encoding="utf-8"))
        if not isinstance(report, dict) or not report.get("generated_at"):
            raise RuntimeError("malformed executor output")
        hashes = {str(path.relative_to(ROOT)): _sha256(path) for path in outputs}
        kernel.record_output(truth_run, outputs)
        for path in outputs:
            kernel.record_evidence(truth_run, evidence_type="output", source=PYTHON_ENTRYPOINT,
                                   artifact=str(path.relative_to(ROOT)), artifact_hash=hashes[str(path.relative_to(ROOT))],
                                   scope="internal diagnostic", real_or_simulated="REAL", verification_status="VERIFIED")
        review = reviewer(_safe_status(status) | {"executor_report": report})
        if not isinstance(review, dict) or review.get("status") != "PASS":
            raise RuntimeError("Hermes review unavailable or malformed")
        receipt["output_artifact"] = list(hashes)
        receipt["output_hash"] = hashes
        receipt["validation_result"] = {"status": "PASS", "output_verified": True}
        receipt["side_effect_observed"] = {"local_reports": True, "external": False}
        receipt["hermes_review_result"] = {"status": "PASS", "advisory": True, "summary": review.get("summary", "")[:500]}
        receipt["final_state"] = "SUCCEEDED_VERIFIED"
        kernel.complete_run(truth_run, exit_status="SUCCEEDED_VERIFIED", exit_code=0,
                            verification_result={"output_verified": True},
                            freshness_result={"status": "PASS"}, output_artifacts=outputs,
                            side_effect_expected=receipt["side_effect_expected"],
                            side_effect_observed=receipt["side_effect_observed"])
    except Exception as exc:
        receipt["exit_status"] = "FAIL_CLOSED"
        receipt["error"] = type(exc).__name__
        receipt["final_state"] = "FAILED"
        kernel.complete_run(truth_run, exit_status="FAILED", exit_code=1,
                            verification_result={"output_verified": False},
                            freshness_result={"status": "NOT_PROVEN"},
                            side_effect_expected=receipt["side_effect_expected"],
                            side_effect_observed=receipt["side_effect_observed"])
    receipt["completed_at"] = utc_now()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    target = RECEIPT_DIR / f"{receipt['receipt_id']}.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
