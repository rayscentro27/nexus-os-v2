# Hermes Primary Failure Isolation

The primary path retains the certified Hermes failure-isolation boundary:
Hermes execution is isolated in the Hermes-supported subprocess and tool
failures remain resource-scoped. The canonical worker remains the sole
delivery owner and no shadow delivery path exists after cutover.

The Hermes primary preflight completed general, web, Nexus, retrieval, Alpha,
and multi-resource turns without worker failure. Existing certified bounded
provider fallback and qualified partial-evidence behavior remain in the same
Hermes runner.

No new write capability is exposed. Payments, live trading, browser
consequential actions, email send, calendar write, and Nexus mutation remain
disabled or governed by their existing boundaries.
