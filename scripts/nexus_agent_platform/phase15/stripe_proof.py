"""Phase 15 Stripe test-mode proof.

Stripe must remain TEST MODE. A live key in the canonical runtime environment
is a critical finding: no checkout can be exercised and no transaction may be
performed until Ray reconciles the key to test mode. Any future successful
test charge is classified TEST_TRANSACTION, never
CONFIRMED_PRODUCTION_REVENUE.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from nexus_agent_platform.phase15.common import MODERNIZATION_DIR, RUNTIME_REPORTS, atomic_write_json, ensure_sources_loaded, load_json, utc_now


def _env(key: str) -> str:
    return __import__("os").environ.get(key, "").strip()


def stripe_test_mode_proof() -> Dict[str, Any]:
    ensure_sources_loaded()
    now = utc_now()
    secret_key = _env("STRIPE_SECRET_KEY")
    webhook_secret = _env("STRIPE_WEBHOOK_SECRET")
    live_webhook = _env("STRIPE_LIVE_WEBHOOK_SECRET")
    publishable_key = _env("VITE_STRIPE_PUBLISHABLE_KEY")
    autonomy_disabled = os.environ.get("NEXUS_AUTONOMY_STRIPE_DISABLED") == "1"

    reason: List[str] = []
    live_detected = False
    if secret_key.startswith("sk_live_"):
        live_detected = True
        reason.append("STRIPE_SECRET_KEY is a live key (sk_live_*) in the canonical runtime env")
    elif not secret_key:
        reason.append("STRIPE_SECRET_KEY is unset (test checkout cannot be exercised)")
    elif secret_key.startswith("sk_test_"):
        reason.append("STRIPE_SECRET_KEY is a test key (sk_test_*)")
    else:
        reason.append("STRIPE_SECRET_KEY prefix is unrecognized")

    if publishable_key.startswith("pk_live_"):
        live_detected = True
        reason.append("VITE_STRIPE_PUBLISHABLE_KEY is live (pk_live_*); any frontend checkout would target live mode")
    if live_webhook:
        live_detected = True
        reason.append("STRIPE_LIVE_WEBHOOK_SECRET is set")

    test_mode_confirmed = not live_detected and secret_key.startswith("sk_test_")
    live_key_present = live_detected or secret_key.startswith("sk_live_") or publishable_key.startswith("pk_live_")

    controls = load_json(RUNTIME_REPORTS / "revenue_activation_pilot_controls_latest.json", {})
    if not controls:
        controls = load_json(RUNTIME_REPORTS / "payment_readiness_contract_latest.json", {})

    report: Dict[str, Any] = {
        "phase": "PHASE 15 — STRIPE TEST MODE PROOF",
        "generated_at": now,
        "stripe_mode": "DISABLED_FOR_AUTONOMY" if autonomy_disabled else ("TEST_CONFIRMED" if test_mode_confirmed else ("LIVE_KEY_PRESENT" if live_key_present else "TEST_NOT_CONFIRMED")),
        "test_mode_confirmed": test_mode_confirmed,
        "live_key_present": live_key_present,
        "stripe_available": "LIVE_CREDENTIALS_AVAILABLE" if live_key_present else ("TEST_CREDENTIALS_AVAILABLE" if test_mode_confirmed else "UNAVAILABLE_OR_UNCONFIRMED"),
        "autonomous_execution_authorized": False,
        "classification": {
            "successful_test_charge": "TEST_TRANSACTION",
            "production_revenue": "DISALLOWED_UNTIL_LIVE_APPROVED",
            "live_discovered_revenue": False,
        },
        "evidence": {
            "secret_key_class": ("sk_live_*" if secret_key.startswith("sk_live_") else ("sk_test_*" if secret_key.startswith("sk_test_") else ("unset" if not secret_key else "unrecognized"))),
            "publishable_key_class": ("pk_live_*" if publishable_key.startswith("pk_live_") else ("pk_test_*" if publishable_key.startswith("pk_test_") else ("unset" if not publishable_key else "unrecognized"))),
            "webhook_secret_real": bool(webhook_secret and webhook_secret != "whsec_example"),
            "live_webhook_set": bool(live_webhook),
            "pilot_controls": controls,
            "reasons": reason,
        },
        "governance": {"live_stripe": "DISABLED", "no_transaction_performed": True, "autonomous_spending": "DISABLED"},
        "requires_ray_attention": (live_key_present or not test_mode_confirmed) and not autonomy_disabled,
        "next_action": "Ray must reconcile the canonical runtime.env Stripe keys to TEST keys (sk_test_*/pk_test_*) before any test checkout; no Stripe operation was performed.",
        "no_live_revenue_recorded": True,
    }
    atomic_write_json(MODERNIZATION_DIR / "stripe_test_mode_proof.json", report)
    lines = [
        "# Stripe Test Mode Proof — Phase 15",
        "",
        f"- mode: **{report['stripe_mode']}**",
        f"- test mode confirmed: **{test_mode_confirmed}**",
        f"- live key present: **{live_key_present}**",
        f"- transaction performed: **false**",
        "",
        "## Classification",
        f"- successful test charge: `{report['classification']['successful_test_charge']}`",
        f"- production revenue: `{report['classification']['production_revenue']}`",
        "",
        "## Evidence",
    ]
    for key, value in report["evidence"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Governance"])
    lines.append(f"- {report['next_action']}")
    lines.append("- No transaction, no client card usage, and no revenue record was performed or claimed.")
    (MODERNIZATION_DIR / "stripe_test_mode_proof.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
