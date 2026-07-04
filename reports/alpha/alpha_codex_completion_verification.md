# Alpha Codex Completion Verification

Required invariants implemented: same-origin provider/search calls, persistent provider choice, opt-in search, complete traces, daily cost controls, current-time greetings, natural fallback, sticky composer, Alpha-specific header, session-memory truth, no Supabase/client data, and no action execution.

## Receipts

- Focused Alpha verification: 10 files, 50 tests passed.
- Frontend secret/direct-third-party grep: clean.
- Alpha Supabase import/path grep: clean.
- Full suite: 73 files and 1,175 tests passed; one known `seed_validation` filesystem scan exceeded its five-second timeout.
- Exact timed-out test rerun individually with a 30-second allowance: passed (1/1; 27 skipped).
- TypeScript and production build: passed.
- Build warning: existing main JavaScript chunk exceeds 500 kB.
- Local backend search proof without SearXNG configuration: returned `search_connector_missing`; no fake results.
- Hosted-provider calls made during verification: 0.
- External sends, posts, charges, trades, applications, disputes, Supabase writes, and real-client records: 0.
