# Nexus V2 Rebuild Program Status

PROGRAM_ID=NEXUS-V2-REBUILD-20260828
PROGRAM_STATE=BLOCKED_PREFLIGHT
CURRENT_SPRINT=SPRINT_2
CURRENT_WORK_PACKAGE=WP2-A_HERMES_UPGRADE_AUTHORIZATION
ACTIVE_OPERATOR_PAUSED=YES

## Current checkpoint

Sprint 0 discovery and Sprint 1 truth-kernel work are complete. WP1-D
Telegram E2E proved remote TruthKernel approval and replay rejection. The
previous Hermes target gate was explicitly held and retired after upstream
version reconciliation.

WP2-A has an approved exact gate, but is blocked before live change by the
isolated 0.20.6 installation preflight:

`HG-WP2-A-HERMES-UPGRADE-20260828-02`

No Hermes upgrade, live installation, profile change, or feature activation has
occurred. The protected 0.14.0 rollback backup is verified. The configured
package index has no 0.20.6 artifact, and the official tagged source install
did not complete its native build within the bounded preflight.

## Version reconciliation

- Current local runtime: `hermes-agent 0.14.0`.
- Official stable target: `0.20.6`, release tag `v2026.8.27`.
- Strategy: `DIRECT_0_14_TO_0_20_6`, currently `NO_GO` pending a completed
  isolated official source-install/toolchain preflight and target startup test.
- The former `0.17.0` gate `HG-WP2-A-HERMES-UPGRADE-20260828-01` is `HELD`.
- Definitive packet: [NEXUS_HERMES_CONTROLLED_MIGRATION_READINESS.md](NEXUS_HERMES_CONTROLLED_MIGRATION_READINESS.md).

## State semantics

`last_completed_work_package_commit` remains the commit that completed the
last completed package (`WP1-D-TELEGRAM-E2E`), while `current_git_head` is the
repository revision at checkpoint time. The two fields are intentionally not
interchangeable.

## Safety

Active Operator remains paused. `live_trading=false`, `auto_trading=false`,
`paper_only=true`. No credentials were changed, no backup was created yet, no
external business action was authorized, and Hermes remains at 0.14.0.

## Resume

Read the canonical program/work-package state, this dashboard, the readiness
packet, TruthKernel gate records, latest receipts, and current Git HEAD. Do
not execute the upgrade until Ray explicitly approves the new exact gate.
