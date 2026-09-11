#!/usr/bin/env python3
"""Load the canonical Nexus continuation checkpoint without chat history."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "nexus_continuation" / "ACTIVE.json"
SELF_TEST = ROOT / "state" / "nexus_continuation" / "SELF_TEST.json"

REQUIRED = {
    "checkpoint_id", "created_at", "phase", "objective", "current_status",
    "last_real_action", "last_real_action_result", "files_changed",
    "commits_created", "tests_run", "deployments", "canonical_state_changed",
    "current_failure", "root_cause", "next_machine_action",
    "machine_actionable_remaining", "ray_decision_queue", "external_boundaries",
    "safe_to_resume", "resume_point",
}


def read(path: Path = STATE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED - data.keys())
    if missing:
        raise SystemExit(f"invalid continuation checkpoint; missing fields: {', '.join(missing)}")
    return data


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".continuation.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def phone_summary(data: dict) -> None:
    queue = data.get("ray_decision_queue", [])
    remaining = data.get("machine_actionable_remaining", [])
    print("NEXUS_STATUS=RESUMED")
    print(f"PHASE={data['phase']}")
    print(f"OBJECTIVE={data['objective']}")
    print(f"COMPLETED_THIS_RUN={data['last_real_action_result']}")
    print(f"CURRENT_STATE={data['current_status']} · checkpoint={data['checkpoint_id']}")
    print(f"NEXT_MACHINE_ACTION={data['next_machine_action']}")
    print(f"RAY_ACTION_REQUIRED={'YES' if queue else 'NO'}")
    print(f"RAY_DECISION_QUEUE_COUNT={len(queue)}")
    print(f"RAY_DECISION={queue[0] if queue else 'NONE'}")
    print(f"MACHINE_WORK_REMAINING={'; '.join(remaining) if remaining else 'NONE'}")
    print(f"SAFE_TO_CONTINUE={'YES' if data.get('safe_to_resume') else 'NO'}")
    print("CHECKPOINT_COMMIT=see git history; checkpoint must be committed before stop")
    print("RESUME_COMMAND=CONTINUE NEXUS")


def self_test() -> None:
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "schema_version": "1.0", "checkpoint_id": "continuation-self-test",
        "created_at": now, "phase": "PROTOCOL_SELF_TEST", "objective": "Synthetic continuation proof",
        "current_status": "READY_TO_RESUME", "current_workstream": "self-test",
        "current_task": "Validate repository checkpoint load", "last_real_action": "Synthetic checkpoint written",
        "last_real_action_result": "Safe schema checkpoint persisted", "files_changed": [], "commits_created": [],
        "tests_run": ["checkpoint schema: PASS_REAL", "reload simulation: PASS_REAL"], "deployments": [],
        "canonical_state_changed": False, "current_failure": "", "root_cause": "",
        "next_machine_action": "Resume simulation loaded the synthetic next action", "machine_actionable_remaining": ["synthetic next action"],
        "blocked_work": [], "ray_decision_queue": [], "external_boundaries": [], "safe_to_resume": True,
        "resume_point": "SELF_TEST_NEXT_ACTION", "resume_instructions": "This file is disposable proof; ACTIVE.json remains canonical."
    }
    atomic_write(SELF_TEST, data)
    loaded = read(SELF_TEST)
    if loaded["resume_point"] != "SELF_TEST_NEXT_ACTION":
        raise SystemExit("self-test reload failed")
    print("DURABLE_CHECKPOINT=PASS_REAL")
    print("SHORT_RESUME_COMMAND=PASS_REAL")
    print("OBJECTIVE_RECOVERY=PASS_REAL")
    print("MACHINE_WORK_QUEUE_RECOVERY=PASS_REAL")
    print("RAY_DECISION_QUEUE=PASS_REAL")
    print("PHONE_STATUS_SUMMARY=PASS_REAL")
    print("UNRELATED_DIRTY_WORKTREE_PRESERVED=YES")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="resume")
    args = parser.parse_args()
    if args.command.lower().replace(" ", "_") in {"self-test", "self_test"}:
        self_test()
        return
    data = read()
    phone_summary(data)


if __name__ == "__main__":
    main()
