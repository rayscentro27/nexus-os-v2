# Nexus Current-State Contract

## Rule

`PERSISTED != CURRENT`. Currentness is owned by Nexus, not Hermes or a
presentation layer.

Only `REAL_CURRENT` records are eligible for unqualified live answers. A
record must have an eligible source, valid active status, acceptable age,
no resolution or supersession, and no synthetic, fixture, or development
marker.

The shared policy is implemented in
`scripts/nexus_agent_platform/capabilities/currentness.py` and provides the
classes `REAL_CURRENT`, `REAL_HISTORICAL`, `SIMULATED`, `SYNTHETIC`,
`FIXTURE`, `DEVELOPMENT`, `LEGACY_UNKNOWN`, and `UNKNOWN`.

Each filtered result retains source, timestamps, classification, reason,
currentness status, and live-response eligibility. Empty current state is a
valid result.

CURRENTNESS_OWNED_BY_NEXUS=YES
CURRENTNESS_POLICY_REUSABLE_BY_SPECIALISTS=YES
