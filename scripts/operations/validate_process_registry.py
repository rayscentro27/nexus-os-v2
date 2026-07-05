#!/usr/bin/env python3
"""Validate nexus_process_registry.json schema and completeness."""

import json
import os
import sys
from datetime import datetime, timezone

REGISTRY_PATH = "data/operations/nexus_process_registry.json"
REPORT_PATH = "reports/runtime/nexus_process_registry_validation_latest.md"

REQUIRED_FIELDS = [
    "process_id", "name", "category", "mode", "enabled", "schedule_type",
    "trigger", "runner_path", "report_path", "receipt_path", "last_run_at",
    "last_status", "next_action", "risk_level", "approval_required",
    "telegram_allowed", "blocked_actions"
]

VALID_MODES = [
    "OBSERVE", "DRY_RUN", "SANDBOX_TEST", "ACTIVE_INTERNAL",
    "TELEGRAM_OPERATOR", "APPROVAL_GATED_LIVE", "APPROVED_LIVE", "BLOCKED"
]

VALID_RISK = ["low", "medium", "high"]

def validate():
    now = datetime.now(timezone.utc).isoformat()
    errors = []
    warnings = []

    if not os.path.exists(REGISTRY_PATH):
        errors.append(f"Registry file not found: {REGISTRY_PATH}")
        return errors, warnings

    with open(REGISTRY_PATH) as f:
        try:
            registry = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
            return errors, warnings

    if not isinstance(registry, list):
        errors.append("Registry must be a JSON array")
        return errors, warnings

    seen_ids = set()
    for i, process in enumerate(registry):
        pid = process.get("process_id", f"index_{i}")

        for field in REQUIRED_FIELDS:
            if field not in process:
                errors.append(f"[{pid}] Missing required field: {field}")

        if process.get("mode") not in VALID_MODES:
            errors.append(f"[{pid}] Invalid mode: {process.get('mode')}")

        if process.get("risk_level") not in VALID_RISK:
            errors.append(f"[{pid}] Invalid risk_level: {process.get('risk_level')}")

        if pid in seen_ids:
            errors.append(f"[{pid}] Duplicate process_id")
        seen_ids.add(pid)

        if process.get("enabled") and not process.get("runner_path"):
            warnings.append(f"[{pid}] Enabled but no runner_path")

    total = len(registry)
    enabled = sum(1 for p in registry if p.get("enabled"))
    telegram_allowed = sum(1 for p in registry if p.get("telegram_allowed"))

    report = f"""# Nexus Process Registry Validation

**Generated**: {now}
**Registry**: {REGISTRY_PATH}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Processes | {total} |
| Enabled | {enabled} |
| Telegram Allowed | {telegram_allowed} |
| Errors | {len(errors)} |
| Warnings | {len(warnings)} |

---

## Errors

"""
    if errors:
        for e in errors:
            report += f"- {e}\n"
    else:
        report += "None\n"

    report += "\n---\n\n## Warnings\n\n"
    if warnings:
        for w in warnings:
            report += f"- {w}\n"
    else:
        report += "None\n"

    report += "\n---\n\n## Process List\n\n"
    report += "| ID | Name | Mode | Enabled | Telegram | Risk |\n"
    report += "|----|------|------|---------|----------|------|\n"
    for p in registry:
        report += f"| {p.get('process_id','')} | {p.get('name','')} | {p.get('mode','')} | {p.get('enabled','')} | {p.get('telegram_allowed','')} | {p.get('risk_level','')} |\n"

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    return errors, warnings

if __name__ == "__main__":
    errors, warnings = validate()
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} errors")
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    else:
        print(f"VALIDATION PASSED: {len(warnings)} warnings")
        sys.exit(0)
