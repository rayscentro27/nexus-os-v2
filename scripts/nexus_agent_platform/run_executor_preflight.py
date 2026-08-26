"""Run the safe Nexus executor preflight and print its evidence matrix."""
from __future__ import annotations

import json

from nexus_agent_platform.capability_broker import run_safe_canaries


if __name__ == "__main__":
    print(json.dumps(run_safe_canaries(), indent=2))
