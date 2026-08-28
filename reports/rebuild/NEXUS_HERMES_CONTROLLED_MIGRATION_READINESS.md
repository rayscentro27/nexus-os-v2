# WP2-A Hermes Controlled-Migration Readiness

`READY_FOR_EXPLICIT_AUTHORIZATION — UPGRADE NOT EXECUTED`

## Current runtime

| Field | Verified value |
|---|---|
| CURRENT_HERMES_VERSION | `0.14.0` (`hermes-agent` package metadata) |
| CURRENT_INSTALL_SOURCE | Existing local Hermes source installation under `~/.hermes/hermes-agent` with its virtual environment |
| CURRENT_PROFILE_CONFIG | Existing `~/.hermes/config.yaml` and profile state under `~/.hermes/` (values not copied) |
| CURRENT_TELEGRAM_INTEGRATION | Nexus wrapper `scripts/operations/nexus_hermes_telegram_worker.py`, launched by the existing user LaunchAgent, using `--once` and the canonical runtime environment |
| CURRENT_PROVIDER_CONFIG | Existing Hermes config/model metadata under `~/.hermes/`; provider names/configuration are not copied into this public packet |
| CURRENT_TRUTHKERNEL_INTEGRATION | Nexus Telegram route now connects exact human-gate responses to TruthKernel; Hermes upgrade has not been performed |

## Proposed target and gate scope

`TARGET_HERMES_VERSION=0.17.0`.

This is the exact currently published upstream release selected for review,
not a blind `latest` selector. Compatibility with the local profile, Python
environment, Nexus wrapper, and launchd behavior must be proven in a staged
preflight before installation. The target may not be changed under a generic
approval.

`TARGET_INSTALL_SOURCE=upstream NousResearch hermes-agent v0.17.0 release,
installed through the existing supported mechanism after explicit approval`.

## Backup and rollback

- `BACKUP_CREATED=NO` — no upgrade is authorized yet, so no profile/config was
  copied or altered during this preparation.
- `BACKUP_LOCATION=planned local-only snapshot outside the repository of the
  Hermes profile/config, virtual-environment/package metadata, and relevant
  LaunchAgent declaration; exact path selected immediately before change`.
- `ROLLBACK_COMMAND_OR_PROCEDURE=restore the verified pre-upgrade profile and
  LaunchAgent declaration, restore the prior 0.14.0 environment, then run the
  bounded Telegram/TruthKernel baseline checks`.
- `ROLLBACK_VERIFIED_POSSIBLE=YES procedurally; not executed or destructive-tested`.

## Feature migration matrix

| Feature | Hermes already has it | Nexus use case | Decision | Nexus security wrapper | TruthKernel dependency | Python integration | Evidence required |
|---|---|---|---|---|---|---|---|
| Bot Mode | YES, documented/native surface | conversational operator gateway | WRAP | authorized identity, no unrestricted actions | read-only status/evidence | worker adapter | real gateway response and receipt |
| Persistent sessions / memory | YES | context continuity | USE_AS_IS | PII/scope policy; no authority from memory | status remains kernel-owned | context adapters | session continuity test |
| Messaging gateways | YES | Telegram/operator communication | WRAP | allowlist, route precedence, delivery receipt | correlation evidence | Telegram worker | real inbound/outbound correlation |
| Skills | YES | reusable operator workflows | USE_AS_IS | skill allowlist and action policy | evidence before claims | Python tool boundary | bounded skill execution |
| MCP | YES | controlled tools/connectors | WRAP | approved servers/tools, no secret expansion | evidence/authority gating | deterministic adapters | tool policy and receipt |
| Browser/tools | YES | browser research/verification | WRAP | no production mutation by default | result verification | Python verification paths | safe read proof |
| Routines | YES | future scheduling/interface | DO_NOT_ENABLE_YET | Active Operator remains paused | scheduler truth required | existing schedulers remain separate | supervised scheduler proof |
| Provider routing | YES | model/provider selection | WRAP | no credential disclosure; fallback bounded | failures remain explicit | Python execution unaffected | provider/fallback benchmark |
| Retry/fallback | YES | communication resilience | WRAP | bounded retry and idempotency | no duplicate evidence/action | receipt-aware wrapper | failure/recovery test |
| Delegation/subagents | YES | approved reasoning/delegation | DO_NOT_ENABLE_YET | explicit authority and worker policy | gate/evidence required | Python remains executor | isolated delegation proof |
| Voice | YES/native capability | future voice interface | DO_NOT_ENABLE_YET | separate microphone/transport gate | kernel evidence required | no Python authority transfer | real microphone/response E2E |

Hermes may own conversation, context, reasoning, research, planning,
communication, and approved tool selection. Nexus retains authority, gates,
work-order governance, safety policy, TruthKernel evidence, and deterministic
Python execution.

## Overlapping Nexus components

| Component | Classification |
|---|---|
| `scripts/operations/nexus_hermes_telegram_worker.py` | WRAP_WITH_HERMES |
| TruthKernel and human-gate route | KEEP |
| deterministic Python monitors/connectors/executors | KEEP |
| legacy generic conversational routing | LEGACY_CANDIDATE; review only after certification |
| duplicate provider/model wrappers | UNKNOWN until feature-by-feature comparison |

Nothing is deleted, retired, or replaced in WP2-A.

## Upgrade stages and communication proof

1. `STAGE_1_RUNTIME_UPGRADE`
2. `STAGE_2_BASIC_STARTUP_CERTIFICATION`
3. `STAGE_3_TRUTHKERNEL_READ_ONLY_INTEGRATION`
4. `STAGE_4_COMMUNICATION_CERTIFICATION`
5. `STAGE_5_NATIVE_FEATURE_ADOPTION`
6. `STAGE_6_DUPLICATE_NEXUS_COMPONENT_REVIEW`
7. `STAGE_7_POST_UPGRADE_CERTIFICATION`

Each stage is independently gated and rollback-capable. The post-upgrade
benchmark must answer: WHAT HAPPENED? WHAT IS TRUE NOW? WHAT HAPPENS NEXT?
DO YOU NEED RAY? It must test understanding, continuity, TruthKernel-grounded
status, follow-up awareness, error explanation, actionability, Telegram,
provider fallback, and memory/session behavior.

`VOICE_E2E_REQUIRED=YES before any voice adoption claim`.
`HERMES_UPGRADED=NO`.
