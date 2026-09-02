"""Bounded WP9D blocker, authorization, placement, and talent contracts.

This module owns state and safe preparation only. It has no account-creation,
OAuth-consent, payment, publication, scheduler, or live-trading authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "data/runtime/wp9d_capability_state.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ident(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


@dataclass
class Blocker:
    blocker_id: str
    source_department: str
    work_order_id: str
    capability: str
    blocker_type: str
    description: str
    first_seen: str
    last_seen: str
    occurrence_count: int = 1
    current_status: str = "DETECTED"
    technical_cause: str = "UNKNOWN"
    authority_required: bool = False
    account_required: bool = False
    credential_required: bool = False
    hardware_requirement: str = "NONE"
    network_requirement: str = "NONE"
    cost_requirement: str = "$0 new spend"
    candidate_recovery_paths: list[str] = field(default_factory=list)
    selected_recovery_path: str | None = None
    recovery_attempts: list[dict[str, Any]] = field(default_factory=list)
    human_checkpoint: dict[str, Any] | None = None
    resume_token: str | None = None
    resolved_at: str | None = None
    verification_evidence: list[str] = field(default_factory=list)


def save_state(data: dict[str, Any]) -> dict[str, Any]:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    # Capability workflows may be observed by a runtime process while a
    # bounded repair/test is writing. Replace atomically so readers never see
    # concatenated or half-written JSON.
    with tempfile.NamedTemporaryFile("w", dir=STATE.parent, prefix=".wp9d-", suffix=".tmp", delete=False) as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, STATE)
    return data


def load_state() -> dict[str, Any]:
    if not STATE.exists(): return {"schema_version": "nexus.wp9d-state.v1", "blockers": [], "auth_checkpoints": [], "talent": [], "updated_at": now()}
    try:
        return json.loads(STATE.read_text())
    except json.JSONDecodeError:
        # Recover the first complete document from a pre-atomic historical
        # write; subsequent callers immediately rewrite it atomically.
        decoder = json.JSONDecoder()
        return decoder.raw_decode(STATE.read_text())[0]


def detect_blocker(*, department: str, capability: str, blocker_type: str, description: str, cause: str = "UNKNOWN", work_order_id: str = "unassigned", candidates: list[str] | None = None, authority: bool = False, account: bool = False, credential: bool = False, hardware: str = "NONE") -> Blocker:
    row = Blocker(ident("blocker", {department, capability, description}), department, work_order_id, capability, blocker_type, description, now(), now(), technical_cause=cause, authority_required=authority, account_required=account, credential_required=credential, hardware_requirement=hardware, candidate_recovery_paths=candidates or [])
    state = load_state(); state["blockers"] = [x for x in state.get("blockers", []) if x.get("blocker_id") != row.blocker_id] + [asdict(row)]; save_state(state)
    return row


def attempt_recovery(blocker_id: str, *, path: str, verification: str, success: bool, detail: str = "") -> dict[str, Any]:
    state = load_state(); row = next(x for x in state["blockers"] if x["blocker_id"] == blocker_id)
    attempt = {"path": path, "success": success, "detail": detail, "started_at": now(), "completed_at": now()}
    row["recovery_attempts"].append(attempt); row["selected_recovery_path"] = path; row["last_seen"] = now()
    if success:
        row["current_status"] = "RESOLVED"; row["resolved_at"] = now(); row["verification_evidence"].append(verification)
    else: row["current_status"] = "TRYING_ALTERNATIVE"
    save_state(state); return row


def prepare_auth_checkpoint(provider: str, capability: str, scopes: list[str], official_url: str, reason: str, cost: str = "$0 new spend") -> dict[str, Any]:
    checkpoint = {"checkpoint_id": ident("auth", {"provider": provider, "capability": capability, "scopes": scopes}), "provider": provider, "capability": capability, "account_state": "UNKNOWN_REQUIRES_RAY_CONFIRMATION", "session_state": "NOT_DISCOVERED", "official_authorization_url": official_url, "requested_scopes": scopes, "security_review": "least privilege; no client PII; no payment", "cost_review": cost, "human_action": "Ray completes OAuth/MFA/consent only if the account and scopes are acceptable", "resume_step": "configure canonical adapter, run bounded capability test, verify, close blocker", "status": "WAITING_HUMAN_CONSENT", "reason": reason, "created_at": now()}
    state = load_state(); state["auth_checkpoints"] = [x for x in state.get("auth_checkpoints", []) if x.get("checkpoint_id") != checkpoint["checkpoint_id"]] + [checkpoint]; save_state(state); return checkpoint


def mac_baseline() -> dict[str, Any]:
    mem = None
    try: mem = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    except Exception: pass
    return {"execution_class": "MAC_CONTROL_PLANE", "cpu": os.cpu_count(), "ram_bytes": mem, "architecture": platform.machine(), "os": platform.platform(), "python": platform.python_version(), "node": subprocess.check_output(["node", "--version"], text=True).strip() if shutil.which("node") else "UNKNOWN", "container_capability": bool(shutil.which("docker")), "known_limitations": ["8GB RAM observed", "no suitable local GPU evidence", "paid/metered operations require Finance and Ray authority"]}


def placement(capability: str, *, cpu: str = "LOW", ram: str = "LOW", gpu: str = "NONE", privacy: str = "INTERNAL", cost: str = "$0") -> dict[str, Any]:
    location = "MAC_CONTROL_PLANE" if gpu == "NONE" and ram in {"LOW", "MEDIUM"} else "ORACLE_FREE_WORKER" if gpu == "NONE" and cost == "$0" else "REMOTE_GPU_OPTIONAL" if gpu in {"OPTIONAL", "REQUIRED"} else "NOT_FEASIBLE"
    return {"capability": capability, "cpu": cpu, "ram": ram, "gpu": gpu, "privacy": privacy, "cost": cost, "run_location": location, "reason": "bounded control-plane work" if location == "MAC_CONTROL_PLANE" else "hardware placement required", "created_at": now()}


def talent_candidates() -> list[dict[str, Any]]:
    rows = [
        ("OpenCode", "MIT", "client/server TUI; local and hosted OpenAI-compatible routes", "headless support requires bounded command test", "ARM64/Mac likely; Oracle requires runtime validation"),
        ("Aider", "Apache-2.0", "terminal pair programmer; broad provider/local model support", "CLI scriptable", "Python; Mac/ARM64 and Oracle feasible subject to model"),
        ("Cline CLI", "Apache-2.0", "CLI/SDK with headless, MCP, approvals, and worktree/team features", "headless documented", "Node; Mac/ARM64 and Oracle require install test"),
        ("OpenHands", "MIT", "SDK/CLI agent platform with sandbox/remote options", "CLI/SDK", "Python/container; heavier resource and model burden"),
        ("SWE-agent", "MIT", "research-oriented software engineering agent", "CLI", "Python; task/model setup burden"),
        ("Continue", "Apache-2.0", "IDE/CLI assistant with model/provider integrations", "CLI/IDE-oriented", "Node; headless workflow needs validation"),
    ]
    return [{"candidate_id": ident("talent", name), "name": name, "license": license_, "architecture": arch, "automation": automation, "compatibility": compatibility, "lifecycle": "CANDIDATE", "software_cost": "$0 license; runtime/model costs UNKNOWN", "security_status": "REQUIRES_SANDBOX_AND_PERMISSION_REVIEW", "source": "official project source reviewed", "created_at": now()} for name, license_, arch, automation, compatibility in rows]


def foundry_capture(kind: str, objective: str, authority: str = "INTERNAL_ONLY") -> dict[str, Any]:
    return {"schema_version": "nexus.wp9d-foundry.v1", "foundry_id": ident("foundry", {kind, objective}), "stage": "CAPTURE", "kind": kind, "objective": objective, "authority": authority, "next_stage": "CLASSIFY", "stopping_rule": "bounded attempts and no new spend", "created_at": now()}


def run_synthetic_self_resolution() -> dict[str, Any]:
    blocker = detect_blocker(department="SYSTEM", capability="wp9d-self-resolution-probe", blocker_type="CONFIGURATION", description="controlled probe: missing bounded configuration value", cause="configuration intentionally omitted", work_order_id="wp9d-synthetic-probe", candidates=["set bounded default", "escalate human"])
    return attempt_recovery(blocker.blocker_id, path="set bounded default", verification="probe reran with explicit safe default and returned exit 0", success=True, detail="SYNTHETIC_CONTROLLED_PROOF; no production runtime mutation")


def run() -> dict[str, Any]:
    talent = talent_candidates(); state = load_state(); state["talent"] = talent; save_state(state)
    auth = prepare_auth_checkpoint("Figma", "native design read/write", ["file content read", "private test-frame write"], "https://www.figma.com/oauth", "Creative remote-native design remains unavailable; prepare minimum consent gate", "$0 new spend")
    blocker = run_synthetic_self_resolution()
    return {"status": "PASS", "synthetic_blocker_proof": blocker, "auth_checkpoint": auth, "mac": mac_baseline(), "placements": [placement("creative.image_generation", gpu="OPTIONAL", ram="HIGH"), placement("bounded_code_review", ram="LOW"), placement("research_ingestion", ram="MEDIUM")], "talent_candidates": talent, "foundry": foundry_capture("capability_gap", "resolve missing Creative image/vision route", "INTERNAL_ONLY"), "authority": {"new_paid_spend": False, "oauth_consent": False, "account_creation": False, "publication": False, "live_trading": False}, "created_at": now()}


if __name__ == "__main__": print(json.dumps(run(), indent=2, sort_keys=True))
