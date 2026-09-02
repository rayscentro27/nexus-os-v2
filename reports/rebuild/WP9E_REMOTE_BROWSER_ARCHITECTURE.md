# WP9E remote browser architecture

The Mac remains the control plane for authority, TruthKernel/state, Finance,
secrets, scheduler and receipts. A bounded job may execute in the existing
Oracle Hermes container. Results return as verified metadata/artifacts; no
second scheduler is introduced.

Limits selected from the measured worker: two sessions maximum, five tabs per
session, 600-second maximum job duration, 45-second idle timeout, 80% memory
guard, and mandatory close/cleanup. Authenticated browsing is a separate
consent-gated class and is off by default.

`scripts/nexus_agent_platform/wp9e_capabilities.py` contains the placement and
limit contract. Heavy non-critical browser work defers when Oracle is
unavailable; it does not silently consume Mac capacity.
