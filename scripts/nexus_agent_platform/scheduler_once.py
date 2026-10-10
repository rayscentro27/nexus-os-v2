#!/usr/bin/env python3
"""Short-lived durable queue scheduler. It only creates jobs and exits."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.durable_jobs import default_store
from nexus_agent_platform.job_health import persist_snapshot

def main() -> int:
    store = default_store()
    created = store.scheduler_once()
    print(json.dumps({"created": created, "health": persist_snapshot()}, separators=(",", ":")))
    return 0

if __name__ == "__main__": raise SystemExit(main())
