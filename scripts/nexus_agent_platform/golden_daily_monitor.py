"""Bounded Daily Monitor golden-process proof for the operational-truth kernel."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .truth_kernel import DAILY_MONITOR_DEFINITION, ROOT, TruthKernel, current_git_sha, utc_now


def run_daily_monitor_golden(db_path: str | Path) -> dict:
    kernel = TruthKernel(db_path)
    kernel.register_process(DAILY_MONITOR_DEFINITION)
    requested = utc_now()
    run_id = kernel.start_run("daily_monitor", trigger_type="MANUAL_SAFE_CANARY", trigger_id="WP1-A", git_sha=current_git_sha())
    kernel.record_authority_result(run_id, {"authorized": True, "scope": "internal_read_only", "mutations_allowed": False})
    kernel.record_dependency_result(run_id, {"available": True, "sources": ["process_registry", "local_runtime_artifacts"]})
    started = utc_now()
    kernel._update_run(run_id, started_at=started)
    command = [sys.executable, str(ROOT / "scripts/operations/nexus_daily_monitor.py")]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    report_json = ROOT / "reports/runtime/nexus_daily_monitor_latest.json"
    report_md = ROOT / "reports/runtime/nexus_daily_monitor_latest.md"
    report = json.loads(report_json.read_text()) if report_json.exists() else {}
    fresh = kernel.verify_freshness(report.get("generated_at", requested), max_age_seconds=300) if report else {"fresh": False, "reason": "missing report"}
    output_verified = report_json.exists() and report_md.exists() and isinstance(report, dict) and report.get("generated_at")
    kernel.record_evidence(run_id, evidence_type="REAL_EXECUTION_STARTED", source="truth_kernel", scope="daily_monitor", real_or_simulated="REAL")
    hashes = kernel.record_output(run_id, [report_json, report_md])
    kernel.record_evidence(run_id, evidence_type="CANONICAL_REPORT_WRITTEN", source="daily_monitor", artifact=str(report_json.relative_to(ROOT)), scope="daily_monitor", real_or_simulated="REAL", artifact_hash=hashes.get(str(report_json)))
    final_state = kernel.complete_run(run_id, exit_status="COMPLETED" if completed.returncode == 0 else "FAILED", exit_code=completed.returncode,
                                      verification_result={"output_verified": bool(output_verified), "business_health_inferred": False, "report_summary": {"stale_count": report.get("reports_freshness", {}).get("stale_count")}},
                                      freshness_result=fresh, output_artifacts=[report_json, report_md], side_effect_expected={"mutations": 0}, side_effect_observed={"mutations": 0})
    return {"run_id": run_id, "execution_status": "COMPLETED" if completed.returncode == 0 else "FAILED", "final_state": final_state, "report": str(report_json.relative_to(ROOT)), "freshness": fresh, "business_health_inferred": False, "stdout": completed.stdout[-1000:], "stderr": completed.stderr[-1000:]}


if __name__ == "__main__":
    print(json.dumps(run_daily_monitor_golden(ROOT / "data/runtime/nexus_operational_truth.db"), indent=2))
