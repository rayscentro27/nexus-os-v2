"""Deterministic, task-scoped evidence projection for Hermes synthesis.

This module never writes canonical state and never produces authoritative prose.
It projects an already-authorized read result into a small, provenance-bearing
contract that a reasoning layer may interpret.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable


EVIDENCE_CLASSES = {"FACT", "ESTIMATE", "ASSUMPTION", "UNKNOWN"}


def _item(claim: str, value: Any, kind: str, source: str, freshness: str,
          confidence: str = "HIGH", authority: str = "TRUTHKERNEL") -> Dict[str, Any]:
    if kind not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence class: {kind}")
    return {
        "claim": claim,
        "type": kind,
        "value": value,
        "source": source,
        "freshness": freshness,
        "confidence": confidence,
        "authority": authority,
    }


def project_evidence(request: str, capability: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Project one certified read result without exposing unrelated state."""
    provenance = result.get("provenance") or {}
    source = provenance.get("source_path") or provenance.get("source") or "UNKNOWN"
    freshness = provenance.get("freshness") or result.get("freshness") or "UNKNOWN"
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    evidence = []
    unknowns = []

    if result.get("status") not in {"ok", "OK", "success"}:
        reason = result.get("error") or f"capability returned {result.get('status', 'UNKNOWN')}"
        unknowns.append(_item(f"{capability} result", reason, "UNKNOWN", source, freshness,
                              confidence="LOW", authority="TRUTHKERNEL"))
    else:
        # Keep projection generic and bounded. Domain-specific handlers can add
        # named facts without changing the contract.
        for key, value in data.items():
            if key in {"provenance", "secret", "token", "credential", "password"}:
                continue
            evidence.append(_item(f"{capability}.{key}", value, "FACT", source, freshness))
        if not evidence:
            unknowns.append(_item(f"{capability} detail", "No structured detail returned",
                                  "UNKNOWN", source, freshness, confidence="LOW"))

    return {
        "request": request,
        "capability": capability,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "evidence": evidence,
        "unknowns": unknowns,
        "conflicts": [],
        "allowed_capabilities": [capability] if result.get("status") in {"ok", "OK", "success"} else [],
        "authority": "TRUTHKERNEL",
    }


def evidence_summary(payload: Dict[str, Any]) -> Dict[str, int]:
    items = list(payload.get("evidence", [])) + list(payload.get("unknowns", []))
    return {kind: sum(1 for item in items if item.get("type") == kind) for kind in EVIDENCE_CLASSES}
