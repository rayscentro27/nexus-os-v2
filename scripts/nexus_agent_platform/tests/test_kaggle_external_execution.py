import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from scripts.nexus_agent_platform.resource_governor import ResourceGovernor
from scripts.nexus_agent_platform.temporary_worker_framework import (
    EnvironmentManifest,
    KaggleAdapter,
    ResourceRequirements,
    WorkerJob,
    run_mac_smoke_canary,
)


class KaggleExternalExecutionTests(unittest.TestCase):
    def test_kaggle_probe_is_truthful_and_quota_is_not_unlimited(self):
        probe = KaggleAdapter().probe()
        self.assertIn(probe["authorization_state"], {"REAUTH_REQUIRED", "AUTHORIZED"})
        if not probe["available"]:
            self.assertFalse(probe["capabilities"]["artifact_download"])
        self.assertFalse(probe["quota_known"])

    def test_blocked_kaggle_job_returns_receipt_shape_without_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            result = KaggleAdapter().execute(WorkerJob("kaggle-blocked-1", "SMOKE_TEST_V1"), Path(directory))
        self.assertEqual(result.status, "BLOCKED_EXTERNAL")
        self.assertEqual(result.worker_job_id, "kaggle-blocked-1")
        self.assertEqual(result.provider, "kaggle")
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)

    def test_real_local_fallback_artifact_hash_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_mac_smoke_canary(Path(directory))
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertTrue(result.cleanup_succeeded)
        self.assertEqual(len(result.artifacts), 2)
        self.assertTrue(all(len(item.sha256) == 64 for item in result.artifacts))

    def test_gpu_job_requires_readiness_and_does_not_activate_routing(self):
        job = WorkerJob("gpu-not-ready", "VIDEO_GENERATION",
                        resource_requirements=ResourceRequirements(gpu_required=True),
                        parameters={"cost_tolerance": "FREE_ONLY"})
        decision = ResourceGovernor().evaluate_job(job)
        self.assertEqual(decision["mode"], "SHADOW")
        self.assertFalse(decision["executed"])
        self.assertIsNone(decision["selected_provider"])

    def test_environment_manifest_and_job_are_json_serializable(self):
        manifest = EnvironmentManifest("kaggle-smoke-v1", "SMOKE_TEST_V1", "python:3.11", "3.11", None,
                                       execution_command="python worker.py")
        job = WorkerJob("serialization-1", "SMOKE_TEST_V1", environment_requirements={"manifest": manifest.environment_id})
        json.dumps({"manifest": asdict(manifest), "job": asdict(job)})


if __name__ == "__main__":
    unittest.main()
