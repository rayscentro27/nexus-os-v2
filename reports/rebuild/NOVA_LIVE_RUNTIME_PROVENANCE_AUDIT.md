# Nova Live Runtime Provenance Audit

Campaign: `HG-WP6.5-NOVA-LIVE-RUNTIME-PROVENANCE-STALE-BRAIN-AND-NEGATIVE-CAPABILITY-BELIEF-AUDIT-20260830-01`

Baseline: `eb09dc3`  
Audit mode: read-only. No prompt, code, provider, process, session, or memory changes were made.

## Executive finding

The strongest proven cause is stale Nova conversation memory combined with insufficient runtime observability. The configured Telegram launch path points at the current checkout and current five-node graph, but the active Ray conversation memory contains eight prior assistant turns asserting that Nova cannot email, schedule, browse, access external systems, or inspect Nexus. The current graph sends those turns back to the model as conversation context. The current prompt does not contain the Gmail/Calendar refusal language found in the session.

The worker is ephemeral: launchd invokes `--once` every 30 seconds. At inspection time no Nova PID was active, so a historical PID could not be introspected directly. The status file recorded the most recent worker PID as `73509`; it is not evidence that this PID remained alive.

## Live consumer and executable provenance

| Field | Evidence |
|---|---|
| Configured consumer count | 1: `com.nexus.telegram-hermes-nova` |
| Active consumer at audit instant | 0; launchd state was `not running` between one-shot cycles |
| Launchd definition | `~/Library/LaunchAgents/com.nexus.telegram-hermes-nova.plist` |
| Program | `/bin/zsh /Users/raymonddavis/nexus-os-v2/scripts/ops/run_nova_with_runtime_env.sh` |
| Worker | `/Users/raymonddavis/nexus-os-v2/scripts/nova/nova_telegram_worker.py --once` |
| Working directory | `/Users/raymonddavis/nexus-os-v2` |
| Python | `/Users/raymonddavis/nexus-os-v2/.venv-agent-platform/bin/python3` (wrapper fallback is `python3` only if preferred path is absent) |
| Service cadence | `RunAtLoad`, `StartInterval=30` seconds |
| Last recorded status PID | `73509`, historical/transient |
| Last processed update | `590357159` |
| Other configured Telegram service | `com.nexus.telegram-hermes-v2` is Nexus Hermes, not a second Nova consumer |
| Duplicate active Nova consumers | None observed in `ps` or launchd |

Recent Telegram log entries show updates `590357155` through `590357159` processed after the `eb09dc3` commit. This disproves a simple “old daemon never restarted” explanation. The worker’s one-shot design naturally reloads source on each cycle.

## Checkout and module proof

The launch path resolves the repository from the wrapper’s own location; it does not use a separate installed package path. Current source SHA-256 prefixes and the corresponding `git show eb09dc3:<path>` prefixes matched:

| Module | Loaded/current path | Source hash prefix |
|---|---|---:|
| Telegram worker | `scripts/nova/nova_telegram_worker.py` | `ab74fb4740847430` |
| Nova graph | `scripts/nexus_agent_platform/agents/nova.py` | `5efe84a519f2accd` |
| Capability broker | `scripts/nexus_agent_platform/nova_capability_broker.py` | `95e68f7c8d4bb67f` |
| Shared capabilities | `scripts/nexus_agent_platform/capabilities/shared.py` | `bf2a52088ee51673` |
| Web adapter | `scripts/nexus_agent_platform/phase15/live_research.py` | `3f401a109e29682d` |
| Alpha adapter | `scripts/nexus_agent_platform/alpha_research.py` | `6f0d4bef2318ec2f` |
| Truth view | `scripts/nexus_agent_platform/nova_truth_view.py` | `c1c394910ceeb3af` |

No site-packages copy or alternate checkout was found in the inspected import paths. The configured runtime path therefore matches `eb09dc3`; a historical process’s in-memory modules cannot be recovered after it exits.

## Live graph

Static/runtime introspection of `get_nova_graph()` produced exactly:

1. `pre_model_boundary`
2. `build_context`
3. `generate_response`
4. `validate_output`
5. `compose_output`

`LIVE_GRAPH_LAYER_COUNT=5`. The current Telegram worker imports this graph after loading the runtime environment and invokes `graph.invoke(state)` when `HERMES_NOVA_ENABLED` is true. The launch wrapper sources `~/.config/nexus/runtime.env`, where the relevant Nova/platform flags are enabled. A bare diagnostic shell without that file reports false flags and is not the Telegram environment.

## Prompt, profile, session, and memory

The live Nova identity/profile is the embedded `SOUL` in `scripts/nexus_agent_platform/agents/nova.py`, for agent `hermes_nova`. There is no separately versioned profile file in the live path. The current SOUL permits conversation, research, approved web tools, bounded Nexus requests, and explicitly says that read-only does not mean unable to research or delegate. It does contain a narrower negative statement about not accessing “Oanda, Temporal, or other Nexus systems”; this can be overgeneralized by a model, but it does not contain the observed Gmail/Calendar refusal text.

For the inspected Ray chat, the current context build produced 42 messages: 20 persisted prior turns plus the current user message, with a system prompt of approximately 12,907 characters. The memory file is:

`/Users/raymonddavis/nexus-os-v2/scripts/data/runtime/nova_memory/nova_1288928049.json`

It was updated at `2026-08-30T22:45:49.913114Z`, contains 20 turns, and includes at least eight stale assistant capability claims, including variants of:

- Nova cannot send email or schedule appointments.
- Nova lacks access to Gmail, Calendar, or external systems.
- Nova cannot directly check Nexus.
- Nova cannot access external APIs.

These are fed back to the model as conversation context. `STALE_SESSION_OR_MEMORY=YES` is therefore proven.

## Flags and timing

The launch wrapper loads `~/.config/nexus/runtime.env`; its relevant flags are enabled: `NEXUS_AGENT_PLATFORM_ENABLED`, `NEXUS_HERMES_LANGGRAPH_ENABLED`, `ALPHA_LANGGRAPH_ENABLED`, and `HERMES_NOVA_ENABLED`. `HERMES_NOVA_MODEL` is set. The shell-only flag check returned false because it did not source that environment file; that result must not be attributed to Telegram.

`eb09dc3` was committed at `2026-08-30T15:08:19-07:00`. The logged Telegram cycles occurred at approximately 15:42–15:45 local time. `PROCESS_STARTED_BEFORE_COMMIT=NO` for the observed cycles. Auto-reload is not needed: launchd creates a fresh one-shot process each cycle.

## Capability invocation evidence

The code contains `get_live_capability_status` and a capability catalog, but the persisted Telegram receipts record only one model call and no capability request, provider, dispatch, or result metadata. For the observed Gmail/Calendar questions, `CAPABILITY_TRUTH_CALLED_IN_TELEGRAM=NOT_PROVEN`; there is no receipt evidence that it ran. This is an observability/proof gap and may also mean the model answered from stale context before emitting a capability envelope.

## Primary root cause

`PRIMARY_ROOT_CAUSE=COMBINATION`

Strongest component: `STALE_SESSION_OR_MEMORY`. Contributing components are missing capability-invocation telemetry and capability truth not proven on the Telegram path. The evidence does not support wrong checkout, old commit, multiple Nova consumers, or a launchd legacy script as the primary explanation.

## Remediation recommendation (not performed)

Run a separate controlled remediation campaign:

1. add non-secret runtime provenance and capability dispatch/result fields to Nova receipts;
2. start a fresh Nova session or quarantine the stale conversation memory without deleting historical evidence;
3. reload the one-shot launchd path and prove the loaded source hash at runtime;
4. run fresh Telegram tests for web, capability status, Gmail, Calendar, and Nexus reads;
5. separately reconcile the existing Google adapters and their authority gates.

No remediation step was executed in this audit.
