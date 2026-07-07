# Router Architecture Contract — 2026-07-07

## Production Routing Hierarchy

### Layer 1: AUTH / SAFETY
- Unauthorized users blocked (chat ID check)
- Risky external actions approval-gated

### Layer 2: DETERMINISTIC COMMANDS
Slash commands: /report, /status, /orders, /approvals, /recs, /help, etc.
First match wins. No ambiguity.

### Layer 3: PENDING ACTIONS
confirm, yes, go ahead, approve work order, revise work order, confirm schedule.
Must run before generic text routing.
If pending_action exists and user says confirm → execute it immediately.

### Layer 4: TEMPORAL INTELLIGENCE
what time is it, what day is it, tomorrow, schedule this for 8 AM, remind me tomorrow.
Only matches pure time/date/schedule questions. Business questions with "today" are NOT temporal.

### Layer 5: ACTIVE CONTEXT FOLLOW-UPS
why is number 2 scored that way, why is that the best option, what is the best option,
compare number 1 and 2, research deeper, turn this into a work order, schedule this.
Requires active context with items.

### Layer 6: EXPLICIT ROLE PREFIX
alpha ..., hermes ..., nexus ...
Stripped and used to select agent role directly.

### Layer 7: STRUCTURED INTENT FAMILY ROUTER
Classifies into intent families:
- money_plan, money_research
- client_acquisition, client_research
- business_strategy
- implementation_plan
- web_research
- opinion, critique
- compare_options
- work_order_request, schedule_request
- system_status
- greeting, help, unknown

### Layer 8: ROLE DECISION
- Hermes for: money_plan, money_research, client_acquisition, client_research,
  business_strategy, implementation_plan, web_research
- Alpha for: opinion, critique, compare_options, explicit alpha prefix
- Nexus for: deterministic_command, system_status

### Layer 9: INTERNAL DRAFT ENGINE
Always produce structured draft first for advisory/research/business questions.
Hermes draft: operator_plan with concrete GoClear/Nexus items.
Alpha draft: outside_opinion with realistic assessment.

### Layer 10: RETRIEVAL GATE
Only use Brave if:
- User explicitly asks to search/research/current/web
- Answer requires fresh/current external facts
- Internal draft marks evidence gaps
- User asks for deeper research on active topic
- Provider is active

### Layer 11: EVIDENCE MERGE
Brave evidence enriches the internal draft.
Must not replace Nexus/GoClear-specific reasoning with generic snippets.
Preserve internal ranking unless evidence clearly changes it.

### Layer 12: RESPONSE RENDER
Render concise Telegram answer with role header, items, source indicator.

### Layer 13: SAVE CONTEXT
Save active context for any answer that creates:
list, plan, recommendation, search results, work order candidate, schedule candidate, priorities
