import json
import fcntl
import plistlib
from contextlib import contextmanager
from pathlib import Path

import scripts.operations.nexus_active_operator_runner as runner
import nexus_agent_platform.governed.persistence as persistence
import process_registry_adapter


def _sandbox(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    (root / "data/operations").mkdir(parents=True)
    (root / "reports/phase16a").mkdir(parents=True)
    (root / "reports/runtime").mkdir(parents=True)
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(root / "data/governed"))
    monkeypatch.setenv("NEXUS_REPO_ROOT", str(root))
    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.setattr(runner, "REGISTRY_PATH", root / "data/operations/nexus_process_registry.json")
    monkeypatch.setattr(runner, "SCHEDULER_HEALTH_PATH", root / "reports/phase16a/scheduler_health.json")
    monkeypatch.setattr(runner, "HEARTBEAT_PATH", root / "reports/runtime/heartbeat.json")
    monkeypatch.setattr(runner, "RUNNER_REPORT_PATH", root / "reports/runtime/report.md")
    monkeypatch.setattr(runner, "RECEIPT_DIR", root / "reports/runtime/receipts")
    monkeypatch.setattr(runner, "LOCK_PATH", root / "data/runtime/operator.lock")
    monkeypatch.setattr(process_registry_adapter, "SPOOL_PATH", root / "data/runtime/spool.jsonl")
    return root


def test_no_action_is_successful_and_writes_heartbeat(monkeypatch, tmp_path):
    root = _sandbox(monkeypatch, tmp_path)
    (root / "data/operations/nexus_process_registry.json").write_text("[]")
    (root / "reports/phase16a/scheduler_health.json").write_text('{"status":"HEALTHY"}')
    result = runner.run_once()
    assert result["status"] == "NO_ACTION_REQUIRED"
    assert result["operator_health"] == "HEALTHY"
    assert Path(result["heartbeat_path"]).name == "heartbeat.json"
    assert json.loads((root / "reports/runtime/heartbeat.json").read_text())["work_discovered"] == 0


def test_work_order_creation_and_duplicate_suppression(monkeypatch, tmp_path):
    root = _sandbox(monkeypatch, tmp_path)
    registry = [{"process_id": "system_health", "name": "System Health", "category": "system_health", "enabled": True, "last_status": "failed", "report_path": "reports/health.json"}]
    (root / "data/operations/nexus_process_registry.json").write_text(json.dumps(registry))
    (root / "reports/phase16a/scheduler_health.json").write_text('{"status":"HEALTHY"}')
    first = runner.run_once()
    second = runner.run_once()
    assert first["status"] == "COMPLETED_WITH_FINDINGS"
    assert len(first["work_orders_created"]) == 1
    assert second["duplicates_suppressed"] == 1
    assert len(persistence.read_records("work_orders")) == 1


def test_priority_and_authority_routing():
    assert runner.priority_for({"category": "system_health"}) == "P0"
    assert runner.priority_for({"category": "client_portal"}) == "P1"
    assert runner.priority_for({"category": "revenue_opportunity"}) == "P2"
    assert runner.classify_action("generate_internal_report") == "AUTO_EXECUTE_INTERNAL_SAFE"
    assert runner.classify_action("runtime_report.generate") == "APPROVAL_REQUIRED"
    assert runner.classify_action("charge_customer") == "NOT_AUTHORIZED"
    assert runner.classify_action("stripe.live_activation") == "NOT_AUTHORIZED"


def test_environment_isolation_removes_stripe_credentials(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sentinel")
    monkeypatch.setenv("VITE_STRIPE_PUBLISHABLE_KEY", "sentinel")
    runner._sanitize_autonomy_environment()
    assert "STRIPE_SECRET_KEY" not in __import__("os").environ
    assert "VITE_STRIPE_PUBLISHABLE_KEY" not in __import__("os").environ
    assert __import__("os").environ["NEXUS_AUTONOMY_STRIPE_DISABLED"] == "1"


def test_overlap_is_skipped_without_running_work(monkeypatch, tmp_path):
    root = _sandbox(monkeypatch, tmp_path)
    (root / "data/operations/nexus_process_registry.json").write_text("[]")
    (root / "reports/phase16a/scheduler_health.json").write_text('{"status":"HEALTHY"}')
    @contextmanager
    def already_locked():
        yield False

    monkeypatch.setattr(runner, "single_run_lock", already_locked)
    result = runner.run_once()
    assert result["status"] == "SKIPPED_OVERLAP"


def test_corrupt_inputs_fail_safe_to_no_action(monkeypatch, tmp_path):
    root = _sandbox(monkeypatch, tmp_path)
    (root / "data/operations/nexus_process_registry.json").write_text("not-json")
    (root / "reports/phase16a/scheduler_health.json").write_text("not-json")
    result = runner.run_once()
    assert result["status"] == "NO_ACTION_REQUIRED"
    assert result["authority"]["external_actions"] == "BLOCKED"


def test_canonical_v2_plist_is_a_launchd_dictionary():
    root = Path(__file__).resolve().parents[3]
    plist = plistlib.loads((root / "ops/launchd/com.nexus.active-operator-v2.plist").read_bytes())
    assert plist["Label"] == "com.nexus.active-operator-v2"
    assert plist["ProgramArguments"][-1] == "--once"
    assert plist["StartInterval"] == 3600
    assert plist["RunAtLoad"] is False
