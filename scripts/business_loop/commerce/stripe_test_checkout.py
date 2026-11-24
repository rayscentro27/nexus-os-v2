#!/usr/bin/env python3
"""Stripe TEST-mode checkout for the pilot (no live keys accepted, no live activation).

setup  : idempotently create one test Product, Price (staged $48) and Payment Link.
sync   : read test Checkout Sessions for the link -> verified commerce_orders rows +
         verified CHECKOUT_STARTED / PURCHASE_COMPLETED events (service role).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from business_loop.commerce.governed_clients import StripeTest, job_context  # noqa: E402
from business_loop.commerce.supabase_io import call  # noqa: E402

STATE = ROOT / "reports/business_loop/stripe_test_checkout_r1.json"
IDS = {"project_id": "proj_98ef515bccee4b58", "venture_id": "vnt_holiday_commerce_pilot_2026",
       "opportunity_id": "opp_holiday_ceramic_mug_2026", "product_id": "prod_stoneware_mug_14oz"}
STORE_URL = "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/"
STAGED_PRICE_CENTS = 4800  # staged price; not changed without authorization


def _state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def setup(stripe: StripeTest | None = None) -> dict:
    job_context("stripe-setup")
    s = stripe or StripeTest()
    st = _state()
    if st.get("payment_link_url"):
        return st
    meta = {"metadata[project_id]": IDS["project_id"], "metadata[nexus_mode]": "TEST"}
    c, prod = s.post("/products", {"name": "The 6:12 AM Ritual Mug - TEST", "description": "Nexus pilot TEST-mode product (no real charge).", **meta})
    if c != 200:
        raise RuntimeError(f"stripe_product_failed:{c}:{prod}")
    c, price = s.post("/prices", {"product": prod["id"], "unit_amount": STAGED_PRICE_CENTS, "currency": "usd", **meta})
    if c != 200:
        raise RuntimeError(f"stripe_price_failed:{c}:{price}")
    c, link = s.post("/payment_links", {"line_items[0][price]": price["id"], "line_items[0][quantity]": 1,
                                        "after_completion[type]": "redirect",
                                        "after_completion[redirect][url]": STORE_URL + "?checkout=success&mode=TEST&checkout_test=1",
                                        **meta})
    if c != 200:
        raise RuntimeError(f"stripe_link_failed:{c}:{link}")
    st = {"mode": "TEST", "livemode": bool(link.get("livemode")), "product_id": prod["id"], "price_id": price["id"],
          "unit_amount_cents": STAGED_PRICE_CENTS, "payment_link_id": link["id"], "payment_link_url": link["url"],
          "created_at": datetime.now(timezone.utc).isoformat()}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2) + "\n")
    return st


def sync(stripe: StripeTest | None = None) -> dict:
    """Server-side verification: Stripe is the source of truth for checkout + purchase."""
    job_context("stripe-sync")
    s = stripe or StripeTest()
    st = _state()
    c, sessions = s.get("/checkout/sessions", {"payment_link": st["payment_link_id"], "limit": 100})
    if c != 200:
        raise RuntimeError(f"stripe_sessions_failed:{c}")
    out = {"sessions": 0, "orders_written": 0, "events_written": 0}
    _, existing = call("GET", f"commerce_events?select=detail&verified=eq.true&project_id=eq.{IDS['project_id']}", role="service", prefer="")
    seen = {(e.get("detail") or {}).get("stripe_session") + ":" + (e.get("detail") or {}).get("kind", "") for e in (existing or []) if isinstance(e, dict)}
    for cs in sessions.get("data", []):
        if cs.get("livemode"):
            continue  # never ingest live objects in this test path
        out["sessions"] += 1
        utm = {"utm_content": (cs.get("metadata") or {}).get("utm_content")}
        sid = (cs.get("client_reference_id") or "unknown")[:64]
        common = {**IDS, "session_id": sid, "verified": True, "is_test": True, "source": "stripe_test",
                  "content_variant": utm["utm_content"], "client_ts": datetime.fromtimestamp(cs["created"], timezone.utc).isoformat()}
        if f"{cs['id']}:started" not in seen:
            call("POST", "commerce_events", {**common, "event_type": "CHECKOUT_STARTED", "detail": {"stripe_session": cs["id"], "kind": "started", "mode": "TEST"}}, role="service")
            out["events_written"] += 1
        if cs.get("payment_status") == "paid":
            code, _ = call("POST", "commerce_orders", {**IDS, "provider": "STRIPE", "mode": "TEST", "provider_session_id": cs["id"],
                                                       "payment_status": cs["payment_status"], "amount_total_cents": cs.get("amount_total") or 0,
                                                       "currency": cs.get("currency") or "usd", "session_id": sid,
                                                       "provider_created_at": common["client_ts"]}, role="service")
            out["orders_written"] += int(code == 201)
            if f"{cs['id']}:purchase" not in seen:
                call("POST", "commerce_events", {**common, "event_type": "PURCHASE_COMPLETED",
                                                 "detail": {"stripe_session": cs["id"], "kind": "purchase", "mode": "TEST", "amount_cents": cs.get("amount_total")}}, role="service")
                out["events_written"] += 1
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    print(json.dumps(setup() if cmd == "setup" else sync(), indent=1))
