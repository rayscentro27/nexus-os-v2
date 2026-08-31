# Nova Hermes Tool Efficiency Analysis

The 60.7-second affiliate example and 122.185-second Tesla example were dominated by repeated model/tool cycles, not Telegram delivery. Tesla repeated search/retrieval pairs seven times. The new receipts distinguish unique network calls from duplicate calls.

Implemented safe optimization:

- Per-turn memoization for normalized equivalent search queries.
- Per-turn memoization for resolved retrieval URLs.
- Duplicate calls remain visible in tool transcripts and receipts; only network work is reused.
- SearXNG, DuckDuckGo HTML fallback, and Bing HTML fallback remain the approved free chain. No paid provider was added.

The measured Tesla run used one search and three retrievals, with no duplicate network calls, and completed in 25.91 seconds. Multi-resource work still used four model calls and three continuations; those passes were retained because the current evidence contract required combined synthesis and validation.

`MODEL_CONTINUATION_OVERHEAD=material on multi-resource turns`; `WEB_SEARCH_OVERHEAD=bounded`; `PAGE_RETRIEVAL_OVERHEAD=material when pages are slow`; `ALPHA_OVERHEAD=one governed call in the challenge run`.

