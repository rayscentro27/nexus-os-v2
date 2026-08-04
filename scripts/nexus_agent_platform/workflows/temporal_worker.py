"""Temporal worker — runs registered workflows and activities."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import timedelta

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

log = logging.getLogger("nexus_agent_platform.temporal_worker")

TEMPORAL_URL = os.getenv("TEMPORAL_URL", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = "nexus-agent-platform"


async def main():
    try:
        from temporalio.client import Client
        from temporalio.worker import Worker
    except ImportError:
        log.error("temporalio not installed")
        return

    # Import workflows
    from nexus_agent_platform.workflows.temporal_workflows import (
        ScheduledReportWorkflow,
        ApprovedEmailWorkflow,
        AlphaResearchWorkflow,
        MissionRecoveryWorkflow,
    )

    client = await Client.connect(TEMPORAL_URL, namespace=TEMPORAL_NAMESPACE)
    log.info("Connected to Temporal at %s", TEMPORAL_URL)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            ScheduledReportWorkflow,
            ApprovedEmailWorkflow,
            AlphaResearchWorkflow,
            MissionRecoveryWorkflow,
        ],
        activities=[],
    )

    log.info("Starting Temporal worker on queue %s", TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
