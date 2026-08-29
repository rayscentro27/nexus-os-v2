# Telegram Department Routing Implementation

`department_router.py` is a closed-world resolver for bounded intents. It
loads and validates the department, loop, skill, and worker registries before
delegating to WP4 governed loop adapters. It does not execute arbitrary shell,
infer approvals, or grant authority.

Every processed update now records sanitized Telegram identity, intent,
department, loop, skill, worker, capability, execution target, run/receipt
correlation, authority result, and response message identifiers where
available.
