# Alpha Success Sprint — Codex Preflight

- Branch: `main`.
- Starting commit: `2f355ae upgrade Got Funding landing page to premium conversion page`.
- Phase A report: OpenCode’s `alpha-success-sprint-phase-b-m-results.md` and related audit artifacts existed; its changes were partly staged and required completion/correction.
- Provider default: `deterministic_local`; provider selection was newly persisted but incorrectly auto-upgraded to a hosted provider when status changed.
- Hosted route: same-origin `/api/alpha/chat` backed by `alpha-provider.mjs`; no frontend provider keys.
- Time source: OpenCode had already replaced stale snapshots with `Date.now()` for sends, but time/source trace detail was incomplete.
- Composer: preliminary sticky styles existed, but source/status/right-panel layout and mobile resilience needed completion.
- Header: global top bar still displayed Nexus Hermes capability text on `#alpha`.
- Web: preliminary DuckDuckGo HTML scraping was automatically invoked for current prompts, search was not opt-in, and the Netlify redirect incorrectly sent `/api/alpha/search` to the model function.
- Trace/cost: preliminary structures lacked the required schema, cost modes, token/estimate labels, fallback/cache/deep counters, and per-response compact source line.
- Memory: localStorage history existed; it must be described as session/local only, never long-term or Supabase memory.
- Unrelated dirty files excluded: `.gitignore`, YouTube cache, NotebookLM exports, manual-publish/runtime/Nexus Research reports, and `docs/design/got-funding-approved-mockup.png`.
- Safe to proceed: yes, by retaining the intended Alpha changes and correcting the above gaps.
