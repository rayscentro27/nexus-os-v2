# WP2-A Hermes Controlled-Migration Readiness — Version Reconciled

`PREPARATION_ONLY — NO UPGRADE EXECUTED`

## Decision

The prior `0.17.0` target was selected because it was the release identified
when the earlier readiness packet was prepared. Official upstream evidence now
identifies `0.20.6` (`v2026.8.27`) as the stable release published 2026-08-27.
No evidence requires an intermediate production install of 0.17.0. The selected
strategy is therefore:

`MIGRATION_STRATEGY=DIRECT_0_14_TO_0_20_6`

The large release delta is handled by an isolated compatibility preflight and
staged post-change verification, not by an unapproved intermediate runtime.

## Exact runtime and target

| Field | Value | Verification |
|---|---|---|
| CURRENT_HERMES_VERSION | `0.14.0` | local `hermes-agent` package metadata |
| CURRENT_INSTALL_SOURCE | local source install with a dedicated virtualenv under `~/.hermes/` | local launcher and package inspection |
| CURRENT_PROFILE_CONFIG | `~/.hermes/config.yaml` plus local profile/session state | local path inspection; values withheld |
| CURRENT_TELEGRAM_INTEGRATION | Nexus one-shot wrapper and existing user LaunchAgent | launchd declaration and worker inspection |
| CURRENT_PROVIDER_CONFIG | local Hermes config/auth sources | names/values withheld |
| TARGET_HERMES_VERSION | `0.20.6` | official release |
| TARGET_RELEASE_TAG | `v2026.8.27` | official release tag |
| TARGET_INSTALL_MECHANISM | existing supported Hermes update/install mechanism, pinned to the exact release after approval | must be exercised in isolated preflight first |

Official upstream release: [Hermes Agent v0.20.6](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.27).
The earlier [v0.17.0 release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.6.19)
is a substantial feature/refactor release, not a required migration checkpoint.

## Compatibility preflight

| Area | Result | Boundary |
|---|---|---|
| macOS | `YES` | current host/runtime is macOS; target install still needs isolated execution |
| Intel/x86_64 | `YES` | current host is x86_64; target dependency resolution must be verified before install |
| Python | `PARTIAL` | current Hermes venv is Python 3.11; target dependency lock/install has not been run |
| config.yaml | `UNVERIFIED` | target schema validation is required on a copied profile |
| profiles/sessions/memory | `UNVERIFIED` | migration/read compatibility must be tested on a copied state set |
| provider configuration | `PARTIAL` | wrapper boundary is known; target provider schema/auth loading is not yet installed-tested |
| Telegram wrapper | `YES_FOR_BOUNDARY` | Nexus worker is external to Hermes package and has prior real E2E evidence; post-change smoke test required |
| TruthKernel integration | `YES_BY_DESIGN` | read-only Nexus boundary; post-change integration test required |
| installer/update | `PARTIAL` | official update path is known; exact source-install behavior must be pinned and tested |
| rollback | `YES_PROCEDURALLY` | restore plan is defined; not executed before authorization |

No runtime was changed to produce these results. `UNVERIFIED` items are
pre-upgrade acceptance conditions, not claims of compatibility.

## Release delta review

| Delta | Relevant upstream change | Classification for Nexus |
|---|---|---|
| 0.14 → 0.17 | large core refactor; Bot API 10.1 rich Telegram formatting; profile builder/multi-profile; memory atomic operations; skills hub; background subagents; desktop/dashboard additions | `MIGRATION_RISK`, `REQUIRES_CONFIG_CHANGE` for copied-profile validation |
| 0.14 → 0.17 | stronger native Bot Mode/session/skills/memory surfaces | `BENEFICIAL`; Nexus remains the authority wrapper |
| 0.17 → 0.20.6 | stable patch release with consent-gated browsing, desktop Browser, managed SSH update, expanded remote MCP, caching/tool-search, keychain option, gateway-pausing updater behavior, cron incident handling, terminal env backends | `BENEFICIAL`, with `SECURITY_RISK`/`MIGRATION_RISK` requiring explicit feature gating |
| 0.17 → 0.20.6 | newer models and runtime/config surface changes | `REQUIRES_CONFIG_CHANGE` only where isolated validation finds schema differences |

The 0.20.6 release describes itself as a stable tagged release for downstream
consumers and documents the update path. New browsing, MCP, updater, keychain,
cron, and remote features remain outside the approved activation scope unless
independently proven and gated.

## Approved feature scope

| Feature | Decision | Nexus boundary |
|---|---|---|
| Bot Mode | `WRAP` | authorized identity, no unrestricted actions |
| persistent sessions/memory | `USE_AS_IS` | scope controls; memory cannot grant authority |
| messaging gateways | `WRAP` | allowlist, correlation, delivery receipt |
| skills | `USE_AS_IS` | explicit allowlists and Python evidence |
| MCP | `WRAP` | approved servers/tools only |
| browser/tools | `WRAP` | read-only by default; result verification |
| routines | `DO_NOT_ENABLE_YET` | Active Operator stays paused |
| provider routing | `WRAP` | bounded fallback; no credential exposure |
| retry/fallback | `WRAP` | idempotent, receipt-aware, bounded |
| delegation/subagents | `DO_NOT_ENABLE_YET` | no worker authority expansion |
| voice | `DO_NOT_ENABLE_YET` | separate microphone/transport E2E required |

Hermes owns conversation, context, reasoning, research, planning,
communication, and approved tool selection. Nexus owns authority, gates,
policy, work-order governance, and consequential-action eligibility. TruthKernel
owns verified state, evidence, freshness, result/side-effect verification, and
receipts. Python owns deterministic execution. These boundaries are unchanged.

## Backup and rollback plan

`BACKUP_CREATED=NO` — no runtime backup was created during preparation.

`BACKUP_CONTENTS=` current 0.14.0 package/venv metadata; `config.yaml`; profile,
session, memory, skill, and provider metadata without secret values; relevant
LaunchAgent declaration; Nexus Telegram wrapper baseline; TruthKernel Telegram
baseline; checksummed manifest.

`BACKUP_LOCATION=` protected local-only snapshot outside the repository, chosen
immediately before an approved change.

`BACKUP_VERIFICATION=` verify manifest/checksums, readable permissions, expected
version 0.14.0, and presence of each required configuration class without
printing values.

`RESTORE_PROCEDURE=` stop only the approved Hermes service if required; restore
the prior virtualenv/source pointer and profile/config snapshot; restore the
LaunchAgent declaration if changed; run bounded Telegram/TruthKernel baseline
checks.

`ROLLBACK_TRIGGER=` failed startup, config/profile migration, Telegram gateway,
TruthKernel boundary, security scan, or post-upgrade communication test.

`POST_ROLLBACK_TEST=` package/version identity, config load, one-shot wrapper,
authorized gate read-only behavior, delivery/correlation, and safety flags.

## Controlled migration stages

1. `STAGE_1_RUNTIME_UPGRADE`
2. `STAGE_2_BASIC_STARTUP_CERTIFICATION`
3. `STAGE_3_TRUTHKERNEL_READ_ONLY_INTEGRATION`
4. `STAGE_4_COMMUNICATION_CERTIFICATION`
5. `STAGE_5_NATIVE_FEATURE_ADOPTION`
6. `STAGE_6_DUPLICATE_NEXUS_COMPONENT_REVIEW`
7. `STAGE_7_POST_UPGRADE_CERTIFICATION`

## Replacement gate

The superseded gate `HG-WP2-A-HERMES-UPGRADE-20260828-01` is `HELD` and must
not be reused. The replacement exact gate is:

`NEW_HERMES_GATE_ID=HG-WP2-A-HERMES-UPGRADE-20260828-02`

It binds the current version `0.14.0`, target `0.20.6`, tag `v2026.8.27`,
direct strategy, the feature matrix above, isolated preflight/config changes,
backup and rollback procedure, unchanged security boundary, and the staged
test plan. Approval authorizes only that exact migration; it does not authorize
voice, routines, delegation, payments, trading, production deployment, client
mutation, credential changes, or Active Operator.

`HERMES_UPGRADED=NO`

`ACTIVE_OPERATOR_PAUSED=YES`

`REMOTE_APPROVAL_READY=YES`
`WAITING_RAY=YES`
