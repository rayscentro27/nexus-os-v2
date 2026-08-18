# Builder Abstraction

## Contract

- task_id: `build_75973c32170e`
- title: Internal Creative Lab proof artifact
- approval_state: approved
- protected_paths: 6
- selected execution adapter: `local_python`
- external CLI workers: health-probed, execution adapters not registered

## Worker health probe results

| Worker | Installed | Version | Probe result | Classification | Reason |
|---|---:|---|---|---|---|
| Codex | yes | `codex-cli 0.147.0` | execution_success | AVAILABLE | version and harmless execution probes succeeded |
| OpenCode | yes | `1.18.18` | execution_timeout | UNAVAILABLE | safe execution probe timed out |
| MiMo | yes | `0.1.12` | execution_failed | INSTALLED_UNPROVEN | execution probe did not prove availability |
| OpenHands | no | UNKNOWN | not_run | NOT_INSTALLED | not proven available |
| Internal worker | yes | `python3` | deterministic_local | AVAILABLE | local deterministic fallback |

The probe captures exit/timeout evidence and bounded version text only. It does not log stdout/stderr payloads or secrets. A successful version command alone is never classified as AVAILABLE or AUTH_BLOCKED.

## Routing safety

Health-positive external CLIs remain probe-only until a bounded `execute_fn` is registered. Therefore the safe builder proof continues to route to the internal worker, while Mission Control can independently show Codex as AVAILABLE.

## Protected boundaries

- no client portal changes
- no production Telegram changes
- no provider login/configuration mutation
- no production Hermes cutover
