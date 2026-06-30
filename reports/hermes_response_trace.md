# Hermes Response Trace Report

Generated: 2025-07-01

## Entry Points Identified

### 1. `buildHermesResponse` (hermesWorkroomData.js)
- **Status**: Active, wired to all page-specific Ask Hermes buttons
- **Used by**: HermesChatPanel, HermesInlineDrawer, NexusAdminUI.askHermes()
- **Capabilities**: Regex intent matching (11 types), canned responses
- **Missing**: Date/time context, entity resolution, memory, clarification, learning
- **Page Context**: Accepts optional `pageId` parameter (added in Task 1)

### 2. `hermesAnswer` (NexusAdminUI.jsx)
- **Status**: Active, used by Command Center, Health, Reports, Settings
- **Used by**: HermesCard, HermesQuickPanel inline
- **Capabilities**: Regex intent matching + JSON snapshot
- **Missing**: Same as above
- **Page Context**: None

### 3. `hermesChat` (sections.tsx)
- **Status**: Unused by active UI (real LLM path)
- **Used by**: DepartmentWorkspace (NOT active)
- **Capabilities**: Real Supabase Edge Function call
- **Missing**: Not wired to active UI

## Response Router Architecture

All entry points now route through `hermesResponseRouter.ts` which:

1. **Classifies** question type (greeting, date_time, scheduling, page_question, entity_question, comparison, memory_history, supabase_query, backend_query, strategy_analysis, execution, learning_instruction, unclear)
2. **Resolves entities** ("this", "that", "first one", etc.) using page context and session memory
3. **Queries memory** using localStorage activity journal
4. **Detects learning** instructions ("remember that...", "from now on...")
5. **Queries adapters** (Supabase stub, Backend stub) — honest about status
6. **Generates response** with source transparency

## Source Transparency Labels

- `time_context` — Response from browser time/date
- `page_context` — Response from loaded page data
- `entity_resolution` — Response from entity resolver
- `memory` — Response from activity journal
- `supabase_stub` — Honest stub for Supabase
- `backend_stub` — Honest stub for backend/model
- `learning` — Response from stored instructions
- `honest_fallback` — Honest "I don't know" with capabilities list

## No More Canned Fallbacks

Old: "I'm tracking" / "Based on what you've shared" / "does this move toward revenue proof"
New: Honest responses with source attribution and clarification questions

## Missing Items (Future Work)

1. **Supabase adapter**: Stubbed but not wired — needs anon-safe read-only queries
2. **Backend adapter**: Stubbed but not wired — needs real model endpoint
3. **Web search**: Not available — needs safe search integration
4. **Activity journal**: Recording events but no automatic triggers yet
5. **Entity resolver**: Basic but needs refinement for complex references
