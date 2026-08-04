"""Temporal workflows for the Nexus Agent Platform."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Dict, Optional

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn
class ScheduledReportWorkflow:
    """Execute a scheduled report and deliver via Telegram."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        report_type = config.get("report_type", "system_status")
        chat_id = config.get("chat_id", "")
        token = config.get("token", "")

        # Generate report
        result = await workflow.execute_activity(
            "generate_report",
            args=[report_type],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Deliver via Telegram
        if chat_id and token:
            await workflow.execute_activity(
                "send_telegram_message",
                args=[token, chat_id, result.get("text", "")],
                start_to_close_timeout=timedelta(seconds=10),
            )

        return {"status": "completed", "report_type": report_type}


@workflow.defn
class ApprovedEmailWorkflow:
    """Send an approved email through the platform."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        to = config.get("to", "")
        subject = config.get("subject", "")
        body = config.get("body", "")

        result = await workflow.execute_activity(
            "send_email",
            args=[to, subject, body],
            start_to_close_timeout=timedelta(seconds=15),
        )

        return {"status": "sent", "to": to}


@workflow.defn
class AlphaResearchWorkflow:
    """Execute Alpha research with retry and timeout."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        query = config.get("query", "")
        max_results = config.get("max_results", 6)

        result = await workflow.execute_activity(
            "execute_alpha_research",
            args=[query, max_results],
            start_to_close_timeout=timedelta(seconds=60),
        )

        return result


@workflow.defn
class MissionRecoveryWorkflow:
    """Recover failed missions."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        mission_id = config.get("mission_id", "")

        result = await workflow.execute_activity(
            "recover_mission",
            args=[mission_id],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return result
