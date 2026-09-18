# Nexus Hermes Native Session Persistence Certification

Date: 2026-09-18

## Result

`PASS_REAL` for the machine-verifiable canonical runtime, native session
creation/resume, Admin transport, Telegram Oracle-primary transport, bounded
operational context, and receipt/profile correlation. `TELEGRAM_HUMAN_TEST`
remains `PENDING_HUMAN`: the unattended Telegram API probe could not complete
`getMe`, so no human delivery is claimed.

## Canonical architecture

Both interface adapters use the same bounded transport:

```text
Admin → nova.goclearonline.cc → nova_admin_server.py
Telegram → nova_telegram_worker.py
             ↓
Oracle Hermes Agent 0.20.6 / profile nova_nexus
             ↓
nexus_mcp_remote → governed Nexus state and department tools
             ↓
OpenRouter / openai/gpt-4o-mini
```

The Admin server no longer imports or invokes `get_nova_graph`. The old direct
graph mode is rejected even if a stale `NEXUS_ADMIN_NOVA_RUNTIME=direct` value
is present. The Admin launcher explicitly forces `NEXUS_ADMIN_NOVA_RUNTIME=hermes`.
The Telegram worker now fails closed on legacy `custom`/local runtime values and
requires the approved `oracle_hermes` runtime.

The Supabase `hermes-chat` Edge Function remains a legacy generic Hermes chat
surface used by older non-Nova UI code; it is not the Admin Nova route and is
not a second `nova_nexus` runtime. It should be retired separately if those
legacy surfaces are migrated.

## Native session persistence repair

The former bridge used `hermes -z --resume <interface-key>`. Hermes treats
`--resume` as lookup of an existing native session; it does not create a
session for a new Admin or Telegram interface key. As a result, the first turn
was not durable and later turns could silently start without native history.

The shared Oracle bridge now uses Hermes' native contract:

```text
hermes chat -Q --query-file - --continue <stable-interface-key>
  --create-if-missing --pass-session-id --no-restore-cwd
```

Hermes creates or resolves the named session in the Oracle profile SQLite
store. The bridge returns the native Hermes session ID as metadata while
retaining the stable interface key for Nexus correlation and MCP turn context.

Verified native sessions in `/opt/data/profiles/nova_nexus` included:

- Admin: `admin-cert-20260918` → `20260918_212946_f3044f`
- Telegram: `nova-telegram-primary-1288928049` → `20260918_213214_29fe59`

The Oracle profile directory is mode `700`; `state.db` and `auth.json` are
mode `600`. The canonical profile store is not the repository and is not
committed.

## State boundaries

- Conversation session: native Hermes SQLite session history, keyed by a
  stable interface session name. Admin and Telegram may have separate
  transcripts.
- Operational state: canonical Nexus MCP read models and governed receipts;
  it is refreshed for operational questions and is not copied into the
  session database as company truth.
- Durable company knowledge: `nova_nexus` profile rules plus Nexus governed
  knowledge/retrieval context. Historical conversation cannot override current
  governed state.

Admin continues to supply bounded relevant pre-context for current Nexus
grounding. It does not own model generation. The provider/model remains below
Hermes and is replaceable at the future Resource Governor boundary.

## Runtime evidence

- Oracle Hermes: `0.20.6` (`2026.8.27`), profile `nova_nexus`.
- Native model: `openai/gpt-4o-mini` through OpenRouter.
- Toolset: `nexus_mcp_remote`.
- Admin `/health`: PASS.
- Real Admin HTTP turn: PASS; response identified Hermes 0.20.6,
  `nova_nexus`, active Nexus MCP, and unavailable Google MCP.
- Real Admin follow-up on the same session: PASS; it recovered the prior
  runtime-profile referent.
- Real Admin operational query: PASS; Hermes read current Research state and
  a follow-up selected the most important finding from that turn.
- Real Telegram Oracle-primary adapter: PASS across two separate worker
  invocations; the second turn recovered `Project Telegram Continuity`.
- Direct native bridge continuity: PASS across separate Python bridge calls;
  `Project Bridge` was recovered by the second call.
- Oracle session listing: PASS; the named Admin/Telegram sessions appeared in
  the `nova_nexus` native session database.
- Hermes container restart was not forced because each production bridge turn
  is a fresh Hermes process and the native SQLite recovery proof already
  exercises the restart boundary without an avoidable service interruption.

## Visibility and receipts

The Admin pre-context and `nexus_mcp_remote` expose the existing canonical
operational read model for Research, Alpha, handoffs, department results, SEO,
and YouTube. Native Hermes session metadata preserves the interface key and
the bridge now also returns the native session ID. Existing MCP/delegation
receipts remain the authoritative action evidence; a narrative response alone
does not create a receipt.

Status semantics remain `REQUESTED`, `QUEUED`, `ACCEPTED`, `EXECUTING`,
`COMPLETED`, `FAILED`, and `BLOCKED`; session continuity does not upgrade a
failed or historical department result.

## Natural conversation and isolation

Ordinary conversation is still sent to Hermes without a local intent/tool/work
order requirement. Explicit current-state or department requests retain the
existing bounded routing and receipt rules. A tool failure, interface delivery
failure, or department blocker is not allowed to reset the native conversation
session.

The Telegram API `getMe` probe was unavailable during this unattended window.
That affects delivery certification only; it does not change the proven
Oracle-primary adapter path.

## Security and retention

No provider credentials, browser cookies, Google MCP credentials, OAuth grants,
publication, external mutation, customer contact, trade, or money movement was
performed. Sensitive Admin input remains rejected at the browser transport.
The native Hermes profile is protected on Oracle. Local legacy shadow/context
files are not canonical Nova state and should not be used for production
continuity. Native Hermes session retention is governed by Hermes' session
store/pruning configuration; Nexus does not copy the full transcript into
operational state.

## Focused changes

- `oracle_hermes_cli.py`: native create-or-resume invocation and native session
  ID extraction.
- `nova_admin_server.py`: direct graph path removed/disabled; Hermes-only
  transport response metadata.
- `nova_telegram_worker.py`: Oracle runtime required; native session ID
  propagated; test mode no longer initializes the local direct graph.
- `run_nova_admin_with_runtime_env.sh`: stale direct-runtime override blocked.
- `nova_capability_truth.py`: current Admin truth now describes Hermes/MCP,
  not the retired direct graph.
- focused transport/session tests.

## Remaining human / follow-up work

1. Ray should send two real Telegram turns to `@HermesNovaBot` after the bot
   API is reachable: a current Research question followed by a referent
   follow-up.
2. If desired, migrate the remaining generic UI calls to the canonical Nova
   transport and retire the unrelated legacy `hermes-chat` Edge Function.

Resource Governor remains inactive.
