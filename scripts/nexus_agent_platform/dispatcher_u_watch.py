"""Parent-side bounded U-state observer for the existing one-shot dispatcher."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from nexus_agent_platform.stability_supervisor import (
    _atomic_json, _read_process_table, capture_uninterruptible_process,
    diagnostics_root, route_recovery_event,
)

POLL_SECONDS = 0.20


def run(command: list[str]) -> int:
    if not command:
        return 64
    child = subprocess.Popen(command)
    captured_ids: set[str] = set()
    while child.poll() is None:
        rows, error = _read_process_table()
        if error is None:
            for row in rows:
                if row["pid"] != str(child.pid):
                    continue
                if "U" in row["state"].upper():
                    incident = capture_uninterruptible_process(row, rows)
                    if incident and incident["event"]["event_id"] not in captured_ids:
                        captured_ids.add(incident["event"]["event_id"])
                        try:
                            decision = route_recovery_event(incident["event"])
                        except Exception as exc:
                            decision = {"event_id": incident["event"]["event_id"], "routing_error": type(exc).__name__}
                        data = incident["artifact_data"]
                        data["supervisor"] = decision
                        _atomic_json(Path(incident["artifact"]), data)
        time.sleep(POLL_SECONDS)
    return child.returncode or 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--":
        args = args[1:]
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
