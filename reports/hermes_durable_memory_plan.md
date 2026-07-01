# Hermes Durable Memory Plan

**Generated:** 2026-07-01

## Current State

| Memory Type | Storage | Durable |
|-------------|---------|---------|
| Conversation History | localStorage | No (browser-local) |
| Usage Ledger | localStorage | No (browser-local) |
| Activity Journal | localStorage | No (browser-local) |
| Second Brain Index | JSON files | Yes (local files) |
| Live Data | Supabase | Yes (cloud) |

### Limitations

- localStorage is browser-local only
- No cross-device sync
- No cross-browser sync
- Data lost on browser clear
- No backup mechanism

## Durable Memory Options

### Supabase Tables (Available)

- Live data already persists in Supabase
- Hermes can read from: task_requests, business_opportunities, research_sources, monetization_opportunities, client_profiles, nexus_events

### Supabase User Preferences (Not Available)

- No user_preferences table exists
- Would need migration

### Supabase Chat History (Not Available)

- No chat_history table exists
- Would need migration
- Privacy concerns

### File-Backed Memory (Available)

- JSON files can store durable memory
- Already used for second-brain index in data/memory/

## Recommendation

| Timeframe | Recommendation |
|-----------|----------------|
| Short-term | Keep localStorage for conversation history and usage ledger. Simple, private, sufficient. |
| Medium-term | If cross-device sync needed, create supabase table for chat_history with RLS. |
| Long-term | Consider dedicated memory service for large-scale durable memory. |
| Critical | Do not store sensitive data in localStorage. Do not sync PII without encryption. |

## Implementation

| Memory Type | Current | Recommendation |
|-------------|---------|----------------|
| Conversation History | localStorage | Keep (sufficient for single-device) |
| Usage Ledger | localStorage | Keep (sufficient for cost tracking) |
| Activity Journal | localStorage | Keep (sufficient for session memory) |
| Second Brain Index | JSON files | Keep (sufficient for research memory) |
| Live Data | Supabase | Keep (already durable) |

## Export Plan

- **Available:** No
- **Note:** No export mechanism exists
- **Recommendation:** Add export button for usage ledger to CSV/JSON for cost reporting
