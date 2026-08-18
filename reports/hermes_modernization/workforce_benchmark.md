# AI Workforce Certification Benchmark — Phase 13

Status: `CERTIFICATION_PARTIAL_PROVIDER_ACTIONS_DEFERRED`

## Current worker certification

| Worker | Installed | Auth state | Execution | Classification | Registry decision |
|---|---:|---|---|---|---|
| Codex | yes | existing local session, execution proof recorded | verified harmless execution | `AVAILABLE` | remains separately governed |
| OpenCode | yes | unproven | timeout | `UNAVAILABLE` | not selectable |
| MiMo | yes | unproven | not proven | `INSTALLED_UNPROVEN` | not selectable |
| Kilo Code / Kilo CLI | yes, `7.3.54` | unproven | no safe non-interactive contract | `INSTALLED_UNPROVEN` | `DO_NOT_REGISTER_AS_EXECUTABLE` |
| OpenHands | no | not applicable | not run | `NOT_INSTALLED` | deferred |
| Local deterministic worker | yes | not applicable | verified isolated artifact execution | `AVAILABLE` | safe fallback |

## Onboarding contract

`DISCOVER → INSTALLATION_CHECK → VERSION_CHECK → AUTH_PROBE → HARMLESS_EXECUTION_PROBE → CAPABILITY_DISCOVERY → COST_CLASSIFICATION → SAFETY_CLASSIFICATION → VERIFICATION_CONTRACT → REGISTRY_ENTRY → CERTIFICATION → AVAILABLE`

Installation/version success does not prove authentication or execution. Provider adapters keep command syntax separate for Codex, OpenCode, MiMo, Kilo, OpenHands, and the internal worker.

## Governance

No software was installed. No provider login or configuration was changed. No credits were purchased. No production routing was changed. No worker was promoted solely from installation evidence. No client portal or production Telegram changes were made.
