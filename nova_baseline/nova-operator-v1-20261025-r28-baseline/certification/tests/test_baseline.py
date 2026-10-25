from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import unittest
from pathlib import Path


COMPONENT = Path(__file__).resolve().parents[2]
RUNTIME = COMPONENT / "runtime"
INPUT_MANIFEST = COMPONENT / "R27_INPUT_MANIFEST.sha256"
LINEAGE = json.loads((COMPONENT / "BASELINE_LINEAGE.json").read_text())
LIVE_MCP = json.loads((COMPONENT / "certification/live_mcp_discovery.json").read_text())
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{24,}\b"),
    re.compile(rb"\bsb_secret_[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{24,}\b"),
)


def input_entries() -> list[tuple[str, str]]:
    entries = []
    for line in INPUT_MANIFEST.read_text().splitlines():
        digest, relative = line.split(maxsplit=1)
        entries.append((digest, relative.strip()))
    return entries


class NovaR28BaselineTests(unittest.TestCase):
    def test_01_rebase_lineage_is_explicit(self):
        self.assertEqual(LINEAGE["source_class"], "VERIFIED_R27_IMMUTABLE_RUNTIME_SUBSET")
        self.assertEqual(LINEAGE["historical_r27_git_source_commit"], "UNKNOWN")
        self.assertEqual(LINEAGE["historical_r27_artifact_archive_sha256"], "UNAVAILABLE")
        self.assertFalse(LINEAGE["historical_r25_to_r27_provenance_asserted"])

    def test_02_new_lineage_begins_here(self):
        self.assertTrue(LINEAGE["new_lineage_begins_at_this_baseline_commit"])

    def test_03_mutable_operational_state_is_classified(self):
        self.assertEqual(LINEAGE["r27_mutable_state_file_count"], 38)
        self.assertIn("data/governed/research_runtime_states.jsonl", LINEAGE["excluded_mutable_state"])

    def test_04_mutable_state_is_not_copied(self):
        self.assertFalse((RUNTIME / "data/governed/research_runtime_states.jsonl").exists())

    def test_05_live_operational_state_is_not_copied(self):
        self.assertFalse(any((RUNTIME / part).exists() for part in ("data/runtime", "data/nova", "reports/runtime")))

    def test_06_selected_file_count_matches_record(self):
        self.assertEqual(len(input_entries()), LINEAGE["selected_runtime_file_count"])
        self.assertEqual(len(input_entries()), 155)

    def test_07_all_selected_files_match_r27_input_hashes(self):
        for expected, relative in input_entries():
            path = COMPONENT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_08_nova_worker_imports_from_baseline(self):
        self._assert_module_imports("nova.nova_telegram_worker")

    def test_09_semantic_router_imports_from_baseline(self):
        self._assert_module_imports("nova.semantic_orchestration")

    def test_10_mcp_adapter_imports_from_baseline(self):
        self._assert_module_imports("nova.nexus_mcp_status")

    def test_11_research_intent_imports_from_baseline(self):
        self._assert_module_imports("nova.research_intent")

    def test_12_hermes_runner_imports_from_baseline(self):
        self._assert_module_imports("nova.nova_hermes_shadow", add_nova_script_dir=True)

    def test_13_wrapper_has_valid_shell_syntax(self):
        path = RUNTIME / "scripts/ops/run_nova_with_runtime_env.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr[:300])

    def test_14_launchagent_plist_is_valid_and_disabled(self):
        path = RUNTIME / "launchd/com.nexus.telegram-hermes-nova.plist"
        with path.open("rb") as stream:
            plist = plistlib.load(stream)
        self.assertEqual(plist.get("Label"), "com.nexus.telegram-hermes-nova")
        self.assertTrue(plist.get("Disabled"))

    def test_15_live_r60_mcp_initialize_passed(self):
        self.assertEqual(LIVE_MCP["initialize"], "PASS")
        self.assertEqual(LIVE_MCP["endpoint"], "http://127.0.0.1:18765/mcp")

    def test_16_live_mcp_exposes_49_tools(self):
        self.assertEqual(LIVE_MCP["tool_count"], 49)

    def test_17_research_assignment_tool_is_discoverable(self):
        self.assertTrue(LIVE_MCP["required_tools"]["nexus_assign_research"])

    def test_18_exact_job_status_tool_is_discoverable(self):
        self.assertTrue(LIVE_MCP["required_tools"]["nexus_get_durable_jobs"])

    def test_19_live_mcp_certification_created_no_research_job(self):
        self.assertEqual(LIVE_MCP["operations_performed"], ["initialize", "list_tools"])
        self.assertEqual(LIVE_MCP["research_jobs_created"], "NO")
        self.assertEqual(LIVE_MCP["supabase_mutations"], "NO")

    def test_20_nova_adapter_uses_existing_mcp_not_direct_supabase(self):
        source = (RUNTIME / "scripts/nova/nexus_mcp_status.py").read_text().casefold()
        self.assertNotIn("postgrest", source)
        self.assertNotIn("supabase.create_client", source)
        self.assertIn('"nexus_assign_research"', source)
        self.assertIn('"nexus_get_durable_jobs"', source)

    def test_21_no_r60_research_execution_file_is_packaged(self):
        self.assertFalse((RUNTIME / "scripts/nexus_agent_platform/research_only_execution.py").exists())

    def test_22_packaged_files_have_no_common_secret_material(self):
        for path in RUNTIME.rglob("*"):
            if path.is_file():
                body = path.read_bytes()
                for pattern in SECRET_PATTERNS:
                    with self.subTest(path=path.relative_to(RUNTIME), pattern=pattern.pattern):
                        self.assertIsNone(pattern.search(body))

    def _assert_module_imports(self, module: str, *, add_nova_script_dir: bool = False):
        script = (
            "import importlib, pathlib, sys; "
            "root=pathlib.Path(sys.argv[1]).resolve(); "
            "sys.path[:0]=[str(root/'scripts'),str(root)]; "
            "sys.path.insert(0,str(root/'scripts/nova')) if sys.argv[3]=='1' else None; "
            "m=importlib.import_module(sys.argv[2]); "
            "p=pathlib.Path(m.__file__).resolve(); "
            "assert p.is_relative_to(root), str(p); print('PASS')"
        )
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, "-B", "-c", script, str(RUNTIME), module,
             "1" if add_nova_script_dir else "0"],
            cwd=RUNTIME, env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
