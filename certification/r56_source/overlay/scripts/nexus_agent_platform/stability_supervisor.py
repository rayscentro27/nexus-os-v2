"""Bounded host incident capture and deterministic Stability Supervisor v1.

This module observes process state and routes durable evidence. It never signals,
restarts, repairs, terminates, or invokes an LLM/provider.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import re
import select
import shlex
import sqlite3
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MAX_CAPTURE_SECONDS = 3.0
MAX_OPEN_FILES_RECORDED = 32
MAX_LOG_LINES = 24
MAX_ARTIFACT_BYTES = 64 * 1024
MAX_PS_OUTPUT_BYTES = 256 * 1024
_NEXUS_MARKERS = (
    "dispatcher_once.py", "job_worker_once.py", "run_dispatched_research_job.py",
    "uvicorn services.nexus_mcp", "nexus-os-v2-canonical",
)
_PATH_MARKERS = (
    ".nexus", "nexus-os-v2-canonical", "research_runtime_states.jsonl",
    "research_execution_jobs.jsonl", "governor", "receipt", ".sqlite", ".db",
    ".log", "pipe", "unix",
)


def diagnostics_root() -> Path:
    configured = os.environ.get("NEXUS_RUNTIME_DIAGNOSTICS_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    state_root = os.environ.get("NEXUS_RESEARCH_STATE_ROOT")
    if state_root:
        return Path(state_root).expanduser().resolve() / "diagnostics" / "runtime_events"
    repo = Path(os.environ.get("NEXUS_REPO_ROOT", Path(__file__).resolve().parents[2]))
    return repo / "data" / "diagnostics" / "runtime_events"


class SupervisorStateStore:
    """Small durable SQLite index for incident, recovery-job, and BLOCKED_BY state."""
    def __init__(self, path: Path | None = None):
        self.path = path or diagnostics_root().parent / "stability_supervisor.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=2) as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS incidents(
              event_id TEXT PRIMARY KEY, event_json TEXT NOT NULL, status TEXT NOT NULL,
              artifact_ref TEXT, recovery_job_id TEXT NOT NULL, created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recovery_jobs(
              recovery_job_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL, plan_state TEXT NOT NULL, execution_state TEXT NOT NULL,
              created_at TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES incidents(event_id)
            );
            CREATE TABLE IF NOT EXISTS objective_blocks(
              objective_id TEXT NOT NULL, event_id TEXT NOT NULL, project_id TEXT, job_id TEXT,
              case_id TEXT, department TEXT NOT NULL DEFAULT '', recovery_job_id TEXT NOT NULL, block_reason TEXT NOT NULL,
              blocked_at TEXT NOT NULL, resume_criteria TEXT NOT NULL, status TEXT NOT NULL,
              relationship_type TEXT NOT NULL DEFAULT 'BLOCKED_BY',
              PRIMARY KEY(objective_id,event_id), FOREIGN KEY(event_id) REFERENCES incidents(event_id)
            );
            CREATE INDEX IF NOT EXISTS objective_blocks_job_idx ON objective_blocks(job_id,status);
            CREATE TABLE IF NOT EXISTS supervisor_flags(flag TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS host_reconciliations(
              event_id TEXT PRIMARY KEY, observed_at TEXT NOT NULL, observation_json TEXT NOT NULL,
              FOREIGN KEY(event_id) REFERENCES incidents(event_id)
            );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(objective_blocks)")}
            if "department" not in columns:
                db.execute("ALTER TABLE objective_blocks ADD COLUMN department TEXT NOT NULL DEFAULT ''")
            if "relationship_type" not in columns:
                db.execute("ALTER TABLE objective_blocks ADD COLUMN relationship_type TEXT NOT NULL DEFAULT 'BLOCKED_BY'")

    def register_event(self, event: dict[str, Any], *, artifact_ref: str | None = None,
                       title: str = "Systems recovery diagnosis") -> dict[str, Any]:
        event_id = str(event["event_id"])
        now = datetime.now(timezone.utc).isoformat()
        recovery_job_id = "sysjob_" + hashlib.sha256(event_id.encode()).hexdigest()[:24]
        is_global_host = event.get("failure_domain") == "SYSTEMS_HOST"
        with sqlite3.connect(self.path, timeout=2) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO incidents VALUES(?,?,?,?,?,?,?)",
                       (event_id, json.dumps(event, separators=(",", ":")), "ACTIVE",
                        artifact_ref, recovery_job_id, now, now))
            db.execute("INSERT OR IGNORE INTO recovery_jobs VALUES(?,?,?,?,?,?)",
                       (recovery_job_id, event_id, title, "PLANNED",
                        "BLOCKED_FOR_EXECUTION" if is_global_host else "ELIGIBLE", now))
            objective_id = event.get("objective_id")
            if objective_id:
                db.execute("""INSERT OR IGNORE INTO objective_blocks
                    (objective_id,event_id,project_id,job_id,case_id,department,recovery_job_id,block_reason,blocked_at,resume_criteria,status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (objective_id, event_id, event.get("project_id"), event.get("job_id"),
                     event.get("case_id"), event.get("department", ""), recovery_job_id,
                     event.get("error_code", "RECOVERY_REQUIRED"), now,
                     json.dumps(event.get("resume_criteria", [])), "BLOCKED"))
            db.commit()
            row = db.execute("SELECT plan_state,execution_state FROM recovery_jobs WHERE recovery_job_id=?",
                             (recovery_job_id,)).fetchone()
        return {"event_id": event_id, "recovery_job_id": recovery_job_id,
                "plan_state": row[0], "execution_state": row[1],
                "objective_id": objective_id}

    def add_dependent_objective(self, event_id: str, *, objective_id: str,
                                project_id: str | None = None, job_id: str | None = None,
                                case_id: str | None = None, department: str = "",
                                reason: str = "HOST_RECOVERY_DEPENDENCY") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path, timeout=2) as db:
            db.execute("PRAGMA foreign_keys=ON")
            job = db.execute("SELECT recovery_job_id FROM recovery_jobs WHERE event_id=?", (event_id,)).fetchone()
            if not job:
                raise KeyError("RECOVERY_EVENT_NOT_FOUND")
            db.execute("""INSERT OR IGNORE INTO objective_blocks
                (objective_id,event_id,project_id,job_id,case_id,department,recovery_job_id,block_reason,blocked_at,resume_criteria,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (objective_id, event_id, project_id, job_id, case_id, department, job[0], reason, now,
                 json.dumps(["HOST_HEALTH_GATE_PASS", "RUNTIME_CONTRACT_PASS"]), "BLOCKED"))
            db.commit()

    def active_global_host_incidents(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path, timeout=2) as db:
            rows = db.execute("SELECT event_id,event_json,status FROM incidents WHERE status='ACTIVE'").fetchall()
        return [{"event_id": row[0], "event": json.loads(row[1]), "status": row[2]}
                for row in rows if json.loads(row[1]).get("failure_domain") == "SYSTEMS_HOST"]

    def incident(self, event_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.path, timeout=2) as db:
            row = db.execute("SELECT event_json,status,recovery_job_id,artifact_ref FROM incidents WHERE event_id=?",
                             (event_id,)).fetchone()
        if not row:
            return None
        return {"event": json.loads(row[0]), "status": row[1], "recovery_job_id": row[2], "artifact_ref": row[3]}

    def blocks_for_event(self, event_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path, timeout=2) as db:
            rows = db.execute("SELECT objective_id,project_id,job_id,case_id,department,recovery_job_id,status,relationship_type FROM objective_blocks WHERE event_id=?",
                              (event_id,)).fetchall()
        keys = ("objective_id", "project_id", "job_id", "case_id", "department", "recovery_job_id", "status", "relationship_type")
        return [dict(zip(keys, row)) for row in rows]

    def mark_resolved(self, event_id: str, *, resume_statuses: dict[str, str] | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path, timeout=2) as db:
            db.execute("UPDATE incidents SET status='RESOLVED',updated_at=? WHERE event_id=?", (now, event_id))
            db.execute("UPDATE recovery_jobs SET execution_state='ELIGIBLE' WHERE event_id=?", (event_id,))
            for objective_id, status in (resume_statuses or {}).items():
                db.execute("UPDATE objective_blocks SET status=? WHERE event_id=? AND objective_id=?",
                           (status, event_id, objective_id))
            db.commit()

    def reconcile_host_incident(self, event_id: str, observation: dict[str, Any]) -> None:
        """Resolve an active host incident only after the caller supplies fresh passing evidence."""
        encoded = json.dumps(observation, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 4096 or observation.get("result") != "HEALTHY":
            raise ValueError("HOST_RECONCILIATION_EVIDENCE_INVALID")
        with sqlite3.connect(self.path, timeout=2) as db:
            row = db.execute("SELECT event_json,status FROM incidents WHERE event_id=?", (event_id,)).fetchone()
            if not row or json.loads(row[0]).get("failure_domain") != "SYSTEMS_HOST":
                raise KeyError("GLOBAL_HOST_INCIDENT_NOT_FOUND")
            db.execute("INSERT INTO host_reconciliations VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET "
                       "observed_at=excluded.observed_at,observation_json=excluded.observation_json",
                       (event_id, str(observation["observed_at"]), encoded))
            db.execute("UPDATE incidents SET status='RESOLVED',updated_at=? WHERE event_id=? AND status='ACTIVE'",
                       (str(observation["observed_at"]), event_id))
            db.commit()

    def set_flag(self, flag: str, value: bool) -> None:
        with sqlite3.connect(self.path, timeout=2) as db:
            db.execute("INSERT INTO supervisor_flags VALUES(?,?,?) ON CONFLICT(flag) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                       (flag, json.dumps(bool(value)), datetime.now(timezone.utc).isoformat()))
            db.commit()

    def get_flag(self, flag: str, default: bool = False) -> bool:
        with sqlite3.connect(self.path, timeout=2) as db:
            row = db.execute("SELECT value FROM supervisor_flags WHERE flag=?", (flag,)).fetchone()
        return json.loads(row[0]) if row else default


def get_host_execution_gate(*, state_store: SupervisorStateStore | None = None,
                            process_rows: list[dict[str, str]] | None = None,
                            filesystem_responsive: bool | None = None,
                            governor_state: str | None = None,
                            process_samples: list[list[dict[str, str]]] | None = None,
                            state_v2_readiness: dict[str, Any] | None = None,
                            active_release: tuple[str | None, bool] | None = None) -> dict[str, Any]:
    """Use fresh bounded health evidence; retain incidents as history and reconcile explicitly."""
    state_store = state_store or SupervisorStateStore()
    reasons: list[str] = []
    evidence: list[str] = []
    incidents = state_store.active_global_host_incidents()
    if process_samples is None:
        if process_rows is not None:
            process_samples = [process_rows]
        else:
            process_samples = []
            for index in range(3):
                rows, error = _read_process_table()
                if error:
                    process_samples.append([])
                    reasons.append("PROCESS_STATE_UNAVAILABLE")
                else:
                    process_samples.append(rows)
                if index < 2:
                    time.sleep(0.5)
    if not process_samples:
        reasons.append("PROCESS_STATE_UNAVAILABLE")
    elif len(process_samples) < 3:
        reasons.append("PROCESS_OBSERVATION_INCOMPLETE")
    if filesystem_responsive is None:
        filesystem_responsive, fs_reasons = _bounded_filesystem_probe(_RECOVERY_CERTIFICATION_PATHS)
        reasons.extend(fs_reasons)
    u_by_sample = [{str(row.get("pid")): row for row in rows
                    if "U" in str(row.get("state", "")).upper() and row.get("pid")}
                   for rows in process_samples]
    common_u = set.intersection(*(set(rows) for rows in u_by_sample)) if u_by_sample else set()
    persistent_rows = [u_by_sample[-1][pid] for pid in sorted(common_u)]
    if filesystem_responsive is False:
        reasons.append("FILESYSTEM_STALL")
    if governor_state and governor_state.upper() in {"BLOCKED", "DEGRADED", "UNAVAILABLE"}:
        reasons.append(f"RESOURCE_GOVERNOR_{governor_state.upper()}")
    nexus_persistent = [row for row in persistent_rows if any(
        marker in str(row.get("command", "")).lower() for marker in _NEXUS_MARKERS)]
    families = {Path(str(row.get("command", "")).split(" ", 1)[0]).name for row in persistent_rows}
    persistent_degradation = bool(nexus_persistent or len(families) >= 2 or
                                  persistent_rows and (filesystem_responsive is False or
                                  (governor_state or "").upper() in {"BLOCKED", "DEGRADED", "UNAVAILABLE"}))
    if persistent_degradation:
        reasons.append("PERSISTENT_HOST_IO_DEGRADED")
        evidence.extend(f"pid:{row['pid']}:{str(row.get('command',''))[:120]}" for row in persistent_rows[:8])
    elif not reasons and incidents:
        observation = {"observed_at": datetime.now(timezone.utc).isoformat(),
                       "sample_count": len(process_samples), "persistent_u_count": 0,
                       "filesystem_responsive": filesystem_responsive,
                       "governor_state": governor_state or "NOT_AVAILABLE",
                       "result": "HEALTHY"}
        for row in incidents:
            state_store.reconcile_host_incident(row["event_id"], observation)
            evidence.append(f"reconciled:{row['event_id']}")
    host_blocked = bool(reasons)
    readiness = evaluate_state_v2_readiness(state_v2_readiness, active_release=active_release)
    if readiness["status"] != "READY":
        reasons.append("STATE_V2_READINESS_UNKNOWN" if readiness["status"] == "UNKNOWN"
                       else "STATE_V2_NOT_READY")
    return {"host_health": "BLOCKED" if host_blocked else "HEALTHY",
            "heavy_work_allowed": not host_blocked,
            "research_execution_allowed": not host_blocked and readiness["status"] == "READY",
            "build_allowed": not host_blocked,
            "migration_allowed": not host_blocked,
            "reason_codes": sorted(set(reasons)),
            "evidence_references": list(dict.fromkeys(evidence)),
            "state_v2_readiness": readiness}


STATE_V2_READINESS_SCHEMA = "nexus.state-v2-readiness.v1"
STATE_V2_REQUIRED_CHECKS = (
    "active_release_supports_state_v2", "migration_applied", "project_index_valid_ready",
    "job_index_valid_ready", "legacy_normal_reads_disabled", "legacy_normal_writes_disabled",
    "legacy_fsync_disabled", "authoritative_backend_available", "hot_state_seed_verified",
    "cutover_verified", "legacy_not_required_for_recovery",
)


_RELEASE_MANIFEST_NAME = re.compile(r"^R([0-9]+)_RELEASE_MANIFEST\.json$")
_MAX_RELEASE_MANIFESTS = 8
_MAX_RELEASE_PAYLOAD_FILES = 1024
_MAX_RELEASE_PAYLOAD_FILE_BYTES = 8 * 1024 * 1024
_MAX_RELEASE_PAYLOAD_BYTES = 64 * 1024 * 1024


def _release_root_for_readiness() -> Path | None:
    """Resolve only the explicitly active release or this module's immutable root.

    A source checkout is deliberately not a release root. In particular, this
    function never searches the canonical worktree or guesses the newest release.
    """
    configured = os.environ.get("NEXUS_ACTIVE_RESEARCH_RELEASE", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_dir():
            candidate = Path.home() / ".nexus" / "releases" / configured
        try:
            candidate = candidate.resolve(strict=True)
        except OSError:
            return None
        return candidate if candidate.is_dir() and (candidate / "RELEASE_MANIFEST.sha256").is_file() else None
    for parent in Path(__file__).resolve().parents:
        if (parent / "RELEASE_MANIFEST.sha256").is_file():
            return parent
    return None


def _validated_active_release_manifest(root: Path) -> dict[str, Any] | None:
    """Validate the one manifest belonging to *root* using bounded root-level reads."""
    try:
        names = sorted(path for path in root.glob("R*_RELEASE_MANIFEST.json")
                       if path.is_file() and _RELEASE_MANIFEST_NAME.fullmatch(path.name))
        if not names or len(names) > _MAX_RELEASE_MANIFESTS:
            return None
        # A layered release can retain its declared base manifest (R53 retains
        # R52). Only the manifest whose release_id matches this directory is an
        # active candidate; duplicate claims for that identity are ambiguous.
        parsed: list[tuple[Path, dict[str, Any]]] = []
        for path in names:
            if path.stat().st_size > 1024 * 1024:
                return None
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                return None
            parsed.append((path, value))
        matching = [(path, value) for path, value in parsed
                    if value.get("release_id") == root.name]
        if len(matching) != 1:
            return None
        manifest_path, manifest = matching[0]
        expected_name = f"R{root.name.rsplit('-r', 1)[-1]}_RELEASE_MANIFEST.json"
        if manifest_path.name != expected_name:
            return None
        # Any additional root-level manifest must be the declared base release,
        # not a second or unrelated release that could make identity ambiguous.
        extras = [(path, value) for path, value in parsed if path != manifest_path]
        if any(value.get("release_id") != manifest.get("base_release_id") for _, value in extras):
            return None
        payload = manifest.get("payload_sha256")
        if not isinstance(payload, dict) or not payload or len(payload) > _MAX_RELEASE_PAYLOAD_FILES:
            return None
        total_bytes = 0
        for relative, expected_hash in payload.items():
            rel = Path(str(relative))
            if rel.is_absolute() or ".." in rel.parts or not isinstance(expected_hash, str):
                return None
            target = root / rel
            resolved = target.resolve(strict=True)
            if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
                return None
            size = resolved.stat().st_size
            total_bytes += size
            if size > _MAX_RELEASE_PAYLOAD_FILE_BYTES or total_bytes > _MAX_RELEASE_PAYLOAD_BYTES:
                return None
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if digest != expected_hash:
                return None
        metadata_path = root / "BUILD_METADATA.json"
        if not metadata_path.is_file() or metadata_path.stat().st_size > 64 * 1024:
            return None
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("release_id") != root.name:
            return None
        expected_metadata_hash = manifest.get("build_metadata_sha256")
        if (expected_metadata_hash and hashlib.sha256(metadata_path.read_bytes()).hexdigest()
                != expected_metadata_hash):
            return None
        for identity_field in ("base_release_id", "overlay_release_id", "source_commit"):
            manifest_value = manifest.get(identity_field)
            metadata_value = metadata.get(identity_field)
            if (manifest_value is not None and metadata_value is not None
                    and manifest_value != metadata_value):
                return None
        if ("runtime_file_count" in metadata
                and int(metadata["runtime_file_count"]) != len(payload)):
            return None
        if ("payload_file_count" in metadata
                and int(metadata["payload_file_count"]) != len(payload)):
            return None
        if ("runtime_file_count" in manifest
                and int(manifest["runtime_file_count"]) != len(payload)):
            return None
        cert = manifest.get("certification") or metadata.get("certification") or {}
        metadata_cert = metadata.get("certification") or {}
        if (cert.get("result") != "PASS"
                or metadata_cert.get("result", "PASS") != "PASS"
                or ("result" in manifest.get("certification", {})
                    and manifest["certification"]["result"] != metadata_cert.get("result"))):
            return None
        for count_key in ("tests", "failures", "errors", "skipped"):
            if (count_key in cert and count_key in metadata_cert
                    and cert[count_key] != metadata_cert[count_key]):
                return None
        # Newer composed releases may declare State v2 in the manifest; older
        # layered releases use the bounded State v2 runtime contract instead.
        capabilities = manifest.get("capabilities", [])
        supports_state_v2 = "state_v2" in capabilities
        if not supports_state_v2:
            contract_path = root / "STATE_V2_RELEASE_CONTRACT.json"
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                supports_state_v2 = (contract.get("STATE_V2_RUNTIME_CERTIFICATION") == "PASS"
                                     and contract.get("LEGACY_LEDGER_REQUIRED") == "NO")
            except (OSError, ValueError, TypeError):
                supports_state_v2 = False
        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        # R55+ sidecars pin the release manifest directly. Older release sidecars
        # inventory payload files; in either format, a matching manifest entry
        # must agree when present.
        sidecar = root / "RELEASE_MANIFEST.sha256"
        if not sidecar.is_file() or sidecar.stat().st_size > 256 * 1024:
            return None
        for line in sidecar.read_text(encoding="utf-8").splitlines():
            fields = line.strip().split(None, 1)
            if len(fields) == 2 and Path(fields[1].strip().lstrip("./")).name == manifest_path.name:
                if fields[0] != manifest_sha:
                    return None
                break
        return {"manifest": manifest, "supports_state_v2": supports_state_v2}
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return None


def _active_state_v2_release() -> tuple[str | None, bool]:
    root = _release_root_for_readiness()
    if root is None:
        return None, False
    validated = _validated_active_release_manifest(root)
    if validated is None:
        return None, False
    return str(validated["manifest"].get("release_id") or "") or None, bool(validated["supports_state_v2"])


def evaluate_state_v2_readiness(record: dict[str, Any] | None = None, *,
                                active_release: tuple[str | None, bool] | None = None) -> dict[str, Any]:
    """Validate a small durable readiness attestation; never infer readiness from build metadata."""
    if record is None:
        path = diagnostics_root().parent / "state_v2_runtime_readiness.json"
        try:
            if not path.is_file() or path.stat().st_size > 16 * 1024:
                return {"status": "UNKNOWN", "reason": "READINESS_RECORD_MISSING_OR_OVERSIZE",
                        "source": str(path)}
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"status": "UNKNOWN", "reason": "READINESS_RECORD_UNREADABLE",
                    "source": str(path)}
    if not isinstance(record, dict) or record.get("schema") != STATE_V2_READINESS_SCHEMA:
        return {"status": "UNKNOWN", "reason": "READINESS_SCHEMA_UNKNOWN"}
    release_id, release_supports_state_v2 = active_release or _active_state_v2_release()
    if (not release_id or not release_supports_state_v2
            or record.get("active_release_id") != release_id):
        return {"status": "UNKNOWN", "reason": "ACTIVE_RELEASE_READINESS_MISMATCH"}
    verified_at = record.get("verified_at")
    try:
        stamp = datetime.fromisoformat(str(verified_at).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
        if age < -300 or age > 7 * 24 * 60 * 60:
            return {"status": "UNKNOWN", "reason": "READINESS_EVIDENCE_STALE_OR_FUTURE"}
    except (TypeError, ValueError):
        return {"status": "UNKNOWN", "reason": "READINESS_TIMESTAMP_INVALID"}
    checks = record.get("checks")
    if not isinstance(checks, dict) or any(key not in checks for key in STATE_V2_REQUIRED_CHECKS):
        return {"status": "UNKNOWN", "reason": "READINESS_CHECKS_INCOMPLETE"}
    if any(checks[key] is not True for key in STATE_V2_REQUIRED_CHECKS):
        return {"status": "NOT_READY", "reason": "REQUIRED_STATE_V2_CHECK_FAILED",
                "failed_checks": [key for key in STATE_V2_REQUIRED_CHECKS if checks[key] is not True]}
    return {"status": "READY", "reason": "ALL_REQUIRED_RUNTIME_CHECKS_PASS",
            "evidence_version": str(record.get("evidence_version") or "unknown"),
            "verified_at": str(record.get("verified_at") or "unknown")}


_RECOVERY_CERTIFICATION_OPERATION = "STABILITY_SUPERVISOR_FOCUSED_TESTS"
_RECOVERY_CERTIFICATION_OPERATIONS = {
    _RECOVERY_CERTIFICATION_OPERATION,
    "RESEARCH_INDEXED_LOOKUP_CONTRACT_TEST",
}
_RESEARCH_INDEXED_LOOKUP_TEST_PATH = "scripts/research/tests/test_case_control_indexed_lookup.py"
_RECOVERY_CERTIFICATION_PATHS = (
    Path.home(), Path.home() / "nexus-os-v2-canonical",
    Path.home() / ".nexus", Path.home() / "nexus-os-v2-canonical" / "data",
)


def _recovery_process_snapshot() -> tuple[list[dict[str, str]], str | None]:
    """Read a bounded process snapshot; shell/ps self-matches are ignored."""
    try:
        result = subprocess.run(["ps", "-axo", "pid=,ppid=,stat=,etime=,%cpu=,rss=,command="],
                                capture_output=True, text=True, timeout=0.6, check=False)
        rows: list[dict[str, str]] = []
        for line in result.stdout[:MAX_PS_OUTPUT_BYTES].splitlines():
            fields = line.strip().split(None, 6)
            if len(fields) != 7 or not fields[0].isdigit():
                continue
            pid, ppid, state, elapsed, cpu, rss, command = fields
            try:
                words = shlex.split(command, posix=True) if command else []
            except ValueError:
                words = command.split()
            executable = os.path.basename(words[0]) if words else ""
            if executable in {"ps", "awk", "zsh", "bash", "sh"}:
                continue
            rows.append({"pid": pid, "ppid": ppid, "state": state,
                         "elapsed": elapsed, "cpu": cpu, "rss": rss,
                         "command": command[:512], "executable": executable})
        return rows, None if result.returncode == 0 else f"ps_exit_{result.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], type(exc).__name__


def _bounded_filesystem_probe(paths: Iterable[Path]) -> tuple[bool, list[str]]:
    """Run metadata probes in one short-lived child so a stalled stat is bounded."""
    script = "import os,sys; [os.stat(p) for p in sys.argv[1:]]"
    try:
        result = subprocess.run([shutil.which("python3") or "python3", "-c", script,
                                 *(str(path) for path in paths)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=0.6, check=False)
        return result.returncode == 0, [] if result.returncode == 0 else ["FILESYSTEM_STAT_FAILED"]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, [f"FILESYSTEM_PROBE_{type(exc).__name__.upper()}"]


def get_recovery_certification_gate(
        operation: str = _RECOVERY_CERTIFICATION_OPERATION, *,
        operation_target: str | None = None,
        process_rows: list[dict[str, str]] | None = None,
        filesystem_responsive: bool | None = None,
        memory_free_percent: float | None = None,
        swap_used_mb: float | None = None,
        load_average: tuple[float, float, float] | None = None,
        active_work: dict[str, bool] | None = None,
        recent_test_stall: bool = False,
) -> dict[str, Any]:
    """Authorize only tiny deterministic recovery certification, never production work."""
    reasons: list[str] = []
    if operation not in _RECOVERY_CERTIFICATION_OPERATIONS:
        reasons.append("OPERATION_NOT_ALLOWLISTED")
    if (operation == "RESEARCH_INDEXED_LOOKUP_CONTRACT_TEST"
            and operation_target != _RESEARCH_INDEXED_LOOKUP_TEST_PATH):
        reasons.append("OPERATION_TARGET_NOT_ALLOWLISTED")

    if process_rows is None:
        process_rows, process_error = _recovery_process_snapshot()
        if process_error:
            reasons.append("PROCESS_STATE_UNAVAILABLE")
    relevant = []
    forbidden_active = False
    for row in process_rows:
        command = row.get("command", "").lower()
        executable = row.get("executable", os.path.basename(command.split(" ", 1)[0])).lower()
        is_test = "pytest" in command or "test_stability_supervisor.py" in command
        is_nexus = any(marker.lower() in command for marker in _NEXUS_MARKERS)
        if "U" in row.get("state", "").upper() and (is_test or is_nexus):
            relevant.append(row)
        if any(token in command for token in ("run_dispatched_research_job.py", "research_migration", "ledger_compact", "release_builder", "build_release")):
            forbidden_active = True
        if executable in {"rg", "find"} and ("nexus-os-v2-canonical" in command or "~/.nexus" in command):
            forbidden_active = True
    if relevant:
        reasons.append("ACTIVE_U_STATE")
    if filesystem_responsive is None:
        filesystem_responsive, fs_reasons = _bounded_filesystem_probe(_RECOVERY_CERTIFICATION_PATHS)
        reasons.extend(fs_reasons)
    if not filesystem_responsive:
        reasons.append("FILESYSTEM_UNRESPONSIVE")

    if memory_free_percent is None or swap_used_mb is None:
        try:
            memory = subprocess.run(["memory_pressure"], capture_output=True, text=True,
                                    timeout=0.6, check=False).stdout
            match = re.search(r"free percentage:\s*(\d+)%", memory, re.IGNORECASE)
            if memory_free_percent is None and match:
                memory_free_percent = float(match.group(1))
            swap = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True,
                                  text=True, timeout=0.4, check=False).stdout
            match = re.search(r"used\s*=\s*([0-9.]+)M", swap)
            if swap_used_mb is None and match:
                swap_used_mb = float(match.group(1))
        except (OSError, subprocess.TimeoutExpired):
            reasons.append("RESOURCE_PRESSURE_UNAVAILABLE")
    if memory_free_percent is None or memory_free_percent < 40:
        reasons.append("MEMORY_PRESSURE")
    if swap_used_mb is None or swap_used_mb > 256:
        reasons.append("SWAP_PRESSURE")

    if load_average is None:
        try:
            load_average = os.getloadavg()
        except (AttributeError, OSError):
            load_average = None
    load_limit = min(3.0, max(1.0, (os.cpu_count() or 2) * 0.5))
    if load_average is None or max(load_average) > load_limit:
        reasons.append("LOAD_PRESSURE")

    active_work = active_work or {}
    if forbidden_active or any(active_work.values()):
        reasons.append("OTHER_HEAVY_WORK_ACTIVE")
    if recent_test_stall:
        reasons.append("RECENT_TEST_STALL")

    return {"gate": "PASS_BOUNDED_CERTIFICATION" if not reasons else "BLOCKED",
            "authorized_operation": operation if not reasons else None,
            "reason_codes": sorted(set(reasons)),
            "production_host_gate_unchanged": True,
            "research_execution_allowed": False, "heavy_work_allowed": False,
            "production_migration_allowed": False, "release_build_allowed": False,
            "golden_path_allowed": False, "phase5_allowed": False,
            "observed_relevant_u_pids": [row.get("pid") for row in relevant]}


def _process_rows(output: str) -> list[dict[str, str]]:
    rows = []
    for line in output.splitlines():
        fields = line.strip().split(None, 6)
        if len(fields) < 7 or not fields[0].isdigit():
            continue
        pid, ppid, state, elapsed, cpu, rss, command = fields
        if any(marker in command for marker in _NEXUS_MARKERS):
            rows.append({"pid": pid, "ppid": ppid, "state": state,
                         "elapsed": elapsed, "cpu": cpu, "rss": rss,
                         "command": command[:512]})
    return rows


def _read_process_table() -> tuple[list[dict[str, str]], str | None]:
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,stat=,etime=,%cpu=,rss=,command="],
            capture_output=True, text=True, timeout=0.6, check=False,
        )
        raw = result.stdout[:MAX_PS_OUTPUT_BYTES]
        return _process_rows(raw), None if result.returncode == 0 else f"ps_exit_{result.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], type(exc).__name__


def _event_id(pid: str, started_identity: str, observed_at: str) -> str:
    return "sys_" + hashlib.sha256(f"{pid}|{started_identity}|{observed_at}".encode()).hexdigest()[:24]


def _make_recovery_event(event_id: str, occurred_at: str, process: dict[str, str], artifact: Path) -> dict[str, Any]:
    return {
        "schema_version": "nexus.recovery-event.v1", "event_id": event_id,
        "occurred_at": occurred_at, "objective_id": None, "project_id": None,
        "job_id": None, "case_id": None, "department": "SYSTEMS",
        "job_type": "SYSTEMS_RECOVERY_DIAGNOSIS", "failure_domain": "SYSTEMS_HOST",
        "current_state": "UNINTERRUPTIBLE_IO", "expected_state": "PROCESS_RESPONSIVE",
        "last_successful_transition": None, "failed_transition": "PROCESS_IO_WAIT",
        "error_code": "PROCESS_UNINTERRUPTIBLE_IO",
        "error_summary": f"Nexus process {process['pid']} entered U state; no automatic repair attempted.",
        "attempt_count": 0, "recent_attempts": [],
        "available_capabilities": ["BOUNDED_DIAGNOSTIC_CAPTURE", "SYSTEMS_RECOVERY_ROUTING"],
        "authorized_actions": ["PAUSE_HEAVY_WORK", "CREATE_SYSTEMS_RECOVERY_JOB", "WAIT_FOR_RESOURCE", "ESCALATE_WITH_ACTIONABLE_DIAGNOSIS", "VERIFY_RECOVERY"],
        "prohibited_actions": ["TERMINATE_OBJECTIVE", "UNAPPROVED_SPEND", "UNAPPROVED_RELEASE_PROMOTION", "DELETE_HISTORY", "BYPASS_GOVERNANCE", "AUTOMATIC_RESTART"],
        "cost_boundary": {"incremental_spend_authorized": False, "max_incremental_cost": 0},
        "evidence_references": [str(artifact)], "relevant_self_knowledge": [],
        "objective_termination_authorized": False,
    }


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    if len(payload) > MAX_ARTIFACT_BYTES:
        value["evidence_limitations"] = list(value.get("evidence_limitations", [])) + ["ARTIFACT_TRUNCATED_TO_HARD_LIMIT"]
        value["kernel_log_window"] = []
        value["dispatcher_log_context"] = []
        value["open_nexus_files"] = value.get("open_nexus_files", [])[:8]
        payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValueError("DIAGNOSTIC_ARTIFACT_HARD_LIMIT_EXCEEDED")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".u-event-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _wait_channel(pid: str, deadline: float) -> tuple[str | None, str | None]:
    if time.monotonic() >= deadline:
        return None, "CAPTURE_DEADLINE"
    try:
        result = subprocess.run(["ps", "-p", pid, "-o", "wchan="], capture_output=True,
                                text=True, timeout=min(.25, max(.05, deadline-time.monotonic())), check=False)
        value = result.stdout.strip()[:128]
        return (value or None), (None if result.returncode == 0 else "WAIT_CHANNEL_UNAVAILABLE")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, type(exc).__name__


def _bounded_lsof(pid: str, deadline: float) -> tuple[list[str], str | None]:
    exe = shutil.which("lsof")
    if not exe or time.monotonic() >= deadline:
        return [], "LSOF_UNAVAILABLE_OR_DEADLINE"
    proc = None
    lines: list[str] = []
    try:
        proc = subprocess.Popen([exe, "-nP", "-p", pid], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, bufsize=1)
        fd = proc.stdout.fileno() if proc.stdout else -1
        while time.monotonic() < deadline and len(lines) < MAX_OPEN_FILES_RECORDED * 8:
            ready, _, _ = select.select([fd], [], [], min(.05, max(.0, deadline-time.monotonic())))
            if not ready:
                if proc.poll() is not None:
                    break
                continue
            line = os.read(fd, 1024).decode("utf-8", "replace")
            if not line:
                break
            for item in line.splitlines():
                if any(marker.lower() in item.lower() for marker in _PATH_MARKERS):
                    lines.append(item.strip()[:512])
                if len(lines) >= MAX_OPEN_FILES_RECORDED * 8:
                    break
        if proc.poll() is None:
            proc.kill()
            return lines[:MAX_OPEN_FILES_RECORDED], "LSOF_TRUNCATED_OR_TIMED_OUT"
        return lines[:MAX_OPEN_FILES_RECORDED], None
    except (OSError, subprocess.TimeoutExpired) as exc:
        if proc and proc.poll() is None:
            proc.kill()
        return lines[:MAX_OPEN_FILES_RECORDED], type(exc).__name__
    finally:
        if proc and proc.stdout:
            proc.stdout.close()


def _children(rows: Iterable[dict[str, str]], pid: str) -> list[dict[str, str]]:
    return [{key: row[key] for key in ("pid", "state", "elapsed", "cpu", "rss", "command")}
            for row in rows if row["ppid"] == pid][:16]


def _dispatcher_context(root: Path, deadline: float) -> dict[str, Any]:
    path = root / "reports" / "runtime" / "durable_dispatcher.log"
    if time.monotonic() >= deadline:
        return {"available": False, "reason": "CAPTURE_DEADLINE"}
    try:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            end = stream.tell()
            stream.seek(max(0, end - 8192))
            lines = stream.read(8192).decode("utf-8", "replace").splitlines()[-MAX_LOG_LINES:]
        allowed = {"started", "active", "ready", "running", "blocked", "failed_retryable", "expired_leases", "active_worker_count", "oldest_queued_age_seconds"}
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            health = row.get("health", {})
            if health:
                return {"available": True,
                        "last_dispatcher_action": "DISPATCH_TICK",
                        "queue": {key: health.get(key) for key in allowed if key in health},
                        "started_this_tick": row.get("started"),
                        "watchdog": row.get("research_parent_watchdog")}
    except OSError:
        pass
    return {"available": False, "reason": "NO_RECENT_STRUCTURED_DISPATCHER_LINE"}


def _kernel_log(deadline: float) -> tuple[list[str], str | None]:
    if sys_platform() != "darwin" or time.monotonic() >= deadline:
        return [], "KERNEL_LOG_UNAVAILABLE_OR_DEADLINE"
    predicate = 'process == "kernel" AND (eventMessage CONTAINS[c] "APFS" OR eventMessage CONTAINS[c] "I/O error" OR eventMessage CONTAINS[c] "disk timeout" OR eventMessage CONTAINS[c] "device reset" OR eventMessage CONTAINS[c] "storage" OR eventMessage CONTAINS[c] "watchdog" OR eventMessage CONTAINS[c] "vnode wait")'
    try:
        result = subprocess.run(["log", "show", "--last", "2m", "--style", "compact", "--predicate", predicate],
                                capture_output=True, text=True,
                                timeout=min(1.0, max(.05, deadline-time.monotonic())), check=False)
        return [line[:240] for line in result.stdout.splitlines()[-MAX_LOG_LINES:]], (None if result.returncode == 0 else "KERNEL_LOG_QUERY_FAILED")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], type(exc).__name__


def sys_platform() -> str:
    import sys
    return sys.platform


def capture_uninterruptible_process(process: dict[str, str], rows: list[dict[str, str]], *, root: Path | None = None,
                                    now: datetime | None = None) -> dict[str, Any] | None:
    """Write one compact artifact for a U process; no inference from open files."""
    root = root or Path(os.environ.get("NEXUS_REPO_ROOT", Path(__file__).resolve().parents[2]))
    store = diagnostics_root()
    pid = process["pid"]
    identity = hashlib.sha256(f"{pid}|{process['elapsed']}|{process['command']}".encode()).hexdigest()[:12]
    marker = store / f".u-active-{pid}-{identity}"
    try:
        store.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError:
        return None
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = observed.strftime("%Y%m%dT%H%M%S")
    event_id = _event_id(pid, identity, observed.isoformat())
    artifact = store / f"dispatcher_u_{stamp}_pid{pid}_{event_id[-8:]}.json"
    deadline = time.monotonic() + MAX_CAPTURE_SECONDS
    wait_channel, wait_limit = _wait_channel(pid, deadline)
    event = _make_recovery_event(event_id, observed.isoformat(), process, artifact)
    value: dict[str, Any] = {
        "event_id": event_id, "timestamp": observed.isoformat(),
        "process": {"name": process["command"].split()[-1][:128], **process,
                    "wait_channel": wait_channel},
        "failure_type": "PROCESS_UNINTERRUPTIBLE_IO", "wait_channel": wait_channel,
        "blocked_operation": "UNKNOWN", "blocked_path": "UNDETERMINED",
        "open_nexus_files": [], "child_processes": _children(rows, pid),
        "job_context": {"available": False, "reason": "CAPTURE_IN_PROGRESS"},
        "host_context": {"platform": sys_platform(), "automatic_restart": False,
                         "objective_terminated": False, "new_work_started": False},
        "kernel_log_window": [], "evidence_limitations": [],
        "recovery_event": event,
    }
    if wait_limit:
        value["evidence_limitations"].append(wait_limit)
    _atomic_json(artifact, value)  # Initial evidence is durable before slower probes.
    value["job_context"] = _dispatcher_context(root, deadline)
    _atomic_json(artifact, value)
    try:
        files, files_limit = _bounded_lsof(pid, deadline)
    except Exception as exc:
        files, files_limit = [], f"OPEN_FILE_CAPTURE_{type(exc).__name__}"
    files = files[:MAX_OPEN_FILES_RECORDED]
    value["open_nexus_files"] = files
    if files_limit:
        value["evidence_limitations"].append(files_limit)
    lowered = "\n".join(files).lower()
    value["research_ledger_open"] = ("YES" if "research_runtime_states.jsonl" in lowered else "NO" if files_limit is None else "UNKNOWN")
    value["execution_ledger_open"] = ("YES" if "research_execution_jobs.jsonl" in lowered else "NO" if files_limit is None else "UNKNOWN")
    value["sqlite_open"] = [line for line in files if ".sqlite" in line.lower() or ".db" in line.lower()]
    value["log_files_open"] = [line for line in files if ".log" in line.lower()]
    value["pipe_socket_summary"] = [line for line in files if "pipe" in line.lower() or "unix" in line.lower()][:8]
    try:
        kernel, kernel_limit = _kernel_log(deadline)
    except Exception as exc:
        kernel, kernel_limit = [], f"KERNEL_LOG_CAPTURE_{type(exc).__name__}"
    value["kernel_log_window"] = kernel
    if kernel_limit:
        value["evidence_limitations"].append(kernel_limit)
    value["capture_elapsed_seconds"] = round(MAX_CAPTURE_SECONDS - max(0, deadline-time.monotonic()), 3)
    value.update({"EVENT_ID": event_id, "TIMESTAMP": observed.isoformat(),
                  "PROCESS": value["process"]["name"], "PID": pid,
                  "FAILURE_TYPE": value["failure_type"], "WAIT_CHANNEL": wait_channel,
                  "BLOCKED_OPERATION": value["blocked_operation"], "BLOCKED_PATH": value["blocked_path"],
                  "OPEN_NEXUS_FILES": files, "CHILD_PROCESSES": value["child_processes"],
                  "JOB_CONTEXT": value["job_context"], "HOST_CONTEXT": value["host_context"],
                  "EVIDENCE_LIMITATIONS": value["evidence_limitations"]})
    _atomic_json(artifact, value)
    return {"event": event, "artifact": str(artifact), "artifact_data": value}


def monitor_uninterruptible_processes(*, root: Path | None = None) -> list[dict[str, Any]]:
    """Reuse the bounded health pass to detect/capture Nexus U-state processes."""
    rows, error = _read_process_table()
    if error:
        return []
    captured = []
    for row in rows:
        if "U" in row["state"].upper():
            result = capture_uninterruptible_process(row, rows, root=root)
            if result:
                captured.append(result)
        else:
            identity = hashlib.sha256(f"{row['pid']}|{row['elapsed']}|{row['command']}".encode()).hexdigest()[:12]
            marker = diagnostics_root() / f".u-active-{row['pid']}-{identity}"
            try:
                marker.unlink(missing_ok=True)
            except OSError:
                pass
    return captured


def supervisor_decision(event: dict[str, Any]) -> list[str]:
    code = event.get("error_code") or event.get("failure_type")
    if code in {"PROCESS_UNINTERRUPTIBLE_IO", "HOST_IO_DEGRADED", "FILESYSTEM_STALL", "LEDGER_SIZE_THRESHOLD_EXCEEDED"}:
        return ["PAUSE_HEAVY_WORK", "CREATE_SYSTEMS_RECOVERY_JOB", "WAIT_FOR_RESOURCE", "ESCALATE_WITH_ACTIONABLE_DIAGNOSIS"]
    if code in {"LEASE_EXPIRED", "WORKER_INTERRUPTED", "READY_TOO_LONG"}:
        return ["RETRY_AUTHORIZED_ACTION", "VERIFY_RECOVERY"]
    if code == "PROVIDER_UNAVAILABLE":
        return ["WAIT_FOR_RESOURCE", "USE_ALTERNATE_AUTHORIZED_TOOL", "VERIFY_RECOVERY"]
    if code in {"CURRENT_STATE_LOOKUP_FAILED", "CURRENT_STATE_LOOKUP_UNAVAILABLE", "CURRENT_STATE_WRITE_FAILED",
                "HISTORY_WRITE_FAILED", "HISTORY_PARTITION_ROTATION_FAILED", "HISTORY_PARTITION_SELECTION_EXHAUSTED",
                "RECONCILIATION_REQUIRED",
                "EXPECTED_ARTIFACT_MISSING", "STATE_DIVERGENCE_DETECTED", "CASE_LOOKUP_LATENCY_EXCEEDED"}:
        return ["CREATE_SYSTEMS_RECOVERY_JOB", "REQUEST_CODEX_SPECIALIST", "ESCALATE_WITH_ACTIONABLE_DIAGNOSIS"]
    return ["ESCALATE_WITH_ACTIONABLE_DIAGNOSIS"]


def route_recovery_event(event: dict[str, Any], store: SupervisorStateStore | None = None,
                         *, artifact_ref: str | None = None) -> dict[str, Any]:
    """Persist one idempotent planned recovery job; never executes repairs."""
    actions = supervisor_decision(event)
    result: dict[str, Any] = {"event_id": event.get("event_id"), "actions": actions,
                              "objective_terminated": False, "automatic_repair": False}
    if "CREATE_SYSTEMS_RECOVERY_JOB" not in actions:
        return result
    store = store or SupervisorStateStore()
    registered = store.register_event(event, artifact_ref=artifact_ref or (event.get("evidence_references") or [None])[0])
    result["recovery_job_id"] = registered["recovery_job_id"]
    result["recovery_job_state"] = registered["execution_state"]
    result["recovery_job_plan_state"] = registered["plan_state"]
    result["original_job_id"] = event.get("job_id")
    result["original_objective_id"] = event.get("objective_id")
    return result


CURRENT_HOST_INCIDENT_ID = "sys_host_io_degraded_20261022_r50_001"


def create_current_host_incident(*, state_store: SupervisorStateStore | None = None) -> dict[str, Any]:
    """Record the already-confirmed host incident without touching production work state."""
    state_store = state_store or SupervisorStateStore()
    root = diagnostics_root()
    artifact = root / "host_io_degraded_20261022_r50_001.json"
    occurred = datetime.now(timezone.utc).isoformat()
    event = {
        "schema_version": "nexus.recovery-event.v1", "event_id": CURRENT_HOST_INCIDENT_ID,
        "occurred_at": occurred, "objective_id": None, "project_id": None,
        "job_id": None, "case_id": None, "department": "SYSTEMS",
        "job_type": "SYSTEMS_RECOVERY_DIAGNOSIS", "failure_domain": "SYSTEMS_HOST",
        "current_state": "HOST_IO_DEGRADED", "expected_state": "HOST_HEALTHY",
        "last_successful_transition": None, "failed_transition": "HOST_HEALTH_GATE_FAILED",
        "error_code": "HOST_IO_DEGRADED",
        "error_summary": "Repeated U-state observations across dispatcher, MCP, workspace search, and focused test; exact kernel cause remains unknown.",
        "attempt_count": 0, "recent_attempts": [],
        "available_capabilities": ["BOUNDED_HOST_DIAGNOSTICS", "SYSTEMS_RECOVERY_ROUTING"],
        "authorized_actions": ["PAUSE_HEAVY_WORK", "CREATE_SYSTEMS_RECOVERY_JOB", "WAIT_FOR_RESOURCE", "ESCALATE_WITH_ACTIONABLE_DIAGNOSIS", "VERIFY_RECOVERY"],
        "prohibited_actions": ["TERMINATE_OBJECTIVE", "UNAPPROVED_SPEND", "UNAPPROVED_RELEASE_PROMOTION", "DELETE_HISTORY", "BYPASS_GOVERNANCE", "AUTOMATIC_RESTART"],
        "cost_boundary": {"incremental_spend_authorized": False, "max_incremental_cost": 0},
        "evidence_references": [str(artifact)], "relevant_self_knowledge": ["Research State Architecture v2 is a planned recovery dependency; ledger causation is not established."],
        "objective_termination_authorized": False,
    }
    known = [
        "durable dispatcher observed in U; exact blocked operation/path not captured",
        "MCP observed in U during prior activity; exact blocked operation/path not captured",
        "workspace rg search entered U without Research execution",
        "focused synthetic-test process entered U; test stopped",
        "storage is internal 1 TB SATA HDD APPLE HDD HTS541010A9E662; SMART Verified",
        "bounded recent query found no matching APFS/storage error",
        "memory pressure remained approximately 70%+ free; swap used 0 MiB",
        "exact kernel/filesystem root cause UNDETERMINED_WITH_EVIDENCE",
    ]
    registered = state_store.register_event(event, artifact_ref=str(artifact),
        title="Research State Architecture v2 / Host I/O Stabilization")
    value = {"EVENT_ID": CURRENT_HOST_INCIDENT_ID, "TIMESTAMP": occurred,
             "FAILURE_TYPE": "HOST_IO_DEGRADED", "FAILURE_DOMAIN": "SYSTEMS_HOST",
             "HOST_EXECUTION_GATE": "BLOCKED", "ROOT_CAUSE": "UNDETERMINED_WITH_EVIDENCE",
             "OBJECTIVE_ID": None, "KNOWN_EVIDENCE": known,
             "NEXT_RECOVERY_PROJECT": "RESEARCH_STATE_ARCHITECTURE_V2",
             "RECOVERY_JOB_ID": registered["recovery_job_id"],
             "RECOVERY_JOB_PLAN_STATE": registered["plan_state"],
             "RECOVERY_JOB_EXECUTION_STATE": registered["execution_state"],
             "RECOVERY_JOB_TITLE": "Research State Architecture v2 / Host I/O Stabilization",
             "recovery_event": event}
    _atomic_json(artifact, value)
    return {"event_id": CURRENT_HOST_INCIDENT_ID, "artifact": str(artifact), **registered}


def recovery_verified(evidence: dict[str, bool], *, research_required: bool = False) -> bool:
    required = ["no_persistent_u_state", "host_health_gate_pass", "mcp_healthy",
                "dispatcher_healthy", "runtime_contract_pass"]
    if research_required:
        required.extend(("current_state_lookups_bounded", "full_ledger_scan_absent", "state_v2_focused_tests_pass"))
    return all(evidence.get(key) is True for key in required)


def certify_recovery(event_id: str, evidence: dict[str, bool], *,
                     state_store: SupervisorStateStore | None = None,
                     job_store: Any = None) -> dict[str, Any]:
    """Verify recovery, then make original jobs eligible without replacing lineage."""
    state_store = state_store or SupervisorStateStore()
    incident = state_store.incident(event_id)
    if not incident:
        return {"verified": False, "reason": "RECOVERY_EVENT_NOT_FOUND"}
    blocks = state_store.blocks_for_event(event_id)
    requires_research = any(row.get("department", "").upper() == "RESEARCH" for row in blocks)
    if not recovery_verified(evidence, research_required=requires_research):
        return {"verified": False, "reason": "RECOVERY_EVIDENCE_INCOMPLETE", "resumed": []}
    outcomes: dict[str, str] = {}
    if blocks and job_store is None:
        return {"verified": False, "reason": "DURABLE_JOB_STORE_REQUIRED_TO_VERIFY_LINEAGE", "resumed": []}
    for block in blocks:
        job_id = block.get("job_id")
        if not job_id:
            return {"verified": False, "reason": "BLOCKED_JOB_ID_MISSING", "resumed": []}
        job = job_store.get(job_id)
        if not job:
            return {"verified": False, "reason": "ORIGINAL_JOB_NOT_FOUND", "resumed": []}
        context = getattr(job, "governance_context", {}) or {}
        linked_objective = context.get("owner_objective_id") or context.get("objective_id")
        linked_project = context.get("project_id") or context.get("work_id")
        linked_case = context.get("case_id") or context.get("research_case_id")
        if linked_objective and linked_objective != block["objective_id"]:
            return {"verified": False, "reason": "ORIGINAL_OBJECTIVE_LINEAGE_MISMATCH", "resumed": []}
        if block.get("project_id") and linked_project and linked_project != block["project_id"]:
            return {"verified": False, "reason": "ORIGINAL_PROJECT_LINEAGE_MISMATCH", "resumed": []}
        if block.get("case_id") and linked_case and linked_case != block["case_id"]:
            return {"verified": False, "reason": "ORIGINAL_CASE_LINEAGE_MISMATCH", "resumed": []}
        state = str(getattr(job, "state", "")).upper()
        if state == "COMPLETED":
            outcomes[block["objective_id"]] = "COMPLETED_NO_REGENERATION"
        elif state in {"BLOCKED", "FAILED_RETRYABLE"}:
            job_store.requeue_for_repair(job_id, reason=f"stability recovery {event_id} certified")
            outcomes[block["objective_id"]] = "ELIGIBLE_SAME_JOB_ID"
        elif state in {"READY", "CLAIMED", "RUNNING", "WAITING"}:
            outcomes[block["objective_id"]] = "ALREADY_PRESENT_NO_DUPLICATE"
        else:
            outcomes[block["objective_id"]] = "PRESERVED_NO_AUTOMATIC_RETRY"
    if requires_research:
        state_store.set_flag("research_state_architecture_certified", True)
    state_store.mark_resolved(event_id, resume_statuses=outcomes)
    return {"verified": True, "research_required": requires_research,
            "resumed": outcomes, "recovery_job_id": incident["recovery_job_id"]}


def resume_action(event: dict[str, Any], evidence: dict[str, bool]) -> str:
    if not recovery_verified(evidence, research_required=bool(event.get("research_required"))):
        return "WAIT_FOR_RESOURCE"
    if event.get("objective_id") is None:
        return "REQUEST_RAY_APPROVAL"
    return "RESUME_BLOCKED_OBJECTIVE"
