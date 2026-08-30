# Nova Telegram Capability Execution and Capability Truth Repair

Campaign: HG-WP6.5-NOVA-TELEGRAM-CAPABILITY-EXECUTION-AND-CAPABILITY-TRUTH-REPAIR-20260830-01

Baseline: 8ac281f

The five-stage Nova brain was preserved. The failure was in execution plumbing:
the model could emit a capability envelope, but the parser accepted only a
whole-string/fenced envelope. Wrapped envelopes therefore reached the Telegram
integrity check instead of being executed. The parser now extracts a bounded
envelope from surrounding model prose, validates it through the capability
broker, executes through the shared adapter, and returns the result for one
bounded synthesis continuation. Telegram also rejects any remaining raw
envelope as a final defense.

The same runtime path was exercised with an embedded public-search request.
Nova selected `public_web_search`, the shared adapter executed the real query,
and the fallback provider returned six Bing HTML results after SearXNG refused
the connection and Brave returned HTTP 402. The final response contained no
internal capability JSON.

Current live capability truth is exposed through `get_live_capability_status`.
It reports implementation, configuration, authentication, callability,
execution mode, and authority requirements. Email is implemented but gated by
approval and not direct Nova execution. Calendar event creation is implemented
in the capability model but has no callable Nova adapter and is therefore not
available now. Google Workspace state is reported without secret values.

These are development/runtime proofs only. Fresh Telegram testing by Ray is
still required; no E2E certification is claimed.
