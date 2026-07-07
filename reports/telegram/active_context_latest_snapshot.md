# Active Context Latest Snapshot — 2026-07-07

Active context state after router refactor tests.

No production context saved yet. The context will be populated when:
1. Hermes web search returns findings
2. Alpha research returns recommendations
3. Draft engine produces items
4. User selects an item by number

## Schema

```json
{
  "source_agent": "hermes|alpha",
  "context_type": "money_plan|client_acquisition|web_search|alpha_research|...",
  "topic": "original query",
  "summary": "brief summary",
  "items": [
    {
      "index": 1,
      "title": "item title",
      "summary": "item description",
      "score": 8.5,
      "url": "",
      "source": "hermes|alpha|brave",
      "evidence": [],
      "risk": [],
      "next_action": "suggested action"
    }
  ],
  "top_index": 1,
  "last_selected_index": null,
  "expires_after_minutes": 180
}
```

No secrets.
