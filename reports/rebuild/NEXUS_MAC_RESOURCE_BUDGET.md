# Nexus Mac Resource Budget — 2026-08-29

Observed read-only during WP4 Phase 0: root filesystem approximately 931 GiB
total, 658 GiB free. VM statistics showed no memory-pressure signal in the
bounded sample.

| Resource | Budget / policy |
|---|---|
| CPU | lightweight control-plane Python only; no new persistent heavy service |
| Memory | reserve for interactive Mac use; bounded subprocesses and explicit timeouts |
| Disk | reserve ample free space; runtime state and secrets remain outside Git |
| Authority | TruthKernel, human gates, Keychain, receipts, and deterministic execution |
| Network | private SSH loopback only for Oracle Hermes |

Placement: MAC_LOCAL for authority, sensitive state, deterministic processing,
and receipts. No duplicate scheduler or Hermes runtime is to be installed here.
