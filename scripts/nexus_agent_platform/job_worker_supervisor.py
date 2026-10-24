"""One-child supervisor with bounded logs and immediate exact-job exit recovery."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
MAX_STREAM_BYTES = 256 * 1024
MAX_WORKER_SECONDS = 1800


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", value):
        raise ValueError("SUPERVISION_ID_INVALID")
    return value


def _metadata_root(job_id: str) -> Path:
    from nexus_agent_platform.runtime.paths import nexus_research_state_path
    return nexus_research_state_path("runtime", "worker_supervision", _safe_id(job_id))


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix="worker-supervision-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _capture(stream, path: Path, lock: threading.Lock, env_secrets: tuple[str, ...]) -> None:
    from nexus_agent_platform.worker_lifecycle import sanitize
    written = 0
    carry = ""
    truncated = False
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("wb") as output:
        os.chmod(path, 0o600)
        while True:
            block = stream.read(4096)
            if not block:
                break
            text = carry + block.decode("utf-8", errors="replace")
            # Preserve a short overlap so a secret split across pipe reads is redacted.
            safe_end = max(0, len(text) - 512)
            complete, carry = text[:safe_end], text[safe_end:]
            sanitized = sanitize(complete, limit=len(complete) + 1)
            for secret in env_secrets:
                if secret:
                    sanitized = sanitized.replace(secret, "<redacted>")
            payload = sanitized.encode("utf-8", errors="replace")
            with lock:
                remaining = max(0, MAX_STREAM_BYTES - written)
                if remaining:
                    output.write(payload[:remaining])
                    output.flush()
                    written += min(remaining, len(payload))
                if len(payload) > remaining and not truncated:
                    marker = b"\n[OUTPUT_TRUNCATED_AT_256_KIB]\n"
                    # Reserve marker space inside, never beyond, the fixed cap.
                    marker = marker[:MAX_STREAM_BYTES]
                    if written + len(marker) > MAX_STREAM_BYTES:
                        trim = written + len(marker) - MAX_STREAM_BYTES
                        output.truncate(max(0, written - trim))
                        output.seek(0, os.SEEK_END)
                        written -= trim
                    output.write(marker)
                    truncated = True
        if carry and not truncated:
            sanitized = sanitize(carry, limit=len(carry) + 1)
            for secret in env_secrets:
                if secret:
                    sanitized = sanitized.replace(secret, "<redacted>")
            payload = sanitized.encode("utf-8", errors="replace")
            with lock:
                remaining = max(0, MAX_STREAM_BYTES - written)
                if remaining:
                    output.write(payload[:remaining])
                    output.flush()
                    written += min(remaining, len(payload))
                if len(payload) > remaining and not truncated:
                    marker = b"\n[OUTPUT_TRUNCATED_AT_256_KIB]\n"
                    marker = marker[:MAX_STREAM_BYTES]
                    if written + len(marker) > MAX_STREAM_BYTES:
                        trim = written + len(marker) - MAX_STREAM_BYTES
                        output.truncate(max(0, written - trim))
                        output.seek(0, os.SEEK_END)
                        written -= trim
                    output.write(marker)
                    truncated = True


def _exception_summary(stderr_path: Path) -> tuple[str | None, str | None]:
    from nexus_agent_platform.worker_lifecycle import sanitize
    try:
        lines = stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None, None
    for line in reversed(lines):
        if ":" in line and ("Error" in line or "Exception" in line):
            name = line.rsplit(":", 1)[0].strip().split()[-1]
            return sanitize(name, limit=100), sanitize(line, limit=500)
    return None, None


def _exact_exit_recovery(job_id: str, worker_id: str) -> dict:
    from nexus_agent_platform.durable_jobs import default_store
    from nexus_agent_platform.supabase_egress_guard import worker_cleanup_scope
    store = default_store()
    with worker_cleanup_scope(job_id, worker_id):
        job = store.get(job_id)
        if job is None:
            return {"status": "JOB_NOT_FOUND", "active_slot_released": False}
        if job.state not in {"CLAIMED", "RUNNING"} or job.claimed_by != worker_id:
            return {"status": job.state, "active_slot_released": job.state not in {"CLAIMED", "RUNNING"}}
        transitioned = store.transition(job_id, "FAILED_RETRYABLE", worker_id=worker_id,
            error_code="WORKER_EXITED_UNEXPECTEDLY",
            error_summary="Supervised worker exited while its exact job remained active.")
        return {"status": transitioned.state, "attempt_count": transitioned.attempt_count,
                "active_slot_released": transitioned.state not in {"CLAIMED", "RUNNING"}}


def supervise(job_id: str, worker_id: str, attempt: int, timeout_seconds: int = 960) -> dict:
    job_id = _safe_id(job_id)
    if not worker_id or len(worker_id) > 160 or attempt < 1:
        raise ValueError("SUPERVISION_ARGUMENT_INVALID")
    timeout_seconds = max(30, min(MAX_WORKER_SECONDS, int(timeout_seconds)))
    from nexus_agent_platform.worker_lifecycle import emit, last_stage
    root = _metadata_root(job_id) / f"attempt-{attempt}"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    stdout_path = root / "stdout.log"
    stderr_path = root / "stderr.log"
    lifecycle_path = root / "lifecycle.jsonl"
    process_path = root / "process.json"
    receipt_path = root / "exit-receipt.json"
    worker_script = ROOT / "scripts/nexus_agent_platform/job_worker_once.py"
    env = dict(os.environ)
    env["NEXUS_DURABLE_JOB_ID"] = job_id
    env["NEXUS_WORKER_ID"] = worker_id
    env["NEXUS_JOB_ATTEMPT_COUNT"] = str(attempt)
    env["NEXUS_WORKER_LIFECYCLE_PATH"] = str(lifecycle_path)
    env["NEXUS_DURABLE_EXECUTION_ID"] = f"worker-{job_id}-{attempt}"
    os.environ["NEXUS_DURABLE_JOB_ID"] = job_id
    os.environ["NEXUS_WORKER_ID"] = worker_id
    os.environ["NEXUS_JOB_ATTEMPT_COUNT"] = str(attempt)
    os.environ["NEXUS_WORKER_LIFECYCLE_PATH"] = str(lifecycle_path)
    os.environ["NEXUS_DURABLE_EXECUTION_ID"] = f"supervisor-{job_id}-{attempt}"
    secrets = tuple(value for key, value in env.items()
                    if value and any(word in key.upper() for word in ("PASSWORD", "TOKEN", "SECRET", "API_KEY", "SERVICE_ROLE_KEY")))
    start = _now()
    base = {"job_id": job_id, "worker_id": worker_id, "attempt": attempt,
            "worker_start_timestamp": start, "worker_path": str(worker_script),
            "stdout_path": str(stdout_path), "stderr_path": str(stderr_path),
            "lifecycle_path": str(lifecycle_path), "timeout_seconds": timeout_seconds}
    _write_json(process_path, {**base, "supervisor_pid": os.getpid(), "status": "STARTING"})
    process = subprocess.Popen([sys.executable, str(worker_script), "--job-id", job_id, "--worker-id", worker_id],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, close_fds=True)
    emit(job_id, "WORKER_PROCESS_STARTED", attempt=attempt, worker_id=worker_id,
         child_pid=process.pid, supervisor_pid=os.getpid())
    _write_json(process_path, {**base, "supervisor_pid": os.getpid(), "child_pid": process.pid,
                               "status": "RUNNING"})
    stream_lock = threading.Lock()
    stdout_thread = threading.Thread(target=_capture, args=(process.stdout, stdout_path, stream_lock, secrets), daemon=True)
    stderr_thread = threading.Thread(target=_capture, args=(process.stderr, stderr_path, stream_lock, secrets), daemon=True)
    stdout_thread.start(); stderr_thread.start()
    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    stdout_thread.join(timeout=10); stderr_thread.join(timeout=10)
    ended = _now()
    exit_code = int(process.returncode if process.returncode is not None else 1)
    termination_signal = signal.Signals(-exit_code).name if exit_code < 0 else None
    error_type, error_summary = _exception_summary(stderr_path)
    # Re-read this exact job after every child exit. A zero exit code alone
    # cannot prove the durable transition committed; recover only if the
    # worker still owns a CLAIMED/RUNNING row.
    try:
        recovery = _exact_exit_recovery(job_id, worker_id)
    except Exception as exc:
        recovery = {"status": "CLEANUP_FAILED", "error_type": type(exc).__name__,
                    "active_slot_released": False}
    final_stage = last_stage(lifecycle_path)
    emit(job_id, "WORKER_PROCESS_EXIT", attempt=attempt, worker_id=worker_id,
         exit_code=exit_code, termination_signal=termination_signal,
         last_lifecycle_stage=final_stage)
    metadata = {**base, "supervisor_pid": os.getpid(), "child_pid": process.pid,
        "worker_end_timestamp": ended, "exit_code": exit_code,
        "termination_signal": termination_signal, "timed_out": timed_out,
        "last_lifecycle_stage": last_stage(lifecycle_path),
        "exception_class": error_type, "exception_summary": error_summary,
        "recovery": recovery}
    _write_json(process_path, metadata)
    _write_json(receipt_path, {"job_id": job_id, "worker_id": worker_id, "attempt": attempt,
        "ended_at": ended, "exit_code": exit_code, "termination_signal": termination_signal,
        "last_lifecycle_stage": metadata["last_lifecycle_stage"],
        "exception_class": error_type, "exception_summary": error_summary,
        "recovery_state": recovery.get("status"), "receipt_type": "WORKER_SUPERVISION_EXIT"})
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--timeout-seconds", type=int, default=960)
    args = parser.parse_args()
    result = supervise(args.job_id, args.worker_id, args.attempt, args.timeout_seconds)
    print(json.dumps({"job_id": args.job_id, "exit_code": result["exit_code"],
                      "recovery_state": result["recovery"].get("status"),
                      "active_slot_released": result["recovery"].get("active_slot_released")}, separators=(",", ":")))
    return 0 if result["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
