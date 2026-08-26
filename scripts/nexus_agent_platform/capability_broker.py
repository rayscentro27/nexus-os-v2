"""Deny-by-default broker for the canonical Nexus capability manifest.

Hermes can select a capability id, never a command string. CLI templates are
fixed arrays, arguments are schema-checked, and all execution returns a
receipt. This module deliberately has no arbitrary shell escape hatch.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs/nexus_capability_manifest.json"
RECEIPT_DIR = ROOT / "reports/runtime/capability_broker"
MAX_OUTPUT = 12000
FORBIDDEN = re.compile(r"(?:[;&|`$()]|\r|\n|>|<)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list):
        raise ValueError("manifest capabilities must be a list")
    ids = [item.get("capability_id") for item in capabilities]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("manifest capability ids must be unique and non-empty")
    return payload


def capability_index(manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    return {row["capability_id"]: row for row in (manifest or load_manifest())["capabilities"]}


def _safe_env() -> Dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CI", "NODE_ENV", "PYTHONPATH"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["NEXUS_ARBITRARY_SHELL"] = "PROHIBITED"
    return env


def _validate_args(spec: Dict[str, Any], args: Dict[str, Any]) -> None:
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    schema = spec.get("allowed_args_schema", {})
    required = set(schema.get("required", []))
    if not required.issubset(args):
        raise ValueError(f"missing required arguments: {sorted(required - set(args))}")
    allowed = set(schema.get("properties", {}))
    unknown = set(args) - allowed
    if schema.get("additionalProperties") is False and unknown:
        raise ValueError(f"unknown arguments: {sorted(unknown)}")
    for name, value in args.items():
        if isinstance(value, str):
            if FORBIDDEN.search(value) or value.startswith("/") or ".." in Path(value).parts:
                raise ValueError(f"unsafe value for {name}")
            pattern = schema.get("properties", {}).get(name, {}).get("pattern")
            if pattern and not re.fullmatch(pattern, value):
                raise ValueError(f"invalid value for {name}")


def _receipt(capability: Dict[str, Any], *, status: str, started_at: str,
             finished_at: str, args: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    result = {
        "schema_version": "nexus.capability-receipt.v1",
        "receipt_id": f"rcpt_{uuid.uuid4().hex}",
        "capability_id": capability["capability_id"],
        "executor": capability.get("executor_ref"),
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "args": args,
        "arbitrary_shell": "PROHIBITED",
        **extra,
    }
    result["fingerprint"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def _write_receipt(receipt: Dict[str, Any], directory: Optional[Path] = None) -> Dict[str, Any]:
    target = directory or RECEIPT_DIR
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{receipt['receipt_id']}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def run_capability(capability_id: str, args: Optional[Dict[str, Any]] = None,
                   *, manifest: Optional[Dict[str, Any]] = None,
                   receipt_dir: Optional[Path] = None) -> Dict[str, Any]:
    args = args or {}
    spec = capability_index(manifest).get(capability_id)
    if not spec:
        raise KeyError(f"unknown capability: {capability_id}")
    _validate_args(spec, args)
    started = utc_now()
    if spec.get("availability") == "PROHIBITED" or spec.get("risk_level", 4) >= 4:
        return _write_receipt(_receipt(spec, status="PROHIBITED", started_at=started, finished_at=utc_now(), args=args, error="capability is prohibited"), receipt_dir)
    if spec.get("risk_level", 4) >= 3 or spec.get("approval_policy") not in {"NONE"}:
        return _write_receipt(_receipt(spec, status="APPROVAL_REQUIRED", started_at=started, finished_at=utc_now(), args=args, error="governance approval is required"), receipt_dir)
    if spec.get("executor_type") not in {"cli", "python_module"}:
        return _write_receipt(_receipt(spec, status="REGISTERED_UNPROVEN", started_at=started, finished_at=utc_now(), args=args, error="executor adapter requires explicit canary implementation"), receipt_dir)
    command = list(spec.get("command_template", []))
    if spec.get("executor_type") == "python_module":
        command = ["python3", "scripts/nexus_agent_platform/capability_runner.py", capability_id]
    if capability_id == "tests.run" and args.get("test_path"):
        command.append(args["test_path"])
    if not command or any(not isinstance(part, str) or FORBIDDEN.search(part) for part in command):
        raise ValueError("manifest contains unsafe command template")
    try:
        completed = subprocess.run(command, cwd=ROOT, env=_safe_env(), shell=False,
                                   capture_output=True, text=True,
                                   timeout=int(spec.get("timeout", 120)), check=False)
        status = "PASS" if completed.returncode == 0 else "FAIL"
        return _write_receipt(_receipt(spec, status=status, started_at=started, finished_at=utc_now(), args=args,
                                       command=command, exit_code=completed.returncode,
                                       stdout=completed.stdout[-MAX_OUTPUT:], stderr=completed.stderr[-MAX_OUTPUT:]), receipt_dir)
    except subprocess.TimeoutExpired as exc:
        return _write_receipt(_receipt(spec, status="TIMEOUT", started_at=started, finished_at=utc_now(), args=args,
                                       command=command, stdout=str(exc.stdout or "")[-MAX_OUTPUT:], stderr=str(exc.stderr or "")[-MAX_OUTPUT:]), receipt_dir)


def discover(*, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rows = (manifest or load_manifest())["capabilities"]
    return {"schema_version": "nexus.capability-discovery.v1", "generated_at": utc_now(),
            "arbitrary_shell": "PROHIBITED", "capabilities": [
                {"capability_id": row["capability_id"], "display_name": row["display_name"],
                 "category": row["category"], "availability": row["availability"],
                 "risk_level": row["risk_level"], "approval_policy": row["approval_policy"],
                 "last_canary": row.get("last_canary")} for row in rows]}


def run_safe_canaries(*, manifest: Optional[Dict[str, Any]] = None,
                      receipt_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Run every enabled class-0/1 capability through its real adapter."""
    loaded = manifest or load_manifest()
    rows = []
    for spec in loaded["capabilities"]:
        if not spec.get("enabled") or spec.get("risk_level", 4) >= 3:
            rows.append({"capability_id": spec["capability_id"], "registered": True,
                         "health": "GATED", "canary": "NOT_RUN", "ready_tonight": False})
            continue
        receipt = run_capability(spec["capability_id"], {}, manifest=loaded, receipt_dir=receipt_dir)
        passed = receipt.get("status") == "PASS"
        rows.append({"capability_id": spec["capability_id"], "registered": True,
                     "health": "PASS" if passed else "FAIL", "canary": receipt.get("status"),
                     "receiver_ack": "PASS" if passed else "FAIL", "executed": True,
                     "result": receipt.get("status"), "verified": passed,
                     "ready_tonight": passed, "receipt_id": receipt.get("receipt_id")})
    report = {"schema_version": "nexus.executor-preflight.v1", "generated_at": utc_now(),
              "arbitrary_shell": "PROHIBITED", "matrix": rows,
              "ready_tonight": all(row["ready_tonight"] for row in rows if row["canary"] != "NOT_RUN")}
    target = (receipt_dir or RECEIPT_DIR) / "executor_preflight.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(discover(), indent=2))
