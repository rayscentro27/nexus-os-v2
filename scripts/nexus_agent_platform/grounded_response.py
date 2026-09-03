"""Narrow grounding boundary for executive/current-state responses.

Hermes remains responsible for prose and recommendations.  This module owns
only facts whose truth must come from the executing runtime or a governed
read-only capability.  It is deliberately not a general response validator.
"""

from __future__ import annotations

import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def requires_current_evidence(request: str) -> bool:
    """Detect requests that explicitly ask for current or runtime facts."""
    text = str(request or "").lower()
    return bool(
        re.search(r"\b(current|right now|today|available|health|what happened|runtime|version|model|python|operating system|podman)\b", text)
        and re.search(r"\b(nexus|system|hermes|finance|alpha|model|python|operating|podman|runtime|health)\b", text)
    )


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def collect_verified_current_state(runtime: Dict[str, Any]) -> Dict[str, Any]:
    """Build a secret-free, read-only evidence object from canonical readers."""
    evidence: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "host": runtime.get("runtime_host", "UNKNOWN"),
            "hermes_version": runtime.get("hermes_version", "UNKNOWN"),
            "profile": runtime.get("profile", "UNKNOWN"),
            "provider": runtime.get("provider", "UNKNOWN"),
            "model": runtime.get("model", "UNKNOWN"),
            "source": "oracle_bridge_runtime_envelope",
            "provenance": "CURRENT",
        },
        "health": {"status": "UNKNOWN", "raw": {}, "source": "UNKNOWN", "provenance": "UNKNOWN"},
        "specialists": {},
        "priority": {"classification": "UNKNOWN", "summary": "Current priority was not verified.", "source": "UNKNOWN"},
    }
    # Read the canonical bounded artifact directly.  Calling the full health
    # capability here can include telemetry/database work; the Telegram
    # response contract must not turn that into an unbounded nested request.
    try:
        path = Path(__file__).resolve().parents[2] / "reports/hermes_modernization/live_runtime_status.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        contract = raw.get("contract", {})
        degraded = sum(1 for row in contract.values() if isinstance(row, dict) and row.get("status") in {"DEGRADED", "STALE"})
        failed = len(raw.get("evidence", {}).get("failures", []))
        worker_status = Path(__file__).resolve().parents[2] / "data/runtime/nova_telegram_status.json"
        worker_running = False
        if worker_status.exists():
            try:
                worker_running = json.loads(worker_status.read_text(encoding="utf-8")).get("state") == "RUNNING"
            except (OSError, ValueError):
                pass
        evidence["health"] = {
            "status": "FAILED" if failed else ("OPERATIONAL_WITH_TELEMETRY_DEGRADED" if degraded else ("HEALTHY" if worker_running or raw.get("nexus_running") == "YES" else "UNKNOWN")),
            "raw": {"overall_status": raw.get("nexus_running", "UNKNOWN"), "worker_running": worker_running, "active_services": None, "degraded_services": degraded, "failed_services": failed},
            "source": "reports/hermes_modernization/live_runtime_status.json",
            "provenance": "CURRENT",
            "interpretation": "Nexus runtime evidence is available; individual degraded sources are reported separately from the Telegram-to-Oracle path.",
        }
    except Exception:
        pass

    # Capability registry status is the canonical availability check for the
    # bounded Alpha lane.  Finance is a governed capability path rather than a
    # standalone agent registry entry, so verify its read-only rollup path.
    try:
        path = Path(__file__).resolve().parents[2] / "data/runtime/alpha_telegram_status.json"
        alpha = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        evidence["specialists"]["alpha"] = {
            "availability": "AVAILABLE" if path.exists() else "UNKNOWN",
            "source": "data/runtime/alpha_telegram_status.json",
            "provenance": "CURRENT",
        }
    except Exception as exc:
        evidence["specialists"]["alpha"] = {"availability": "UNKNOWN", "source": type(exc).__name__, "provenance": "UNKNOWN"}

    try:
        root = Path(__file__).resolve().parents[2]
        finance_path = root / "scripts/nexus_agent_platform/finance/engine.py"
        ledger = root / "data/governed/finance_resource_ledger.jsonl"
        if not finance_path.exists() or not ledger.exists():
            raise RuntimeError("governed_finance_path_unavailable")
        evidence["specialists"]["finance"] = {
            "availability": "AVAILABLE",
            "source": "GOVERNED_FINANCE_ROLLUP",
            "provenance": "CURRENT",
        }
    except Exception as exc:
        evidence["specialists"]["finance"] = {"availability": "UNKNOWN", "source": type(exc).__name__, "provenance": "UNKNOWN"}

    try:
        from nexus_agent_platform.capabilities.operational_reads import read_operational_capability
        approvals = read_operational_capability("APPROVAL_QUEUE")
        items = (approvals.get("data") or {}).get("items", []) if approvals.get("status") in {"OK", "success"} else []
        if not items:
            from nexus_agent_platform.governed.approvals import get_pending_approvals
            items = get_pending_approvals(requested_for="ray", include_self=False)
        ray_items = [item for item in items if item.get("approval_required") is True]
        if ray_items:
            top = ray_items[0]
            evidence["priority"] = {
                "classification": "REQUIRES_RAY",
                "summary": str(top.get("title") or top.get("exact_action_requested") or "A governed approval is pending."),
                "source": approvals.get("source_path", "APPROVAL_QUEUE"),
                "provenance": "CURRENT",
            }
        else:
            evidence["priority"] = {"classification": "SOLVABLE_WITH_EXISTING_CAPABILITY", "summary": "No current governed approval requiring Ray was found.", "source": "APPROVAL_QUEUE", "provenance": "CURRENT"}
    except Exception:
        pass
    return evidence


_FACT_LABEL = re.compile(
    r"^(?:python(?:\s+version)?|operating\s+system(?:\s+version)?|os(?:\s+version)?|podman(?:\s+version)?|hermes(?:\s+runtime)?(?:\s+version)?|runtime(?:\s+host|\s+version)?|provider(?:\s*/\s*model)?|model|finance|alpha)\s*[:：-]",
    re.I,
)


def _normalized_line(line: str) -> str:
    value = re.sub(r"^\s*(?:[-*•]\s*|\d+[.)]\s*)", "", line)
    value = value.replace("**", "").replace("`", "").strip()
    return value


def _verified_lines(evidence: Dict[str, Any]) -> list[str]:
    runtime = evidence["runtime"]
    health = evidence["health"]
    specialists = evidence["specialists"]
    priority = evidence["priority"]
    return [
        "Verified current facts (from runtime and governed read-only evidence):",
        f"- Health: {health.get('status', 'UNKNOWN')}; raw active={health.get('raw', {}).get('active_services', 'UNKNOWN')}, degraded={health.get('raw', {}).get('degraded_services', 'UNKNOWN')}, failed={health.get('raw', {}).get('failed_services', 'UNKNOWN')}.",
        f"- Priority: {priority.get('summary', 'UNKNOWN')} ({priority.get('classification', 'UNKNOWN')}).",
        f"- Finance availability: {specialists.get('finance', {}).get('availability', 'UNKNOWN')}.",
        f"- Alpha availability: {specialists.get('alpha', {}).get('availability', 'UNKNOWN')}.",
        f"- Hermes runtime: {runtime.get('host', 'UNKNOWN')} Hermes {runtime.get('hermes_version', 'UNKNOWN')}, profile {runtime.get('profile', 'UNKNOWN')}, {runtime.get('provider', 'UNKNOWN')} / {runtime.get('model', 'UNKNOWN')}.",
        "- Python, operating-system, and Podman versions: UNKNOWN unless separately verified; not inferred from the model response.",
    ]


def ground_response(response: str, request: str, runtime: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """Ground only current-state responses and return the evidence object."""
    if not requires_current_evidence(request):
        return str(response or "").strip(), {}
    evidence = collect_verified_current_state(runtime)
    # Remove model-authored field claims only where deterministic evidence now
    # owns that field.  Narrative, analysis, and recommendations remain intact.
    kept = []
    owned_section = False
    for line in str(response or "").splitlines():
        heading = line.strip().lower()
        if re.search(r"highest[- ]priority|priority work item", heading):
            owned_section = True
            continue
        if re.search(r"(?:current )?system health|availability(?: of resources| of finance)|hermes runtime", heading):
            owned_section = True
            continue
        if owned_section and re.search(r"availability|hermes runtime|runtime|let me know", heading):
            owned_section = False
        if owned_section or _FACT_LABEL.match(_normalized_line(line)):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()
    return (text + "\n\n" if text else "") + "\n".join(_verified_lines(evidence)), evidence


def response_completeness(response: str) -> Dict[str, bool]:
    """General multipart coverage check for the grounded executive surface."""
    text = str(response or "").lower()
    return {
        "system_health": "health:" in text,
        "ray_priority": "priority:" in text,
        "finance": "finance availability:" in text,
        "alpha": "alpha availability:" in text,
        "runtime": "hermes runtime:" in text,
    }
