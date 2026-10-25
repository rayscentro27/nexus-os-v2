from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[2]
RUNTIME = COMPONENT / "runtime"
BASE = COMPONENT.parent / "nova-operator-v1-20261025-r28-baseline" / "runtime"
OVERLAY = set(json.loads((COMPONENT / "BASELINE_LINEAGE.json").read_text())["overlay_files"])


class NovaR29LineageTests(unittest.TestCase):
    def test_01_lineage_is_certified_r28(self):
        info = json.loads((COMPONENT / "BASELINE_LINEAGE.json").read_text())
        self.assertEqual(info["base_release"], "nova-operator-v1-20261025-r28-baseline")
        self.assertEqual(info["base_source_commit"], "f99c1eb04dc4ba6017de6de5bdade72f0f3f1d75")
        self.assertEqual(info["base_artifact_sha256"], "70cfae57ac5a566165276ece9a23c972b14d251a3d736452e699253a60af0f4f")

    def test_02_all_r28_base_files_verify_from_input_manifest(self):
        lines = (COMPONENT / "R28_BASE_INPUT_MANIFEST.sha256").read_text().splitlines()
        self.assertEqual(len(lines), 155)
        for line in lines:
            expected, relative = line.split(maxsplit=1)
            relative = relative.strip()
            base_file = BASE / relative.removeprefix("runtime/")
            self.assertTrue(base_file.is_file(), relative)
            self.assertEqual(hashlib.sha256(base_file.read_bytes()).hexdigest(), expected, relative)

    def test_03_only_declared_runtime_files_differ_from_r28(self):
        for line in (COMPONENT / "R28_BASE_INPUT_MANIFEST.sha256").read_text().splitlines():
            expected, relative = line.split(maxsplit=1)
            relative = relative.strip().removeprefix("runtime/")
            current = RUNTIME / relative
            self.assertTrue(current.is_file(), relative)
            actual = hashlib.sha256(current.read_bytes()).hexdigest()
            if relative not in OVERLAY:
                self.assertEqual(actual, expected, relative)
            else:
                self.assertNotEqual(actual, expected, relative)

    def test_04_overlay_is_exact_and_research_runtime_untouched(self):
        self.assertEqual(OVERLAY, {
            "scripts/nova/nova_telegram_worker.py", "scripts/nova/semantic_orchestration.py",
            "scripts/nova/nexus_mcp_status.py", "scripts/nova/research_intent.py",
            "scripts/nova/nova_research_control.py",
        })
        self.assertFalse((RUNTIME / "scripts/nexus_agent_platform/research_only_execution.py").exists())
        self.assertEqual(json.loads((COMPONENT / "BASELINE_LINEAGE.json").read_text())["research_runtime_changed_files"], [])

    def test_05_mcp_fixture_is_read_only_and_has_required_tools(self):
        proof = json.loads((COMPONENT / "certification/live_r60_mcp_discovery.json").read_text())
        self.assertEqual(proof["initialize"], "PASS")
        self.assertEqual(proof["tool_count"], 49)
        self.assertTrue(proof["required_tools"]["nexus_assign_research"])
        self.assertTrue(proof["required_tools"]["nexus_get_durable_jobs"])
        self.assertEqual(proof["research_jobs_created"], "NO")

    def test_06_current_r60_mcp_readonly_discovery_is_recorded(self):
        proof = json.loads((COMPONENT / "certification/live_r60_mcp_discovery.json").read_text())
        self.assertEqual(proof["operations_performed"], ["initialize", "tools/list"])
        self.assertEqual(proof["supabase_mutations"], "NO")


if __name__ == "__main__":
    unittest.main()
