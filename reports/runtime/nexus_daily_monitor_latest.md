# Nexus Daily Monitor Report

**Generated**: 2026-07-05T20:14:39.994423+00:00

---

## Process Registry

| Metric | Value |
|--------|-------|
| Total | 19 |
| Enabled | 17 |
| Telegram Allowed | 17 |
| Blocked | 1 |

---

## Runner Heartbeat

| Metric | Value |
|--------|-------|
| Exists | True |
| Last Run | 2026-07-05T20:14:22.396769+00:00 |
| Processes Run | 17 |

---

## Reports Freshness

| Metric | Value |
|--------|-------|
| Fresh | 5 |
| Stale | 0 |


---

## Supabase

| Dimension | Status |
|-----------|--------|
| Env Keys | Present |
| Browser Verification | Unverified |
| Classification | ENV_PRESENT_BROWSER_EXPECTED |

---

## Blocked Actions

- send_customer_email
- post_to_social_media
- place_trade
- charge_customer
- submit_credit_dispute
- submit_grant_application
- export_sensitive_client_data
- modify_production_database
- restart_production_services
- send_sms
- make_phone_calls
- submit_legal_documents

---

## Next Actions

1. Verify Supabase via browser DevTools
2. Start Telegram bridge
3. Run active operator runner
4. Build client portal premium shell
5. Connect Stripe test-mode
