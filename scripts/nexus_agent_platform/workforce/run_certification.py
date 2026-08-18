#!/usr/bin/env python3
"""Generate the Phase 13 workforce certification snapshot."""

import json

from nexus_agent_platform.workforce.certification import write_workforce_reports


if __name__ == "__main__":
    print(json.dumps(write_workforce_reports(), indent=2, sort_keys=True))
