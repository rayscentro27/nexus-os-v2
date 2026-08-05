# Langfuse Cloud Deployment

## Why Local Self-Hosting Was Rejected

The host is a 2014 Intel Mac mini with macOS 12.7.6 (Monterey), 8 GB RAM, x86_64.
Colima requires QEMU on this host (Apple VZ framework needs macOS 13+).
QEMU has no pre-built Homebrew bottle for Monterey x86_64 and requires compiling
~25 dependencies from source. The compile+test cycles exceed practical time limits
on this hardware. Docker Desktop was not installed.

**Decision:** Use Langfuse Cloud for the visual dashboard. Keep local trace-file
persistence as the fail-safe fallback.

## Cloud Configuration

- **Project:** Nexus Agent Platform (under Nexus OS organization)
- **Host:** `https://cloud.langfuse.com`
- **Environment:** production

## Environment Variables

All stored in `/Users/raymonddavis/.config/nexus/runtime.env` (mode 600).

| Variable | Purpose |
|---|---|
| `LANGFUSE_TRACING_ENABLED` | Master switch — `true` to activate |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` |
| `LANGFUSE_PUBLIC_KEY` | Project public API key |
| `LANGFUSE_SECRET_KEY` | Project secret API key |
| `LANGFUSE_TRACING_ENVIRONMENT` | `production` |
| `NEXUS_TRACE_SALT` | Salt for identifier hashing (auto-generated if unset) |

**Do not hard-code keys into source code. Do not commit keys.**

## Tracing Flow

```
Telegram message
  → process_command() [nexus_telegram_bridge.py]
    → try_hermes_platform() or try_alpha_platform()
      → OtelAdapter.trace() / .span() / .record_generation()
        → _redact_text() + _redact_metadata() [runs FIRST]
          → Langfuse Cloud (if keys valid)
          → local JSON fallback (if Cloud unavailable)
```

One real Telegram turn produces:
- One top-level trace/session
  - intake span
  - authorization span
  - routing span
  - context span
  - capability/mode span
  - tool/model span
  - formatting span
  - Telegram delivery span

Sessions are namespaced: `nexus-hermes:<hash>` and `alpha:<hash>`.

## Redaction Policy

All trace payloads are redacted before leaving the machine. The `_redact_text()`
and `_redact_metadata()` functions in `otel_adapter.py` scrub:

- Telegram bot tokens, chat IDs, user IDs
- API keys (OpenRouter, Stripe, Resend, Oanda, Netlify, Meta)
- JWT / Supabase service-role keys
- Bearer / Authorization headers
- Email addresses, phone numbers, SSNs
- Client names, addresses, account numbers
- Credit report details, uploaded document contents
- Full email bodies, runtime.env contents

Chat/user IDs are salted-hashed (deterministic, non-reversible).
Metadata keys in `_REDACT_META_KEYS` are replaced with `REDACTED`.

## Local Fallback

When Langfuse Cloud is unavailable (network error, bad keys, SDK init failure):

1. `OtelAdapter` falls back to writing local JSON files
2. Directory: `reports/runtime/agent_traces/`
3. Files are named: `{agent}_{name}_{timestamp}.json`
4. Input/output text is truncated to 500 characters
5. All redaction still applies to local traces
6. Directory is git-ignored via `reports/runtime/` in `.gitignore`

**Required behavior:**
- Langfuse Cloud available → send redacted trace + write local receipt
- Langfuse Cloud unavailable → write safe local trace + continue Telegram response + record trace-export failure

## Startup / Restart Behavior

Workers are managed via launchd:

```
com.nexus.telegram-hermes   → --once (every 30s), sources runtime.env
com.nexus.telegram-alpha    → --poll (KeepAlive), sources runtime.env
```

Both use wrapper scripts that `source runtime.env` before executing.
New env vars take effect on next Hermes cycle (≤30s) or Alpha restart.

**To restart workers:**
```zsh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.nexus.telegram-hermes.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nexus.telegram-hermes.plist

launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.nexus.telegram-alpha.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nexus.telegram-alpha.plist
```

## Outage Behavior

- **Langfuse Cloud down:** Traces write to local JSON. Telegram responses unaffected.
- **SDK init failure:** Silent fallback to local traces. No error shown to users.
- **Tracing disabled:** All adapter methods are no-op. Zero overhead.

## Retention

- **Cloud:** Langfuse Cloud retains traces per project settings (default: 30 days free tier).
- **Local:** No automatic rotation. Files accumulate in `reports/runtime/agent_traces/`.
  Manual cleanup recommended periodically.

## Key Rotation

1. Generate new keys in Langfuse Cloud project settings
2. Run the secure key entry script:
   ```zsh
   /Users/raymonddavis/.config/nexus/set-langfuse-keys.sh
   ```
3. Restart workers (Hermes auto-restarts within 30s)

## Complete Disable Procedure

Set in `runtime.env`:
```
LANGFUSE_TRACING_ENABLED=false
```

This preserves local tracing as a no-op. All adapter methods become silent.
No traces are written anywhere. Telegram responses are unaffected.

To also disable local traces, the adapter must be modified (currently writes
local traces when `LANGFUSE_TRACING_ENABLED=true` but Cloud init fails).

## Rollback

To revert to pre-Langfuse state:
1. Set `LANGFUSE_TRACING_ENABLED=false` in runtime.env
2. Workers pick up the change on next cycle
3. No code changes needed — the adapter is fully no-op when disabled
