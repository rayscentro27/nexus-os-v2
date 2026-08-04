# Nexus Hermes Telegram Routing Root Cause

Generated: 2026-08-04T20:21:24.944339+00:00

## Defect

Ray-originated Nexus Telegram messages reached the generic Hermes draft fallback:

- `Clarify the question`
- `Source: internal Nexus context`
- `Say 'research deeper' or 'search the web for...'`

## Source

- File: `scripts/hermes/hermes_draft_engine.py`
- Function: `generate_hermes_draft`
- Placeholder item: `Clarify the question`
- Telegram render path: `scripts/telegram/nexus_telegram_bridge.py::_render_draft`

## Routing Failure

`process_command()` handled non-slash Telegram messages by calling
`process_with_new_router()` first. The structured message understanding layer
classified several operational phrases as generic/unknown or general advisory
instead of deterministic Nexus operations. That path selected Hermes draft
generation, rendered local-context source text, and never called live tools.

## Repair

A deterministic Nexus pre-router now runs before the draft/model path. Known
Nexus intents route to live tools and mission tracking before any generic
Hermes draft fallback can execute.

## Mission Lifecycle

Incoming authorized Telegram updates now create durable mission JSON records in
`reports/runtime/nexus_telegram_missions/` and a redacted public summary in
`public/runtime/nexus-telegram-missions.json`.
