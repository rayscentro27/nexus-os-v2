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


def _load_canonical_runtime() -> dict[str, bool]:
    """Load canonical runtime env and return presence report."""
    runtime_env = "/Users/raymonddavis/.config/nexus/runtime.env"
    if os.path.isfile(runtime_env):
        try:
            with open(runtime_env) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip().removeprefix("export ").strip()
                    if key and not os.environ.get(key):
                        os.environ[key] = value.strip().strip("'").strip('"')
        except Exception:
            pass

    report = {
        "supabase": bool(os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")),
        "supabase_service_key": bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY")),
        "telegram_bot_token": bool(os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("NEXUS_TELEGRAM_BOT_TOKEN")),
        "telegram_allowed_chat_ids": bool(os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS")),
        "langfuse": os.environ.get("LANGFUSE_TRACING_ENABLED", "").lower() == "true",
    }
    return report


# Configuration
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "nexus-scheduled-reports")


async def main():
    """Main worker entry point."""
    presence = _load_canonical_runtime()
    log.info("Starting Nexus Temporal worker")
    log.info("  Address: %s", TEMPORAL_ADDRESS)
    log.info("  Namespace: %s", TEMPORAL_NAMESPACE)
    log.info("  Task queue: %s", TEMPORAL_TASK_QUEUE)
    log.info("  Runtime presence: %s", presence)

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
