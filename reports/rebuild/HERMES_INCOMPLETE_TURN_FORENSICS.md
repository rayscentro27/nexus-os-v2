# Incomplete-turn forensics

The 590357276 receipt was marked `DELIVERED`, but its response was only an
interim-looking model message and no Nexus tool executed. The exact cause was
terminal acceptance of progress prose from `_run_hermes_primary`; it was not a
Telegram send failure and not a Nexus MCP payload.

The new completion guard classifies bounded progress-only output as non-terminal,
retries once through the same native runtime, and raises a processing error if
the retry also fails. The poller no longer advances its offset when processing
raises.
