"""Temporal workflow adapter — wraps Temporal behind Nexus-owned interface.

Temporal is installed as an optional dependency behind the
``TEMPORAL_WORKFLOWS_ENABLED`` flag.  When disabled, activities and
workflows run as direct function calls (no server required).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, Dict, Optional

log = logging.getLogger(__name__)

_USE_TEMPORAL = os.getenv("TEMPORAL_WORKFLOWS_ENABLED", "").lower() == "true"


class TemporalAdapter:
    """Nexus-owned wrapper around Temporal workflows.

    When Temporal is disabled, activities execute as plain async calls.
    """

    def __init__(self, agent_id: str, task_queue: str = ""):
        self.agent_id = agent_id
        self.task_queue = task_queue or f"nexus-{agent_id}"
        self._client: Any = None
        self._worker: Any = None
        self._enabled = _USE_TEMPORAL and self._temporal_available()
        self._activities: Dict[str, Callable] = {}
        self._workflows: Dict[str, Any] = {}

    @staticmethod
    def _temporal_available() -> bool:
        try:
            from temporalio.client import Client  # noqa: F401
            return True
        except ImportError:
            return False

    async def connect(self, server_url: str = "localhost:7233") -> None:
        if not self._enabled:
            log.info("Temporal disabled, using direct invocation for %s", self.agent_id)
            return
        try:
            from temporalio.client import Client
            self._client = await Client.connect(server_url)
            log.info("Connected to Temporal server for agent %s", self.agent_id)
        except Exception as exc:
            log.warning("Temporal connect failed for %s: %s — falling back to direct", self.agent_id, exc)
            self._enabled = False

    def register_activity(self, name: str, fn: Callable) -> None:
        self._activities[name] = fn
        if self._enabled:
            log.info("Registered Temporal activity %s for %s", name, self.agent_id)

    def register_workflow(self, name: str, workflow_cls: Any) -> None:
        self._workflows[name] = workflow_cls
        if self._enabled:
            log.info("Registered Temporal workflow %s for %s", name, self.agent_id)

    async def execute_activity(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an activity — via Temporal or directly."""
        activity = self._activities.get(name)
        if activity is None:
            raise ValueError(f"Unknown activity: {name}")

        if self._enabled and self._client is not None:
            return await self._client.execute_workflow(
                name, *args, task_queue=self.task_queue, **kwargs
            )
        # Direct invocation
        if asyncio.iscoroutinefunction(activity):
            return await activity(*args, **kwargs)
        return activity(*args, **kwargs)

    async def start_workflow(self, name: str, *args: Any, workflow_id: str = "",
                             **kwargs: Any) -> Any:
        if self._enabled and self._client is not None:
            handle = await self._client.start_workflow(
                name, *args, id=workflow_id, task_queue=self.task_queue, **kwargs
            )
            return await handle.result()
        # Direct invocation
        wf = self._workflows.get(name)
        if wf is None:
            raise ValueError(f"Unknown workflow: {name}")
        if hasattr(wf, "run"):
            if asyncio.iscoroutinefunction(wf.run):
                return await wf.run(*args, **kwargs)
            return wf.run(*args, **kwargs)
        if callable(wf):
            if asyncio.iscoroutinefunction(wf):
                return await wf(*args, **kwargs)
            return wf(*args, **kwargs)
        raise ValueError(f"Workflow {name} is not callable")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def connected(self) -> bool:
        return self._client is not None
