# WP9.0 Scheduler Architecture

Canonical entrypoint: `scripts/wp9_company_scheduler.py`.
Canonical intended launchd label: `com.nexus.wp9-company-cycle` using
`ops/launchd/com.nexus.wp9-company-cycle.plist`. The plist is not loaded in this
campaign because the required morning-email transport gate is externally blocked.

The entrypoint supports the same `--manual` and `--scheduled` paths, a durable
company cycle ID, process lock, cycle receipts, Finance preflight/postrun, and
6:00 local morning-report dispatch. Existing daily/evening/continuous launchd
jobs remain separate legacy/non-WP9 jobs and were not duplicated or modified.

WP9_SCHEDULER_AUDIT=PASS
WP9_SINGLE_SCHEDULER_AUTHORITY=PASS_DESIGN_READY_NOT_INSTALLED
WP9_COMPANY_CYCLE_ID=PASS
WP9_CYCLE_START_RECEIPT=PASS
