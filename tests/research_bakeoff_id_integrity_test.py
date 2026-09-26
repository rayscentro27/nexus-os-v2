import json
import tempfile
import unittest
from pathlib import Path

from scripts.research.run_three_mode_architecture_bakeoff import (
    completed_experiment_state,
    refuse_completed_experiment,
)


class BakeoffExperimentIdIntegrityTests(unittest.TestCase):
    def test_completed_state_is_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "experiment_state.json"
            state_path.write_text(
                json.dumps({"status": "COMPLETED", "actual_end_at": "2026-09-26T17:38:05Z"}),
                encoding="utf-8",
            )
            self.assertIsNotNone(completed_experiment_state(state_path))
            self.assertTrue(refuse_completed_experiment(state_path))

    def test_running_state_can_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "experiment_state.json"
            state_path.write_text(json.dumps({"status": "RUNNING"}), encoding="utf-8")
            self.assertIsNone(completed_experiment_state(state_path))
            self.assertFalse(refuse_completed_experiment(state_path))


if __name__ == "__main__":
    unittest.main()
