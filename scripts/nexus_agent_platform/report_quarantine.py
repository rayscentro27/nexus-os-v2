"""Deterministic classification of report provenance for Nova reads."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict


def classify_report(path: str, data: Any = None) -> Dict[str, Any]:
    name = str(path or "UNKNOWN").lower()
    text = str(data if isinstance(data, dict) else "").lower()
    if isinstance(data, dict) and str(data.get("source_type", "")).lower() in {
        "live_governed_state", "current_runtime_ledger", "live_database",
        "live_receipt", "live_heartbeat", "live_artifact_index", "live_research_artifact",
    }:
        return {"provenance": "REAL_CURRENT", "current_truth_eligible": True,
                "historical_reference_allowed": True,
                "reason": "Explicit live canonical source metadata."}
    if any(x in name for x in ("fixture", "synthetic", "simulation", "dry_run", "test_")) or any(x in text for x in ("safe_synthetic", "synthetic_only", "fixture-driven", "dry_run")):
        provenance = "SYNTHETIC" if "synthetic" in name or "synthetic" in text else "FIXTURE"
        return {"provenance": provenance, "current_truth_eligible": False, "historical_reference_allowed": True, "reason": "Synthetic or fixture evidence cannot establish current truth."}
    if any(x in name for x in ("development", "benchmark", "preflight")):
        return {"provenance": "DEVELOPMENT", "current_truth_eligible": False, "historical_reference_allowed": True, "reason": "Development artifact is not current operational evidence."}
    if name.startswith("reports/hermes_modernization/") or "legacy" in name:
        return {"provenance": "LEGACY_UNKNOWN", "current_truth_eligible": False, "historical_reference_allowed": True, "reason": "Legacy report provenance is insufficient for current truth."}
    if name.startswith("reports/runtime/") or name.startswith("data/runtime/"):
        realness = re.search(r"real|launchd|receipt|heartbeat|governed|truthkernel", text)
        return {"provenance": "REAL_CURRENT" if realness else "UNKNOWN", "current_truth_eligible": bool(realness), "historical_reference_allowed": True, "reason": "Runtime source requires explicit real-evidence metadata."}
    return {"provenance": "UNKNOWN", "current_truth_eligible": False, "historical_reference_allowed": True, "reason": "Source provenance not established."}
