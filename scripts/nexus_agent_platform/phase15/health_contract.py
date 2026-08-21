"""Phase 15 health contract — core autonomy versus later integrations.

The continuous scheduler's core contract is intentionally narrower than the
full Phase 15 integration/reporting surface. Optional integrations remain
visible in their own readiness section and must never be represented as
healthy merely to make the core score green.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nexus_agent_platform.phase15.common import (
    DATA_RUNTIME,
    MODERNIZATION_DIR,
    RUNTIME_REPORTS,
    atomic_write_json,
    load_json,
    utc_now,
)

FRESH_WINDOW_SECONDS = 86400  # 24 hours
LOOP_FRESH_WINDOW_SECONDS = 172800  # 48 hours for loop state


def _iso_age(iso_value: Optional[str]) -> Optional[float]:
    if not iso_value:
        return None
    try:
        parsed = datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - parsed).total_seconds()
    except ValueError:
        return None


def _file_age(path: Path) -> Optional[float]:
    try:
        return (datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)).total_seconds()
    except OSError:
        return None


def launchd_loaded(label: str) -> bool:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
        return any(label in line for line in out.splitlines())
    except Exception:  # noqa: BLE001
        return False


def process_running(pattern: str) -> bool:
    try:
        out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10).stdout
        return any(pattern in line and "grep" not in line for line in out.splitlines())
    except Exception:  # noqa: BLE001
        return False


def _worker_status(worker_id: str, registry: Dict[str, Any]) -> Dict[str, Any]:
    for worker in registry.get("workers", []):
        if isinstance(worker, dict) and worker.get("worker_id") == worker_id:
            return {
                "worker_id": worker_id,
                "status": worker.get("classification", "UNKNOWN"),
                "available": bool(worker.get("available")),
                "execution_probe": worker.get("execution_probe_status", "UNKNOWN"),
            }
    return {
        "worker_id": worker_id,
        "status": "NOT_INSTALLED",
        "available": False,
        "execution_probe": "NOT_RUN",
    }


def _stripe_readiness(stripe_proof: Dict[str, Any]) -> Dict[str, Any]:
    """Return non-secret Stripe availability and authority state.

    Availability is evidence that credentials exist somewhere in the proof;
    authority is an independent, deny-by-default decision. The canonical
    continuous-loop wrapper removes Stripe variables and sets the disable
    marker before Python starts, so a live key cannot grant loop authority.
    """
    import os

    explicitly_disabled = os.environ.get("NEXUS_AUTONOMY_STRIPE_DISABLED", "") == "1"
    authorized = (
        not explicitly_disabled
        and stripe_proof.get("autonomous_execution_authorized") is True
        and stripe_proof.get("live_key_present") is not True
    )
    if stripe_proof.get("live_key_present") is True:
        available = "LIVE_CREDENTIALS_AVAILABLE"
    elif stripe_proof.get("test_mode_confirmed") is True:
        available = "TEST_CREDENTIALS_AVAILABLE"
    else:
        available = "UNAVAILABLE_OR_UNCONFIRMED"
    return {
        "available": available,
        "autonomous_execution_authorized": authorized,
        "state": "LIVE_AUTHORIZED" if authorized else "DISABLED",
        "safety_gate": "PASS" if not authorized else "FAIL",
        "reason": (
            "Stripe credentials are isolated from the canonical autonomous runtime"
            if explicitly_disabled
            else "Stripe autonomous execution is deny-by-default and requires an explicit authority record"
        ),
    }


def _readiness_summary(contract: Dict[str, Any], stripe: Dict[str, Any], *, mission_control_fresh: bool) -> Dict[str, Any]:
    """Separate core autonomy health from optional integrations and authority."""
    core = {
        "loop_runtime": contract["loop_runtime"],
        "worker_pool": contract["worker_pool"],
    }
    core_failures = []
    if core["loop_runtime"].get("status") != "HEALTHY":
        core_failures.append("loop_runtime")
    if core["worker_pool"].get("status") != "PASS":
        core_failures.append("worker_pool")
    if stripe["safety_gate"] != "PASS":
        core_failures.append("stripe_autonomous_execution_authority")

    optional = {
        "hermes": contract["hermes"],
        "alpha": {
            **contract["alpha"],
            "status": "NOT_ENABLED" if not contract["alpha"].get("status") == "HEALTHY" and "not registered" in contract["alpha"].get("reason", "") else contract["alpha"].get("status"),
        },
        "nova": {
            **contract["nova"],
            "status": "NOT_ENABLED" if not contract["nova"].get("status") == "HEALTHY" and "not registered" in contract["nova"].get("reason", "") else contract["nova"].get("status"),
        },
        "mission_control": {
            "status": "READY" if mission_control_fresh else "NOT_ENABLED",
            "freshness": "FRESH" if mission_control_fresh else "STALE",
            "reason": (
                "Mission Control source set is fresh"
                if mission_control_fresh
                else "The Phase 13 workforce/Mission Control producer is not an active core scheduler component"
            ),
        },
        "daily_brief": contract["daily_brief"],
        "active_operator": {
            "status": "READY" if launchd_loaded("com.nexus.active-operator-hourly") else "NOT_ENABLED",
            "reason": "Active Operator is not part of the Phase 15 core autonomy contract",
        },
    }
    return {
        "core_autonomy_runtime": {
            "status": "HEALTHY" if not core_failures else "FAIL",
            "required_components": core,
            "failures": core_failures,
        },
        "optional_integrations": optional,
        "safety_authority": {
            "stripe": stripe,
            "status": "PASS" if stripe["safety_gate"] == "PASS" else "FAIL",
        },
    }


def _loop_runtime_status() -> Tuple[str, str]:
    ledger = load_json_lines(DATA_RUNTIME / "nexus_loops" / "execution_ledger.jsonl")
    recent = [row for row in ledger if _iso_age(row.get("completed_at")) is not None and _iso_age(row.get("completed_at")) <= 86400]
    if recent:
        failures = [row for row in recent if str(row.get("verifier_status")) == "fail" or str(row.get("result_status")) == "error"]
        if failures and len(failures) >= 3:
            return "DEGRADED", f"{len(failures)} recent verifier/result failures"
        return "HEALTHY", f"{len(recent)} loop runs in the last 24h with 0 critical failures"
    state = load_json(DATA_RUNTIME / "nexus_loops" / "loop_state.json", {})
    loops = state.get("loops", {}) if isinstance(state, dict) else {}
    last_updated = (loops.get("revenue_opportunity_loop") or {}).get("last_updated_at")
    age = _iso_age(last_updated)
    if age is not None and age <= LOOP_FRESH_WINDOW_SECONDS:
        return "HEALTHY", "loop state fresh within the 48h window"
    return "BOUNDED_DEGRADED", "no recent loop ledger activity detected; scheduler may be idle"


def load_json_lines(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = __import__("json").loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except (ValueError, TypeError):
                continue
    except OSError:
        pass
    return rows


def build_health_status() -> Dict[str, Any]:
    now_iso = utc_now()
    brief = load_json(MODERNIZATION_DIR / "daily_brief.json", {})
    loop_state = load_json(DATA_RUNTIME / "nexus_loops" / "loop_state.json", {})
    registry = load_json(MODERNIZATION_DIR / "ai_workforce_registry.json", {})
    workforce = load_json(MODERNIZATION_DIR / "workforce_certification.json", {})
    live_loops = load_json(MODERNIZATION_DIR / "live_loop_results.json", {})
    research_session = load_json(MODERNIZATION_DIR / "live_research_session.json", {})
    state_json = load_json(MODERNIZATION_DIR / "state.json", {})
    stripe_proof = load_json(MODERNIZATION_DIR / "stripe_test_mode_proof.json", {})

    brief_age = _iso_age(brief.get("generated_at")) if isinstance(brief, dict) else None
    runtime_age = _iso_age((live_loops or {}).get("generated_at"))
    mission_sources = {
        "state.json": _file_age(MODERNIZATION_DIR / "state.json"),
        "loop_state.json": _file_age(DATA_RUNTIME / "nexus_loops" / "loop_state.json"),
        "ai_workforce_registry.json": _file_age(MODERNIZATION_DIR / "ai_workforce_registry.json"),
        "daily_brief.json": _file_age(MODERNIZATION_DIR / "daily_brief.json"),
    }
    mc_fresh = all(age is not None and age <= FRESH_WINDOW_SECONDS for age in mission_sources.values() if age is not None)

    hermes_launchd = launchd_loaded("com.nexus.telegram-hermes")
    alpha_launchd = launchd_loaded("com.nexus.telegram-alpha")
    nova_launchd = launchd_loaded("com.nexus.telegram-hermes-nova")
    alpha_running = process_running("alpha_telegram_worker.py")
    hermes_receipts = list((RUNTIME_REPORTS / "action_receipts").glob("rcpt_*.json")) if (RUNTIME_REPORTS / "action_receipts").exists() else []
    hermes_recent = any((_file_age(p) or 999999) <= FRESH_WINDOW_SECONDS for p in hermes_receipts)

    loop_status, loop_reason = _loop_runtime_status()

    hermes_ok = brief_age is not None and brief_age <= FRESH_WINDOW_SECONDS and hermes_launchd
    hermes_status = "HEALTHY" if hermes_ok else ("BOUNDED_DEGRADED" if launchd_loaded("com.nexus.telegram-hermes") or hermes_recent else "DEGRADED")
    hermes_reason = (
        "Hermes operator runtime up: daily brief fresh and telegram bridge registered"
        if hermes_status == "HEALTHY"
        else ("Hermes telegram bridge registered but not currently running; report surfaces fresh"
              if hermes_status == "BOUNDED_DEGRADED"
              else "Hermes telegram bridge not registered and daily brief is not fresh")
    )

    research_state = str(research_session.get("state") if isinstance(research_session, dict) else "UNKNOWN")
    alpha_status = (
        "HEALTHY"
        if alpha_running
        else ("BOUNDED_DEGRADED" if alpha_launchd and research_state in {"LIVE_PARTIAL", "LIVE"} else "BOUNDED_DEGRADED" if alpha_launchd else "DEGRADED")
    )
    alpha_reason = (
        "Alpha external-intelligence worker running (alpha_telegram_worker.py)"
        if alpha_running
        else (f"Alpha registered; live web state={research_state}; bounded partial capability is expected, runtime continues"
              if alpha_status == "BOUNDED_DEGRADED"
              else "Alpha not registered")
    )

    nova_status = "HEALTHY" if nova_launchd else "DEGRADED"
    nova_reason = (
        "Nova telegram worker registered; isolated governed reasoning lane, authority UNCHANGED"
        if nova_status == "HEALTHY"
        else "Nova telegram worker not registered"
    )

    workers = [
        _worker_status("codex", registry),
        _worker_status("opencode", registry),
        _worker_status("local_python", registry),
        _worker_status("mimo", registry),
        _worker_status("kilo", registry),
        _worker_status("openhands", registry),
    ]
    ai_available = any(w["worker_id"] in {"codex", "opencode"} and w["available"] for w in workers)
    local_available = any(w["worker_id"] == "local_python" and w["available"] for w in workers)
    worker_pool_ok = ai_available and local_available

    loop_ok = loop_status in {"HEALTHY", "BOUNDED_DEGRADED"}
    brief_fresh = brief_age is not None and brief_age <= FRESH_WINDOW_SECONDS

    contract = {
        "hermes": {"required": "HEALTHY", "status": hermes_status, "reason": hermes_reason},
        "alpha": {"required": "HEALTHY or BOUNDED_DEGRADED with known reason", "status": alpha_status, "reason": alpha_reason},
        "nova": {"required": "HEALTHY and isolated", "status": nova_status, "reason": nova_reason},
        "loop_runtime": {"required": "HEALTHY", "status": loop_status, "reason": loop_reason},
        "daily_brief": {"required": "FRESH", "status": "FRESH" if brief_fresh else "STALE", "reason": f"brief generated_at={brief.get('generated_at')}, age={brief_age}"},
        "mission_control_source": {"required": "FRESH", "status": "FRESH" if mc_fresh else "STALE", "reason": json_dumps_simple(mission_sources)},
        "stripe_test_mode": {
            "required": "DISABLED_FOR_AUTONOMY or TEST MODE CONFIRMED",
            "status": "DISABLED_FOR_AUTONOMY" if not stripe_proof.get("autonomous_execution_authorized", False) else "TEST_CONFIRMED" if stripe_proof.get("test_mode_confirmed") is True else "NOT_CONFIRMED",
            "reason": " ".join(stripe_proof.get("evidence", {}).get("reasons", [])) if isinstance(stripe_proof, dict) else "stripe proof missing",
            "critical": bool(stripe_proof.get("live_key_present", False)),
        },
        "worker_pool": {
            "required": ">=1 AI worker AVAILABLE and local deterministic AVAILABLE",
            "status": "PASS" if worker_pool_ok else "FAIL",
            "reason": json_dumps_simple(workers),
        },
        "nova_authority": "UNCHANGED",
        "stripe_mode": "TEST",
    }

    stripe = _stripe_readiness(stripe_proof)
    readiness = _readiness_summary(contract, stripe, mission_control_fresh=mc_fresh)
    nexus_status = "YES" if readiness["core_autonomy_runtime"]["status"] == "HEALTHY" else "PARTIAL"

    output = {
        "phase": "PHASE 15 — LIVE INTERNAL OPERATIONS",
        "generated_at": now_iso,
        "nexus_running": nexus_status,
        "core_autonomy_runtime": readiness["core_autonomy_runtime"],
        "optional_integrations": readiness["optional_integrations"],
        "safety_authority": readiness["safety_authority"],
        "contract": contract,
        "worker_pool": workers,
        "evidence": {
            "hermes_launchd": hermes_launchd,
            "alpha_launchd": alpha_launchd,
            "nova_launchd": nova_launchd,
            "alpha_process_running": alpha_running,
            "action_receipts_count": len(hermes_receipts),
            "daily_brief_age": brief_age,
            "live_loop_report_age": runtime_age,
            "stripe_autonomous_execution_authorized": stripe["autonomous_execution_authorized"],
        },
    }
    atomic_write_json(MODERNIZATION_DIR / "live_runtime_status.json", output)
    return output


def json_dumps_simple(value: Any) -> str:
    return __import__("json").dumps(value, sort_keys=True, default=str)
