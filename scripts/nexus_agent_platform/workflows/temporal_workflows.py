"""Temporal workflows for the Nexus Agent Platform.

All workflows must be deterministic:
- No direct Supabase calls
- No direct Telegram API calls
- No direct filesystem writes
- No random UUIDs outside workflow APIs
- No non-deterministic time calls

All side effects run as activities.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    pass


def _make_workflow_id(mission_id: str, capability_id: str) -> str:
    """Generate deterministic workflow ID."""
    return f"{capability_id}:{mission_id}"


@workflow.defn
class ScheduledReportWorkflow:
    """Execute a scheduled report and deliver via Telegram.
    
    Workflow input must contain only serializable, non-secret values.
    All side effects run as activities.
    """

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        mission_id = config.get("mission_id", "")
        report_definition = config.get("report_definition", "")
        scheduled_time = config.get("scheduled_time", "")
        timezone_str = config.get("timezone", "America/Phoenix")
        delivery_channel = config.get("delivery_channel", "telegram")
        delivery_target = config.get("delivery_target", "")
        idempotency_key = config.get("idempotency_key", "")
        trace_id = config.get("trace_id", "")

        # Wait until scheduled time if provided
        if scheduled_time:
            try:
                from datetime import datetime, timezone, timedelta
                target = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
                now = workflow.now()
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                delay = (target - now).total_seconds()
                if delay > 0:
                    await workflow.sleep(timedelta(seconds=delay))
            except Exception:
                pass

        # Step 1: Resolve report definition
        report_def = await workflow.execute_activity(
            "resolve_report_definition_activity",
            args=[report_definition],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 2: Retrieve fresh report data
        report_data = await workflow.execute_activity(
            "retrieve_fresh_report_data_activity",
            args=[report_def],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 3: Render report
        rendered = await workflow.execute_activity(
            "render_report_activity",
            args=[report_data, report_def],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 4: Deliver via Telegram
        delivery_result = await workflow.execute_activity(
            "deliver_telegram_report_activity",
            args=[delivery_target, rendered],
            start_to_close_timeout=timedelta(seconds=15),
        )

        # Step 5: Persist delivery receipt
        await workflow.execute_activity(
            "persist_delivery_receipt_activity",
            args=[mission_id, delivery_result, idempotency_key],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 6: Update mission
        await workflow.execute_activity(
            "update_nexus_mission_activity",
            args=[mission_id, "completed"],
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Step 7: Emit trace
        await workflow.execute_activity(
            "emit_safe_trace_activity",
            args=[trace_id, "completed"],
            start_to_close_timeout=timedelta(seconds=5),
        )

        return {
            "status": "completed",
            "mission_id": mission_id,
            "report_definition": report_definition,
            "delivered_at": workflow.now().isoformat(),
        }


@workflow.defn
class ApprovedEmailWorkflow:
    """Send an approved email through the platform."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        mission_id = config.get("mission_id", "")
        recipient = config.get("recipient", "")
        subject = config.get("subject", "")
        body = config.get("body", "")
        idempotency_key = config.get("idempotency_key", "")

        result = await workflow.execute_activity(
            "send_email_activity",
            args=[recipient, subject, body, idempotency_key],
            start_to_close_timeout=timedelta(seconds=30),
        )

        await workflow.execute_activity(
            "persist_delivery_receipt_activity",
            args=[mission_id, result, idempotency_key],
            start_to_close_timeout=timedelta(seconds=10),
        )

        return {"status": "sent", "mission_id": mission_id}


@workflow.defn
class MissionRecoveryWorkflow:
    """Recover failed missions."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        mission_id = config.get("mission_id", "")

        result = await workflow.execute_activity(
            "recover_mission_activity",
            args=[mission_id],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return result
