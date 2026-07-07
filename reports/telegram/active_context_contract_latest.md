# Active Context Contract — Latest

**Date**: 2026-07-06

## Shared Active Context Object

**File**: `data/runtime/telegram_active_context.json`

### Schema

```json
{
  "updated_at": "ISO timestamp",
  "source_agent": "alpha|hermes|nexus",
  "context_type": "web_search|alpha_research|recommendation_list|advisory|report|schedule_draft|work_order_draft",
  "topic": "original query or topic",
  "summary": "brief summary of results",
  "items": [
    {
      "index": 1,
      "title": "result title",
      "summary": "snippet or description (cleaned of HTML)",
      "score": 7.5,
      "url": "https://...",
      "source": "provider or source label",
      "evidence": ["supporting detail 1"],
      "risk": ["risk 1"],
      "next_action": "suggested action"
    }
  ],
  "top_index": 1,
  "last_selected_index": null,
  "allowed_followups": [
    "explain_score",
    "explain_best",
    "research_deeper",
    "create_work_order",
    "schedule",
    "compare",
    "send_to_hermes",
    "send_to_alpha"
  ],
  "receipt_path": "path to search receipt",
  "brief_path": null,
  "provider": "brave|null",
  "query": "original search query",
  "expires_after_minutes": 180
}
```

### Rules

1. Any Hermes web search result saves this context
2. Any Alpha research result saves this context
3. Any recommendation list saves this context
4. Any Hermes advisory with numbered priorities saves this context
5. Schedule draft does NOT erase active context; it can reference it
6. /report updates context only if it presents actionable priorities; must not erase a more specific search context
7. If context is older than expiration, ask clarification

### Follow-up Priority Order

1. Explicit slash commands (always win)
2. Temporal intelligence (time/date/schedule)
3. Explicit agent commands (alpha..., hermes...)
4. **Active context follow-ups** (number, this, that, deeper, work order)
5. Alpha context follow-ups (legacy, still works for Alpha research)
6. Normal advisory/opinion routing
7. Generic fallback

### Selection Detection

Must understand:
- `number 1`, `number 2`, `option 2`, `item 2`
- `second one`, `first one`
- `that one`, `this`, `this option`, `that option`
- `the best option`, `top one`

### Follow-up Intent Detection

Must understand:
- `why is number 2 scored that way`
- `why is that scored that way`
- `why is this scored that way`
- `why is that the best option`
- `why is this the best move`
- `research deeper`, `look deeper`, `get more details`
- `turn this into a work order`, `create a work order`, `make this a task`
- `schedule this`
- `send that to Hermes`, `send that to Alpha`
- `compare number 1 and 2`
