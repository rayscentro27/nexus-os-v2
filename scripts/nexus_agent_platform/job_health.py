"""Compact Systems read model for durable queue health; payloads are never read."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from nexus_agent_platform.durable_jobs import ROOT, default_store


def _launchd_status(label: str) -> str:
    """Return the loaded/disabled state without starting or modifying a job."""
    if sys.platform != "darwin":
        return "UNKNOWN"
    domain = f"gui/{os.getuid()}"
    try:
        disabled = subprocess.run(["launchctl", "print-disabled", domain], capture_output=True, text=True, timeout=3, check=False)
        match = re.search(r'"' + re.escape(label) + r'"\s*=>\s*(true|false)', disabled.stdout)
        if match and match.group(1) == "true":
            return "DISABLED"
        loaded = subprocess.run(["launchctl", "print", f"{domain}/{label}"], capture_output=True, text=True, timeout=3, check=False)
        return "ENABLED" if loaded.returncode == 0 and f"{domain}/{label} = {{" in loaded.stdout else "DISABLED"
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"

def snapshot() -> dict:
    health = default_store().health()
    counts = health.get("counts", {})
    try:
        from nexus_agent_platform.resource_spend_governor import default_store as governor_store
        governor=governor_store().summary()
    except Exception as exc:
        governor={"state":"UNAVAILABLE","error_code":type(exc).__name__}
    try:
        from nexus_agent_platform.supabase_egress_guard import snapshot as egress_snapshot
        egress = egress_snapshot()
    except Exception: egress = {}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_mode": "DURABLE_JOB_DISPATCHER",
        "old_continuous_kernel": "DISABLED",
        "scheduler": _launchd_status("com.nexus.scheduler"),
        "dispatcher": _launchd_status("com.nexus.dispatcher"),
        "ready": counts.get("READY", 0), "running": counts.get("RUNNING", 0),
        "blocked": counts.get("BLOCKED", 0), "failed_retryable": counts.get("FAILED_RETRYABLE", 0),
        "expired_leases": health.get("expired_leases", 0),
        "oldest_queued_age_seconds": health.get("oldest_queued_age_seconds", 0),
        "active_worker_count": health.get("active_worker_count", 0),
        "jobs_completed_today": health.get("jobs_completed_today", 0),
        "retry_count": health.get("retry_count", 0),
        "recent_failures": counts.get("FAILED_RETRYABLE", 0),
        "egress_incidents": int(egress.get("large_control_plane_response_count", 0)) + int(egress.get("http_522_count", 0)),
        "resource_spend_governor": governor,
    }

def persist_snapshot(path: Path = ROOT / "data/runtime/durable_job_health_latest.json") -> dict:
    value=snapshot(); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix="durable-job-health-",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w") as stream: json.dump(value,stream,separators=(",",":"))
        os.chmod(tmp,0o600); os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return value
