# WP0-F — Mac Mini Runtime and Credential Location Map

**Classification:** sanitized discovery evidence; no secret values are included.

## Hardware and operating system

| Field | Observed value |
|---|---|
| Host | Raymonds-Mac-mini.local |
| Model | Mac mini, `Macmini7,1` |
| CPU | Dual-Core Intel Core i5, 2.6 GHz |
| Memory | 8 GB |
| OS | macOS 12.7.6, Darwin 21.6.0 |
| Architecture | x86_64 |
| Boot mode | Normal |
| SIP | Enabled |
| Active Operator policy | Paused in Nexus safety state |

Hardware identifiers and serial values were intentionally excluded.

## Canonical Nexus runtime paths

| Location | Purpose | Load chain / scope | Presence |
|---|---|---|---|
| `/Users/raymonddavis/nexus-os-v2` | Canonical repository | launchd working directory and source root | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/.venv-agent-platform` | Agent-platform Python environment | launchd worker arguments for selected Nexus processes | PRESENT |
| `/Users/raymonddavis/.config/nexus/runtime.env` | Canonical runtime environment | `run_with_nexus_runtime_env.sh` sources it, exports values, then execs the requested child | PRESENT / READABLE |
| `/Users/raymonddavis/nexus-os-v2/scripts/ops/run_with_nexus_runtime_env.sh` | Environment bootstrap | launchd wrapper for Active Operator, recovery, Telegram Hermes, and related jobs | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/scripts/ops/nexus_runtime_env.py` | Python environment loader and alias policy | imported by Python callers; does not print values | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/scripts/operations/nexus_hermes_telegram_worker.py` | Telegram Hermes worker | loaded by `com.nexus.telegram-hermes-v2` wrapper | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/scripts/operations/nexus_active_operator_runner.py` | bounded registered-process runner | loaded by Active Operator plist; policy remains paused | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/reports/runtime` | runtime reports, receipts, and logs | process-specific output paths | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/data/runtime` | durable runtime state | campaign and program state | PRESENT |
| `/Users/raymonddavis/nexus-os-v2/launchd` | repository scheduler declarations | source templates; user LaunchAgents are the loaded copies | PRESENT |

## Credential and session locations — names only

| Location | Purpose | Variable/key names observed | Load/scope | Presence |
|---|---|---|---|---|
| `~/.config/nexus/runtime.env` | canonical server/runtime secrets and feature flags | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENROUTER_API_KEY`, `OLLAMA_BASE_URL`, `OANDA_API_TOKEN`, `STRIPE_SECRET_KEY`, `RESEND_API_KEY`, `META_PAGE_ACCESS_TOKEN`, `NETLIFY_AUTH_TOKEN`, `GITHUB_TOKEN`, related flags | canonical wrapper source; server-side scope | PRESENT |
| repo `.env` | legacy/local application configuration | Supabase, Telegram-adjacent, OANDA, Stripe, Meta, Resend, trading flags | directly read by some legacy callers; duplicate source | PRESENT |
| repo `.env.local` | local override | `YOUTUBE_API_KEY` observed | local scope | PRESENT |
| repo `.env.e2e.local` | synthetic Playwright persona credentials | `E2E_PERSONA_A/B/C/D_*`, `E2E_ADMIN_*`, `E2E_ENABLE_AUTHENTICATED` | test-only scope; must not enter production workers | PRESENT |
| repo `.env.nexus.recovered.local` | recovered/legacy runtime configuration | Telegram, Stripe, frontend public configuration, feature values | recovery/local scope; duplicate/stale risk | PRESENT |
| `~/.hermes/.env` | Hermes gateway configuration | Hermes gateway, Telegram, email, Groq, home-channel names | Hermes scope; separate from Nexus canonical wrapper | PRESENT |
| `~/.hermes/auth.json` | Hermes auth/session store | key names not enumerated; values intentionally not read | Hermes desktop/CLI scope | PRESENT |
| `~/Library/Preferences/com.nousresearch.hermes.plist` | Hermes desktop preferences | preference keys not enumerated; values intentionally not read | macOS preference scope | PRESENT |
| `~/.cloudflared/hermes-gateway-config.yml` | Hermes gateway tunnel configuration | tunnel configuration metadata; values not copied | cloudflared scope | PRESENT |
| macOS Keychain | possible provider credential source | source is referenced by `access_resolver.py` and credential control-plane code | presence/value not queried; UNKNOWN | UNKNOWN |
| `~/.ssh/oracle_vm` | Oracle tunnel private key | path only; no key material read | Oracle SSH scope | PRESENT |
| `~/.ssh/known_hosts` | SSH host trust records | host-key records; contents not copied | SSH scope | PRESENT |

No secret values, tokens, passwords, JWTs, cookies, private-key contents, or
session contents were read into this artifact.

## Actual load chain

1. User LaunchAgent invokes a wrapper or shell script.
2. `run_with_nexus_runtime_env.sh` sources the canonical runtime file and
   exports it to the child; it also removes Stripe variables from the
   continuous-loop child.
3. The child receives `PYTHONPATH` for repository imports and runs the
   selected Python entrypoint.
4. Some legacy Python callers independently inspect repo `.env` files or use
   `nexus_runtime_env.py`; this is a duplicate-source risk.
5. Hermes gateway has a separate `~/.hermes` environment/auth chain and is not
   proof that the Nexus Telegram worker received the same environment.

## Loaded versus running

Read-only `launchctl list` showed loaded Nexus/Hermes labels including
`com.nexus.active-operator-v2`, `com.nexus.telegram-hermes-v2`,
`com.nexus.telegram-hermes-nova`, `com.nexus.continuous-loop`, and
`com.nexus.recovery-check-v2`. Generic `Python`, `python`, and `node` process
names were present. This proves configured/loaded presence only; it does not
prove a particular worker is currently executing, responding, or healthy.

Active Operator remains safety-paused. No scheduler was started, resumed, or
reloaded by WP0-F.

## Oracle SSH/tunnel metadata

- Remote host: `161.153.40.41`
- Remote user: `opc`
- Local key path: `~/.ssh/oracle_vm`
- Local forward: `127.0.0.1:11435` to remote `127.0.0.1:11434`
- Script: `scripts/ops/nexus_oracle_ollama_tunnel.sh`
- launchd declaration: `launchd/com.nexus.oracle-ollama-tunnel.plist`
- KeepAlive/network behavior is declared; live tunnel health was not asserted
  by this read-only map.

## WP0-F result

**COMPLETED_WITH_LIMITS.** Hardware, runtime paths, sanitized credential
locations, load chains, duplicate sources, loaded-label state, and Oracle
tunnel metadata are recorded. Keychain contents and secret presence are not
claimed. Loaded launchd state and generic process names are not treated as
runtime certification.
