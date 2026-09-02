# WP9.0 Morning Email

The morning report generator and archive schema are implemented, including the
Finance section, cycle window, delivery state, and idempotency fingerprint.
The real authorized delivery gate is not passed: direct Resend send returned
HTTP 403/code 1010, and the existing Supabase `send-client-email` path returned
401. Resend read-only domain audit returned 200 with the configured sender domain
verified. No successful delivery is claimed.

WP9_MORNING_EMAIL_SCHEDULE=PASS_DESIGN_0600_LOCAL
WP9_MORNING_REPORT_WINDOW=PASS_DESIGN
WP9_MORNING_FINANCE_SECTION=PASS
REAL_WP9_MORNING_EMAIL_DELIVERY=BLOCKED_EXTERNAL_RESEND_403_AND_SUPABASE_401
