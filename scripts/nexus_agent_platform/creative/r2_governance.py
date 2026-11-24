"""Bounded Cloudflare R2 cost estimates and governor policy definitions."""
from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
COST_POLICY_PATH = ROOT / "configs/nexus_r2_storage_cost_policy.json"
GOVERNOR_POLICY_PATH = ROOT / "configs/nexus_r2_data_governor_policy.json"
CERTIFICATION_JOB_TYPE = "NEXUS_R2_LIVE_CERTIFICATION"
PRODUCTION_JOB_TYPE = "CREATIVE_ASSET_PERSISTENCE"
_RUN_LOCK = threading.Lock()
_RUNS: dict[str, dict[str, Any]] = {}


class R2PolicyError(RuntimeError):
    pass


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise R2PolicyError("R2_GOVERNOR_CONFIGURATION_UNAVAILABLE") from exc
    if not isinstance(value, dict):
        raise R2PolicyError("R2_GOVERNOR_CONFIGURATION_INVALID")
    return value


def load_cost_policy() -> dict[str, Any]:
    value = _read(COST_POLICY_PATH)
    if value.get("storage_class") != "STANDARD":
        raise R2PolicyError("R2_COST_MODEL_STORAGE_CLASS_UNSUPPORTED")
    rates = value.get("rates_usd") or {}
    required = ("storage_gb_month", "class_a_per_million", "class_b_per_million", "egress_per_gb")
    if any(not isinstance(rates.get(key), (int, float)) or rates[key] < 0 for key in required):
        raise R2PolicyError("R2_COST_RATES_UNAVAILABLE")
    return value


def estimate_cost(*, action: str, upload_bytes: int = 0, download_bytes: int = 0,
                  class_a_count: int = 0, class_b_count: int = 0,
                  cost_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Calculate a gross upper bound without assuming free-tier availability."""
    policy = cost_policy or load_cost_policy()
    rates = policy["rates_usd"]
    if min(upload_bytes, download_bytes, class_a_count, class_b_count) < 0:
        raise ValueError("R2_USAGE_MUST_BE_NONNEGATIVE")
    # Reserve one full month of Standard storage for newly uploaded bytes.
    storage_gb_month = upload_bytes / 1_000_000_000
    operation_cost = (class_a_count * float(rates["class_a_per_million"])
                      + class_b_count * float(rates["class_b_per_million"])) / 1_000_000
    storage_cost = storage_gb_month * float(rates["storage_gb_month"])
    egress_cost = (download_bytes / 1_000_000_000) * float(rates["egress_per_gb"])
    total = operation_cost + storage_cost + egress_cost
    if not math.isfinite(total):
        raise R2PolicyError("R2_COST_ESTIMATE_INVALID")
    return {"cost": round(total, 12),
            "storage_gb_month": storage_gb_month, "class_a_count": class_a_count,
            "class_b_count": class_b_count, "upload_bytes": upload_bytes,
            "download_bytes": download_bytes, "action": action}


def operation_estimate(action: str, *, byte_count: int = 0) -> dict[str, Any]:
    """Bound one actual Standard-class S3 request shape."""
    action = action.upper()
    if byte_count < 0:
        raise ValueError("R2_USAGE_MUST_BE_NONNEGATIVE")
    if action == "OBJECT_PUT":
        if byte_count > 50 * 1024 * 1024:
            raise R2PolicyError("R2_SINGLE_OBJECT_LIMIT_EXCEEDED")
        # boto3's managed transfer may multipart-upload above its default
        # threshold. Reserve conservatively for create/upload/complete calls.
        part_size = 8 * 1024 * 1024
        class_a = 1 if byte_count < part_size else math.ceil(byte_count / part_size) + 2
        class_b = 0
        upload_bytes, download_bytes = byte_count, 0
    elif action in {"OBJECT_HEAD", "OBJECT_GET_METADATA"}:
        class_a = class_b = 0
        class_b = 1
        upload_bytes = download_bytes = 0
    elif action == "OBJECT_GET_VERIFICATION":
        class_a, class_b = 0, 1
        upload_bytes, download_bytes = 0, byte_count
    elif action == "OBJECT_DELETE_CERTIFICATION_ONLY":
        class_a = class_b = upload_bytes = download_bytes = 0
    elif action == "SIGNED_READ_URL":
        # Local presigning itself incurs no R2 request; the accompanying HEAD
        # check is separately governed as Class B.
        class_a = class_b = upload_bytes = download_bytes = 0
    else:
        raise R2PolicyError("R2_OPERATION_NOT_ALLOWED")
    cost = estimate_cost(action=action, upload_bytes=upload_bytes,
                         download_bytes=download_bytes, class_a_count=class_a,
                         class_b_count=class_b)
    return {"requests": 1, "operations": 1, "api_calls": 1,
            "bytes": upload_bytes + download_bytes, "upload_bytes": upload_bytes,
            "download_bytes": download_bytes, "class_a_count": class_a,
            "class_b_count": class_b, "object_count": int(action == "OBJECT_PUT"),
            "delete_operations": int(action == "OBJECT_DELETE_CERTIFICATION_ONLY"),
            "storage_bytes": upload_bytes, "billable": True,
            "cost_estimate_mode": "BOUNDED_ADVISORY", **cost}


def governor_estimate(action: str, *, byte_count: int = 0) -> dict[str, Any]:
    """Return numeric dimensions only; annotations stay in the usage receipt."""
    estimate = operation_estimate(action, byte_count=byte_count)
    return {key: value for key, value in estimate.items()
            if isinstance(value, (int, float, bool))}


def reserve_process_run_usage(job_id: str, action: str, detail: dict[str, Any],
                              limits: dict[str, Any]) -> None:
    """Apply a strict per-process certification/job envelope before I/O."""
    if not job_id:
        raise R2PolicyError("DURABLE_JOB_ID_REQUIRED")
    certification = "max_objects_per_run" in limits
    max_seconds = int(limits.get("max_runtime_seconds", limits.get("production_max_runtime_seconds", 0)))
    upload_cap = int(limits.get("max_total_upload_bytes_per_run", limits.get("production_max_bytes_per_job", 0)))
    single_cap = int(limits.get("max_single_object_bytes", upload_cap))
    class_a_cap = int(limits.get("max_class_a_operations_per_run", limits.get("production_max_operations_per_job", 0)))
    class_b_cap = int(limits.get("max_class_b_operations_per_run", limits.get("production_max_operations_per_job", 0)))
    object_cap = int(limits.get("max_objects_per_run", limits.get("production_max_objects_per_job", 0)))
    delete_cap = int(limits.get("max_delete_operations_per_run", 0)) if certification else 0
    if detail.get("upload_bytes", 0) > single_cap:
        raise R2PolicyError("R2_SINGLE_OBJECT_LIMIT_EXCEEDED")
    with _RUN_LOCK:
        current = _RUNS.get(job_id)
        if current is None:
            current = {"started": time.monotonic(), "objects": 0, "upload_bytes": 0,
                       "class_a": 0, "class_b": 0, "deletes": 0, "operations": 0}
        if max_seconds <= 0 or time.monotonic() - current["started"] >= max_seconds:
            raise R2PolicyError("R2_RUN_TIME_LIMIT_EXCEEDED")
        next_values = {
            "objects": current["objects"] + int(detail.get("object_count", 0)),
            "upload_bytes": current["upload_bytes"] + int(detail.get("upload_bytes", 0)),
            "class_a": current["class_a"] + int(detail.get("class_a_count", 0)),
            "class_b": current["class_b"] + int(detail.get("class_b_count", 0)),
            "deletes": current["deletes"] + int(detail.get("delete_operations", 0)),
            "operations": current["operations"] + int(detail.get("operations", 0)),
        }
        max_ops = (class_a_cap + class_b_cap) if certification else int(limits["production_max_operations_per_job"])
        if (next_values["objects"] > object_cap or next_values["upload_bytes"] > upload_cap
                or next_values["class_a"] > class_a_cap or next_values["class_b"] > class_b_cap
                or next_values["deletes"] > delete_cap or next_values["operations"] > max_ops):
            raise R2PolicyError("R2_RUN_OPERATION_LIMIT_EXCEEDED")
        _RUNS[job_id] = {**current, **next_values}


def policy_definitions() -> list[dict[str, Any]]:
    cfg = _read(GOVERNOR_POLICY_PATH)
    limits = cfg["certification_limits"]
    ceiling = float(cfg["certification_cost_ceiling_usd"])
    cert_usage = {
        "requests": limits["max_class_a_operations_per_run"] + limits["max_class_b_operations_per_run"],
        "operations": limits["max_class_a_operations_per_run"] + limits["max_class_b_operations_per_run"],
        "bytes": limits["max_total_upload_bytes_per_run"] + limits["max_single_object_bytes"],
        "upload_bytes": limits["max_total_upload_bytes_per_run"],
        "download_bytes": limits["max_total_upload_bytes_per_run"],
        "class_a_count": limits["max_class_a_operations_per_run"],
        "class_b_count": limits["max_class_b_operations_per_run"],
        "object_count": limits["max_objects_per_run"],
        "delete_operations": limits["max_delete_operations_per_run"],
        "runtime_seconds": limits["max_runtime_seconds"],
        "storage_bytes": limits["max_total_upload_bytes_per_run"],
        "cost": ceiling,
    }
    cert = {"provider": "CLOUDFLARE_R2", "service": "creative_canonical_storage",
        "job_type": CERTIFICATION_JOB_TYPE, "budget_period": "DAILY",
        "autonomous_usage_allowed": True, "autonomous_spend_allowed": True,
        "soft_limits": {"rate": {"requests": 20, "operations": 20, "window_seconds": 60},
                        "usage": cert_usage, "money": {"per_job": ceiling, "per_day": ceiling}},
        "hard_limits": {"rate": {"requests": 20, "operations": 20, "window_seconds": 60},
                        "usage": cert_usage, "money": {"per_job": ceiling, "per_day": ceiling}},
        "concurrency_limit": 1, "resource_creation_limit": 0,
        "state": "NORMAL", "approval_required": False}
    production = cfg["production_limits"]
    prod_usage = {
        "requests": production["production_max_operations_per_job"],
        "operations": production["production_max_operations_per_job"],
        "bytes": production["production_max_bytes_per_job"],
        "upload_bytes": production["production_max_bytes_per_job"],
        "download_bytes": production["production_max_bytes_per_job"],
        "class_a_count": production["production_max_operations_per_job"],
        "class_b_count": production["production_max_operations_per_job"],
        "object_count": production["production_max_objects_per_job"],
        "delete_operations": 0,
        "runtime_seconds": production["production_max_runtime_seconds"],
        "storage_bytes": production["production_max_bytes_per_job"],
        "cost": production["production_max_estimated_cost_usd_per_job"],
    }
    prod = {"provider": "CLOUDFLARE_R2", "service": "creative_canonical_storage",
        "job_type": PRODUCTION_JOB_TYPE, "budget_period": "DAILY",
        "autonomous_usage_allowed": False, "autonomous_spend_allowed": False,
        "soft_limits": {"rate": {"requests": 0, "operations": 0, "window_seconds": 60},
                        "usage": prod_usage, "money": {"per_job": prod_usage["cost"], "per_day": 0}},
        "hard_limits": {"rate": {"requests": 0, "operations": 0, "window_seconds": 60},
                        "usage": prod_usage, "money": {"per_job": prod_usage["cost"], "per_day": 0}},
        "concurrency_limit": 1, "resource_creation_limit": 0,
        "state": "HUMAN_APPROVAL_REQUIRED", "approval_required": True}
    return [cert, prod]


def ensure_r2_governor_policies(store: Any) -> dict[str, Any]:
    """Insert absent exact policies; never update a stop or an existing policy."""
    outcomes = []
    for policy in policy_definitions():
        inserted = store.ensure_policy(
            policy["provider"], policy["service"], policy["job_type"], policy["budget_period"],
            autonomous_usage_allowed=policy["autonomous_usage_allowed"],
            autonomous_spend_allowed=policy["autonomous_spend_allowed"],
            soft_limits=policy["soft_limits"], hard_limits=policy["hard_limits"],
            concurrency_limit=policy["concurrency_limit"],
            resource_creation_limit=policy["resource_creation_limit"],
            state=policy["state"], approval_required=policy["approval_required"])
        resolved = store.resolve_policy(policy["provider"], policy["service"], policy["job_type"], policy["budget_period"])
        existing_limits = (json.loads(resolved["hard_limits"]) if resolved and isinstance(resolved.get("hard_limits"), str)
                           else (resolved or {}).get("hard_limits"))
        if policy["job_type"] == PRODUCTION_JOB_TYPE and resolved and resolved.get("state") != "HARD_STOP":
            expected_limits = policy["hard_limits"]
            if (resolved.get("state") != "HUMAN_APPROVAL_REQUIRED"
                    or resolved.get("autonomous_usage_allowed") is not False
                    or resolved.get("autonomous_spend_allowed") is not False
                    or existing_limits != expected_limits):
                store.set_policy(
                    policy["provider"], policy["service"], policy["job_type"], policy["budget_period"],
                    autonomous_usage_allowed=False, autonomous_spend_allowed=False,
                    soft_limits=policy["soft_limits"], hard_limits=expected_limits,
                    concurrency_limit=policy["concurrency_limit"], state="HUMAN_APPROVAL_REQUIRED",
                    approval_required=True)
                resolved = store.resolve_policy(policy["provider"], policy["service"], policy["job_type"], policy["budget_period"])
                existing_limits = (json.loads(resolved["hard_limits"]) if resolved and isinstance(resolved.get("hard_limits"), str)
                                   else (resolved or {}).get("hard_limits"))
        exact = bool(resolved and not resolved.get("wildcard_fallback_used", False)
                     and resolved.get("job_type") == policy["job_type"]
                     and resolved.get("service") == policy["service"])
        limits_match = bool(resolved and existing_limits == policy["hard_limits"])
        outcomes.append({"job_type": policy["job_type"], "inserted": bool(inserted),
                         "verified": exact and limits_match, "state": (resolved or {}).get("state")})
    return {"policies": outcomes, "all_verified": all(item["verified"] for item in outcomes)}
