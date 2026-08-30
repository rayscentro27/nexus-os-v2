"""Compact, provenance-preserving truth view for Nova.

This is an adapter over existing canonical readers, not a second truth store.
It intentionally returns claims with freshness and certification metadata so a
conversation can remain natural without losing source discipline.
"""

from __future__ import annotations

from typing import Any, Dict


def _claim(domain: str, value: Any, source: str, source_type: str,
           timestamp: Any, freshness: Any, *, real_or_test: str = "UNKNOWN",
           certification: str = "NOT_PROVEN", confidence: str = "MEDIUM",
           contradictions=None) -> Dict[str, Any]:
    return {
        "domain": domain,
        "value": value,
        "source": source,
        "source_type": source_type,
        "timestamp": timestamp or "UNKNOWN",
        "freshness": freshness or "UNKNOWN",
        "real_or_test": real_or_test,
        "certification_level": certification,
        "confidence": confidence,
        "contradictions": list(contradictions or []),
    }


def read_truth_domains(*domains: str) -> Dict[str, Any]:
    """Read selected current domains through existing approved adapters."""
    from nexus_agent_platform.capabilities.operational_reads import read_operational_capability
    from nexus_agent_platform.report_quarantine import classify_report

    requested = tuple(domains) or ("NEXUS_RUNTIME", "SYSTEM_HEALTH", "RAY_REVIEW", "RESEARCH")
    aliases = {
        "NEXUS_RUNTIME": "SYSTEM_HEALTH",
        "ACTIVE_OPERATOR": "SYSTEM_HEALTH",
        "SYSTEM_HEALTH": "SYSTEM_HEALTH",
        "RAY_REVIEW": "APPROVAL_QUEUE",
        "RESEARCH": "ALPHA_LATEST",
        "RECENT_ACTIVITY": "DAILY_BRIEF",
        "CLIENTS": "CLIENT_COUNT",
    }
    claims = []
    reads = {}
    for domain in requested:
        capability = aliases.get(domain, domain)
        result = read_operational_capability(capability)
        reads[domain] = result
        data = result.get("data", {}) if isinstance(result, dict) else {}
        status = result.get("status", "UNAVAILABLE") if isinstance(result, dict) else "UNAVAILABLE"
        assessment = classify_report(result.get("source_path", "UNKNOWN"), data)
        eligible = status == "OK" and assessment["current_truth_eligible"]
        claims.append(_claim(
            domain,
            data if eligible else {"status": "UNKNOWN", "reason": assessment["reason"]},
            result.get("source_path", "UNKNOWN"),
            result.get("source_type", "UNKNOWN"),
            result.get("as_of", "UNKNOWN"),
            result.get("freshness", "UNKNOWN"),
            certification="REAL_WORLD_CERTIFIED_BOUNDED" if eligible else "NOT_PROVEN",
            confidence="HIGH" if eligible else "LOW",
        ))
    return {
        "view": "NOVA_TRUTH_VIEW",
        "domains": list(requested),
        "claims": claims,
        "reads": reads,
        "authority": "NEXUS_TRUTHKERNEL_CANONICAL_READS",
        "independent_truth_store": False,
    }


def capability_discovery() -> Dict[str, Any]:
    """Compact conceptual map used for Nova context/tool discovery."""
    return {
        "NEXUS_OS": {"read": ["runtime", "health", "work orders", "receipts", "clients"], "write": "Nexus/TruthKernel only"},
        "HERMES_OPERATIONS": {"submit": "bounded Nexus request", "execute": "Nexus authority path only"},
        "ALPHA_RESEARCH": {"read": ["research artifacts", "decisions", "source metadata"], "fresh_research": "approved free/private path first"},
        "boundaries": ["privacy", "cost", "direct execution", "external consequential action"],
    }
