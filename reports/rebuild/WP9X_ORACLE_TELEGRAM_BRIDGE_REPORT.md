# WP9X Oracle Telegram Bridge Report

## Executive Result

Reversible crossover completed. The existing Mac Telegram worker now selects the governed oracle_hermes adapter. A fresh real probe and a fresh worker-path dry run reached Oracle Hermes 0.20.6, profile nova_nexus, OpenRouter openai/gpt-4o-mini, and the real Nexus MCP-backed health path.

Telegram polling remains on the Mac. No second responder was started. No inbound human Telegram message was simulated or sent.

## Previous Live Route

com.nexus.telegram-hermes-nova -> scripts/ops/run_nova_with_runtime_env.sh -> scripts/nova/nova_telegram_worker.py -> _run_hermes_primary -> Mac Hermes 0.14.0.

Previous selector: NOVA_PRIMARY_RUNTIME=hermes.

## WP9V Target Route

Mac Telegram worker -> fixed Oracle adapter -> SSH opc@161.153.40.41 using the existing private key -> podman exec nexus-hermes-0206 -> /opt/hermes/.venv/bin/hermes.

Remote settings: HERMES_HOME=/opt/data/profiles/nova_nexus, HERMES_PROFILE=nova_nexus, OpenRouter openai/gpt-4o-mini, toolset nexus_mcp_remote.

No public Hermes endpoint was added.

## Runtime Selector

Mac selector: hermes
Oracle selector: oracle_hermes
Unknown values: rejected by the worker
Adapter: scripts/nexus_agent_platform/bridge/oracle_hermes_cli.py

The adapter validates the canonical session ID, uses a fixed remote command, sends user text on stdin, applies a bounded timeout, and returns a fail-closed structured result. User text is never interpolated into the remote command.

## Target Direct Probe

Fresh real adapter probe passed with STATUS=SUCCEEDED, HOST=ORACLE, VERSION=0.20.6, PROFILE=nova_nexus, PROVIDER=openrouter, MODEL=openai/gpt-4o-mini, response WP9X_ADAPTER_OK.

Fresh worker-path dry run passed with runtime_host=ORACLE, hermes_version=0.20.6, profile=nova_nexus, completed=True, and current Nexus system-health output.

## Crossover

Only the private mode-600 runtime environment selector was changed from hermes to oracle_hermes. The existing launchd job com.nexus.telegram-hermes-nova was kickstarted. Telegram identity, token, offset, session mapping, deduplication, and formatter were unchanged.

## Post-Crossover Identity

The actual selected worker branch was _run_oracle_primary and its real execution returned Oracle Hermes 0.20.6 provenance. The worker remains the sole Telegram update consumer.

## Safety and Rollback

Worker status returned IDLE after its bounded one-shot cycle. Offset 590357325 was preserved. No old update was replayed.

Rollback, not executed: restore NOVA_PRIMARY_RUNTIME=hermes, kickstart gui/$(id -u)/com.nexus.telegram-hermes-nova, and verify Mac Hermes 0.14.0 provenance.

## Human Certification Handoff

Unique phrase: NEXUS-WP9X-00CD61BB

Ray must send this exact message from the human Telegram account:

Nexus, WP9X human certification NEXUS-WP9X-00CD61BB. Give me current system health, tell me the highest-priority item requiring my attention, confirm whether Finance and Alpha are available, and tell me which Hermes runtime is answering me.

The bot was not used to simulate inbound traffic.

## Tests and Security

Focused bridge/runtime tests: 14 passed. Fresh real adapter probe: passed. Fresh worker-path Oracle dry run: passed. Python syntax compilation: passed. Secret scan: PASS.

The unrelated canonical frontend Tailwind build was not rerun; this backend-only change does not affect its known hang.

## Final Status

WP9X=PARTIAL_HUMAN_TEST_PENDING
TELEGRAM_CROSSOVER=PASS_REAL
TELEGRAM_CUTOVER=YES
TELEGRAM_READY_FOR_HUMAN_TEST=YES
TELEGRAM_HUMAN_ACTION_REQUIRED=YES
WP9=RETRY_NIGHT_1
