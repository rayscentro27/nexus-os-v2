"""Migration adapter for the proven Daily/System Operations loop."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from .kernel import LoopDefinition, LoopResult, run_loop

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = "scripts/operations/nexus_daily_monitor.py"
OUTPUTS = (ROOT / "reports/runtime/nexus_daily_monitor_latest.json", ROOT / "reports/runtime/nexus_daily_monitor_latest.md")

DAILY_SYSTEM_DEFINITION = LoopDefinition(
    loop_id="NEXUS_DAILY_SYSTEM_OPERATIONS",
    name="Daily / System Operations",
    purpose="Bounded internal diagnostic and advisory review loop.",
    trigger_types=("campaign", "synthetic", "on_demand"),
    default_skill="system-operations",
    allowed_skills=("system-operations", "system-recovery", "failure-recovery"),
    default_worker="NEXUS_OPERATIONS_WORKER",
    allowed_workers=("NEXUS_OPERATIONS_WORKER", "NEXUS_REVIEW_WORKER"),
    default_profile="nexusworker",
    model_policy="LOCAL_PRIVATE",
    allowed_executors=("daily_system_operations",),
    authority_class="internal_read_only",
    dependencies=("TruthKernel", "process registry"),
    side_effect_class="local_reports",
    autonomy_level="A2_AUTOMATIC_REVIEW",
)


def _executor(_: Mapping[str, Any]) -> Mapping[str, Any]:
    completed = subprocess.run([sys.executable, ENTRYPOINT], cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
    if completed.returncode != 0:
        return {"status": "FAIL", "entrypoint": ENTRYPOINT, "stderr": completed.stderr[-500:]}
    if any(not path.is_file() for path in OUTPUTS):
        return {"status": "FAIL", "entrypoint": ENTRYPOINT}
    payload = json.loads(OUTPUTS[0].read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload.get("generated_at"):
        return {"status": "FAIL", "entrypoint": ENTRYPOINT}
    digest = hashlib.sha256(OUTPUTS[0].read_bytes()).hexdigest()
    return {"status": "PASS", "entrypoint": ENTRYPOINT, "artifact": [str(p.relative_to(ROOT)) for p in OUTPUTS], "output_hash": digest, "side_effect": {"external": False, "local_reports": True}}


def run_daily_system_loop(context: Mapping[str, Any], *, reviewer=None, receipt_dir=None) -> LoopResult:
    return run_loop(DAILY_SYSTEM_DEFINITION, context, trigger="on_demand", executor=_executor, reviewer=reviewer, receipt_dir=receipt_dir)
