# WP8.14E WP9 Preconditions

Revalidated without activation:

- temporary overnight observability mode
- three certification nights
- START, MEANINGFUL_PROGRESS, DECISION_READY, WARNING, CRITICAL, COMPLETE
  Telegram event policy with no NO_CHANGE spam
- configurable 06:00 local morning email target
- Finance morning content contract

All required regression, build, artifact, and secret-scan gates passed. The next
phase is WP9.0, but the scheduler and observability window remain stopped.

WP9_TEMPORARY_OBSERVABILITY_READY=PASS
WP9_TELEGRAM_CERTIFICATION_POLICY=PASS
WP9_TELEGRAM_TEMPORARY_MODE=PASS
WP9_MORNING_EMAIL_CONTRACT=PASS
WP9_MORNING_REPORT_SCHEDULE_CONTRACT=PASS_0600_LOCAL_CONFIGURABLE
WP9_MORNING_FINANCE_CONTENT=PASS
WP9_CERTIFICATION_WINDOW_CONFIG=PASS_3_NIGHTS
