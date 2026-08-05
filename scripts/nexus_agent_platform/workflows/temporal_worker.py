"""Temporal worker for the Nexus Agent Platform.

This worker:
1. Connects to the Temporal server
2. Registers all workflows and activities
3. Polls the task queue
4. Emits heartbeats
5. Handles graceful shutdown
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import timedelta

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nexus_agent_platform.workflows.temporal_workflows import (
    ScheduledReportWorkflow,
    ApprovedEmailWorkflow,
    MissionRecoveryWorkflow,
)
from nexus_agent_platform.workflows.temporal_activities import (
    resolve_report_definition_activity,
    retrieve_fresh_report_data_activity,
    render_report_activity,
    deliver_telegram_report_activity,
    send_email_activity,
    persist_delivery_receipt_activity,
    update_nexus_mission_activity,
    emit_safe_trace_activity,
    recover_mission_activity,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("nexus-temporal-worker")

# Configuration
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "nexus-scheduled-reports")


async def main():
    """Main worker entry point."""
    log.info("Starting Nexus Temporal worker")
    log.info("  Address: %s", TEMPORAL_ADDRESS)
    log.info("  Namespace: %s", TEMPORAL_NAMESPACE)
    log.info("  Task queue: %s", TEMPORAL_TASK_QUEUE)

    try:
        from temporalio.client import Client
        from temporalio.worker import Worker
    except ImportError:
        log.error("temporalio not installed. Run: pip install temporalio")
        sys.exit(1)

    # Connect to Temporal server
    try:
        client = await Client.connect(TEMPORAL_ADDRESS)
        log.info("Connected to Temporal server")
    except Exception as exc:
        log.error("Failed to connect to Temporal server: %s", exc)
        sys.exit(1)

    # Register workflows
    workflows = [
        ScheduledReportWorkflow,
        ApprovedEmailWorkflow,
        MissionRecoveryWorkflow,
    ]

    # Register activities
    activities = [
        resolve_report_definition_activity,
        retrieve_fresh_report_data_activity,
        render_report_activity,
        deliver_telegram_report_activity,
        send_email_activity,
        persist_delivery_receipt_activity,
        update_nexus_mission_activity,
        emit_safe_trace_activity,
        recover_mission_activity,
    ]

    log.info("Registered %d workflows, %d activities", len(workflows), len(activities))

    # Create worker
    worker = Worker(
        client,
        task_queue=TEMPORAL_TASK_QUEUE,
        workflows=workflows,
        activities=activities,
        max_concurrent_activities=10,
        max_concurrent_workflow_tasks=5,
    )

    # Handle graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        log.info("Received signal %s, shutting down...", sig)
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run worker
    log.info("Worker polling task queue: %s", TEMPORAL_TASK_QUEUE)
    try:
        async with worker:
            await shutdown_event.wait()
    except Exception as exc:
        log.error("Worker failed: %s", exc)
        sys.exit(1)

    log.info("Worker stopped gracefully")


if __name__ == "__main__":
    asyncio.run(main())
