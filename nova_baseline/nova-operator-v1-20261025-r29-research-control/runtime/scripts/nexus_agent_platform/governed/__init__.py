"""Governed operating loop package.

Owns the recommend → approve → work order → policy gate → executor → telemetry
→ review chain. Trusted runtime code; Nova's permission set still has zero
general writes.
"""

from nexus_agent_platform.governed import action_registry  # noqa: F401
from nexus_agent_platform.governed import actions_api  # noqa: F401
from nexus_agent_platform.governed import approvals  # noqa: F401
from nexus_agent_platform.governed import engine  # noqa: F401
from nexus_agent_platform.governed import executors  # noqa: F401
from nexus_agent_platform.governed import persistence  # noqa: F401
from nexus_agent_platform.governed import policy_gate  # noqa: F401
from nexus_agent_platform.governed import queue  # noqa: F401
from nexus_agent_platform.governed import recommendations  # noqa: F401
from nexus_agent_platform.governed import resolution  # noqa: F401
from nexus_agent_platform.governed import work_orders  # noqa: F401