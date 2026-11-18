import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S1_RELEASE = Path.home() / ".nexus/releases/nexus-systems-engine-s1-20261028"
S1 = S1_RELEASE / "systems_engine_s1_batch_d"
sys.path.insert(0, str(ROOT / "scripts/systems"))
sys.path.insert(0, str(S1_RELEASE))
sys.path.insert(0, str(S1))

import managed_work
from bridge import validate_request
from systems_engine_s1_batch_d.service import _safe_install_failure
from change_target_resolver import MANIFEST, resolve_target
import json
import sqlite3
import tempfile
import subprocess

CONFIG = str(Path.home() / ".config/opencode/opencode.jsonc")
NODE_ROOT = str(Path.home() / ".nvm/versions/node/v24.22.1")
METHOD = "NVM_PINNED_NODE_24_22_1_NPM_GLOBAL_REA_6_8_0_OPENCODE_SETUP"
ROLLBACK = "Restore exact OpenCode config backup; npm uninstall REA; nvm uninstall 24.22.1"
FACTS = {
    "zero_unexpected_cost": True, "unexpected_cost": False,
    "no_paid_activation": True, "paid_activation": False,
    "no_credential_access": True, "credential_or_private_data_access": False,
    "no_sensitive_data_movement": True, "material_sensitive_data_movement": False,
    "external_payment_step": False,
}
ACTION = {"operation": "systems.install_technology", "payload": {}}
BASE_PAYLOAD = {
    "technology_name": "REA MCP", "technology_source": "https://github.com/morluto/rea",
    "target_environment": "MAC_MINI", "target_component": "OpenCode / REA integration",
    "target_scope": CONFIG, "native_install_method": METHOD,
    "configuration_targets": [CONFIG], "allowed_paths": [CONFIG, NODE_ROOT],
    "prohibited_paths": ["~/.config/opencode/auth.json", "data/runtime/research_work_queue.json"],
    "health_check": "scoped doctor and MCP list", "rollback_or_uninstall_method": ROLLBACK,
    "node_version": "24.22.1", "node_install_path": NODE_ROOT,
    "package_name": "rea-agents", "package_version": "6.8.0",
    "policy_classification": "AUTONOMOUS_BOUNDED",
}

def request(payload):
    return {"request_id": "test-request", "caller": "NOVA_NEXUS", "operation": "systems.install_technology",
            "environment_id": "MAC_MINI", "scope": "nova-typed-systems-bridge", "idempotency_key": "test-key",
            "approval_context": {}, "reason": "bounded test", "payload": payload}

class MaintenancePolicyTests(unittest.TestCase):
    def classify(self, facts=FACTS, **kwargs):
        config = {"policy_facts": facts}
        return managed_work.classify_maintenance_policy(config, target_resolved=True,
            validation={"required": ["focused_validation"]}, rollback=ROLLBACK, typed_action=ACTION)

    def test_manifest_target_resolves_install_scope(self):
        manifest=json.loads(MANIFEST.read_text())
        target=resolve_target(manifest,"opencode","Install pinned REA MCP for OpenCode",[
            CONFIG,NODE_ROOT+"/bin/node",str(MANIFEST)])
        self.assertEqual(target["authority_check"],"PASS")

    def test_prohibited_auth_target_is_rejected(self):
        manifest=json.loads(MANIFEST.read_text())
        with self.assertRaisesRegex(ValueError,"OUT_OF_AUTHORITY_SCOPE"):
            resolve_target(manifest,"opencode","Do not touch credentials",[
                str(Path.home()/".config/opencode/auth.json")])

    def test_autonomous_bounded_does_not_need_reference(self):
        self.assertEqual(self.classify(), "AUTONOMOUS_BOUNDED")

    def test_paid_activation_requires_ray(self):
        facts = {**FACTS, "paid_activation": True}
        self.assertEqual(self.classify(facts), "RAY_APPROVAL_REQUIRED")

    def test_credential_access_requires_ray(self):
        facts = {**FACTS, "credential_or_private_data_access": True}
        self.assertEqual(self.classify(facts), "RAY_APPROVAL_REQUIRED")

    def test_sensitive_movement_requires_ray(self):
        facts = {**FACTS, "material_sensitive_data_movement": True}
        self.assertEqual(self.classify(facts), "RAY_APPROVAL_REQUIRED")

    def test_unresolved_target_rejected(self):
        with self.assertRaisesRegex(ValueError, "TARGET_UNRESOLVED"):
            managed_work.classify_maintenance_policy({"policy_facts": FACTS}, target_resolved=False,
                validation={"required": ["x"]}, rollback=ROLLBACK, typed_action=ACTION)

    def test_missing_rollback_rejected(self):
        with self.assertRaisesRegex(ValueError, "CONTRACT_INCOMPLETE"):
            managed_work.classify_maintenance_policy({"policy_facts": FACTS}, target_resolved=True,
                validation={"required": ["x"]}, rollback=None, typed_action=ACTION)

    def test_missing_validation_rejected(self):
        with self.assertRaisesRegex(ValueError, "CONTRACT_INCOMPLETE"):
            managed_work.classify_maintenance_policy({"policy_facts": FACTS}, target_resolved=True,
                validation={}, rollback=ROLLBACK, typed_action=ACTION)

    def test_valid_autonomous_install_request_accepted_without_approval(self):
        self.assertEqual(validate_request(request(dict(BASE_PAYLOAD)))["operation"], "systems.install_technology")

    def test_ray_classification_requires_durable_reference(self):
        payload = {**BASE_PAYLOAD, "policy_classification": "RAY_APPROVAL_REQUIRED"}
        with self.assertRaisesRegex(ValueError, "APPROVAL_REFERENCE_REQUIRED"):
            validate_request(request(payload))

    def test_matching_reference_shape_accepted_for_ray_policy(self):
        payload = {**BASE_PAYLOAD, "policy_classification": "RAY_APPROVAL_REQUIRED",
                   "approval_reference": "sysapproval_" + "a" * 48}
        self.assertEqual(validate_request(request(payload))["operation"], "systems.install_technology")

    def test_autonomous_reference_rejected(self):
        payload = {**BASE_PAYLOAD, "approval_reference": "sysapproval_" + "a" * 48}
        with self.assertRaisesRegex(ValueError, "MUST_NOT_REQUIRE_APPROVAL"):
            validate_request(request(payload))

    def test_arbitrary_command_rejected(self):
        with self.assertRaisesRegex(ValueError, "SCHEMA_INVALID"):
            validate_request(request({**BASE_PAYLOAD, "command": "anything"}))

    def test_environment_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "ENVIRONMENT_MISMATCH"):
            validate_request({**request(BASE_PAYLOAD), "environment_id": "ORACLE"})

    def test_managed_work_dispatches_autonomous_install_without_reference(self):
        manifest=json.loads(MANIFEST.read_text())
        cfg=manifest["systems_managed_work"]["action_targets"]["INSTALL_TECHNOLOGY"]
        calls=[]
        def executor(operation, **kwargs):
            calls.append((operation, kwargs))
            return {"engine_status":"PRECONDITION_FAILED", "data":{}, "verification":"TEST_STOP"}
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"systems.sqlite3"
            with sqlite3.connect(db) as con:
                con.execute("CREATE TABLE receipts(receipt_id TEXT,request_id TEXT,receipt_type TEXT,created_at TEXT,payload TEXT)")
            work=managed_work.create_work_order(component="opencode", objective="bounded REA integration",
                requested_files=cfg["requested_files"], requested_by="test", environment="MAC_MINI",
                change_class="AUTONOMOUS_BOUNDED_INSTALL_TECHNOLOGY", execution_agent="SYSTEMS_LOCAL",
                approval_requirement="POLICY_CLASSIFIED", validation={"required":["focused_validation"]},
                rollback=cfg["rollback"], manifest=manifest, db_path=db, requested_action="INSTALL_TECHNOLOGY",
                typed_action_config=cfg["typed_action"], typed_executor=executor)
        self.assertEqual(work["maintenance_classification"],"AUTONOMOUS_BOUNDED")
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],"systems.install_technology")
        self.assertNotIn("approval_reference",calls[0][1]["payload"])
        self.assertEqual(work["authoritative_target"]["authority_check"],"PASS")

    def test_installer_failure_persists_only_standard_error_code(self):
        result=subprocess.CompletedProcess(["npm"],1,stdout="",stderr="npm error code EBADENGINE\nAuthorization: Bearer never-print-this")
        self.assertEqual(_safe_install_failure(result,"REA_PACKAGE_INSTALL"),"REA_PACKAGE_INSTALL_EBADENGINE")

    def test_existing_handoff_remains_in_operation_allowlist(self):
        self.assertIn("systems.technology_handoff", __import__("bridge").HANDOFF_OPS)

if __name__ == "__main__":
    unittest.main()
