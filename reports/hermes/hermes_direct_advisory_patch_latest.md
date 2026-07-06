# Hermes Direct Advisory Patch Report

**Date**: 2026-07-06

---

## What Was Wrong

`cmd_hermes()` was purely a work-order router:
1. Classified the route by keyword
2. Created a work order
3. Returned "Hermes Request / Routed to: hermes_general / Work Order: wo_xxx"

Ray asked "what is today's priority?" and got a routing receipt instead of an answer.

## What Changed

### New `hermes_direct_answer()` Function
- Reads current system state: pending approvals, Alpha topic, Alpha recommendations
- Generates contextual advisory answer based on question type:
  - **Priorities**: Lists 4-5 current priorities with reasoning
  - **Recommendations**: Suggests next steps based on state
  - **Risk**: Assesses current blockers and risk level
  - **Approvals**: Shows pending approval count
  - **Status**: Quick system status summary
  - **General**: Contextual overview with offer to discuss specifics
- Creates work order in background (non-blocking)
- Returns answer first, work order reference second

### `/hermes` Slash Command
- Delegates to `hermes_direct_answer()` for direct answer
- Work order still created for routing/tracking

### Plain-Language Hermes
- `classify_message_intent()` detects HERMES_ADVISORY patterns
- Routes to `hermes_direct_answer()` directly
- No slash command required

## Before/After

| Message | Before | After |
|---------|--------|-------|
| /hermes what is today's priority? | "Hermes Request / Routed to: hermes_general / Work Order: wo_xxx" | Direct advisory with 5 priorities + work order |
| Hermes what should we do next? | Command menu (no handler) | Direct advisory with priorities |
| /hermes how is nexus doing? | "Hermes Request / Routed to: system_health / Work Order: wo_xxx" | Status summary with key metrics |

## Advisory Response Types

| Question Type | Example Phrases | Response |
|--------------|-----------------|----------|
| Priority | "what is today's priority?", "what should we do next?", "where should we focus?" | Ranked list with reasoning |
| Recommendation | "what do you recommend?", "suggest next steps" | Contextual suggestions |
| Risk | "is this realistic?", "what would stop us?", "what's blocking us?" | Risk assessment |
| Approval | "what needs my approval?", "pending reviews" | Approval count + instructions |
| Status | "how is nexus doing?", "system status" | Quick metrics |
| General | Other questions | Contextual overview |

## Tests

- "/hermes what is today's priority?" → Direct advisory ✓
- "Hermes what should we do next?" → Direct advisory ✓
- "hermes how is nexus doing?" → Status summary ✓
- "hermes what needs my approval?" → Approval info ✓
