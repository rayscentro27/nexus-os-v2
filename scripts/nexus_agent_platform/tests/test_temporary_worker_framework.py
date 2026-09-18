import tempfile
import unittest
from pathlib import Path

from scripts.nexus_agent_platform.temporary_worker_framework import (
    EnvironmentManifest,
    KaggleAdapter,
    MacAdapter,
    WorkerJob,
    batch_compatible,
    provider_registry,
    run_mac_smoke_canary,
)


class TemporaryWorkerFrameworkTest(unittest.TestCase):
    def test_mac_canary_returns_hashed_artifacts_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_mac_smoke_canary(Path(directory))
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertTrue(result.cleanup_succeeded)
        self.assertEqual({item.logical_name for item in result.artifacts}, {"result.json", "artifact.txt"})
        self.assertTrue(all(item.sha256 for item in result.artifacts))

    def test_provider_registry_has_one_entry_per_provider(self):
        registry = provider_registry()
        self.assertEqual(set(registry), {"mac", "oracle", "modal", "kaggle"})
        self.assertFalse(registry["kaggle"]["available"])
        self.assertFalse(registry["kaggle"]["quota_known"])

    def test_kaggle_failure_is_blocked_not_exception(self):
        result = KaggleAdapter().execute(WorkerJob("k1", "SMOKE_TEST_V1"), Path(tempfile.mkdtemp()))
        self.assertEqual(result.status, "BLOCKED_EXTERNAL")

    def test_batch_compatibility_uses_environment_signatures(self):
        metadata = {"worker_class": "MEDIA_RENDER", "environment_signature": "e1", "dependency_signature": "d1", "model_signature": "m1", "gpu_class": "none"}
        self.assertTrue(batch_compatible(WorkerJob("a", "x", batch_metadata=metadata), WorkerJob("b", "x", batch_metadata=metadata.copy())))
        changed = dict(metadata, model_signature="m2")
        self.assertFalse(batch_compatible(WorkerJob("a", "x", batch_metadata=metadata), WorkerJob("b", "x", batch_metadata=changed)))

    def test_environment_manifest_is_rebuildable(self):
        manifest = EnvironmentManifest("smoke-v1", "SMOKE_TEST_V1", "python:3.11", "3.11", None, execution_command="python worker.py")
        self.assertEqual(manifest.input_schema, "application/json")
        self.assertEqual(manifest.execution_command, "python worker.py")


if __name__ == "__main__":
    unittest.main()
