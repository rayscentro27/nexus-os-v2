#!/usr/bin/env python3
"""Run one bounded argv workload without inheriting Nexus credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    from secret_guard import redact
except ImportError:
    from scripts.systems.secret_guard import redact

JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
WORKLOAD_TYPES = {"video_media_analysis", "ai_model_experiment", "batch_analysis", "research_enrichment", "creative_model_workload", "resource_heavy_other"}
MAX_TIMEOUT = 21600
MAX_INPUT_BYTES = 1024 * 1024 * 1024
SAFE_ENV = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "CUDA_VISIBLE_DEVICES")


def _inside(root: Path, candidate: str) -> Path:
    p = (root / candidate).resolve()
    if p == root or root not in p.parents or Path(candidate).is_absolute() or ".." in Path(candidate).parts:
        raise ValueError("ARTIFACT_PATH_OUTSIDE_JOB_ROOT")
    return p


def validate_job(job: dict, workdir: Path) -> tuple[list[str], list[dict]]:
    if not JOB_ID_RE.fullmatch(str(job.get("job_id", ""))):
        raise ValueError("JOB_ID_INVALID")
    if not isinstance(job.get("objective"), str) or not job["objective"].strip() or len(job["objective"]) > 2000:
        raise ValueError("OBJECTIVE_INVALID")
    if job.get("workload_type") not in WORKLOAD_TYPES:
        raise ValueError("WORKLOAD_TYPE_INVALID")
    argv = job.get("command_argv")
    if not isinstance(argv, list) or not argv or len(argv) > 64 or any(not isinstance(x, str) or len(x) > 4096 for x in argv):
        raise ValueError("COMMAND_ARGV_INVALID")
    timeout = int(job.get("timeout_seconds", 0))
    if timeout < 1 or timeout > MAX_TIMEOUT:
        raise ValueError("TIMEOUT_OUT_OF_BOUNDS")
    ins = job.get("input_artifacts", [])
    if not isinstance(ins, list) or len(ins) > 100:
        raise ValueError("INPUT_ARTIFACTS_INVALID")
    checked = []
    total = 0
    for item in ins:
        path = _inside(workdir, str(item.get("path", "")))
        if path.is_symlink() or not path.is_file():
            raise ValueError("INPUT_ARTIFACT_NOT_REGULAR_FILE")
        size = path.stat().st_size
        total += size
        h = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                h.update(chunk)
        digest = h.hexdigest()
        if item.get("sha256") and item["sha256"] != digest:
            raise ValueError("INPUT_ARTIFACT_HASH_MISMATCH")
        checked.append({"path": str(path.relative_to(workdir)), "sha256": digest, "size_bytes": size})
    if total > MAX_INPUT_BYTES:
        raise ValueError("INPUT_SIZE_LIMIT")
    for rel in job.get("expected_outputs", []):
        _inside(workdir, str(rel))
    return argv, checked


def run_job(contract_path: Path, workdir: Path) -> dict:
    workdir = workdir.expanduser().resolve()
    raw = json.loads(contract_path.read_text(encoding="utf-8"))
    job = raw.get("job", raw)
    argv, inputs = validate_job(job, workdir)
    env = {key: os.environ[key] for key in SAFE_ENV if key in os.environ}
    env.update({"NEXUS_EXTERNAL_JOB_ID": job["job_id"], "NEXUS_EXTERNAL_JOB_DIR": str(workdir)})
    started = time.monotonic()
    status = "FAILED"
    returncode = None
    stdout = stderr = ""
    proc = subprocess.Popen(argv, cwd=workdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=int(job["timeout_seconds"]))
        returncode = proc.returncode
        status = "SUCCEEDED" if returncode == 0 else "FAILED"
    except subprocess.TimeoutExpired:
        status = "TIMED_OUT"
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        returncode = proc.returncode
    stdout, stderr = stdout[-4000:], stderr[-4000:]
    result = {"job_id": job["job_id"], "workload_type": job["workload_type"], "completion_status": status, "exit_code": returncode, "runtime_seconds": round(time.monotonic() - started, 3), "input_artifacts": inputs, "stdout_tail": redact(stdout), "stderr_tail": redact(stderr), "durable_nexus_state_created": False}
    out = workdir / "outputs" / "nexus_external_job_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("contract", type=Path)
    p.add_argument("--workdir", type=Path, required=True)
    a = p.parse_args()
    try:
        result = run_job(a.contract, a.workdir)
        return 0 if result["completion_status"] == "SUCCEEDED" else 1
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"completion_status": "FAILED", "error": redact(str(exc))}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
