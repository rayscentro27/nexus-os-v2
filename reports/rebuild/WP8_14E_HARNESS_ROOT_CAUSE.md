# WP8.14E Harness Root Cause

The former aggregate certification process mixed Python, Playwright, Creative, and
child-process work in one long-lived process. Output was buffered and no durable
per-phase receipt was written until the aggregate completed; child processes could
also outlive the test invocation. A stalled aggregate therefore produced neither a
reliable final result nor usable partial evidence.

WP8.14E adds `scripts/finance/run_wp8_14e_regression.py`. It runs each mapped phase
in an isolated process, captures stdout and stderr, enforces a 90-second phase
timeout, kills the process group on timeout, and writes the JSON matrix after every
phase. The resulting run completed all 15 named phases with exit code 0.

REGRESSION_HARNESS_ROOT_CAUSE=IDENTIFIED
INDEPENDENT_PHASE_REGRESSION_RUNNER=PASS
REGRESSION_RECEIPT_SCHEMA=PASS
REGRESSION_TIMEOUT_GUARD=PASS
REGRESSION_OUTPUT_CAPTURE=PASS
