#!/usr/bin/env python3
"""Shared Stripe test-plan helpers. No Stripe API writes are permitted here."""
from __future__ import annotations
import os, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
from same_day_common import ROOT, SUPABASE_READY, env_presence, now, parse_env, write_json, write_report  # noqa:E402,F401

KEY_NAMES = ["STRIPE_SECRET_KEY", "STRIPE_TEST_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "VITE_STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID", "STRIPE_PRICE_READINESS_REVIEW"]

def env_data():
    values = dict(os.environ)
    for path in (ROOT/".env", ROOT/".env.local", ROOT/".env.nexus.recovered.local"):
        values.update(parse_env(path))
    present = {name: bool(values.get(name)) for name in KEY_NAMES}
    secret = values.get("STRIPE_TEST_SECRET_KEY") or values.get("STRIPE_SECRET_KEY", "")
    publishable = values.get("STRIPE_PUBLISHABLE_KEY") or values.get("VITE_STRIPE_PUBLISHABLE_KEY", "")
    return {"presence": present, "test_secret_detected": secret.startswith("sk_test_"),
            "live_secret_detected": secret.startswith("sk_live_"),
            "test_publishable_detected": publishable.startswith("pk_test_"),
            "live_publishable_detected": publishable.startswith("pk_live_")}

def stripe_cli():
    path = shutil.which("stripe")
    version = ""
    if path:
        run = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
        version = (run.stdout or run.stderr).strip().splitlines()[0] if run.returncode == 0 else ""
    # Auth/config output is discarded because it can contain credentials.
    auth_checked = False; auth_available = False
    if path:
        run = subprocess.run([path, "config", "--list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        auth_checked = True; auth_available = run.returncode == 0
    return {"installed": bool(path), "path": path, "version": version,
            "auth_checked_without_output": auth_checked, "config_available": auth_available}

def approval(card_id, title, decision):
    return {"id": card_id, "tenant_id": "tenant_test_goclear", "client_id": "client_test_julius_erving",
            "category": "payment_approval", "title": title, "status": "pending_Ray_review",
            "priority": "high", "risk_level": "high", "automation_level": "approval_required",
            "client_visible": False, "approval_required": True, "exact_decision_needed": decision,
            "options": ["approve", "reject", "defer"], "test_mode_only": True,
            "external_action_performed": False, "created_at": now()}

def payment_record(status="planned_test_only"):
    return {"id": "stripe_test_payment_97", "tenant_id": "tenant_test_goclear", "client_id": "client_test_julius_erving",
            "category": "payment_status", "title": "$97 readiness review test payment", "status": status,
            "amount_cents": 9700, "currency": "usd", "provider": "stripe", "mode": "test",
            "do_not_charge": True, "approval_required": True, "external_action_performed": False,
            "created_at": now()}
