"""Focused tests for Temporal schedule_report execution path."""

import os
import sys
import pytest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.contracts.actions import schedule_report
from nexus_agent_platform.contracts.typed import TaskSpec, ResultStatus
from nexus_agent_platform.flags import SCHEDULE_REPORT_EXECUTION_MODE, TEMPORAL_WORKFLOWS_ENABLED


class TestScheduleReportExecutionMode:
    """Test schedule_report respects SCHEDULE_REPORT_EXECUTION_MODE."""

    def test_default_mode_is_local_file(self):
        assert SCHEDULE_REPORT_EXECUTION_MODE == "local_file"

    def test_local_file_mode_creates_local_schedule(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SCHEDULE_REPORT_EXECUTION_MODE", "local_file")
        monkeypatch.setenv("TEMPORAL_WORKFLOWS_ENABLED", "false")
        monkeypatch.setattr(
            "nexus_agent_platform.contracts.actions.RECEIPTS_DIR",
            str(tmp_path / "receipts"),
        )

        exec_time = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
        result = schedule_report(
            taskspec={
                "report_definition": "process_status",
                "execution_time": exec_time,
                "timezone": "America/Phoenix",
            },
            mission_id="test-local-file",
            tenant="goclear",
        )
        assert result.status == ResultStatus.OK.value
        assert result.source.source_id == "local_file_scheduler"
        assert result.data["status"] == "scheduled"

    def test_temporal_mode_unavailable_fails_closed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SCHEDULE_REPORT_EXECUTION_MODE", "temporal")
        monkeypatch.setenv("TEMPORAL_WORKFLOWS_ENABLED", "true")

        from nexus_agent_platform.contracts import actions

        monkeypatch.setattr(actions, "RECEIPTS_DIR", str(tmp_path / "receipts"))

        async def _failing_connect(*args, **kwargs):
            raise ConnectionError("Temporal server unreachable")

        monkeypatch.setattr(actions.TemporalClient, "connect", _failing_connect)

        exec_time = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
        result = schedule_report(
            taskspec={
                "report_definition": "process_status",
                "execution_time": exec_time,
                "timezone": "America/Phoenix",
            },
            mission_id="test-unavailable",
            tenant="goclear",
        )
        assert result.status == ResultStatus.UNAVAILABLE.value
        assert "temporal" in result.error.lower() or "unreachable" in result.error.lower()

    @pytest.mark.skipif(
        os.environ.get("TEMPORAL_WORKFLOWS_ENABLED", "").lower() != "true",
        reason="Temporal server not available in test environment",
    )
    def test_temporal_mode_starts_workflow(self, monkeypatch):
        monkeypatch.setenv("SCHEDULE_REPORT_EXECUTION_MODE", "temporal")
        monkeypatch.setenv("TEMPORAL_WORKFLOWS_ENABLED", "true")

        exec_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        result = schedule_report(
            taskspec={
                "report_definition": "process_status",
                "execution_time": exec_time,
                "timezone": "America/Phoenix",
            },
            mission_id="test-temporal-workflow",
            tenant="goclear",
        )
        assert result.status == ResultStatus.OK.value
        assert result.source.source_id == "temporal_workflow"
        assert result.data["status"] == "started"
        assert "schedule_report:test-temporal-workflow" in result.data["schedule_id"]

    def test_idempotency_prevents_duplicate_local(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SCHEDULE_REPORT_EXECUTION_MODE", "local_file")
        monkeypatch.setenv("TEMPORAL_WORKFLOWS_ENABLED", "false")
        receipts_dir = tmp_path / "receipts"
        receipts_dir.mkdir()
        monkeypatch.setattr(
            "nexus_agent_platform.contracts.actions.RECEIPTS_DIR",
            str(receipts_dir),
        )

        exec_time = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
        taskspec = {
            "report_definition": "process_status",
            "execution_time": exec_time,
            "timezone": "America/Phoenix",
        }

        result1 = schedule_report(taskspec=taskspec, mission_id="test-idempotent", tenant="goclear")
        assert result1.status == ResultStatus.OK.value

        result2 = schedule_report(taskspec=taskspec, mission_id="test-idempotent", tenant="goclear")
        assert result2.status == ResultStatus.OK.value
        assert "Duplicate" in result2.warnings[0]
