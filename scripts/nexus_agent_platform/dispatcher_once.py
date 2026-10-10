#!/usr/bin/env python3
"""Short-lived bounded dispatcher; department execution happens in children."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.durable_jobs import default_store, dispatch_once
from nexus_agent_platform.job_health import persist_snapshot

def main() -> int:
    store = default_store()
    store.recover_expired()
    result = dispatch_once(store)
    print(json.dumps({**result, "health": persist_snapshot()}, separators=(",", ":")))
    return 0

if __name__ == "__main__": raise SystemExit(main())
