# WP8.14E Voice Disposition

The relevant voice tests produced 5 passing tests and 3 failures. The failures
are the same pre-existing/unconfigured route and approval expectations documented
in WP8.13/WP8.14D: tests expect legacy `VOICE_REPAIR_*` routes while the current
governed repair control returns `GOVERNED_REPAIR_CONTROL` / `UNKNOWN_REPAIR`.
No Finance files or behavior are involved, and no new voice failure was introduced.

VOICE_FAILURES_NO_NEW_REGRESSION=PASS
VOICE_FAILURE_CLASSIFICATION=PREEXISTING_UNCONFIGURED_EXPECTATION
