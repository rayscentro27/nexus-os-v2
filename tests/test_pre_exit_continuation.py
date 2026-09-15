import unittest

from scripts.nexus_agent_platform.pre_exit_continuation import (
    BlockerRecord,
    assert_safe_to_stop,
    pre_exit_state_reload,
)


def blocker(valid=True):
    return BlockerRecord(
        blocker_id="penpot-auth",
        blocker_type="HUMAN_AUTHENTICATION",
        created_at="2026-09-14T00:00:00+00:00",
        last_verified_at="2026-09-14T00:00:00+00:00",
        evidence="session unavailable",
        revalidation_method="authenticated browser session probe",
        revalidation_interval_seconds=300,
        currently_valid=valid,
        exact_action="Authenticate Penpot",
    )


def reload(*, rows=(), tasks=(), work=False, ray="Authenticate Penpot"):
    return pre_exit_state_reload(
        loaders={"goals": lambda: {"active": True}, "workers": lambda: {"penpot": "CONNECTED"}},
        blockers=rows,
        blocker_verifier=lambda row: (row.currently_valid, "live proof"),
        background_tasks=tasks,
        background_waiter=lambda task: {"state": "COMPLETED", "result": "resolved"},
        machine_work_probe=lambda state: work,
        requested_ray_action=ray,
    )


class PreExitContinuationTests(unittest.TestCase):
    def test_valid_blocker_legitimately_stops(self):
        result = reload(rows=[blocker(True)])
        self.assertTrue(result["ray_action_required"])

    def test_blocker_resolved_before_exit_continues(self):
        result = reload(rows=[blocker(False)])
        self.assertFalse(result["ray_action_required"])
        self.assertTrue(result["blocker_superseded"])

    def test_background_task_resolves_blocker_and_continues(self):
        result = reload(rows=[blocker(True)], tasks=[{"task_id": "browser", "state": "RUNNING"}])
        self.assertFalse(result["ray_action_required"])
        self.assertEqual(result["background_result_barrier"][0]["state"], "COMPLETED")

    def test_stale_human_required_is_revalidated(self):
        result = reload(rows=[blocker(False)], ray="Authenticate Penpot")
        self.assertEqual(result["blocker_revalidation"], "PASS")
        self.assertFalse(result["ray_action_required"])

    def test_local_blocker_does_not_stop_other_machine_work(self):
        result = reload(rows=[blocker(True)], work=True)
        self.assertFalse(result["ray_action_required"])
        with self.assertRaises(RuntimeError):
            assert_safe_to_stop(result)

    def test_newer_receipt_supersedes_blocker(self):
        result = reload(rows=[blocker(False)], tasks=[{"task_id": "receipt", "state": "COMPLETED"}])
        self.assertTrue(result["blocker_superseded"])
        self.assertTrue(result["codex_required_to_continue"])

    def test_connector_available_after_earlier_failure_continues(self):
        result = reload(rows=[blocker(False)], tasks=[{"task_id": "connector", "state": "COMPLETED"}])
        self.assertFalse(result["ray_action_required"])
        self.assertEqual(result["next_action"], "CONTINUE_FROM_RELOADED_STATE")


if __name__ == "__main__":
    unittest.main()
