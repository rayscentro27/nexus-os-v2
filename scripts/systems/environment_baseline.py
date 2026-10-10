"""Create and validate a secret-free PRE_CERTIFICATION local baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nexus_agent_platform.environment_drift_monitor import collect_local_state


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ID = "nexus-pre-certification-local-20261009"


def _json_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def build_baseline(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    state = collect_local_state(repo_root)
    launch_labels = sorted(item["label"] for item in state["launch_agents"] if item.get("label"))
    pm2_path = Path.home() / ".pm2/dump.pm2"
    pm2_expected = []
    if pm2_path.is_file():
        try:
            rows = json.loads(pm2_path.read_text(encoding="utf-8"))
            pm2_expected = [row.get("name") for row in rows if isinstance(row, dict) and row.get("name")]
        except (OSError, ValueError, TypeError):
            pm2_expected = ["UNREADABLE_REQUIRES_REVIEW"]
    return {
        "BASELINE_ID": BASELINE_ID,
        "STATUS": "PRE_CERTIFICATION",
        "CERTIFIED_COMMIT": None,
        "CANONICAL_REPO": str(repo_root.resolve()),
        "CANONICAL_BRANCH": state["repository"]["branch"],
        "LOCAL_CANONICAL_COMMIT": state["repository"]["commit"],
        "CANONICAL_PYTHON": state["python_runtime"],
        "EXPECTED_LAUNCHD_LABELS": launch_labels,
        "EXPECTED_ENABLED_LAUNCHD": [],
        "EXPECTED_CRON": {
            "user_sha256": state.get("user_cron_sha256"),
            "root_sha256": state.get("root_cron_sha256"),
            "nexus_workflow_entries": 0,
        },
        "EXPECTED_PM2": {"workflow_apps": [], "saved_app_names": pm2_expected, "saved_state_sha256": state.get("pm2_saved_state_sha256")},
        "EXPECTED_HERMES_SCHEDULES": {"sha256": state.get("hermes_schedule_sha256"), "active_nexus_workflows": 0},
        "EXPECTED_OPENCLAW_SCHEDULES": {"sha256": state.get("openclaw_schedule_sha256"), "active_jobs": 0},
        "EXPECTED_LOCAL_PORTS": {"snapshot_sha256": state.get("listener_snapshot_sha256")},
        "EXPECTED_PROVIDER_CALLER_REGISTRY_HASH": _json_hash(repo_root / "reports/remediation/provider_caller_registry_20261009.json"),
        "EXPECTED_SECRET_CONSUMER_REGISTRY_HASH": _json_hash(repo_root / "reports/remediation/local_secret_consumer_registry_20261009.json"),
        "EXPECTED_ENVIRONMENTS": {
            "registry_sha256": state.get("environment_registry_sha256"),
            "scheduler": "OFF",
            "dispatcher": "OFF",
            "old_kernel": "OFF",
            "active_operator": "OFF",
        },
        "EXPECTED_RUNTIME_LIMITS": {
            "max_total_active_workers": 2,
            "max_research_workers": 1,
            "max_browser_workers": 1,
            "max_heavy_workers": 1,
            "interactive_agents": "SERIALIZED",
        },
        "EXPECTED_LOCAL_STATE": state,
        "CREATED_AT": datetime.now(timezone.utc).isoformat(),
        "CERTIFICATION_CAMPAIGN_ID": "NEXUS_STAGED_RECERTIFICATION_PENDING",
        "REMOTE_STATE": "EXTERNAL_METADATA_UNVERIFIED",
        "AUTONOMOUS_ENABLEMENT": False,
        "SECRET_VALUES_INCLUDED": False,
    }


def validate_baseline(data: dict[str, Any]) -> list[str]:
    required = (
        "BASELINE_ID", "STATUS", "CANONICAL_REPO", "CANONICAL_BRANCH", "LOCAL_CANONICAL_COMMIT",
        "CANONICAL_PYTHON", "EXPECTED_LAUNCHD_LABELS", "EXPECTED_ENABLED_LAUNCHD", "EXPECTED_CRON",
        "EXPECTED_PM2", "EXPECTED_HERMES_SCHEDULES", "EXPECTED_OPENCLAW_SCHEDULES", "EXPECTED_LOCAL_PORTS",
        "EXPECTED_PROVIDER_CALLER_REGISTRY_HASH", "EXPECTED_SECRET_CONSUMER_REGISTRY_HASH", "EXPECTED_ENVIRONMENTS",
        "EXPECTED_RUNTIME_LIMITS", "CREATED_AT", "CERTIFICATION_CAMPAIGN_ID",
    )
    missing = [key for key in required if key not in data]
    if data.get("STATUS") not in {"PRE_CERTIFICATION", "PRE_ACTIVATION_RECOVERY_BASELINE", "CERTIFIED"}:
        missing.append("STATUS_INVALID")
    if data.get("AUTONOMOUS_ENABLEMENT") is not False:
        missing.append("AUTONOMOUS_ENABLEMENT_MUST_BE_FALSE")
    if data.get("SECRET_VALUES_INCLUDED") is not False:
        missing.append("SECRET_VALUES_INCLUDED_MUST_BE_FALSE")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    payload = build_baseline(args.repo_root)
    missing = validate_baseline(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not missing, "missing": missing, "status": payload["STATUS"]}))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
