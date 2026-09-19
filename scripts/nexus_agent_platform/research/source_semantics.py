"""Durable source-purpose semantics for Research selection and provenance."""
from __future__ import annotations

from typing import Any

TEST_EXAMPLE = "TEST_EXAMPLE"
HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"
INSTALLED_CAPABILITY = "INSTALLED_CAPABILITY"
MONITOR_ONLY = "MONITOR_ONLY"
ACTIVE_DISCOVERY = "ACTIVE_DISCOVERY"
ACTIVE_INVESTIGATION = "ACTIVE_INVESTIGATION"
EXTERNAL_EVIDENCE_SOURCE = "EXTERNAL_EVIDENCE_SOURCE"

LEGACY_TEST_SOURCE_IDS = {
    "mobile-detailing-academy-phoenix": TEST_EXAMPLE,
    "hubspot-affiliate": TEST_EXAMPLE,
    "shopify-partners": TEST_EXAMPLE,
}

INSTALLED_CAPABILITY_IDS = {
    "mvanhorn/last30days-skill": INSTALLED_CAPABILITY,
    "sushantkarn/SEO-engine": INSTALLED_CAPABILITY,
}


def source_purpose(source_id: str | None, *, explicit: str | None = None,
                   work_class: str | None = None, lifecycle: str | None = None) -> str:
    if explicit:
        return str(explicit).upper()
    key = str(source_id or "").strip()
    if key in LEGACY_TEST_SOURCE_IDS:
        return LEGACY_TEST_SOURCE_IDS[key]
    if key in INSTALLED_CAPABILITY_IDS:
        return INSTALLED_CAPABILITY_IDS[key]
    if str(work_class or "").upper() == "ASSIGNED" or str(lifecycle or "").upper() == "ONE_TIME":
        return ACTIVE_INVESTIGATION
    if str(work_class or "").upper() in {"DEMAND_DISCOVERY", "GENERAL_DISCOVERY"}:
        return ACTIVE_DISCOVERY
    return EXTERNAL_EVIDENCE_SOURCE


def annotate(item: dict[str, Any]) -> dict[str, Any]:
    return {**item, "source_purpose": source_purpose(
        item.get("source_id"), explicit=item.get("source_purpose"),
        work_class=item.get("work_class") or item.get("selected_work_class"),
        lifecycle=item.get("lifecycle"),
    )}


def autonomous_discovery_allowed(item: dict[str, Any]) -> bool:
    purpose = source_purpose(item.get("source_id"), explicit=item.get("source_purpose"),
                             work_class=item.get("work_class") or item.get("selected_work_class"),
                             lifecycle=item.get("lifecycle"))
    return purpose not in {TEST_EXAMPLE, HISTORICAL_REFERENCE, INSTALLED_CAPABILITY}


__all__ = [
    "TEST_EXAMPLE", "HISTORICAL_REFERENCE", "INSTALLED_CAPABILITY", "MONITOR_ONLY",
    "ACTIVE_DISCOVERY", "ACTIVE_INVESTIGATION", "EXTERNAL_EVIDENCE_SOURCE",
    "LEGACY_TEST_SOURCE_IDS", "INSTALLED_CAPABILITY_IDS", "source_purpose",
    "annotate", "autonomous_discovery_allowed",
]
