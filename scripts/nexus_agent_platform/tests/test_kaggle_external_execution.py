import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

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

    def test_new_api_token_file_and_legacy_env_are_supported_without_reading_values(self):
        with tempfile.TemporaryDirectory() as directory:
            token_path = Path(directory) / "access_token"
            token_path.write_text("sentinel-not-a-real-token", encoding="utf-8")
            with patch.dict(os.environ, {"KAGGLE_CONFIG_DIR": directory}, clear=False):
                self.assertEqual(KaggleAdapter._auth_source(), "~/.kaggle/access_token")
            with patch.dict(os.environ, {"KAGGLE_CONFIG_DIR": directory, "KAGGLE_USERNAME": "user", "KAGGLE_KEY": "key"}, clear=False):
                token_path.unlink()
                self.assertEqual(KaggleAdapter._auth_source(), "KAGGLE_USERNAME+KAGGLE_KEY")

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
