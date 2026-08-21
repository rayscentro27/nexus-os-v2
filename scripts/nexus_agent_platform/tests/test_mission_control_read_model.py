import json
from datetime import datetime, timedelta, timezone

from scripts.nexus_agent_platform.phase15.mission_control_read_model import build_read_model


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def seed_runtime(root, now, *, core_status="HEALTHY"):
    stamp = now.isoformat()
    write_json(root / "reports/hermes_modernization/live_runtime_status.json", {
        "generated_at": stamp,
        "core_autonomy_runtime": {"status": core_status},
        "optional_integrations": {"alpha": {"status": "NOT_ENABLED"}, "nova": {"status": "NOT_ENABLED"}},
    })
    write_json(root / "reports/phase16a/scheduler_health.json", {"status": "HEALTHY", "last_heartbeat": stamp, "last_exit_code": 0, "next_dispatch": (now + timedelta(hours=1)).isoformat()})
    write_json(root / "reports/runtime/nexus_active_operator_heartbeat_latest.json", {"operator_health": "HEALTHY", "last_successful_run": stamp, "run_status": "NO_ACTION_REQUIRED", "next_scheduled_run": (now + timedelta(hours=1)).isoformat()})
    write_json(root / "reports/runtime/nexus_recovery_check_heartbeat_latest.json", {"run_status": "NO_ACTION_REQUIRED", "last_successful_run": stamp, "next_scheduled_check": (now + timedelta(hours=3)).isoformat()})
    write_json(root / "reports/runtime/nexus_hermes_telegram_heartbeat_latest.json", {"api_status": "HEALTHY", "last_run": stamp, "run_status": "NO_UPDATES"})
    write_json(root / "data/operations/nexus_process_registry.json", [])
    (root / "data/runtime/nexus_loops").mkdir(parents=True, exist_ok=True)
    (root / "data/runtime/nexus_loops/execution_ledger.jsonl").write_text(json.dumps({"completed_at": stamp, "delta_status": "NO_CHANGE", "run_id": "loop-1"}) + "\n", encoding="utf-8")


def test_healthy_stack_and_disabled_optional_integrations(tmp_path):
    now = datetime.now(timezone.utc)
    seed_runtime(tmp_path, now)
    model = build_read_model(root=tmp_path, now=now, approval_rows=[], work_rows=[])
    assert model["system"]["overall_status"] == "HEALTHY"
    assert model["system"]["core_runtime"]["status"] == "HEALTHY"
    assert model["optional_integrations"]["alpha"]["status"] == "NOT_ENABLED"
    assert model["optional_integrations"]["nova"]["status"] == "NOT_ENABLED"
    assert model["needs_ray"]["count"] == 0
    assert model["safety"] == {"stripe_autonomy": "DISABLED", "arbitrary_shell": "UNAVAILABLE", "external_actions": "BLOCKED", "source": "canonical runtime authority state"}


def test_needs_ray_and_priority_counts_are_derived_from_governed_rows(tmp_path):
    now = datetime.now(timezone.utc)
    seed_runtime(tmp_path, now)
    approvals = [{"id": "appr-1", "action_id": "runtime_report.generate", "requested_by": "hermes_telegram", "created_at": now.isoformat(), "status": "pending"}]
    work = [
        {"work_order_id": "wo-p0", "status": "pending_approval", "inputs": {"priority": "P0"}},
        {"work_order_id": "wo-p1", "status": "queued", "inputs": {"priority": "P1"}},
    ]
    model = build_read_model(root=tmp_path, now=now, approval_rows=approvals, work_rows=work)
    assert model["needs_ray"] == {"count": 3, "pending_approvals": 1, "p0_work": 1, "p1_work": 1, "recovery_escalations": 0, "items": [{"kind": "approval", "id": "appr-1", "status": "pending", "action_id": "runtime_report.generate"}, {"kind": "work_order", "id": "wo-p0", "priority": "P0", "status": "pending_approval"}, {"kind": "work_order", "id": "wo-p1", "priority": "P1", "status": "queued"}]}


def test_stale_core_and_corrupt_optional_state_fail_safe(tmp_path):
    now = datetime.now(timezone.utc)
    seed_runtime(tmp_path, now - timedelta(hours=5), core_status="HEALTHY")
    (tmp_path / "reports/hermes_modernization/live_runtime_status.json").write_text("{bad", encoding="utf-8")
    model = build_read_model(root=tmp_path, now=now, approval_rows=[], work_rows=[])
    assert model["system"]["core_runtime"]["status"] == "UNKNOWN"
    assert model["system"]["core_runtime"]["freshness"] == "UNKNOWN"
    assert model["system"]["overall_status"] == "DEGRADED"


def test_evidence_ingestion_is_optional_and_visible_without_degrading_core(tmp_path):
    now = datetime.now(timezone.utc)
    seed_runtime(tmp_path, now)
    write_json(tmp_path / "reports/runtime/nexus_evidence_ingestion_heartbeat_latest.json", {
        "capability": "evidence_ingestion", "status": "DEGRADED", "last_result": "DEPENDENCY_UNAVAILABLE",
        "last_adapter": "crawl4ai", "updated_at": now.isoformat(), "optional": True,
        "core_health_dependency": False,
    })
    model = build_read_model(root=tmp_path, now=now, approval_rows=[], work_rows=[])
    assert model["system"]["overall_status"] == "HEALTHY"
    assert model["optional_integrations"]["evidence_ingestion"]["status"] == "DEGRADED"
    assert model["freshness"]["evidence_ingestion"]["freshness"] == "CURRENT"
