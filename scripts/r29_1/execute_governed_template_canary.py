"""Execute the single approved R29.1 governed-template canary.

This runner is intentionally narrow: it accepts only the registry's
approval-gated ``controlled_announcement`` template, the configured safe test
recipient, and one fixed idempotency key. Secrets and recipient values are
never printed or persisted.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/customer_email_template_registry.json"
REPORT = ROOT / "reports/runtime/r29_1/governed_template_canary_latest.json"
TEMPLATE_ID = "controlled_announcement"
IDEMPOTENCY_KEY = "nexus-r29-1-governed-template-canary-v1"


def load_env() -> dict[str, str]:
    values = dict(os.environ)
    paths = (
        Path.home() / ".config/nexus/runtime.env",
        ROOT / ".env",
        ROOT / ".env.local",
        ROOT / ".env.nexus.recovered.local",
    )
    for path in paths:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values.setdefault(key.strip(), value.strip().strip("'\""))
    return values


def write_report(report: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def verify_provider_status(values: dict[str, str], report: dict[str, object]) -> int:
    message_id = report.get("provider_message_id")
    key = values.get("RESEND_API_KEY", "")
    if not message_id or not key:
        report["delivery_evidence"] = "PROVIDER_ACCEPTED_ONLY"
        report["delivery_observation"] = "NOT_AVAILABLE"
        write_report(report)
        return 1
    request = urllib.request.Request(
        "https://api.resend.com/emails/" + str(message_id),
        headers={"Authorization": f"Bearer {key}", "User-Agent": "nexus-os-v2/r29.1-governed-canary"},
    )
    try:
        import certifi
        with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context(cafile=certifi.where())) as response:
            body = json.loads(response.read().decode() or "{}")
            state = body.get("last_event") or body.get("status") or "provider_message_read"
            report.update({"delivery_evidence": "PASS_REAL", "delivery_observation": state, "status_http": response.status})
            write_report(report)
            print(json.dumps({k: report.get(k) for k in ("status", "template_id", "send_count", "delivery_evidence", "delivery_observation", "duplicate_protection", "secrets_included")}, indent=2))
            return 0
    except Exception as exc:
        report.update({"delivery_evidence": "PROVIDER_ACCEPTED_ONLY", "delivery_observation": "STATUS_UNAVAILABLE", "status_error_class": type(exc).__name__})
        write_report(report)
        return 1


def main() -> int:
    values = load_env()
    if "--verify-only" in sys.argv:
        if not REPORT.is_file():
            return 1
        return verify_provider_status(values, json.loads(REPORT.read_text(encoding="utf-8")))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    template = next((item for item in registry.get("templates", []) if item.get("id") == TEMPLATE_ID), None)
    now = datetime.now(timezone.utc).isoformat()
    base: dict[str, object] = {
        "schema_version": "nexus.r29-1.governed-template-canary.v1",
        "generated_at": now,
        "provider": "RESEND",
        "template_id": TEMPLATE_ID,
        "template_authority": template.get("authority") if template else None,
        "recipient_class": "synthetic_nonproduction_configured_test_recipient",
        "environment": "test",
        "purpose": "R29.1 governed customer-template integration canary",
        "idempotency_key_hash": hashlib.sha256(IDEMPOTENCY_KEY.encode()).hexdigest()[:16],
        "secrets_included": False,
        "recipient_persisted": False,
        "customer_contacted": False,
        "send_count": 0,
    }
    if REPORT.is_file():
        prior = json.loads(REPORT.read_text(encoding="utf-8"))
        if prior.get("status") == "PASS_REAL":
            prior["duplicate_protection"] = "PASS_REAL_ALREADY_EXECUTED_NO_SECOND_SEND"
            print(json.dumps({k: prior.get(k) for k in ("status", "template_id", "send_count", "delivery_evidence", "duplicate_protection", "secrets_included")}, indent=2))
            return 0
    key = values.get("RESEND_API_KEY", "")
    sender = values.get("RESEND_FROM_EMAIL") or values.get("RESEND_FROM") or ""
    recipient = values.get("RESEND_TO_EMAIL", "")
    if not template or template.get("authority") != "APPROVAL_GATED":
        base.update({"status": "FAIL", "failure_class": "registry_template_not_approval_gated"})
        write_report(base)
        return 1
    if not (key and sender and recipient):
        base.update({"status": "FAIL", "failure_class": "protected_provider_configuration_missing"})
        write_report(base)
        return 1

    payload = json.dumps({
        "from": sender,
        "to": [recipient],
        "subject": "GoClear controlled R29.1 test message",
        "html": "<p>This is one controlled GoClear R29.1 test message. No action is required.</p>",
    }).encode()
    request = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Idempotency-Key": IDEMPOTENCY_KEY,
            "User-Agent": "nexus-os-v2/r29.1-governed-canary",
        },
    )
    try:
        import certifi
        with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context(cafile=certifi.where())) as response:
            body = json.loads(response.read().decode() or "{}")
            message_id = body.get("id")
            base.update({
                "status": "PASS_REAL" if response.status == 200 and message_id else "FAIL",
                "provider_http_status": response.status,
                "provider_message_id_present": bool(message_id),
                "provider_message_id": message_id,
                "send_count": 1,
                "delivery_evidence": "PROVIDER_ACCEPTED",
                "duplicate_protection": "PASS_REAL_FIXED_IDEMPOTENCY_KEY",
                "external_side_effect": "one_test_email",
            })
    except urllib.error.HTTPError as exc:
        base.update({"status": "FAIL", "provider_http_status": exc.code, "failure_class": "provider_rejection"})
    except Exception as exc:
        base.update({"status": "FAIL", "failure_class": type(exc).__name__})
    write_report(base)
    print(json.dumps({k: base.get(k) for k in ("status", "template_id", "provider_http_status", "provider_message_id_present", "send_count", "delivery_evidence", "duplicate_protection", "secrets_included")}, indent=2))
    return 0 if base.get("status") == "PASS_REAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
