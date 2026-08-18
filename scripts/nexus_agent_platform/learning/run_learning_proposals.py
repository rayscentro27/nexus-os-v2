#!/usr/bin/env python3
"""Generate the Phase 12 report-backed learning proposal snapshot."""

import json

from nexus_agent_platform.learning.engine import write_learning_reports


if __name__ == "__main__":
    print(json.dumps(write_learning_reports(), indent=2, sort_keys=True))
