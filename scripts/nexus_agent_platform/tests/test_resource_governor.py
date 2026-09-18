import unittest

from scripts.nexus_agent_platform.resource_governor import ResourceGovernor, model_routing_compatibility
from scripts.nexus_agent_platform.temporary_worker_framework import ResourceRequirements, WorkerJob


def job(name, **kwargs):
    return WorkerJob(name, "SMOKE_TEST_V1", parameters=kwargs)


class ResourceGovernorTest(unittest.TestCase):
    def setUp(self):
        self.governor = ResourceGovernor()

    def test_cpu_job_selects_mac_in_shadow_mode(self):
        decision = self.governor.evaluate_job(job("cpu-a", cost_tolerance="FREE_ONLY"))
        self.assertEqual(decision["selected_provider"], "mac")
        self.assertFalse(decision["executed"])

    def test_gpu_job_is_not_routed_without_ready_authorized_provider(self):
        gpu = WorkerJob("gpu-a", "VIDEO_GENERATION", resource_requirements=ResourceRequirements(gpu_required=True), parameters={"production_ready": True, "cost_tolerance": "FREE_ONLY"})
        decision = self.governor.evaluate_job(gpu)
        self.assertIsNone(decision["selected_provider"])
        self.assertTrue(any(item["outcome"] in {"INELIGIBLE_AUTH", "INELIGIBLE_COST", "INELIGIBLE_CAPABILITY", "INELIGIBLE_UNAVAILABLE"} for item in decision["eligibility"]))

    def test_blocked_preferred_provider_has_bounded_fallback(self):
        preferred = job("fallback-a", cost_tolerance="FREE_ONLY", provider_exclusions=["mac"])
        preferred.provider_exclusions = ["mac"]
        decision = self.governor.evaluate_job(preferred)
        self.assertIsNone(decision["selected_provider"])
        self.assertIsNone(self.governor.select_fallback(preferred, "mac"))

    def test_batch_group_is_proposed_not_executed(self):
        metadata = {"worker_class": "SMOKE", "environment_signature": "e", "dependency_signature": "d", "model_signature": "m", "gpu_class": "none"}
        jobs = [WorkerJob(f"batch-{i}", "SMOKE_TEST_V1", batch_metadata=metadata.copy()) for i in range(2)]
        plan = self.governor.group_batch_candidates(jobs)
        self.assertEqual(len(plan["job_ids"]), 2)
        self.assertEqual(self.governor.store.execution_history, [])

    def test_unknown_or_paid_path_does_not_become_free(self):
        paid = job("paid-a", cost_tolerance="PREAPPROVED_LOW_COST")
        decision = self.governor.evaluate_job(paid)
        modal = next(item for item in decision["eligibility"] if item["provider"] == "modal")
        self.assertEqual(modal["outcome"], "UNKNOWN")

    def test_gpu_requires_production_readiness(self):
        gpu = WorkerJob("gpu-b", "VIDEO_GENERATION", resource_requirements=ResourceRequirements(gpu_required=True), parameters={"cost_tolerance": "FREE_ONLY"})
        self.assertTrue(any("production_ready" in reason for item in self.governor.eligible_providers(gpu) for reason in item["reasons"]))

    def test_reservation_lifecycle_and_model_compatibility(self):
        item = job("reserve-a")
        reservation = self.governor.reserve_capacity(item, "mac")
        self.assertEqual(reservation.status, "ACTIVE")
        self.assertTrue(self.governor.release_reservation(reservation.reservation_id))
        self.assertEqual(model_routing_compatibility("ALPHA_REVIEW")["model"], "google/gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
