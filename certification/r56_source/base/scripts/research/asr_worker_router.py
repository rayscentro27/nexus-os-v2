"""Mechanical routing for captionless YouTube transcription.

This module is deliberately below Research orchestration.  The universal FIFO
still owns work.  This layer only checks compute availability, dispatches one
normalized audio file to Oracle, and returns a transcript or a retryable
technical failure so the caller can use the Mac fallback.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORACLE_HOST = os.environ.get("NEXUS_ORACLE_HOST", "opc@161.153.40.41")
ORACLE_KEY = Path(os.environ.get("NEXUS_ORACLE_SSH_KEY", str(Path.home() / ".ssh" / "oracle_vm")))
ORACLE_ASR_DIR = os.environ.get("NEXUS_ORACLE_ASR_DIR", "/home/opc/.runtime/asr-faster-whisper-cert")
ORACLE_HELPER = f"{ORACLE_ASR_DIR}/faster_whisper_worker.py"
ORACLE_PYTHON = f"{ORACLE_ASR_DIR}/bin/python"
ORACLE_MODEL = os.environ.get("NEXUS_ORACLE_ASR_MODEL", "tiny.en")
ORACLE_MAX_CONCURRENCY = 1
ORACLE_MIN_FREE_BYTES = int(os.environ.get("NEXUS_ORACLE_ASR_MIN_FREE_BYTES", str(2 * 1024**3)))
ORACLE_MODEL_CACHE_BYTES = int(os.environ.get("NEXUS_ORACLE_ASR_MODEL_CACHE_BYTES", str(100 * 1024**2)))
ORACLE_TEMP_MULTIPLIER = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ssh(command: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", "-i", str(ORACLE_KEY), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", ORACLE_HOST, command],
        cwd=ROOT, text=True, capture_output=True, timeout=timeout,
    )


def _scp(source: str, destination: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["scp", "-i", str(ORACLE_KEY), "-o", "BatchMode=yes", source, f"{ORACLE_HOST}:{destination}"],
        cwd=ROOT, text=True, capture_output=True, timeout=timeout,
    )


def _scp_from(source: str, destination: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["scp", "-i", str(ORACLE_KEY), "-o", "BatchMode=yes", f"{ORACLE_HOST}:{source}", destination],
        cwd=ROOT, text=True, capture_output=True, timeout=timeout,
    )


def _remote_json(command: str, timeout: int = 20) -> dict[str, Any]:
    result = _ssh(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "oracle command failed")[-800:])
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"oracle returned non-JSON health response: {result.stdout[-500:]}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("oracle returned non-object health response")
    return value


def _audio_bytes(audio_path: Path) -> int:
    try:
        return audio_path.stat().st_size
    except OSError:
        return 0


def disk_guard(audio_path: Path) -> dict[str, Any]:
    """Check Oracle disk before dispatching one audio job."""
    audio_bytes = _audio_bytes(audio_path)
    required = max(64 * 1024**2, audio_bytes * ORACLE_TEMP_MULTIPLIER) + ORACLE_MODEL_CACHE_BYTES
    command = "df -Pk / | awk 'NR==2 {print $4}'"
    result = _ssh(command)
    if result.returncode != 0:
        return {"job_allowed": False, "reason": "ORACLE_DISK_CHECK_FAILED", "error": result.stderr[-400:]}
    try:
        free_bytes = int(result.stdout.strip().splitlines()[-1]) * 1024
    except (ValueError, IndexError):
        return {"job_allowed": False, "reason": "ORACLE_DISK_CHECK_UNPARSEABLE", "raw": result.stdout[-400:]}
    allowed = free_bytes >= max(ORACLE_MIN_FREE_BYTES, required)
    return {
        "disk_free_before_bytes": free_bytes,
        "audio_bytes": audio_bytes,
        "estimated_job_disk_required_bytes": required,
        "minimum_free_disk_threshold_bytes": ORACLE_MIN_FREE_BYTES,
        "job_allowed": allowed,
        "reason": None if allowed else "INSUFFICIENT_ASR_DISK_HEADROOM",
    }


def oracle_health(audio_path: Path | None = None) -> dict[str, Any]:
    """Read-only worker health; no research relevance or AI checks."""
    try:
        health = _remote_json(
            shlex.quote(ORACLE_PYTHON) + " -c " + shlex.quote(
                "import json,shutil,subprocess; "
                "from pathlib import Path; "
                "p=Path('/home/opc/.runtime/asr-faster-whisper-cert'); "
                "ok=p.joinpath('bin/python').is_file() and p.joinpath('faster_whisper_worker.py').is_file(); "
                "mods=__import__('importlib.util').util.find_spec('faster_whisper') is not None; "
                "busy=bool([x for x in subprocess.run(['pgrep','-af','faster_whisper_worker.py'],capture_output=True,text=True).stdout.splitlines() if 'pgrep' not in x]); "
                "print(json.dumps({'ssh':True,'environment':ok,'faster_whisper':mods,'host_ffmpeg':bool(shutil.which('ffmpeg')),'busy':busy}))"
            )
        )
    except Exception as exc:  # noqa: BLE001
        return {"healthy": False, "reason": "ORACLE_UNREACHABLE", "error": str(exc)}
    guard = disk_guard(audio_path) if audio_path else {"job_allowed": True}
    healthy = bool(health.get("ssh") and health.get("environment") and health.get("faster_whisper") and not health.get("busy") and guard.get("job_allowed"))
    return {**health, **guard, "healthy": healthy, "reason": None if healthy else (guard.get("reason") or "ORACLE_ASR_ENVIRONMENT_UNHEALTHY")}


def _lock_path(job_id: str) -> str:
    safe = hashlib.sha256(job_id.encode()).hexdigest()[:24]
    return f"{ORACLE_ASR_DIR}/jobs/{safe}"


def _dispatch_oracle_unwrapped(audio_path: Path, *, job_id: str, video_id: str, audio_duration: float | None = None) -> tuple[str, dict[str, Any]]:
    """Execute one already-authorized Oracle ASR request."""
    durable_job=os.environ.get("NEXUS_DURABLE_JOB_ID")
    if not durable_job or durable_job != job_id:
        raise PermissionError("durable_job_identity_required_or_mismatched")
    estimate={"requests":1,"runtime_seconds":950,"billable":True}
    try:
        estimate["cost"]=float(os.environ["NEXUS_ORACLE_ESTIMATED_COST_PER_JOB"])
    except (KeyError,ValueError):
        pass
    health = oracle_health(audio_path)
    if not health.get("healthy"):
        raise RuntimeError(json.dumps({"status": "FAILED_RETRYABLE", "reason": health.get("reason"), "health": health}))
    remote_job = _lock_path(job_id)
    create = _ssh(f"mkdir -p {shlex.quote(ORACLE_ASR_DIR + '/jobs')} && mkdir {shlex.quote(remote_job)}")
    if create.returncode != 0:
        raise RuntimeError(json.dumps({"status": "FAILED_RETRYABLE", "reason": "ORACLE_ASR_CAPACITY_BUSY"}))
    remote_audio = f"{remote_job}/audio.wav"
    remote_transcript = f"{remote_job}/transcript.txt"
    remote_progress = f"{remote_job}/progress.json"
    remote_result = f"{remote_job}/result.json"
    local_transcript = Path(tempfile.mkstemp(prefix=f"nexus-oracle-{video_id}-", suffix=".txt")[1])
    started_at = _now()
    try:
        copied = _scp(str(audio_path), remote_audio)
        if copied.returncode != 0:
            raise RuntimeError(f"oracle audio transfer failed: {copied.stderr[-500:]}")
        command = " ".join([
            shlex.quote(ORACLE_PYTHON), shlex.quote(ORACLE_HELPER),
            shlex.quote(remote_audio), shlex.quote(remote_transcript),
            shlex.quote(remote_progress), shlex.quote(remote_result), shlex.quote(ORACLE_MODEL),
        ])
        run = _ssh(command, timeout=950)
        if run.returncode != 0:
            raise RuntimeError(json.dumps({"status": "FAILED_RETRYABLE", "reason": "ORACLE_ASR_FAILED", "stderr": run.stderr[-700:]}))
        result_copy = _scp_from(remote_result, str(local_transcript.with_suffix(".json")))
        transcript_copy = _scp_from(remote_transcript, str(local_transcript))
        if result_copy.returncode != 0 or transcript_copy.returncode != 0:
            raise RuntimeError("oracle transcript/result retrieval failed")
        payload = json.loads(local_transcript.with_suffix(".json").read_text(encoding="utf-8"))
        transcript = local_transcript.read_text(encoding="utf-8").strip()
        if not transcript:
            raise RuntimeError("oracle returned an empty transcript")
        diagnostics = {
            "status": "FULL_TRANSCRIPT", "engine": "oracle_faster_whisper", "model": ORACLE_MODEL,
            "worker_host": ORACLE_HOST, "asr_started_at": started_at,
            "audio_duration_seconds": payload.get("audio_duration_seconds") or audio_duration,
            "runtime_seconds": payload.get("runtime_seconds"), "words_written": len(transcript.split()),
            "cpu_percent_estimate": payload.get("cpu_percent_estimate"), "ram_peak_bytes": payload.get("ram_peak_bytes"),
            "disk_guard": health, "cleanup_token": {"remote_job": remote_job, "disk_free_before_bytes": health.get("disk_free_before_bytes")},
            "routing": {"primary_worker": "oracle", "fallback_worker": "mac", "reason": "certified Oracle worker healthy, idle, and within disk budget"},
        }
        diagnostics["estimated_cost"] = estimate.get("cost")
        diagnostics["actual_cost"] = estimate.get("cost")
        return transcript, diagnostics
    finally:
        try:
            local_transcript.unlink(missing_ok=True)
            local_transcript.with_suffix(".json").unlink(missing_ok=True)
        except OSError:
            pass


def dispatch_oracle(audio_path: Path, *, job_id: str, video_id: str, audio_duration: float | None = None) -> tuple[str, dict[str, Any]]:
    """Authorize, reserve, execute, reconcile and receipt one Oracle ASR job."""
    from nexus_agent_platform.provider_enforcement import execute
    durable_job=os.environ.get("NEXUS_DURABLE_JOB_ID")
    if not durable_job or durable_job != job_id:
        from nexus_agent_platform.resource_spend_governor import GovernanceDenied
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DURABLE_JOB_ID_REQUIRED_OR_MISMATCH")
    estimate={"requests":1,"runtime_seconds":950,"billable":True}
    try: estimate["cost"]=float(os.environ["NEXUS_ORACLE_ESTIMATED_COST_PER_JOB"])
    except (KeyError,ValueError): pass
    return execute("ORACLE","ASR","REMOTE_ASR",estimate,
        lambda:_dispatch_oracle_unwrapped(audio_path,job_id=job_id,video_id=video_id,audio_duration=audio_duration),
        job_id=durable_job,job_type=os.environ.get("NEXUS_JOB_TYPE","NOTEBOOKLM_RESEARCH"),
        correlation_id=os.environ.get("NEXUS_CORRELATION_ID") or durable_job,
        actual_usage=lambda result:{"requests":1,"runtime_seconds":float(result[1].get("runtime_seconds") or 0),**({"cost":estimate["cost"]} if "cost" in estimate else {})},
        external_ref=lambda result:result[1].get("cleanup_token",{}).get("remote_job"))


def cleanup_oracle_job(cleanup_token: dict[str, Any] | None) -> dict[str, Any]:
    """Delete remote audio/intermediate files after canonical readback."""
    if not cleanup_token or not cleanup_token.get("remote_job"):
        return {"cleaned": True, "files_before": 0, "files_after": 0, "bytes_reclaimed": 0}
    remote_job = str(cleanup_token["remote_job"])
    command = f"before=$(du -sb {shlex.quote(remote_job)} 2>/dev/null | awk '{{print $1}}'); files_before=$(find {shlex.quote(remote_job)} -type f 2>/dev/null | wc -l); rm -rf {shlex.quote(remote_job)}; echo $before $files_before"
    result = _ssh(command)
    before = 0
    files = 0
    if result.returncode == 0:
        parts = result.stdout.strip().split()
        if parts:
            before = int(parts[0] or 0)
        if len(parts) > 1:
            files = int(parts[1] or 0)
    return {"cleaned": result.returncode == 0, "files_before": files, "files_after": 0, "bytes_reclaimed": before}
