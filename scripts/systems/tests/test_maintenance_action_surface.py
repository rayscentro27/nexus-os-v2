"""Contract tests for the existing Systems managed-work/S1 action surface."""
from __future__ import annotations

import json
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/systems"))

import managed_work

S1_ROOT = Path.home() / ".nexus/releases/nexus-systems-engine-s1-20261028"
sys.path.insert(0, str(S1_ROOT))
from systems_engine_s1_batch_d.bridge import validate_request
from systems_engine_s1_batch_d import service as s1_service


def request(operation: str, payload: dict, *, service_id: str | None = None) -> dict:
    value = {
        "request_id": "systems-test-request",
        "caller": "NOVA_NEXUS",
        "operation": operation,
        "environment_id": "MAC_MINI",
        "scope": "systems-test",
        "idempotency_key": "systems-test-idempotency",
        "approval_context": {},
        "reason": "contract test",
        "payload": payload,
    }
    if service_id:
        value["service_id"] = service_id
    return value


class ManagedActionMappingTests(unittest.TestCase):
    def test_remaining_actions_map_to_existing_typed_s1_operations(self) -> None:
        expected = {
            "BOUNDED_UPGRADE": "systems.upgrade_component",
            "SAFE_CLEANUP": "systems.safe_cleanup",
            "CREDENTIAL_ROTATION": "systems.rotate_credential",
            "KAGGLE_PREP": "systems.prepare_kaggle_job",
            "SAFE_RESTART": "systems.restart_safe",
            "ROLLBACK": "systems.rollback",
        }
        for action, operation in expected.items():
            with self.subTest(action=action):
                self.assertEqual(managed_work.MANAGED_ACTION_OPERATIONS[action], operation)

    def test_coding_worker_requires_resolved_scope(self) -> None:
        self.assertTrue(managed_work.worker_scope_required("CODEX"))
        self.assertTrue(managed_work.worker_scope_required("OPENCODE"))
        self.assertTrue(managed_work.worker_scope_required("KILO"))


class TypedS1RequestContractTests(unittest.TestCase):
    def test_upgrade_payload_is_typed_and_rejects_commands(self) -> None:
        payload = {
            "component": "OpenCode", "authoritative_target": "opencode",
            "current_version": "1.19.5", "approved_target_version": "1.19.5",
            "installation_method": "HOMEBREW_FORMULA", "allowed_paths": ["/usr/local/Cellar/opencode"],
            "prohibited_paths": ["~/.config/opencode/auth.json"], "health_check": "opencode --version",
            "rollback_reference": "retained-homebrew-keg", "policy_classification": "AUTONOMOUS_BOUNDED",
            "dry_run": True,
        }
        self.assertEqual(validate_request(request("systems.upgrade_component", payload))["operation"],
                         "systems.upgrade_component")
        payload["command"] = "brew upgrade"
        with self.assertRaises((ValueError, PermissionError)):
            validate_request(request("systems.upgrade_component", payload))

    def test_cleanup_requires_manifest_target_ids_and_safe_classifications(self) -> None:
        payload = {"target_environment": "MAC_MINI", "target_component": "Systems",
                   "target_scope": "living-manifest-cleanup-targets", "targets": [],
                   "policy_classification": "AUTONOMOUS_BOUNDED", "dry_run": True}
        self.assertEqual(validate_request(request("systems.safe_cleanup", payload))["operation"],
                         "systems.safe_cleanup")
        payload["targets"] = [{"target_id": "x", "classification": "UNKNOWN", "disposition": "DELETE"}]
        with self.assertRaises((ValueError, PermissionError)):
            validate_request(request("systems.safe_cleanup", payload))

    def test_credential_rotation_payload_cannot_carry_secret_values(self) -> None:
        payload = {"credential_reference": "github-nexus", "provider": "GitHub",
                   "consumer_services": ["nexus-mcp"], "secure_store_reference": "keychain:github",
                   "rotation_method": "provider-console", "verification_method": "health-check",
                   "revocation_method": "provider-revoke", "target_environment": "MAC_MINI",
                   "policy_classification": "RAY_APPROVAL_REQUIRED", "dry_run": True}
        self.assertEqual(validate_request(request("systems.rotate_credential", payload))["operation"],
                         "systems.rotate_credential")
        payload["secret_value"] = "must-never-be-accepted"
        with self.assertRaises((ValueError, PermissionError)):
            validate_request(request("systems.rotate_credential", payload))

    def test_kaggle_prepare_is_bounded_and_rejects_arbitrary_argv(self) -> None:
        payload = {"job": {"job_id": "systems-test-job", "objective": "bounded dry run",
                           "workload_type": "batch_analysis", "input_artifacts": [],
                           "expected_outputs": ["outputs/result.json"],
                           "resource_request": {"cpu_count": 1, "memory_gb": 2, "gpu_required": False},
                           "timeout_seconds": 60},
                   "target_environment": "MAC_MINI", "policy_classification": "AUTONOMOUS_BOUNDED",
                   "dry_run": True}
        self.assertEqual(validate_request(request("systems.prepare_kaggle_job", payload))["operation"],
                         "systems.prepare_kaggle_job")
        payload["command_argv"] = ["/bin/sh", "-c", "arbitrary"]
        with self.assertRaises((ValueError, PermissionError)):
            validate_request(request("systems.prepare_kaggle_job", payload))

    def test_existing_restart_and_rollback_contracts_remain(self) -> None:
        for operation in ("systems.restart_safe", "systems.rollback"):
            with self.subTest(operation=operation):
                value = request(operation, {}, service_id="test-registered-service")
                value["environment_id"] = "DISPOSABLE_SANDBOX"
                self.assertEqual(validate_request(value)["operation"], operation)


class SafeDispatchBehaviorTests(unittest.TestCase):
    def _dispatch(self, operation: str, payload: dict) -> dict:
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE receipts(receipt_id TEXT PRIMARY KEY, request_id TEXT, receipt_type TEXT, created_at TEXT, payload TEXT)")
        req = request(operation, payload)
        try:
            return s1_service._bounded_maintenance_dispatch(req, db)
        finally:
            db.close()

    def test_upgrade_noop_is_review_only(self) -> None:
        import json
        manifest = json.loads((ROOT / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json").read_text())
        payload = dict(manifest["systems_managed_work"]["action_targets"]["UPGRADE"]["typed_action"]["payload"])
        payload["dry_run"] = True
        self.assertEqual(self._dispatch("systems.upgrade_component", payload)["status"], "DRY_RUN_VALIDATED")

    def test_empty_cleanup_is_noop(self) -> None:
        payload = {"target_environment":"MAC_MINI","target_component":"Systems","target_scope":"manifest-safe-targets",
            "targets":[],"policy_classification":"AUTONOMOUS_BOUNDED","dry_run":True}
        self.assertEqual(self._dispatch("systems.safe_cleanup", payload)["status"], "NO_SAFE_CLEANUP_TARGETS")

    def test_credential_rotation_stays_at_provider_boundary(self) -> None:
        payload = {"credential_reference":"registry-review-only","provider":"GitHub","consumer_services":["nexus-mcp"],
            "secure_store_reference":"keychain-reference","rotation_method":"provider-managed","verification_method":"health-check",
            "revocation_method":"provider-revoke","target_environment":"MAC_MINI",
            "policy_classification":"RAY_APPROVAL_REQUIRED","dry_run":True}
        self.assertEqual(self._dispatch("systems.rotate_credential", payload)["status"], "WAITING_EXTERNAL_BOUNDARY")

    def test_kaggle_contract_is_prepared_without_external_transfer(self) -> None:
        payload = {"job":{"job_id":"systems-test-job","objective":"bounded test","workload_type":"batch_analysis",
            "input_artifacts":[],"expected_outputs":["result_manifest.json"],"resource_request":{"gpu_required":False},"timeout_seconds":60},
            "target_environment":"MAC_MINI","policy_classification":"AUTONOMOUS_BOUNDED","dry_run":True}
        self.assertEqual(self._dispatch("systems.prepare_kaggle_job", payload)["status"], "DRY_RUN_VALIDATED")

    def test_existing_kaggle_bootstrap_prepares_only_bounded_local_workspace(self) -> None:
        job = {"job_id":"systems-test-job","objective":"bounded test","workload_type":"batch_analysis",
               "input_artifacts":[],"expected_outputs":["result_manifest.json"],
               "resource_request":{"gpu_required":False},"timeout_seconds":60}
        with tempfile.TemporaryDirectory(prefix="systems-kaggle-prep-test-") as temp:
            result = s1_service._prepare_kaggle_workspace({"job":job}, root=Path(temp)/"prep")
            self.assertEqual(result["state"], "AWAITING_BOUNDED_WORKLOAD_BINDING")
            self.assertFalse(result["external_transfer"])
            request_record = json.loads(Path(result["request_file"]).read_text())
            self.assertEqual(request_record["job"]["job_id"], job["job_id"])
            self.assertFalse("command_argv" in request_record["job"])
            replay = s1_service._prepare_kaggle_workspace({"job":job}, root=Path(temp)/"prep")
            self.assertFalse(replay["workspace_created"])

    def test_kaggle_typed_action_returns_prepared_without_platform_transfer(self) -> None:
        payload = {"job":{"job_id":"systems-test-job","objective":"bounded test","workload_type":"batch_analysis",
                           "input_artifacts":[],"expected_outputs":["result_manifest.json"],
                           "resource_request":{"gpu_required":False},"timeout_seconds":60},
                   "target_environment":"MAC_MINI","policy_classification":"AUTONOMOUS_BOUNDED","dry_run":False}
        with patch.object(s1_service, "_prepare_kaggle_workspace", return_value={
                "workdir":"/bounded/test","request_file":"/bounded/test/job_request.json",
                "state":"AWAITING_BOUNDED_WORKLOAD_BINDING","external_transfer":False,
                "workspace_created":True,"rollback_reference":"exact-test-path"}):
            result = self._dispatch("systems.prepare_kaggle_job", payload)
        self.assertEqual(result["status"], "PREPARED")
        self.assertFalse(result["data"]["validation"]["external_transfer"])


if __name__ == "__main__":
    unittest.main()
