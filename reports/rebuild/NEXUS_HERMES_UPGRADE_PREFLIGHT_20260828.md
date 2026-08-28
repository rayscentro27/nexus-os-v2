# Hermes 0.20.6 Controlled-Migration Preflight

`GO_NO_GO=NO_GO`  
`UPGRADE_EXECUTED=NO`

## Authority and backup

- Gate `HG-WP2-A-HERMES-UPGRADE-20260828-02` was verified `APPROVED`, with
  exact action and unexpired approval.
- A protected local-only backup was created at the approved local backup
  location. It contains the 0.14.0 virtualenv, profile/session state,
  source recovery material, relevant LaunchAgent declaration, Nexus wrapper,
  TruthKernel baseline, and a SHA-256 manifest.
- `BACKUP_READABLE=YES`, `BACKUP_MANIFEST_VALID=YES`,
  `BACKUP_CHECKSUMS_VALID=YES`, `BACKUP_CURRENT_VERSION=0.14.0`,
  `ROLLBACK_ASSETS_PRESENT=YES`.

## Isolated target checks

| Check | Result | Evidence / limit |
|---|---|---|
| official tag | `PASS` | `v2026.8.27` resolves to an official upstream tagged source revision |
| Python requirement | `PASS` | target source declares `>=3.11,<3.14`; local Hermes venv is Python 3.11.15 |
| package-index install | `FAIL` | configured index exposes versions through 0.19.0, not 0.20.6 |
| source install | `INCOMPLETE` | isolated tagged source install entered a native `maturin` build and did not complete within bounded preflight; process was stopped; live runtime untouched |
| config/profile parse | `NOT_PROVEN` | requires completed target install/runtime; no live profile was altered |
| sessions/memory/providers | `NOT_PROVEN` | requires target runtime migration test against copied state |
| Telegram wrapper boundary | `NOT_PROVEN_POST_TARGET` | current wrapper baseline is preserved; target startup was not completed |
| TruthKernel boundary | `DESIGN_COMPATIBLE` | integration is external/read-only by design; post-target runtime proof remains required |
| rollback | `READY` | verified local backup and restore procedure are available |

## Decision

The approved migration cannot safely proceed under the current installer
conditions. No live source, virtualenv, profile, LaunchAgent, credentials, or
service state was modified. No substitute version was installed.

The approved direct strategy remains the intended target, but the live upgrade
requires a new bounded assessment of the official source installation path
(including the native build dependency/toolchain and an isolated completed
startup/config test). This report does not authorize a target change or broaden
the existing gate.

`HERMES_UPGRADED=NO`

`ACTIVE_OPERATOR_PAUSED=YES`
