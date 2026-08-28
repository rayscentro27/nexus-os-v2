"""Narrow governed bridge from the real VOICE-001 approval to engineering.

This is deliberately not a general repair engine.  It accepts one existing
manual-certification approval, one repair ID, and one fixed coding contract.
It creates a canonical governed work order and invokes the existing Builder
Codex adapter in an isolated worktree.  Production deployment and the human
Voice canary remain separate gates.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from nexus_agent_platform.governed import approvals, persistence, work_orders

ROOT = Path(__file__).resolve().parents[3]
MANUAL_CERT_REPORT = ROOT / "reports/runtime/manual_e2e_latest.json"
STATE_PATH = ROOT / "reports/runtime/voice_repair_latest.json"
REPAIR_ID = "VOICE-001"
ACTION_ID = "engineering.repair.voice"
IDEMPOTENCY_PREFIX = "manual-repair:VOICE-001:"
SAFE_ENV_KEYS = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV", "TERM", "NO_COLOR"}


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, path)


def _manual_approval(run_id: str) -> Optional[Dict[str, Any]]:
    report = _load(MANUAL_CERT_REPORT, {})
    if report.get("run_id") != run_id:
        return None
    key = f"{REPAIR_ID}:{run_id}"
    approval = (report.get("repair_approvals") or {}).get(key)
    if not isinstance(approval, dict) or approval.get("status") != "PASS":
        return None
    if approval.get("authority_scope") != [REPAIR_ID]:
        return None
    return approval


def _existing_order(run_id: str) -> Optional[Dict[str, Any]]:
    key = f"{IDEMPOTENCY_PREFIX}{run_id}"
    return next((row for row in work_orders.list_work_orders(limit=1000) if row.get("idempotency_key") == key), None)


def _state(run_id: str, **changes: Any) -> Dict[str, Any]:
    current = _load(STATE_PATH, {})
    value = {**(current if isinstance(current, dict) else {}), "run_id": run_id, "repair_id": REPAIR_ID, **changes, "updated_at": persistence._now()}
    _write(STATE_PATH, value)
    return value


def _process_alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def _launch_existing_order(order: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    current = _load(STATE_PATH, {})
    if current.get("state") == "ENGINEERING" and _process_alive(current.get("worker_pid")):
        return {"status": "already_running", "work_order_id": order["work_order_id"], "state": "ENGINEERING", "worker_pid": current.get("worker_pid")}
    if current.get("state") in {"PATCH_READY", "TESTING", "PASS", "BLOCKED"}:
        return {"status": "already_started", "work_order_id": order["work_order_id"], "state": current.get("state")}
    result = order.get("result") or {}
    capacity_failure = (str(order.get("error") or "") in {"UNAVAILABLE", "WORKER_CAPACITY", "NO_CERTIFIED_WORKER_AVAILABLE"}
                        or (result.get("state") in {"FAIL", "WAITING_WORKER"} and result.get("failure") in {"UNAVAILABLE", "WORKER_CAPACITY", "NO_CERTIFIED_WORKER_AVAILABLE"})
                        or current.get("failure") in {"UNAVAILABLE", "WORKER_CAPACITY", "NO_CERTIFIED_WORKER_AVAILABLE"})
    if ((order.get("status") == "failed" and str(order.get("error") or "") == "MissionContract.__init__() got an unexpected keyword argument 'mission_id'")
            or (order.get("status") in {"completed", "blocked"} and capacity_failure)
            or (current.get("state") in {"FAIL", "WORKER_SELECTION", "WAITING_WORKER"} and capacity_failure)):
        raw = persistence.get_record("work_orders", order["work_order_id"], key="work_order_id")
        if raw:
            order = {**raw, "status": "queued", "started_at": None, "completed_at": None, "error": None, "result": None, "retry_reason": "worker-capacity retry; preserve prior failure in audit ledger"}
            persistence.append_record("work_orders", order)
            approval = approvals.get_approval(raw.get("approval_id")) if raw.get("approval_id") else None
            if approval and approval.get("status") == "consumed":
                persistence.append_record("approvals", {**approval, "status": "approved", "resolved_at": persistence._now(), "resolved_by": "capacity_retry_reconciliation", "resolution": "prior worker-capacity outcome did not execute repair"})
    if order.get("status") != "queued":
        return {"status": "blocked", "work_order_id": order["work_order_id"], "state": order.get("status"), "reason": "work_order_not_queued"}
    child_env = {key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS}
    child_env["PYTHONPATH"] = str(ROOT / "scripts")
    if os.environ.get("NEXUS_GOVERNED_DATA_DIR"):
        child_env["NEXUS_GOVERNED_DATA_DIR"] = os.environ["NEXUS_GOVERNED_DATA_DIR"]
    process = subprocess.Popen([sys.executable, "-m", "nexus_agent_platform.governed.voice_repair", "execute", order["work_order_id"]], cwd=ROOT, env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    _state(run_id, state="QUEUED", work_order_id=order["work_order_id"], approval_reference=f"manual:{REPAIR_ID}:{run_id}", authority_scope=[REPAIR_ID], executor=ACTION_ID, dispatcher="manual-approved-repair-dispatch", dispatcher_requested_at=persistence._now(), worker_pid=process.pid, automatic_resume=True, retry_class="APPROVED_WORK_WAITING_CAPACITY", mission_id="manual-repair-voice-001")
    return {"status": "queued", "work_order_id": order["work_order_id"], "state": "QUEUED", "worker_pid": process.pid}


def _canonical_approval(run_id: str, manual: Dict[str, Any]) -> Dict[str, Any]:
    """Bridge the already-recorded human approval into the governed ledger."""
    existing = next((row for row in persistence.read_records("approvals")
                     if row.get("source_approval_reference") == f"manual:{REPAIR_ID}:{run_id}"), None)
    if existing:
        return existing
    record = approvals.create_approval_request(
        action_id=ACTION_ID,
        requested_by="manual_certification",
        requested_for="ray",
        input_summary={"repair_id": REPAIR_ID, "run_id": run_id},
        action_summary="VOICE-001 bounded engineering repair",
        evidence_refs=[f"manual-cert:{run_id}", f"telegram-update:{manual.get('update_id')}"],
        ttl_seconds=24 * 60 * 60,
    )
    approved = {**record, "status": "approved", "resolved_at": persistence._now(),
                "resolved_by": "ray", "resolution": "existing_manual_certification_approval",
                "source_approval_reference": f"manual:{REPAIR_ID}:{run_id}"}
    persistence.append_record("approvals", approved)
    return approved


def start_voice_repair(run_id: str, *, chat_id: Optional[int] = None) -> Dict[str, Any]:
    """Queue exactly one VOICE-001 repair and start its fixed worker."""
    if run_id != "MANUAL-E2E-20260827-2992":
        return {"status": "blocked", "reason": "wrong_manual_certification_run"}
    manual = _manual_approval(run_id)
    if manual is None:
        return {"status": "waiting_approval", "repair_id": REPAIR_ID, "run_id": run_id}
    existing = _existing_order(run_id)
    if existing and existing.get("status") in {"queued", "running", "completed", "failed", "blocked"}:
        resumed = _launch_existing_order(existing, run_id)
        return {**resumed, "repair_id": REPAIR_ID}
    canonical = _canonical_approval(run_id, manual)
    order = work_orders.create_work_order(
        approval_id=canonical["id"], action_id=ACTION_ID,
        requested_by="hermes_telegram", approved_by="ray",
        inputs={"repair_id": REPAIR_ID, "run_id": run_id},
        expected_outcome="Patch the Voice browser transport to use the governed same-origin relay; pass bounded tests; stop before deployment.",
        idempotency_key=f"{IDEMPOTENCY_PREFIX}{run_id}", status="approved",
    )
    work_orders.transition(order["work_order_id"], "queued", repair_id=REPAIR_ID, run_id=run_id, mission_id="manual-repair-voice-001")
    _state(run_id, state="QUEUED", work_order_id=order["work_order_id"], approval_reference=f"manual:{REPAIR_ID}:{run_id}", authority_scope=[REPAIR_ID], executor=ACTION_ID)
    queued = _launch_existing_order({**order, "status": "queued"}, run_id)
    return {**queued, "repair_id": REPAIR_ID, "run_id": run_id}


def resume_waiting_worker(run_id: str = "MANUAL-E2E-20260827-2992") -> Dict[str, Any]:
    """Bounded capacity retry for the same approved VOICE-001 order."""
    if run_id != "MANUAL-E2E-20260827-2992":
        return {"status": "blocked", "reason": "wrong_manual_certification_run"}
    if _manual_approval(run_id) is None:
        return {"status": "waiting_approval", "repair_id": REPAIR_ID, "run_id": run_id}
    order = _existing_order(run_id)
    state = _load(STATE_PATH, {}) or {}
    if not order:
        return {"status": "waiting_worker", "reason": "repair_work_order_not_found", "repair_id": REPAIR_ID}
    if state.get("state") not in {"WAITING_WORKER", "WORKER_SELECTION", "QUEUED", "RECOVERING", "RETRY_BACKOFF"}:
        return {"status": "not_eligible", "state": state.get("state"), "work_order_id": order.get("work_order_id")}
    # The recovery launchd job is intentionally more frequent than the worker
    # retry budget.  Refresh cheap static discovery, but do not launch another
    # child or repeat an expensive worker execution probe until the pool changes
    # or the persisted bounded backoff expires.
    from nexus_agent_platform.governed.engineering_broker import worker_matrix, retry_state_due
    pool = worker_matrix(None)
    retry = _load(ROOT / "reports/runtime/voice_repair_retry_state.json", {}) or {}
    if not retry_state_due(retry):
        return {"status": "not_due", "state": "WAITING_WORKER", "work_order_id": order.get("work_order_id"),
                "worker_pool_generation": retry.get("worker_pool_generation"), "next_retry_at": retry.get("next_retry_at"),
                "worker_matrix": pool, "automatic_resume": True}
    return {**_launch_existing_order(order, run_id), "repair_id": REPAIR_ID, "run_id": run_id, "automatic_resume": True}


def _build_task(run_id: str):
    from nexus_product_evolution.adapters.builder_adapter import mission_to_build_task
    from nexus_product_evolution.loop import MissionContract
    contract = MissionContract(
        goal="Repair the production Voice browser transport so it uses the same-origin governed Netlify relay.",
        user_visible_outcome="Voice requests use the server-side relay and never expose Cloudflare credentials.",
        acceptance_criteria=["transcribe and preview use /.netlify/functions/voice-relay", "no browser request targets voice.goclearonline.cc", "focused Voice transport tests pass"],
        security_boundaries=["do not expose CF_ACCESS credentials", "do not deploy", "do not modify unrelated paths"],
        cost_ceiling="$0", deployment_policy="DEPLOYMENT_REQUIRES_SEPARATE_APPROVAL", locked_systems=["forex", "active_operator"], human_only_gates=["real Voice canary"],
    )
    return mission_to_build_task(
        f"{REPAIR_ID}-{run_id}", contract,
        allowed_paths=["src/admin/VoicePushToTalk.jsx", "src/admin/NexusWakeVoice.jsx", "scripts/nexus_agent_platform/tests/"],
        protected_paths=[".env", "runtime.env", "secrets/", "supabase/", "netlify/.env"],
        tests=[[sys.executable, "-m", "pytest", "tests/voice_live_preview_test.py"]],
        visual_requirements=False, timeout_seconds=600, max_retries=0,
    )


def execute_voice_repair(run_id: str) -> Dict[str, Any]:
    """Executor body called only by the registered governed action."""
    order = next((row for row in work_orders.list_work_orders(limit=1000) if row.get("action_id") == ACTION_ID and row.get("inputs", {}).get("run_id") == run_id), None)
    if not order:
        return {"state": "BLOCKED", "failure": "repair_work_order_not_found"}
    task = _build_task(run_id)
    from nexus_agent_platform.governed.engineering_broker import run_voice_task
    previous = (_load(STATE_PATH, {}) or {}).get("executor")
    engineering_run_id = (_load(STATE_PATH, {}) or {}).get("engineering_run_id") or f"voice-eng-{uuid.uuid4().hex[:12]}"
    _state(run_id, state="WORKER_SELECTION", work_order_id=order["work_order_id"], executor="engineering_broker", engineering_run_id=engineering_run_id)
    result = run_voice_task(task=task, repair_id=REPAIR_ID, work_order_id=order["work_order_id"], run_id=run_id, engineering_run_id=engineering_run_id, previous_worker=previous if previous in {"codex", "opencode"} else None)
    if result.get("_execution_status") == "WAITING_WORKER":
        retry = result.get("retry_state") or {}
        _state(run_id, state="WAITING_WORKER", failure="NO_CERTIFIED_AI_ENGINEERING_WORKER", work_order_id=order["work_order_id"], worker_matrix=result.get("worker_matrix", []), runtime_pickup_state="NOT_OBSERVED", automatic_resume=True, retry_class="APPROVED_WORK_WAITING_CAPACITY", worker_pool_generation=retry.get("worker_pool_generation"), last_pool_check=retry.get("last_meaningful_probe"), next_retry_at=retry.get("next_retry_at"), retry_backoff=retry.get("retry_backoff"), last_stop_reason="NO_CERTIFIED_AI_ENGINEERING_WORKER", last_stop_category="WORKER_CAPACITY")
        return result
    worker = result.get("worker", "unknown")
    _state(run_id, state="ENGINEERING", work_order_id=order["work_order_id"], executor=worker, engineering_run_id=engineering_run_id, runtime_pickup_state="OBSERVED", pickup_observed_at=persistence._now())
    if result.get("_execution_status") == "REPAIR_FAILED":
        _state(run_id, state="FAIL", failure=(result.get("worker_result") or {}).get("verification", {}).get("reason", "ENGINEERING_FAILED"), work_order_id=order["work_order_id"], worker_matrix=result.get("worker_matrix", []))
        return {"state": "FAIL", "failure": "ENGINEERING_FAILED", "patch": "NOT_READY", "worker": worker}
    _state(run_id, state="TESTING", work_order_id=order["work_order_id"], patch="READY", test_result="RUNNING")
    test_env = {key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS}
    test_env["PYTHONPATH"] = str(ROOT / "scripts")
    test = subprocess.run([sys.executable, "-m", "pytest", "tests/voice_live_preview_test.py", "-q"], cwd=ROOT, env=test_env, capture_output=True, text=True, timeout=180, check=False)
    if test.returncode != 0:
        _state(run_id, state="FAIL", work_order_id=order["work_order_id"], patch="READY", test_result="FAIL")
        return {"_execution_status": "REPAIR_FAILED", "state": "FAIL", "patch": "READY", "test_result": "FAIL", "failure": "VOICE_FOCUSED_TESTS_FAILED", "worker": worker}
    _state(run_id, state="PATCH_READY", work_order_id=order["work_order_id"], patch="READY", test_result="PASS", deployment="REQUIRES_SEPARATE_APPROVAL", human_canary="WAITING")
    return {"_execution_status": "PATCH_READY", "state": "PATCH_READY", "patch": "READY", "test_result": "PASS", "deployment": "REQUIRES_SEPARATE_APPROVAL", "human_canary": "WAITING", "worker": worker}


def main() -> int:
    if len(sys.argv) in {2, 3} and sys.argv[1] == "retry":
        result = resume_waiting_worker(sys.argv[2] if len(sys.argv) == 3 else "MANUAL-E2E-20260827-2992")
        print(json.dumps({k: v for k, v in result.items() if k not in {"stdout", "stderr"}}, sort_keys=True))
        return 0 if result.get("status") not in {"blocked", "waiting_approval"} else 1
    if len(sys.argv) == 3 and sys.argv[1] == "execute":
        from nexus_agent_platform.governed.engine import execute_approved_work_order
        work_order_id = sys.argv[2]
        order = work_orders.get_work_order(work_order_id)
        if not order:
            return 2
        run_id = str((order.get("inputs") or {}).get("run_id") or "")
        engineering_run_id = f"voice-eng-{uuid.uuid4().hex[:12]}"
        _state(run_id, state="WORKER_SELECTION", work_order_id=work_order_id, executor="engineering_broker", runtime_pickup_state="NOT_OBSERVED", engineering_run_id=engineering_run_id, worker_pid=os.getpid(), pickup_observed_at=None, mission_id="manual-repair-voice-001")
        result = execute_approved_work_order(work_order_id, resolved_by="ray")
        print(json.dumps({"work_order_id": work_order_id, "result": result.get("result"), "status": result.get("status")}, sort_keys=True))
        return 0 if result.get("status") == "completed" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
