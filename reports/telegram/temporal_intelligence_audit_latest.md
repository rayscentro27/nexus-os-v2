# Temporal Intelligence Audit — Latest

**Date**: 2026-07-06
**Branch**: main
**Commit**: 808627d

## Current Time/Date Handler Status

**No time/date handler exists.** When Ray asks "what time is it", the message falls through all intent patterns to `UNKNOWN_HELPFUL_FALLBACK`, which returns the generic help menu.

### Current Routing Chain (no temporal intent)
1. APPROVAL_ACTION
2. WORK_ORDER_REQUEST
3. GREETING
4. CASUAL_AGENT_CHAT
5. HERMES_ADVISORY
6. HERMES_WEB_SEARCH
7. NEXUS_STATUS_OR_REPORT
8. ALPHA_OPINION
9. ALPHA_CONTEXT_FOLLOWUP
10. ALPHA_RESEARCH_REQUEST
11. UNKNOWN_HELPFUL_FALLBACK ← "what time is it" lands here

### No Temporal Patterns Exist
- No `TEMPORAL_TIME` patterns
- No `TEMPORAL_DATE` patterns
- No `TEMPORAL_SCHEDULE` patterns
- No `TEMPORAL_RECAP` patterns
- No `temporal_intent.py` module

## Current Fallback Route

`handle_unknown_fallback()` returns:
```
I can help with:
- Outside opinion: 'alpha what do you think about...'
- Operational advice: 'hermes what should we do next?'
- System status: 'what's the status?'
- Research: 'alpha research <topic>'
```

This does NOT mention time, date, scheduling, or reminders.

## Current Report Provider Detection

**Location**: `cmd_report()` line 213-220

```python
providers = []
for env_name, label in [("BRAVE_SEARCH_API_KEY", "Brave"), ...]:
    if os.environ.get(env_name, "").strip():
        providers.append(label)
web_search_status = f"ACTIVE ({', '.join(providers)})" if providers else "AVAILABLE (no provider key)"
```

**Problem**: This reads `os.environ` directly, but the env vars may not be exported in the shell running the bridge. The env vars are in `.env` and loaded by the web search module at import time, not by the bridge at report time.

**Fix needed**: Check the actual provider status from `hermes_web_search` module, not raw env vars.

## Stale Priority Source

**Location**: `cmd_report()` lines 207-210 + `hermes_direct_answer()` lines 494-495

Hardcoded stale priorities:
```python
priorities.append("Publish GoClear public landing page with plans/login/signup")
priorities.append("Run Supabase browser verification (2 min)")
```

These appear even though:
- GoClear pages are live (commit ebc80f5 fixed the deploy)
- Supabase migration was applied (commit 14581f3)
- Brave Search is working (Ray confirmed)

**Also in hermes_direct_answer()**:
```python
priorities.append("Publish GoClear public landing page with plans/login/signup")
priorities.append("Run Supabase browser verification (2 min)")
```

## Scheduling/Reminder Capability Status

- No schedule_draft.json exists
- No reports/scheduler/ directory exists
- No scheduler scripts exist in scripts/ops/
- No reminder functionality exists
- The only "scheduler" references are in legacy hermes_context_common.py (describing launchd cycles, not task scheduling)

## Summary

| Component | Status | Fix Needed |
|-----------|--------|------------|
| Time handler | MISSING | Create temporal_intent.py + patterns |
| Date handler | MISSING | Create temporal_intent.py + patterns |
| Schedule/reminder | MISSING | Create schedule draft system |
| Relative date resolution | MISSING | Implement in temporal_intent.py |
| Timeframe recap | MISSING | Stub with report search |
| Web search status | WRONG (reads env directly) | Read from hermes_web_search module |
| Stale priorities | HARDCODED | Make dynamic based on completion status |
| Fallback menu | INCOMPLETE | Add time/date/schedule options |
