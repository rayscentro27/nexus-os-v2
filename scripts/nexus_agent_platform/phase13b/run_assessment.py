#!/usr/bin/env python3
import json

from nexus_agent_platform.phase13b.assessment import write_phase13b_reports


if __name__ == "__main__":
    print(json.dumps(write_phase13b_reports(), indent=2, sort_keys=True))
