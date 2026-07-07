# Agent Brain Separation Audit — Latest

**Date**: 2026-07-06
**Branch**: main
**Commit**: e7fabc2

## Current Agent Roles

### Nexus (COMMAND/OPERATOR)
- `/report`, `/status`, `/orders`, `/approvals`, `/recover`, `/recs`, `/processes`, `/run`, `/blocked`
- Reports, approvals, work orders, system health
- Controlled and approval-gated
- **Status**: WORKING CORRECTLY

### Hermes (CEO/OPERATOR ADVISOR)
- `/hermes <msg>` + natural language routing
- Explains Nexus status, recommends priorities
- Reviews reports, uses web search when needed
- Creates work orders when Ray asks
- Conversational but operational
- **Status**: WORKING CORRECTLY

### Alpha (OUTSIDE OPINION/ADVISOR) — BROKEN
- Currently: research-first, command-first, work-order-first
- Should be: outside opinion, critique, independent perspective

## Where Alpha Is Being Treated as Research-First

1. **ALPHA_RESEARCH_PATTERNS** (line 1000-1017): Overly broad patterns like `compare`, `pros and cons`, `what are the best`, `how can we`, `what are the options`, `explore`, `analyze`, `evaluate`, `strategize`, `plan for` all trigger research brief creation. These are opinion/advice questions, not research requests.

2. **cmd_alpha_fallback** (line 1405): Called for ANY `ALPHA_RESEARCH_REQUEST`. Always creates: intake record, brief, score record, advisory feed, shared recommendation ingest, conversation context update. This is a full research pipeline, not an opinion response.

3. **Alpha greeting** (line 1240-1244): "I can research opportunities, compare tools, score ideas, or turn findings into work orders." — Research/work-order framing, not outside-advisor framing.

4. **Alpha casual chat** (line 1271-1275): "I can research, score, compare, or turn an idea into a Nexus work order." — Same problem.

5. **Help text** (line 135): `/alpha <topic> - Alpha research` — Labels Alpha as research.

6. **cmd_alpha slash handler** (line 646-671): Immediately creates a work order for ANY `/alpha` input. No opinion mode.

7. **Alpha fallback always includes research disclaimer** (line 1531): "Note: Live external research not configured. This is an internal Nexus context brief." — Shows even for opinion questions.

8. **get_next_step_suggestion** (line 1215): "Start research: 'Alpha research <topic>'" — Default suggestion is research.

## Where Alpha Is Being Treated as Command-First

1. **Work order creation in follow-up** (line 1574-1592): `turn_into_work_order` creates work orders directly from Alpha follow-ups without checking if Ray wants operational action.

2. **send_to_hermes** (line 1594-1604): Automatically creates work order when routing Alpha brief to Hermes.

## Where Work-Order Routing Is Too Aggressive

1. `cmd_alpha` (line 663): Creates work order for every `/alpha` input
2. `cmd_followup` turn_into_work_order (line 1584): Creates work order from follow-up
3. `cmd_followup` send_to_hermes (line 1597): Creates work order for Hermes handoff
4. `WORK_ORDER_PATTERNS` (line 1086-1091): Catches generic "create a task" messages

## Where Fallback/Help Is Too Dominant

1. **handle_unknown_fallback** (line 1302-1311): Defaults to "Research a topic: 'Alpha research <topic>'" — pushes toward research
2. **HERMES_ADVISORY_PATTERNS** (line 1036): "what should we do next" routes to Hermes, not Alpha — correct but Alpha should also handle "what do you think" type questions
3. No Alpha opinion/intent exists — everything unknown falls through to research or Nexus

## Summary of Problems

| Problem | Location | Impact |
|---------|----------|--------|
| Research patterns too broad | ALPHA_RESEARCH_PATTERNS | Opinion questions trigger research briefs |
| No opinion mode | classify_message_intent | Alpha can only research, not advise |
| Greeting framed as research | handle_greeting(alpha) | Sets research-first expectation |
| Casual chat framed as research | handle_casual_chat(alpha) | Sets research-first expectation |
| /alpha creates work order | cmd_alpha | Immediate command action |
| Fallback pushes research | handle_unknown_fallback | "Research a topic" is first suggestion |
| Help labels as research | cmd_start | "/alpha <topic> - Alpha research" |
| Research disclaimer always shown | cmd_alpha_fallback | Even for opinion questions |
