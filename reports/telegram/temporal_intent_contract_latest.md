# Temporal Intent Contract — Latest

**Date**: 2026-07-06

## Temporal Intent Categories

### 1. CURRENT_TIME
- `what time is it`
- `time`
- `current time`
- `what is the time`
- `what time`

**Response**: Current time with timezone label.

### 2. CURRENT_DATE
- `what day is it`
- `today's date`
- `what is today`
- `what is the date`
- `what day`

**Response**: Full date with day of week.

### 3. RELATIVE_DATE_CONTEXT
- `yesterday`
- `tomorrow`
- `next week`
- `last week`
- `this week`
- `this morning`
- `tonight`
- `later today`
- `next month`
- `last month`

**Response**: Resolved absolute date.

### 4. RECAP_BY_TIMEFRAME
- `what happened yesterday`
- `what changed today`
- `what did Nexus do last week`
- `summarize this week`
- `what happened today`
- `what changed this week`

**Response**: Concise recap from local reports/receipts. No web search.

### 5. PLAN_BY_TIMEFRAME
- `what should we do tomorrow`
- `what is the plan for next week`
- `what should I focus on this morning`
- `what's on the agenda today`

**Response**: Priority list from context + recommendations.

### 6. SCHEDULE_REQUEST
- `schedule this for 8 AM`
- `remind me tomorrow`
- `remind me at 8 AM`
- `put this on the schedule for next week`
- `follow up tomorrow morning`
- `set a reminder for Friday`

**Response**: Schedule draft with clarification if needed.

### 7. DEADLINE_OR_DUE_DATE
- `make this due Friday`
- `set deadline for tomorrow`
- `this needs to be done next week`

**Response**: Deadline draft with confirmation.

## Priority Rules

1. Temporal intents run BEFORE generic fallback
2. Temporal intents do NOT hijack Alpha opinion
3. Temporal intents do NOT trigger web search (unless user asks for external current info)
4. Schedule requests create drafts, not external calendar events
5. If "this" is ambiguous, ask for clarification
6. Use system local timezone, clearly labeled

## Output Schema

```json
{
  "intent": "CURRENT_TIME|CURRENT_DATE|RELATIVE_DATE|RECAP|PLAN|SCHEDULE|DEADLINE",
  "matched": true,
  "resolved_start": "2026-07-07T08:00:00",
  "resolved_end": null,
  "timezone": "America/Phoenix",
  "confidence": 0.95,
  "needs_clarification": false,
  "clarification_question": null,
  "task_reference": "last recommendation / last topic / explicit text"
}
```
