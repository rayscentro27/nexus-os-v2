# Nova Negative Capability Belief Sources

Audit classification: no implementation performed.

| Belief | Source found | Truth | Recommended action |
|---|---|---|---|
| “I cannot browse/search the internet” | Stale assistant turns in Nova session; not present verbatim in current SOUL | STALE | REFRESH session; add capability telemetry |
| “I cannot access external websites/systems” | Stale assistant turns; current SOUL has only narrower Nexus-system restrictions | STALE / PARTIAL | Refresh session; narrow prompt wording in a future campaign only if needed |
| “I cannot access Nexus” | Stale assistant turn; current graph includes Nexus reads; SOUL’s “other Nexus systems” sentence may be overgeneralized | FALSE/PARTIAL | Refresh session; clarify at capability boundary later |
| “I cannot send email” | Stale assistant turns; current capability handler reports governed email status | STALE/PARTIAL | Consult live capability truth; do not answer from memory |
| “I cannot use Calendar” | Stale assistant turns; Google read authorization is verified, event creation is not proven | PARTIAL | Distinguish read, request, and mutation capability |
| “I cannot delegate to Research” | No current SOUL prohibition found; no Telegram execution proof found | NOT_PROVEN | Instrument and test Alpha handoff |
| “Degraded Nexus means external research is unavailable” | Stale conversation/fallback reasoning; no current prompt rule proving this global dependency | FALSE | Service-specific capability status |

## Current prompt findings

The assembled current system prompt contained `CANNOT` and `read-only` language, but did not contain the observed Gmail, Calendar, “external systems,” or “cannot search internet” phrases. The relevant current doctrine is:

- broad conversation/research/recommendation is allowed;
- direct Nexus mutation/execution is prohibited;
- arbitrary SQL and unrestricted Nexus systems are prohibited;
- authorized reads and approved public research are allowed.

The observed negative Gmail/Calendar beliefs are therefore proven in the session context, not proven as current profile text.

## Reachability and evidence limits

The worker had no active PID at audit time. Logs and receipts do not contain assembled prompts, memory hashes, capability envelopes, or dispatch results. Consequently, a specific historical model token path cannot be reconstructed beyond the persisted context and current source.
